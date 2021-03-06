from PyQt5.QtCore import *
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import os
import sys
import shutil
from subprocess import Popen, PIPE, STDOUT
import re
sys.path = [os.path.join(os.path.dirname(__file__), 'ffmpeg')] + sys.path
os.environ['PATH'] = ';'.join(sys.path)


class NoFFMPEG(QMessageBox):
    def __init__(self):
        super(NoFFMPEG, self).__init__()
        self.setText("WARNING: ffmpeg has not been found. Please install it to be able to create a de-interlaced "
                     "version of this video.")


class VideoConverter(QObject):
    update_status = pyqtSignal(int)
    started = pyqtSignal()
    finished = pyqtSignal(str)
    set_duration = pyqtSignal(int)
    no_ffmpeg = pyqtSignal()

    def __init__(self):
        #  TODO: add relative directory that may have ffmpeg so that it can be packaged with this script
        super(VideoConverter, self).__init__()
        self.time_regex = re.compile('.*time=(\d+):(\d+):(\d+).(\d+).*')
        self.loading_bar = QProgressBar()
        self.loading_bar.setWindowTitle("Converting to mp4 with deinterlacing")
        self.loading_bar.setMinimum(0)
        self.loading_bar.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.loading_bar.resize(500, 25)
        self.update_status.connect(self.loading_bar.setValue)
        self.started.connect(self.loading_bar.show)
        self.finished.connect(lambda x: self.loading_bar.hide())
        self.set_duration.connect(self.loading_bar.setMaximum)
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.start()
        self.no_ffmpeg_warning = NoFFMPEG()
        self.no_ffmpeg.connect(self.no_ffmpeg_warning.exec)

    @pyqtSlot(str, int)
    def do_conversion(self, video_file: str, duration: int) -> None:
        check = shutil.which('ffmpeg')
        if not check:
            self.no_ffmpeg.emit()
            return

        filename = os.path.basename(video_file)
        new_name = f'{os.path.splitext(filename)[0]}_conv.mp4'
        new_filepath = os.path.join(os.path.dirname(video_file), new_name)
        p = Popen(["ffmpeg", "-i", video_file, '-vf', 'yadif', new_filepath],
                  stdout=PIPE,
                  stderr=STDOUT)
        output = iter(lambda: p.stdout.read(1).decode('ascii'), str)
        buffer = ''
        self.set_duration.emit(duration)
        self.started.emit()
        while p.poll() is None:
            c = next(output)
            if c != '\r':
                buffer += c
            else:
                timestamp = re.findall(self.time_regex, buffer)
                if timestamp:
                    timestamp = timestamp[0]
                    h = float(timestamp[0])
                    m = float(timestamp[1])
                    s = float(timestamp[2]) + float(timestamp[3])/100
                    ms = int(h*60*60*1000 + m*60*1000 + s*1000)
                    self.update_status.emit(ms)
                buffer = ''
        self.finished.emit(new_filepath)


