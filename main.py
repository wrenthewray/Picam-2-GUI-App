#!/usr/bin/python3

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QStackedLayout, QComboBox, QFileDialog, QTabWidget

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput
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

def is_int(obj):
    return isinstance(obj, int)

def is_tuple(obj):
    return isinstance(obj, tuple) and len(obj) == 2 and all(isinstance(i, int) for i in obj)

def post_callback(request):
    metadata.setText(''.join(f"{k}: {v}\n" for k, v in request.get_metadata().items()))

def get_still_file_path():
    return prefs.still_save_directory + f'/IMG_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.jpg'

def get_video_file_path():
    return prefs.video_save_directory + f'/VID_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.mp4'

def on_record_button_clicked():
    global recording
    if not recording:
        encoder = H264Encoder(prefs.bitrate)
        output = FfmpegOutput(get_video_file_path(), audio=prefs.audio_mode)
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

def on_select_video_aspect_ratio(aspect_ratio: AspectRatio):
    prefs.video_aspect_ratio = aspect_ratio
    video_resolution_stacked_layout.setCurrentIndex(aspect_ratio.value)
    prefs.video_resolution = list(SixteenNineResolution.__dict__.values())[0] if aspect_ratio == AspectRatio.SIXTEEN_BY_NINE else list(FourThreeResolution.__dict__.values())[0] if aspect_ratio == AspectRatio.FOUR_BY_THREE else list(OneOneResolution.__dict__.values())[0]
    change_prefs(prefs)  # Save updated preferences to file

def on_select_still_aspect_ratio(aspect_ratio: AspectRatio):
    prefs.still_aspect_ratio = aspect_ratio
    prefs.still_resolution = list(SixteenNineResolution.__dict__.values())[0] if aspect_ratio == AspectRatio.SIXTEEN_BY_NINE else list(FourThreeResolution.__dict__.values())[0] if aspect_ratio == AspectRatio.FOUR_BY_THREE else list(OneOneResolution.__dict__.values())[0]
    change_prefs(prefs)  # Save updated preferences to file

def on_close():
    picam2.stop()
    app.quit()

app = QApplication([])

bitrate_list = list(filter(is_int, list(BitRate.__dict__.values())))
bitrate_list.pop(0) # Remove the first element of the list as its not one of the specified values
frame_rate_list = list(filter(is_int, list(FrameRate.__dict__.values())))
frame_rate_list.pop(0) # Remove the first element of the list as its not one of the specified values
sixteen_nine_resolutions = list(filter(is_tuple, list(SixteenNineResolution.__dict__.values())))
four_three_resolutions = list(filter(is_tuple, list(FourThreeResolution.__dict__.values())))
one_one_resolutions = list(filter(is_tuple, list(OneOneResolution.__dict__.values())))

metadata = QLabel()
window = QWidget()
recording_window = QWidget()
capture_window = QWidget()
common_options_window = QWidget()
autofocus_options_window = QWidget()
video_options_window = QWidget()
still_options_window = QWidget()
options_tab_window = QTabWidget()
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

autofocus_options_layout_v = QVBoxLayout()

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

autofocus_options_layout_v.addLayout(autofocus_layout_h)
autofocus_options_layout_v.addLayout(autofocus_speed_layout_h)
autofocus_options_layout_v.addLayout(autofocus_range_layout_h)
autofocus_options_window.setLayout(autofocus_options_layout_v)

video_options_layout_v = QVBoxLayout()

preview_frame_rate_label = QLabel("Preview Frame Rate:")
preview_frame_rate_combo = QComboBox()
preview_frame_rate_combo.addItem("12 FPS")
preview_frame_rate_combo.addItem("24 FPS")
preview_frame_rate_combo.addItem("25 FPS")
preview_frame_rate_combo.addItem("30 FPS")
preview_frame_rate_combo.setCurrentIndex(frame_rate_list.index(prefs.preview_frame_rate))
preview_frame_rate_combo.currentIndexChanged.connect(lambda index: change_prefs(prefs, preview_frame_rate=frame_rate_list[index]))
preview_frame_rate_layout_h = QHBoxLayout()
preview_frame_rate_layout_h.addWidget(preview_frame_rate_label)
preview_frame_rate_layout_h.addWidget(preview_frame_rate_combo)
video_options_layout_v.addLayout(preview_frame_rate_layout_h)

video_frame_rate_label = QLabel("Video Frame Rate:")
video_frame_rate_combo = QComboBox()
video_frame_rate_combo.addItem("12 FPS")
video_frame_rate_combo.addItem("24 FPS")
video_frame_rate_combo.addItem("25 FPS")
video_frame_rate_combo.addItem("30 FPS")
video_frame_rate_combo.setCurrentIndex(frame_rate_list.index(prefs.video_frame_rate))
video_frame_rate_combo.currentIndexChanged.connect(lambda index: change_prefs(prefs, video_frame_rate=frame_rate_list[index]))
video_frame_rate_layout_h = QHBoxLayout()
video_frame_rate_layout_h.addWidget(video_frame_rate_label)
video_frame_rate_layout_h.addWidget(video_frame_rate_combo)
video_options_layout_v.addLayout(video_frame_rate_layout_h)

