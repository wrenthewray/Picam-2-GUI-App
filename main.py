#!/usr/bin/python3

from PyQt5 import QtCore
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton, 
    QVBoxLayout, QWidget, QStackedLayout, QComboBox, QFileDialog, QTabWidget, 
    QMainWindow, QMenu, QToolBar, QAction, QDockWidget, QSizePolicy, QStackedWidget)

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput
from picamera2.previews.qt import QGlPicamera2

from constants import *
from config import *
from preferences import Prefs
import pickle
from datetime import datetime
prefs = Prefs()
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
    change_prefs(prefs, camera_mode=mode)
    change_camera_config(picam2, mode, prefs)
    change_layout(stacked_layout, mode.value)

    picam2.start()

def on_options_button_clicked():
    if(picam_stacked_layout.currentIndex() == 1):
        change_layout(picam_stacked_layout, 0)  # Show current camera mode window
    else:
        change_layout(picam_stacked_layout, 1)  # Show options window

def on_select_video_directory():
    directory = file_dialog.getExistingDirectory(None, "Select where to save videos...", prefs.video_save_directory)
    if directory:
        prefs.video_save_directory = directory
    change_prefs(prefs)  # Save updated preferences to file

def on_select_stills_directory():
    directory = file_dialog.getExistingDirectory(None, "Select where to save stills...", prefs.still_save_directory)
    if directory:
        prefs.still_save_directory = directory
    change_prefs(prefs)  # Save updated preferences to file

def on_select_video_aspect_ratio(aspect_ratio: AspectRatio):
    global prefs
    prefs.video_aspect_ratio = aspect_ratio
    video_resolution_stacked_layout.setCurrentIndex(aspect_ratio.value)
    if aspect_ratio == AspectRatio.FOUR_BY_THREE:
        prefs.video_resolution = FourThreeResolution.FOUR_THREE_ASPECT_RATIO_1280_960
        video_resolution_combo_4_3.setCurrentIndex(four_three_resolutions.index(prefs.video_resolution) )
    elif aspect_ratio == AspectRatio.ONE_BY_ONE:
        prefs.video_resolution = OneOneResolution.ONE_ONE_ASPECT_RATIO_HD
        video_resolution_combo_1_1.setCurrentIndex(one_one_resolutions.index(prefs.video_resolution))
    else:
        prefs.video_resolution = SixteenNineResolution.SIXTEEN_NINE_ASPECT_RATIO_HD
        video_resolution_combo_16_9.setCurrentIndex(sixteen_nine_resolutions.index(prefs.video_resolution) )

def on_select_still_aspect_ratio(aspect_ratio: AspectRatio):
    global prefs
    prefs.still_aspect_ratio = aspect_ratio
    still_resolution_stacked_layout.setCurrentIndex(aspect_ratio.value)
    if aspect_ratio == AspectRatio.FOUR_BY_THREE:
        prefs.still_resolution = FourThreeResolution.FOUR_THREE_ASPECT_RATIO_1280_960
        still_resolution_combo_4_3.setCurrentIndex(four_three_resolutions.index(prefs.still_resolution) )
    elif aspect_ratio == AspectRatio.ONE_BY_ONE:
        prefs.still_resolution = OneOneResolution.ONE_ONE_ASPECT_RATIO_HD
        still_resolution_combo_1_1.setCurrentIndex(one_one_resolutions.index(prefs.still_resolution))
    else:
        prefs.still_resolution = SixteenNineResolution.SIXTEEN_NINE_ASPECT_RATIO_HD
        still_resolution_combo_16_9.setCurrentIndex(sixteen_nine_resolutions.index(prefs.still_resolution) )

def on_select_video_resolution(resolution: tuple):
    change_prefs(prefs, video_resolution=resolution)
    change_controls(picam2, prefs)
    change_camera_config(picam2, CameraMode.VIDEO, prefs)

def on_select_video_framerate(frame_rate):
    change_prefs(prefs, video_frame_rate=frame_rate)
    change_controls(picam2, prefs)
    change_camera_config(picam2, CameraMode.VIDEO, prefs)

