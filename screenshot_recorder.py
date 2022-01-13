from PyQt5.QtCore import *
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import os
import sys


class VideoWindow(QMainWindow):
    """ From https://pythonprogramminglanguage.com/pyqt5-video-widget/"""
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
        openAction.triggered.connect(self.openFile)

        # Create exit action
        exitAction = QAction(QIcon('exit.png'), '&Exit', self)        
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.exitCall)

        # Create menu bar and add action
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        #fileMenu.addAction(newAction)
        fileMenu.addAction(openAction)
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

        self.mediaPlayer.setVideoOutput(self.videoWidget)
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
        self.grabber = VideoFrameGrabber(self.videoWidget, self)
        self._grabbing = False

    def openFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Movie", QDir.homePath())

        if fileName != '':
            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(fileName)))
            self.playButton.setEnabled(True)
            self.speedupButton.setEnabled(True)
            self.slowdownButton.setEnabled(True)
            self.normspeedButton.setEnabled(True)
            self._current_playbackrate = 1
            self.video_name = os.path.splitext(os.path.basename(fileName))[0]
            self.video_path = f'{os.path.dirname(fileName)}/{self.video_name}'
            self.folder.file.setText(self.video_path)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_S:
            self.save_frame()

    def save_frame(self):
        self.mediaPlayer.pause()
        self.mediaPlayer.setVideoOutput(self.grabber)
        self._grabbing = True
        self.grabber.frameAvailable.connect(self.process_frame)

    def process_frame(self, frame: QImage):
        if not os.path.exists(self.folder.file.text()):
            os.mkdir(self.folder.file.text())
        t_milliseconds = self.mediaPlayer.position()
        file_name = f'{self.folder.file.text()}/{t_milliseconds}.png'
        frame.save(file_name)
        self.play()

    def exitCall(self):
        sys.exit(app.exec_())

    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
            if self._grabbing:
                self.mediaPlayer.setVideoOutput(self.videoWidget)
                self._grabbing = False

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
    frameAvailable = pyqtSignal(QImage)

    def __init__(self, widget: QWidget, parent: QObject):
        super().__init__(parent)

        self.widget = widget
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

    def isFormatSupported(self, format):
        imageFormat = QVideoFrame.imageFormatFromPixelFormat(format.pixelFormat())
        size = format.frameSize()

        return imageFormat != QImage.Format_Invalid and not size.isEmpty() and \
               format.handleType() == QAbstractVideoBuffer.NoHandle

    def start(self, format: QVideoSurfaceFormat):
        imageFormat = QVideoFrame.imageFormatFromPixelFormat(format.pixelFormat())
        size = format.frameSize()

        if imageFormat != QImage.Format_Invalid and not size.isEmpty():
            self.imageFormat = imageFormat
            self.imageSize = size
            self.sourceRect = format.viewport()

            super().start(format)

            self.widget.updateGeometry()
            self.updateVideoRect()

            return True
        else:
            return False

    def stop(self):
        self.currentFrame = QVideoFrame()
        self.targetRect = QRect()

        super().stop()

        self.widget.update()

    def present(self, frame):
        if frame.isValid():
            cloneFrame = QVideoFrame(frame)
            cloneFrame.map(QAbstractVideoBuffer.ReadOnly)
            image = QImage(cloneFrame.bits(), cloneFrame.width(), cloneFrame.height(),
                           QVideoFrame.imageFormatFromPixelFormat(cloneFrame.pixelFormat()))
            self.frameAvailable.emit(image)  # this is very important
            cloneFrame.unmap()

        if self.surfaceFormat().pixelFormat() != frame.pixelFormat() or \
                self.surfaceFormat().frameSize() != frame.size():
            self.setError(QAbstractVideoSurface.IncorrectFormatError)
            self.stop()

            return False
        else:
            self.currentFrame = frame
            self.widget.repaint(self.targetRect)

            return True

    def updateVideoRect(self):
        size = self.surfaceFormat().sizeHint()
        size.scale(self.widget.size().boundedTo(size), Qt.KeepAspectRatio)

        self.targetRect = QRect(QPoint(0, 0), size)
        self.targetRect.moveCenter(self.widget.rect().center())

    def paint(self, painter):
        if self.currentFrame.map(QAbstractVideoBuffer.ReadOnly):
            oldTransform = self.painter.transform()

        if self.surfaceFormat().scanLineDirection() == QVideoSurfaceFormat.BottomToTop:
            self.painter.scale(1, -1)
            self.painter.translate(0, -self.widget.height())

        image = QImage(self.currentFrame.bits(), self.currentFrame.width(), self.currentFrame.height(),
                       self.currentFrame.bytesPerLine(), self.imageFormat)

        self.painter.drawImage(self.targetRect, image, self.sourceRect)

        self.painter.setTransform(oldTransform)

        self.currentFrame.unmap()


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
        self.file.setPlaceholderText('C:\\\\Path\\to\\where_videos\\will_be_saved\\')
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoWindow()
    player.resize(640, 480)
    player.show()
    sys.exit(app.exec_())