video_bitrate_label = QLabel("Bitrate:")
video_bitrate_combo = QComboBox()
video_bitrate_combo.addItem("10.24 Mbps")
video_bitrate_combo.addItem("20.48 Mbps")
video_bitrate_combo.addItem("45 Mbps")
video_bitrate_combo.addItem("60 Mbps")
video_bitrate_combo.setCurrentIndex(bitrate_list.index(prefs.bitrate))
video_bitrate_combo.currentIndexChanged.connect(lambda index: change_prefs(prefs, bitrate=bitrate_list[index]))
video_bitrate_layout_h = QHBoxLayout()
video_bitrate_layout_h.addWidget(video_bitrate_label)
video_bitrate_layout_h.addWidget(video_bitrate_combo)
video_options_layout_v.addLayout(video_bitrate_layout_h)

video_aspect_ratio_label = QLabel("Aspect Ratio:")
video_aspect_ratio_combo = QComboBox()
video_aspect_ratio_combo.addItem("16:9")
video_aspect_ratio_combo.addItem("4:3")
video_aspect_ratio_combo.addItem("1:1")
video_aspect_ratio_combo.setCurrentIndex(prefs.video_aspect_ratio.value)
video_aspect_ratio_combo.currentIndexChanged.connect(lambda index: on_select_video_aspect_ratio(AspectRatio(index)))
video_aspect_ratio_layout_h = QHBoxLayout()
video_aspect_ratio_layout_h.addWidget(video_aspect_ratio_label)
video_aspect_ratio_layout_h.addWidget(video_aspect_ratio_combo)
video_options_layout_v.addLayout(video_aspect_ratio_layout_h)

video_resolution_stacked_layout = QStackedLayout()
video_resolution_combo_16_9 = QComboBox()
video_resolution_combo_16_9.addItem("3840x2160 (4K)")
video_resolution_combo_16_9.addItem("2560x1440 (QHD)")
video_resolution_combo_16_9.addItem("1920x1080 (HD)")
video_resolution_combo_16_9.addItem("1280x720 (SD)")
video_resolution_combo_16_9.addItem("960x540 (qHD)")
video_resolution_combo_16_9.setCurrentIndex(sixteen_nine_resolutions.index(prefs.video_resolution) if prefs.video_aspect_ratio == AspectRatio.SIXTEEN_BY_NINE and prefs.video_resolution in sixteen_nine_resolutions else 0)
video_resolution_combo_16_9.currentIndexChanged.connect(lambda index: change_prefs(prefs, video_resolution=sixteen_nine_resolutions[index]))
video_resolution_combo_4_3 = QComboBox()
video_resolution_combo_4_3.addItem("3840x2880 (4K)")
video_resolution_combo_4_3.addItem("3200x2400 (QUXGA)")
video_resolution_combo_4_3.addItem("2048x1536 (QXGA)")
video_resolution_combo_4_3.addItem("1600x1200 (UXGA)")
video_resolution_combo_4_3.addItem("1280x960")
video_resolution_combo_4_3.addItem("1024x768 (XGA)")
video_resolution_combo_4_3.addItem("800x600 (SVGA)")
video_resolution_combo_4_3.addItem("640x480 (VGA)")
video_resolution_combo_4_3.setCurrentIndex(four_three_resolutions.index(prefs.video_resolution) if prefs.video_aspect_ratio == AspectRatio.FOUR_BY_THREE and prefs.video_resolution in four_three_resolutions else 0)
video_resolution_combo_4_3.currentIndexChanged.connect(lambda index: change_prefs(prefs, video_resolution=four_three_resolutions[index]))
video_resolution_combo_1_1 = QComboBox()
video_resolution_combo_1_1.addItem("3840x3840 (4K)")
video_resolution_combo_1_1.addItem("2560x2560 (QHD)")
video_resolution_combo_1_1.addItem("1920x1920 (HD)")
video_resolution_combo_1_1.addItem("1280x1280 (SD)")
video_resolution_combo_1_1.addItem("960x960 (qHD)")
video_resolution_combo_1_1.setCurrentIndex(one_one_resolutions.index(prefs.video_resolution) if prefs.video_aspect_ratio == AspectRatio.ONE_BY_ONE and prefs.video_resolution in one_one_resolutions else 0)
video_resolution_combo_1_1.currentIndexChanged.connect(lambda index: change_prefs(prefs, video_resolution=one_one_resolutions[index]))
video_resolution_stacked_layout.addWidget(video_resolution_combo_16_9)
video_resolution_stacked_layout.addWidget(video_resolution_combo_4_3)
video_resolution_stacked_layout.addWidget(video_resolution_combo_1_1)
video_resolution_stacked_layout.setCurrentIndex(prefs.video_aspect_ratio.value)
video_options_layout_v.addLayout(video_resolution_stacked_layout)
video_options_window.setLayout(video_options_layout_v)

options_tab_window.addTab(autofocus_options_window, "Autofocus")
options_tab_window.addTab(video_options_window, "Video")

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
stacked_layout.addWidget(options_tab_window)  # Index 3 for Options
stacked_layout.setCurrentIndex(prefs.camera_mode.value)  # Set initial mode based on prefs

layout_h.addWidget(qpicamera2, 9)
layout_h.addLayout(layout_v, 0)
window.setLayout(layout_h)

picam2.start()
window.showMaximized()
app.exec()