def on_select_preview_framerate(frame_rate):
    change_prefs(prefs, preview_frame_rate=frame_rate)
    change_controls(picam2, prefs)
    change_camera_config(picam2, CameraMode.VIDEO, prefs)

def on_select_still_resolution(resolution: tuple):
    change_prefs(prefs, still_resolution=resolution)
    change_controls(picam2, prefs)
    change_camera_config(picam2, CameraMode.STILL, prefs)

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
window = QMainWindow()
dock_widget = QWidget()
file_menu = QMenu("File")
main_toolbar = QToolBar()

button_size_policy = QSizePolicy()
button_size_policy.setVerticalPolicy(QSizePolicy.Maximum)
button_size_policy.setVerticalStretch(1)
button_size_policy.setHorizontalPolicy(QSizePolicy.Maximum)
button_size_policy.setHorizontalStretch(1)

layout_size_policy = QSizePolicy()
layout_size_policy.setVerticalPolicy(QSizePolicy.Minimum)
layout_size_policy.setVerticalStretch(1)
layout_size_policy.setHorizontalPolicy(QSizePolicy.Minimum)
layout_size_policy.setHorizontalStretch(1)

recording_window = QWidget()
capture_window = QWidget()

common_options_window = QWidget()
video_options_window = QWidget()
still_options_window = QWidget()

options_tab_window = QTabWidget()
stacked_layout = QStackedLayout()
layout_h = QHBoxLayout()
capture_dock_widget = QDockWidget()
layout_v = QVBoxLayout()
picam_widget = QWidget()
picam_stacked_layout = QStackedLayout()
picam_widget.setLayout(picam_stacked_layout)

file_dialog = QFileDialog()
file_dialog.setFileMode(QFileDialog.Directory)

select_video_directory_action = QAction("Select Video Path")
select_video_directory_action.triggered.connect(on_select_video_directory)
file_menu.addAction(select_video_directory_action)

select_stills_directory_action = QAction("Select Photo Path")
select_stills_directory_action.triggered.connect(on_select_stills_directory)
file_menu.addAction(select_stills_directory_action)

quit_action = QAction("Quit")
quit_action.triggered.connect(on_close)
file_menu.addSeparator()
file_menu.addAction(quit_action)

options_action = QAction("Settings")
options_action.triggered.connect(on_options_button_clicked)

record_button = QPushButton("Start recording")
record_button.clicked.connect(on_record_button_clicked)
record_button.setSizePolicy(button_size_policy)

capture_button = QPushButton("Capture")
capture_button.clicked.connect(on_capture_button_clicked)
capture_button.setSizePolicy(button_size_policy)

video_options_layout_v = QVBoxLayout()

preview_frame_rate_label = QLabel("Preview Frame Rate:")
preview_frame_rate_combo = QComboBox()
preview_frame_rate_combo.addItem("12 FPS")
preview_frame_rate_combo.addItem("24 FPS")
preview_frame_rate_combo.addItem("25 FPS")
preview_frame_rate_combo.addItem("30 FPS")
preview_frame_rate_combo.setCurrentIndex(frame_rate_list.index(prefs.preview_frame_rate))
preview_frame_rate_combo.currentIndexChanged.connect(lambda index: on_select_preview_framerate(frame_rate_list[index]))
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
video_frame_rate_combo.currentIndexChanged.connect(lambda index: on_select_video_framerate(frame_rate_list[index]))
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

video_aspect_ratio_label = QLabel("Sideo Aspect Ratio:")
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

video_resolution_label = QLabel("Video Resolution:")
video_resolution_stacked_layout = QStackedWidget()

video_resolution_combo_16_9 = QComboBox()
video_resolution_combo_16_9.addItem("3840x2160 (4K)")
video_resolution_combo_16_9.addItem("2560x1440 (QHD)")
video_resolution_combo_16_9.addItem("1920x1080 (HD)")
video_resolution_combo_16_9.addItem("1280x720 (SD)")
video_resolution_combo_16_9.addItem("960x540 (qHD)")
video_resolution_combo_16_9.addItem("640x480 (480p)")
video_resolution_combo_16_9.setCurrentIndex(sixteen_nine_resolutions.index(prefs.video_resolution) if prefs.video_aspect_ratio == AspectRatio.SIXTEEN_BY_NINE and prefs.video_resolution in sixteen_nine_resolutions else 0)
video_resolution_combo_16_9.currentIndexChanged.connect(lambda index: on_select_video_resolution(sixteen_nine_resolutions[index]))

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
video_resolution_combo_4_3.currentIndexChanged.connect(lambda index: on_select_video_resolution(four_three_resolutions[index]))

