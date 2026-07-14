#!/usr/bin/python3

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QStackedLayout, QComboBox, QFileDialog

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from picamera2.previews.qt import QGlPicamera2

from constants import *
from config import *
from preferences import Prefs
import pickle
from datetime import datetime

try:
    with open("prefs.pkl", "rb") as f:
        prefs = pickle.load(f)
except FileNotFoundError:
    prefs = Prefs()

def post_callback(request):
    metadata.setText(''.join(f"{k}: {v}\n" for k, v in request.get_metadata().items()))

def get_still_file_path():
    return prefs.still_save_directory + f'/IMG_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.jpg'

def get_video_file_path():
    return prefs.video_save_directory + f'/VID_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.h264'

def on_record_button_clicked():
    global recording
    if not recording:
        encoder = H264Encoder(10000000)
        output = FileOutput(get_video_file_path())
        picam2.start_encoder(encoder, output)
        record_button.setText("Stop recording")
        recording = True
    else:
        picam2.stop_encoder()
        record_button.setText("Start recording")
        recording = False

def on_capture_button_clicked():
    capture_button.setEnabled(False)
    cfg = picam2.create_still_configuration(main={"size": prefs.still_resolution})
    picam2.switch_mode_and_capture_file(cfg, get_still_file_path(), signal_function=qpicamera2.signal_done)

def capture_done(job):
    result = picam2.wait(job)
    capture_button.setEnabled(True)

def switch_camera_mode(mode:CameraMode):
    picam2.stop()
    prefs.camera_mode = mode
    change_camera_config(picam2, mode, prefs)
    change_layout(stacked_layout, mode.value)
    if(options_button.text() == "Hide Options"):
        options_button.setText("Show Options")
    picam2.start()

def on_options_button_clicked():
    if(stacked_layout.currentIndex() == 3):
        change_layout(stacked_layout, prefs.camera_mode.value)  # Show current camera mode window
        options_button.setText("Show Options")
    else:
        change_layout(stacked_layout, 3)  # Show options window
        options_button.setText("Hide Options")

def on_select_directory_button_clicked():
    if prefs.camera_mode == CameraMode.VIDEO:
        directory = file_dialog.getExistingDirectory(None, "Select where to save videos...", prefs.video_save_directory)
        if directory:
            prefs.video_save_directory = directory
    elif prefs.camera_mode == CameraMode.STILL:
        directory = file_dialog.getExistingDirectory(None, "Select where to save stills...", prefs.still_save_directory)
        if directory:
            prefs.still_save_directory = directory
    change_prefs(prefs)  # Save updated preferences to file

def on_close():
    picam2.stop()
    app.quit()

app = QApplication([])

metadata = QLabel()
window = QWidget()
recording_window = QWidget()
capture_window = QWidget()
options_window = QWidget()
stacked_layout = QStackedLayout()
layout_h = QHBoxLayout()
layout_v = QVBoxLayout()
file_dialog = QFileDialog()
file_dialog.setFileMode(QFileDialog.Directory)

select_directory_button = QPushButton("Select Save Directory")
select_directory_button.clicked.connect(on_select_directory_button_clicked)
quit_button = QPushButton("Quit")
quit_button.clicked.connect(on_close)
options_button = QPushButton("Show Options")
options_button.clicked.connect(on_options_button_clicked)

record_button = QPushButton("Start recording")
record_button.clicked.connect(on_record_button_clicked)
record_layout_v = QVBoxLayout()
record_layout_v.addWidget(record_button)
recording_window.setLayout(record_layout_v)

capture_button = QPushButton("Capture")
capture_button.clicked.connect(on_capture_button_clicked)
capture_layout_v = QVBoxLayout()
capture_layout_v.addWidget(capture_button)
capture_window.setLayout(capture_layout_v)

options_layout_v = QVBoxLayout()

autofocus_label = QLabel("Autofocus:")
autofocus_combo = QComboBox()
autofocus_combo.addItem("Manual")
autofocus_combo.addItem("Auto")
autofocus_combo.addItem("Continuous")
autofocus_combo.setCurrentIndex(prefs.autofocus_mode.value)
autofocus_combo.currentIndexChanged.connect(lambda index: change_prefs(prefs, autofocus=controls.AfModeEnum(index)))
autofocus_layout_h = QHBoxLayout()
autofocus_layout_h.addWidget(autofocus_label)
autofocus_layout_h.addWidget(autofocus_combo)

autofocus_speed_label = QLabel("Autofocus Speed:")
autofocus_speed_combo = QComboBox()
autofocus_speed_combo.addItem("Normal")
autofocus_speed_combo.addItem("Fast")
autofocus_speed_combo.setCurrentIndex(prefs.autofocus_speed.value)
autofocus_speed_combo.currentIndexChanged.connect(lambda index: change_prefs(prefs, autofocus_speed=controls.AfSpeedEnum(index)))
autofocus_speed_layout_h = QHBoxLayout()
autofocus_speed_layout_h.addWidget(autofocus_speed_label)
autofocus_speed_layout_h.addWidget(autofocus_speed_combo)

autofocus_range_label = QLabel("Autofocus Range:")
autofocus_range_combo = QComboBox()
autofocus_range_combo.addItem("Normal")
autofocus_range_combo.addItem("Macro")
autofocus_range_combo.setCurrentIndex(prefs.autofocus_range.value)
autofocus_range_combo.currentIndexChanged.connect(lambda index: change_prefs(prefs, autofocus_range=controls.AfRangeEnum(index)))
autofocus_range_layout_h = QHBoxLayout()
autofocus_range_layout_h.addWidget(autofocus_range_label)
autofocus_range_layout_h.addWidget(autofocus_range_combo)

options_layout_v.addLayout(autofocus_layout_h)
options_layout_v.addLayout(autofocus_speed_layout_h)
options_layout_v.addLayout(autofocus_range_layout_h)
options_window.setLayout(options_layout_v)

switch_mode_button = QComboBox() 
switch_mode_button.addItem("Stills")
switch_mode_button.addItem("Video")
switch_mode_button.addItem("Timelapse")
switch_mode_button.setCurrentIndex(prefs.camera_mode.value)
switch_mode_button.currentIndexChanged.connect(lambda index: switch_camera_mode(CameraMode(index)))

picam2 = Picamera2()
picam2.post_callback = post_callback
change_camera_config(picam2, prefs.camera_mode, prefs)
qpicamera2 = QGlPicamera2(picam2, width=800, height=480, keep_ar=False)
qpicamera2.done_signal.connect(capture_done)

window.setWindowTitle("Camera")
recording = False

metadata.setFixedWidth(400)
metadata.setAlignment(QtCore.Qt.AlignTop)

layout_v.addWidget(quit_button)
layout_v.addWidget(select_directory_button)
layout_v.addWidget(switch_mode_button)
layout_v.addWidget(options_button)
layout_v.addWidget(metadata)
layout_v.addLayout(stacked_layout)

stacked_layout.addWidget(capture_window)  # Index 0 for Stills
stacked_layout.addWidget(recording_window)   # Index 1 for Video
stacked_layout.addWidget(QLabel("Timelapse mode not implemented yet"))  # Index 2 for Timelapse
stacked_layout.addWidget(options_window)  # Index 3 for Options
stacked_layout.setCurrentIndex(prefs.camera_mode.value)  # Set initial mode based on prefs

layout_h.addWidget(qpicamera2, 80)
layout_h.addLayout(layout_v, 20)
window.setLayout(layout_h)

picam2.start()
window.showMaximized()
app.exec()