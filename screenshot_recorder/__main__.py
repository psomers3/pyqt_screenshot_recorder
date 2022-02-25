from PyQt5.QtWidgets import *
from screenshot_recorder import VideoWindow
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoWindow()
    player.resize(640, 480)
    player.show()
    sys.exit(app.exec())