video_resolution_combo_1_1 = QComboBox()
video_resolution_combo_1_1.addItem("3840x3840 (4K)")
video_resolution_combo_1_1.addItem("2560x2560 (QHD)")
video_resolution_combo_1_1.addItem("1920x1920 (HD)")
video_resolution_combo_1_1.addItem("1280x1280 (SD)")
video_resolution_combo_1_1.addItem("960x960 (qHD)")
video_resolution_combo_1_1.setCurrentIndex(one_one_resolutions.index(prefs.video_resolution) if prefs.video_aspect_ratio == AspectRatio.ONE_BY_ONE and prefs.video_resolution in one_one_resolutions else 0)
video_resolution_combo_1_1.currentIndexChanged.connect(lambda index: on_select_video_resolution(one_one_resolutions[index]))

video_resolution_stacked_layout.addWidget(video_resolution_combo_16_9)
video_resolution_stacked_layout.addWidget(video_resolution_combo_4_3)
video_resolution_stacked_layout.addWidget(video_resolution_combo_1_1)
video_resolution_stacked_layout.setCurrentIndex(prefs.video_aspect_ratio.value)

video_resolution_layout_h = QHBoxLayout()
video_resolution_layout_h.addWidget(video_resolution_label)
video_resolution_layout_h.addWidget(video_resolution_stacked_layout)
video_options_layout_v.addLayout(video_resolution_layout_h)

still_aspect_ratio_label = QLabel("Still Aspect Ratio:")
still_aspect_ratio_combo = QComboBox()
still_aspect_ratio_combo.addItem("16:9")
still_aspect_ratio_combo.addItem("4:3")
still_aspect_ratio_combo.addItem("1:1")
still_aspect_ratio_combo.setCurrentIndex(prefs.still_aspect_ratio.value)
still_aspect_ratio_combo.currentIndexChanged.connect(lambda index: on_select_still_aspect_ratio(AspectRatio(index)))
still_aspect_ratio_layout_h = QHBoxLayout()
still_aspect_ratio_layout_h.addWidget(still_aspect_ratio_label)
still_aspect_ratio_layout_h.addWidget(still_aspect_ratio_combo)
video_options_layout_v.addLayout(still_aspect_ratio_layout_h)

still_resolution_label = QLabel("Still Resolution:")
still_resolution_stacked_layout = QStackedWidget()

still_resolution_combo_16_9 = QComboBox()
still_resolution_combo_16_9.addItem("3840x2160 (4K)")
still_resolution_combo_16_9.addItem("2560x1440 (QHD)")
still_resolution_combo_16_9.addItem("1920x1080 (HD)")
still_resolution_combo_16_9.addItem("1280x720 (SD)")
still_resolution_combo_16_9.addItem("960x540 (qHD)")
still_resolution_combo_16_9.addItem("640x480 (480p)")
still_resolution_combo_16_9.setCurrentIndex(sixteen_nine_resolutions.index(prefs.still_resolution) if prefs.still_aspect_ratio == AspectRatio.SIXTEEN_BY_NINE and prefs.still_resolution in sixteen_nine_resolutions else 0)
still_resolution_combo_16_9.currentIndexChanged.connect(lambda index: on_select_still_resolution(sixteen_nine_resolutions[index]))