class VideoWindow(QMainWindow):
    """ From https://pythonprogramminglanguage.com/pyqt5-video-widget/"""
    start_conversion = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super(VideoWindow, self).__init__(parent)
        self.setWindowTitle("Screenshot Recorder")

        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.videoWidget = QVideoWidget()

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        self.speedupButton = QPushButton()
        self.speedupButton.setEnabled(False)
        self.speedupButton.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekForward))
        self.speedupButton.clicked.connect(self.speed_up)

        self.slowdownButton = QPushButton()
        self.slowdownButton.setEnabled(False)
        self.slowdownButton.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekBackward))
        self.slowdownButton.clicked.connect(self.slow_down)

        self.normspeedButton = QPushButton()
        self.normspeedButton.setEnabled(False)
        self.normspeedButton.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.normspeedButton.clicked.connect(self.norm_speed)

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        self.errorLabel = QLabel()
        self.errorLabel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        # Create new action
        openAction = QAction(QIcon('open.png'), '&Open', self)        
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open movie')
        openAction.triggered.connect(self.open_file)

        self.convertAction = QAction("Create deinterlaced video", self)
        self.convertAction.triggered.connect(self.convert_video)
        self.convertAction.setEnabled(False)

        # Create exit action
        exitAction = QAction(QIcon('exit.png'), '&Exit', self)        
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.exitCall)

        # Create menu bar and add action
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(self.convertAction)
        fileMenu.addAction(exitAction)

        # Create a widget for window contents
        wid = QWidget(self)
        self.setCentralWidget(wid)

        # Create layouts to place inside widget
        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.slowdownButton)
        controlLayout.addWidget(self.normspeedButton)
        controlLayout.addWidget(self.speedupButton)
        controlLayout.addWidget(self.positionSlider)

        layout = QVBoxLayout()
        layout.setSpacing(0)

        layout.addWidget(self.videoWidget)
        layout.addLayout(controlLayout)

        # Set widget to contain window contents
        wid.setLayout(layout)
        self.grabber = VideoFrameGrabber(self)
        self.mediaPlayer.setVideoOutput([self.videoWidget.videoSurface(), self.grabber])
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)

        self._default_playbackrate = 1
        self._current_playbackrate = None
        self.videoWidget.setMinimumSize(500, 500)

        layout.addWidget(self.errorLabel)
        layout.setAlignment(Qt.AlignBottom)
        self.folder = FolderSelector()
        layout.addWidget(self.folder)

        hint = QLabel()
        hint.setText('Press S to save a screenshot to the folder displayed above.')
        layout.addWidget(hint)

        self.video_name = None
        self.video_path = None
        self.file_name = ''
        self.grabber.frameAvailable.connect(self.process_frame)
        self.converter = VideoConverter()
        self.start_conversion.connect(self.converter.do_conversion)
        self.converter.finished.connect(self.open_file)

    def convert_video(self):
        if not self.file_name:
            return
        self.start_conversion.emit(self.file_name, self.mediaPlayer.duration())

    def open_file(self, vid_file: str = None):
        if vid_file:
            file_name = vid_file
        else:
            file_name, _ = QFileDialog.getOpenFileName(self, "Open Movie", QDir.homePath())
        self.file_name = file_name
        if file_name != '':
            self.mediaPlayer.stop()
            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(file_name)))
            self.playButton.setEnabled(True)
            self.speedupButton.setEnabled(True)
            self.slowdownButton.setEnabled(True)
            self.normspeedButton.setEnabled(True)
            self._current_playbackrate = 1
            self.video_name = os.path.splitext(os.path.basename(file_name))[0]
            self.video_path = f'{os.path.dirname(file_name)}/{self.video_name}'
            self.folder.file.setText(self.video_path)
            self.convertAction.setEnabled(True)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_S:
            self.grabber.save_image()

    def process_frame(self, frame: QImage, timestamp: int):
        is_playing = self.mediaPlayer.state()
        self.mediaPlayer.pause()
        if not os.path.exists(self.folder.get_path()):
            os.mkdir(self.folder.get_path())
        file_name = f'{self.folder.get_path()}/{timestamp}.png'
        frame.save(file_name)
        if is_playing == QMediaPlayer.PlayingState:
            self.mediaPlayer.play()

    def exitCall(self):
        self.close()

    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def slow_down(self):
        self._current_playbackrate = self._current_playbackrate * 0.5
        self.mediaPlayer.setPlaybackRate(self._current_playbackrate)

    def speed_up(self):
        self._current_playbackrate = self._current_playbackrate * 2
        self.mediaPlayer.setPlaybackRate(self._current_playbackrate)

    def norm_speed(self):
        self.mediaPlayer.setPlaybackRate(self._default_playbackrate)
        self._current_playbackrate = self._default_playbackrate

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(
                    self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(
                    self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        self.positionSlider.setValue(position)

    def durationChanged(self, duration):
        self.positionSlider.setRange(0, duration)

    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def handleError(self):
        self.playButton.setEnabled(False)
        self.errorLabel.setText("Error: " + self.mediaPlayer.errorString())


class VideoFrameGrabber(QAbstractVideoSurface):
    """ From https://stackoverflow.com/questions/55349153/pyqt5-grabbing-current-frame-displays-blank"""
    frameAvailable = pyqtSignal(QImage, int)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._grab_frame = False

    def supportedPixelFormats(self, handleType):
        return [QVideoFrame.Format_ARGB32, QVideoFrame.Format_ARGB32_Premultiplied,
                QVideoFrame.Format_RGB32, QVideoFrame.Format_RGB24, QVideoFrame.Format_RGB565,
                QVideoFrame.Format_RGB555, QVideoFrame.Format_ARGB8565_Premultiplied,
                QVideoFrame.Format_BGRA32, QVideoFrame.Format_BGRA32_Premultiplied, QVideoFrame.Format_BGR32,
                QVideoFrame.Format_BGR24, QVideoFrame.Format_BGR565, QVideoFrame.Format_BGR555,
                QVideoFrame.Format_BGRA5658_Premultiplied, QVideoFrame.Format_AYUV444,
                QVideoFrame.Format_AYUV444_Premultiplied, QVideoFrame.Format_YUV444,
                QVideoFrame.Format_YUV420P, QVideoFrame.Format_YV12, QVideoFrame.Format_UYVY,
                QVideoFrame.Format_YUYV, QVideoFrame.Format_NV12, QVideoFrame.Format_NV21,
                QVideoFrame.Format_IMC1, QVideoFrame.Format_IMC2, QVideoFrame.Format_IMC3,
                QVideoFrame.Format_IMC4, QVideoFrame.Format_Y8, QVideoFrame.Format_Y16,
                QVideoFrame.Format_Jpeg, QVideoFrame.Format_CameraRaw, QVideoFrame.Format_AdobeDng]

    def present(self, frame: QVideoFrame):
        if frame.isValid():
            frame = QVideoFrame(frame)
            frame.map(QAbstractVideoBuffer.ReadOnly)
            image = QImage(frame.bits(), frame.width(), frame.height(), frame.bytesPerLine(), QVideoFrame.imageFormatFromPixelFormat(frame.pixelFormat()))
            if self._grab_frame:
                self.frameAvailable.emit(image, frame.startTime())  # this is very important
                self._grab_frame = False
        return True

    def save_image(self):
        self._grab_frame = True


class FolderSelector(QWidget):
    """
    Widget with a LineEdit and a button to the right for selecting either a folder or a file
    """
    def __init__(self):
        """
        :param folder: whether or not to ask for a folder or a file
        """
        super(FolderSelector, self).__init__()
        self.setLayout(QHBoxLayout())
        self.file = QLineEdit()
        self.file.setMinimumWidth(500)
        self.file.setPlaceholderText('C:\\\\Path\\to\\where_images\\will_be_saved\\')
        self.find_btn = QPushButton('Select Folder')
        self.find_btn.clicked.connect(self.select_folder)
        self.layout().addWidget(self.file)
        self.layout().addWidget(self.find_btn)

    def select_folder(self):
        """
        Called when the button is pushed. Fills the LineEdit with the folder/file selected.
        :return:
        """
        file = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.file.setText(file)

    def get_path(self):
        """
        :return: the text in the LineEdit
        """
        return self.file.text()
