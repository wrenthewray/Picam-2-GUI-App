from PyQt5.QtWidgets import QApplication, QLabel
from picamera2 import Picamera2
from picamera2.previews.qt import QGlPicamera2, QPicamera2

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (800, 600)}))

app = QApplication([])
qpicamera2 = QPicamera2(picam2, width=800, height=600, keep_ar=False)
qpicamera2.setWindowTitle("Qt Picamera2 App")

picam2.start()
qpicamera2.show()
app.exec()