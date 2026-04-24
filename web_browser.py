from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
import sys

class Main(QMainWindow):
    def __init__(self):
        super(Main, self).__init__()
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl('http://localhost:8090'))  # Fixed: was loadUrl(), which doesn't exist
        self.setCentralWidget(self.browser)                 # Fixed: was setControlWidget(), which doesn't exist
        self.showMaximized()

app = QApplication(sys.argv)
QApplication.setApplicationName("SwordFish")
window = Main()
app.exec_()  # Fixed: missing event loop — without this the window closes instantly