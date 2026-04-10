from PyQt5.QtWidgets import QApplication, QLabel
from globals import Globals
from picamera2.previews.qt import QGlPicamera2

GLOBALS = Globals();

app = QApplication([])
qpicamera2 = QGlPicamera2(GLOBALS.PICAM2, width=800, height=600, keep_ar=False)
qpicamera2.setWindowTitle("Qt Picamera2 App")

app = QApplication([])
qpicamera2.show()
app.exec()