still_resolution_combo_4_3 = QComboBox()
still_resolution_combo_4_3.addItem("3840x2880 (4K)")
still_resolution_combo_4_3.addItem("3200x2400 (QUXGA)")
still_resolution_combo_4_3.addItem("2048x1536 (QXGA)")
still_resolution_combo_4_3.addItem("1600x1200 (UXGA)")
still_resolution_combo_4_3.addItem("1280x960")
still_resolution_combo_4_3.addItem("1024x768 (XGA)")
still_resolution_combo_4_3.addItem("800x600 (SVGA)")
still_resolution_combo_4_3.addItem("640x480 (VGA)")
still_resolution_combo_4_3.setCurrentIndex(four_three_resolutions.index(prefs.still_resolution) if prefs.still_aspect_ratio == AspectRatio.FOUR_BY_THREE and prefs.still_resolution in four_three_resolutions else 0)
still_resolution_combo_4_3.currentIndexChanged.connect(lambda index: on_select_still_resolution(four_three_resolutions[index]))

still_resolution_combo_1_1 = QComboBox()
still_resolution_combo_1_1.addItem("3840x3840 (4K)")
still_resolution_combo_1_1.addItem("2560x2560 (QHD)")
still_resolution_combo_1_1.addItem("1920x1920 (HD)")
still_resolution_combo_1_1.addItem("1280x1280 (SD)")
still_resolution_combo_1_1.addItem("960x960 (qHD)")
still_resolution_combo_1_1.setCurrentIndex(one_one_resolutions.index(prefs.still_resolution) if prefs.video_aspect_ratio == AspectRatio.ONE_BY_ONE and prefs.still_resolution in one_one_resolutions else 0)
still_resolution_combo_1_1.currentIndexChanged.connect(lambda index: on_select_video_resolution(one_one_resolutions[index]))

still_resolution_stacked_layout.addWidget(still_resolution_combo_16_9)
still_resolution_stacked_layout.addWidget(still_resolution_combo_4_3)
still_resolution_stacked_layout.addWidget(still_resolution_combo_1_1)
still_resolution_stacked_layout.setCurrentIndex(prefs.still_aspect_ratio.value)

still_resolution_layout_h = QHBoxLayout()
still_resolution_layout_h.addWidget(still_resolution_label)
still_resolution_layout_h.addWidget(still_resolution_stacked_layout)

video_options_layout_v.addLayout(still_resolution_layout_h)
video_options_window.setLayout(video_options_layout_v)

options_tab_window.addTab(video_options_window, "Video")

switch_mode_button = QComboBox() 
switch_mode_button.addItem("Stills")
switch_mode_button.addItem("Video")
switch_mode_button.addItem("Timelapse")
switch_mode_button.setCurrentIndex(prefs.camera_mode.value)
switch_mode_button.currentIndexChanged.connect(lambda index: switch_camera_mode(CameraMode(index)))

picam2 = Picamera2()
picam2.post_callback = post_callback
qpicamera2 = QGlPicamera2(picam2, width=800, height=480, keep_ar=True)
qpicamera2.done_signal.connect(capture_done)

window.setWindowTitle("Camera")
recording = False

metadata.setFixedWidth(100)
metadata.setAlignment(QtCore.Qt.AlignTop)

main_toolbar.addWidget(QLabel("Camera Mode: "))
main_toolbar.addWidget(switch_mode_button)
main_toolbar.addAction(options_action)

dock_widget.setLayout(stacked_layout)
capture_dock_widget.setWidget(dock_widget)
capture_dock_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)

stacked_layout.addWidget(capture_button)  # Index 0 for Stills
stacked_layout.addWidget(record_button)   # Index 1 for Video
stacked_layout.addWidget(QLabel("Timelapse mode not implemented yet"))  # Index 2 for Timelapse
stacked_layout.setCurrentIndex(prefs.camera_mode.value)  # Set initial mode based on prefs

picam_stacked_layout.addWidget(qpicamera2)
picam_stacked_layout.addWidget(options_tab_window)
picam_stacked_layout.setCurrentIndex(0)

window.setCentralWidget(picam_widget)
window.addDockWidget(2, capture_dock_widget)
capture_dock_widget.setFixedWidth(125)
capture_dock_widget.setContentsMargins(0, 0, 5, 5)
window.menuBar().addMenu(file_menu)
window.addToolBar(main_toolbar)

picam2.start()
change_camera_config(picam2, prefs.camera_mode, prefs)
window.showMaximized()
app.exec()