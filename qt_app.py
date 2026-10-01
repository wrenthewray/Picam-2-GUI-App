#!/usr/bin/python3

import pickle
import os
from datetime import datetime

from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QMenuBar, QPushButton, QSizePolicy, QStackedLayout, QStackedWidget,
    QTabWidget, QToolBar, QVBoxLayout, QWidget, QAction, QDockWidget, QGroupBox,
)

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
from picamera2.previews.qt import QGlPicamera2

try:
    from ups import UPS
except ImportError:
    UPS = None

from config import change_camera_config, change_controls, change_layout, change_prefs
from config import (
    change_autofocus_controls, change_camera_config, change_controls,
    change_layout, change_prefs,
)
from constants import (
    AspectRatio, BitRate, CameraMode, FourThreeResolution, FrameRate,
    OneOneResolution, SixteenNineResolution, WhiteBalanceMode,
)
from preferences import Prefs


class CameraApplication:
    def __init__(self):
        self.app = QApplication([])
        self.prefs = self.load_preferences()
        self.time_count = 0
        self.recording = False

        self.bitrate_list = self.enum_values(BitRate)
        self.frame_rate_list = self.enum_values(FrameRate)
        self.sixteen_nine_resolutions = self.tuple_values(SixteenNineResolution)
        self.four_three_resolutions = self.tuple_values(FourThreeResolution)
        self.one_one_resolutions = self.tuple_values(OneOneResolution)
        self.tuning_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "lens-tuning-files"
        )
        self.tuning_files = self.get_tuning_files()
        if self.prefs.tuning_file not in self.tuning_files:
            self.prefs.tuning_file = self.tuning_files[0] if self.tuning_files else None

        self.picam2 = Picamera2(tuning=self.load_tuning(self.prefs.tuning_file))
        self.build_interface()
        self.picam2.post_callback = self.post_callback
        self.qpicamera2 = QGlPicamera2(self.picam2, width=800, height=480, keep_ar=True)
        self.qpicamera2.done_signal.connect(self.capture_done)
        self.picam_stacked_layout.addWidget(self.qpicamera2)
        self.picam_stacked_layout.addWidget(self.options_tab_window)
        self.picam_stacked_layout.setCurrentIndex(0)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.show_time)
        self.timer_label = QLabel("00:00:00")
        self.battery_sensor = self.create_battery_sensor()
        self.battery_label = QLabel("Battery: --%")
        self.battery_timer = QtCore.QTimer()
        self.battery_timer.timeout.connect(self.update_battery_display)
        status_bar = self.window.statusBar()
        status_bar.setFont(QFont("Sans Serif", 12))
        status_bar.addWidget(self.timer_label)
        status_bar.addPermanentWidget(self.battery_label)
        self.update_battery_display()
        self.battery_timer.start(2000)

        self.picam2.start()
        change_camera_config(self.picam2, self.prefs.camera_mode, self.prefs)
        self.update_autofocus_availability()
        self.window.showFullScreen()

    @staticmethod
    def load_preferences():
        try:
            with open("prefs.pkl", "rb") as preferences_file:
                return pickle.load(preferences_file)
        except FileNotFoundError:
            return Prefs()

    @staticmethod
    def enum_values(value_type):
        return [value for value in value_type.__dict__.values() if isinstance(value, int)]

    @staticmethod
    def tuple_values(value_type):
        return [
            value for value in value_type.__dict__.values()
            if isinstance(value, tuple) and len(value) == 2
            and all(isinstance(item, int) for item in value)
        ]

    def get_tuning_files(self):
        if not os.path.isdir(self.tuning_directory):
            return []
        return sorted(
            filename for filename in os.listdir(self.tuning_directory)
            if filename.lower().endswith(".json")
            and os.path.isfile(os.path.join(self.tuning_directory, filename))
        )

    def load_tuning(self, filename):
        if filename is None:
            return None
        return Picamera2.load_tuning_file(filename, dir=self.tuning_directory)

    def on_select_tuning_file(self, index):
        if index < 0:
            return
        filename = self.tuning_files[index]
        if filename == self.prefs.tuning_file:
            return

        tuning = self.load_tuning(filename)
        change_prefs(self.prefs, tuning_file=filename)
        showing_settings = self.picam_stacked_layout.currentWidget() is self.options_tab_window
        self.picam2.stop()
        old_preview = self.qpicamera2
        self.picam_stacked_layout.removeWidget(old_preview)
        old_preview.deleteLater()
        self.picam2.close()

        self.picam2 = Picamera2(tuning=tuning)
        self.picam2.post_callback = self.post_callback
        self.qpicamera2 = QGlPicamera2(self.picam2, width=800, height=480, keep_ar=True)
        self.qpicamera2.done_signal.connect(self.capture_done)
        self.picam_stacked_layout.insertWidget(0, self.qpicamera2)
        self.picam2.start()
        change_camera_config(self.picam2, self.prefs.camera_mode, self.prefs)
        change_controls(self.picam2, self.prefs)
        self.update_autofocus_availability()
        if showing_settings:
            self.picam_stacked_layout.setCurrentWidget(self.options_tab_window)

    @staticmethod
    def create_battery_sensor():
        if UPS is None:
            return None
        try:
            return UPS()
        except Exception:
            return None

    def update_battery_display(self):
        if self.battery_sensor is None:
            self.battery_label.setText("Battery: --%")
            return
        try:
            percentage = self.battery_sensor.get_battery_percentage()
            percentage = max(0, min(100, percentage))
            self.battery_label.setText(f"Battery: {percentage}%")
        except Exception:
            self.battery_label.setText("Battery: --%")

    def post_callback(self, request):
        self.metadata.setText(''.join(
            f"{key}: {value}\n" for key, value in request.get_metadata().items()
        ))

    def get_still_file_path(self):
        return self.prefs.still_save_directory + (
            f'/IMG_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.jpg'
        )

    def get_video_file_path(self):
        return self.prefs.video_save_directory + (
            f'/VID_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.mp4'
        )

    def on_record_button_clicked(self):
        if not self.recording:
            self.start_recording()
            self.take_button.setEnabled(True)
            self.record_button.setText("Stop recording")
            self.recording = True
        else:
            self.stop_recording()
            self.take_button.setEnabled(False)
            self.record_button.setText("Start recording")
            self.recording = False

    def on_take_button_clicked(self):
        self.stop_recording()
        self.start_recording()

    def stop_recording(self):
        self.picam2.stop_encoder()
        self.timer.stop()
        self.timer_label.setText("00:00:00")

    def start_recording(self):
        encoder = H264Encoder(self.prefs.bitrate)
        output = FfmpegOutput(self.get_video_file_path(), audio=self.prefs.audio_mode)
        self.picam2.start_encoder(encoder, output)
        self.time_count = 0
        self.timer.start(1000)

    def on_capture_button_clicked(self):
        self.capture_button.setEnabled(False)
        configuration = self.picam2.create_still_configuration(
            main={"size": self.prefs.still_resolution}
        )
        self.picam2.switch_mode_and_capture_file(
            configuration, self.get_still_file_path(),
            signal_function=self.qpicamera2.signal_done,
        )

    def capture_done(self, job):
        self.picam2.wait(job)
        self.capture_button.setEnabled(True)

    def switch_camera_mode(self, mode):
        self.picam2.stop()
        change_prefs(self.prefs, camera_mode=mode)
        change_camera_config(self.picam2, mode, self.prefs)
        change_layout(self.stacked_layout, mode.value)
        self.update_autofocus_availability()
        self.picam2.start()

    def show_time(self):
        self.time_count += 1
        hours, remainder = divmod(self.time_count, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer_label.setText(f'{hours:02}:{minutes:02}:{seconds:02}')

    def on_options_button_clicked(self):
        self.picam_stacked_layout.setCurrentIndex(
            0 if self.picam_stacked_layout.currentIndex() == 1 else 1
        )

    def on_toggle_auto_white_balance(self):
        change_prefs(self.prefs, auto_white_balance=not self.prefs.auto_white_balance)
        self.white_balance_action.setText(
            "Disable WB" if self.prefs.auto_white_balance else "Enable WB"
        )
        change_controls(self.picam2, self.prefs)
        self.update_white_balance_visibility()

    def update_white_balance_visibility(self):
        self.white_balance_mode_combo.setVisible(self.prefs.auto_white_balance)
        self.white_balance_mode_action.setVisible(self.prefs.auto_white_balance)
        self.white_balance_label.setVisible(self.prefs.auto_white_balance)

    def on_select_white_balance_mode(self, white_balance):
        change_prefs(self.prefs, white_balance_mode=white_balance)
        change_controls(self.picam2, self.prefs)

    def on_toggle_autofocus(self, enabled):
        change_prefs(self.prefs, autofocus_enabled=enabled)
        change_autofocus_controls(self.picam2, self.prefs)
        self.update_autofocus_availability()

    def on_select_autofocus_speed(self, speed):
        change_prefs(self.prefs, autofocus_speed=speed)
        change_autofocus_controls(self.picam2, self.prefs)

    def update_autofocus_availability(self):
        try:
            available_controls = self.picam2.camera_controls
        except Exception:
            available_controls = {}
        self.autofocus_supported = "AfMode" in available_controls
        speed_supported = "AfSpeed" in available_controls
        self.autofocus_checkbox.setEnabled(self.autofocus_supported)
        self.autofocus_speed_combo.setEnabled(
            self.autofocus_supported and speed_supported and self.prefs.autofocus_enabled
        )

    def on_select_video_directory(self):
        directory = self.file_dialog.getExistingDirectory(
            None, "Select where to save videos...", self.prefs.video_save_directory
        )
        if directory:
            change_prefs(self.prefs, video_save_directory=directory)

    def on_select_stills_directory(self):
        directory = self.file_dialog.getExistingDirectory(
            None, "Select where to save stills...", self.prefs.still_save_directory
        )
        if directory:
            change_prefs(self.prefs, still_save_directory=directory)

    def on_select_video_aspect_ratio(self, aspect_ratio):
        change_prefs(self.prefs, video_aspect_ratio=aspect_ratio)
        self.video_resolution_stacked_layout.setCurrentIndex(aspect_ratio.value)
        self.set_default_resolution(
            aspect_ratio, "video_resolution", self.video_resolution_combos
        )

    def on_select_still_aspect_ratio(self, aspect_ratio):
        change_prefs(self.prefs, still_aspect_ratio=aspect_ratio)
        self.still_resolution_stacked_layout.setCurrentIndex(aspect_ratio.value)
        self.set_default_resolution(
            aspect_ratio, "still_resolution", self.still_resolution_combos
        )

    def set_default_resolution(self, aspect_ratio, preference_name, combos):
        defaults = {
            AspectRatio.SIXTEEN_BY_NINE: SixteenNineResolution.SIXTEEN_NINE_ASPECT_RATIO_HD,
            AspectRatio.FOUR_BY_THREE: FourThreeResolution.FOUR_THREE_ASPECT_RATIO_1280_960,
            AspectRatio.ONE_BY_ONE: OneOneResolution.ONE_ONE_ASPECT_RATIO_HD,
        }
        resolution = defaults[aspect_ratio]
        change_prefs(self.prefs, **{preference_name: resolution})
        combos[aspect_ratio.value].setCurrentIndex(
            self.resolution_values[aspect_ratio.value].index(resolution)
        )

    def on_select_video_resolution(self, resolution):
        change_prefs(self.prefs, video_resolution=resolution)
        change_controls(self.picam2, self.prefs)
        change_camera_config(self.picam2, CameraMode.VIDEO, self.prefs)

    def on_select_video_framerate(self, frame_rate):
        change_prefs(self.prefs, video_frame_rate=frame_rate)
        change_controls(self.picam2, self.prefs)
        change_camera_config(self.picam2, CameraMode.VIDEO, self.prefs)

    def on_select_preview_framerate(self, frame_rate):
        change_prefs(self.prefs, preview_frame_rate=frame_rate)
        change_controls(self.picam2, self.prefs)
        change_camera_config(self.picam2, CameraMode.VIDEO, self.prefs)

    def on_select_still_resolution(self, resolution):
        change_prefs(self.prefs, still_resolution=resolution)
        change_controls(self.picam2, self.prefs)
        change_camera_config(self.picam2, CameraMode.STILL, self.prefs)

    def on_close(self):
        self.picam2.stop()
        self.app.quit()

    def build_interface(self):
        self.metadata = QLabel()
        self.window = QMainWindow()
        self.window.setWindowTitle("Camera")
        self.file_dialog = QFileDialog()
        self.file_dialog.setFileMode(QFileDialog.Directory)

        self.stacked_layout = QStackedLayout()
        self.picam_stacked_layout = QStackedLayout()
        self.picam_widget = QWidget()
        self.picam_widget.setLayout(self.picam_stacked_layout)
        self.capture_dock_widget = QDockWidget()
        dock_widget = QWidget()
        dock_widget.setLayout(self.stacked_layout)
        self.capture_dock_widget.setWidget(dock_widget)
        self.capture_dock_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.capture_dock_widget.setFixedWidth(125)

        self.build_menu()
        self.build_toolbar()
        self.build_capture_controls()
        self.build_video_options()
        self.build_autofocus_options()

        self.window.setCentralWidget(self.picam_widget)
        self.window.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.capture_dock_widget)
        self.stacked_layout.setCurrentIndex(self.prefs.camera_mode.value)
        self.metadata.setFixedWidth(100)
        self.metadata.setAlignment(QtCore.Qt.AlignTop)

    def build_menu(self):
        self.menu_bar = QMenuBar(self.window)
        self.menu_bar.setNativeMenuBar(False)
        self.menu_bar.setMinimumHeight(36)
        self.menu_bar.setFont(QFont("Sans Serif", 12))
        file_menu = self.menu_bar.addMenu("File")
        actions = (
            ("Select Video Path", self.on_select_video_directory),
            ("Select Photo Path", self.on_select_stills_directory),
        )
        for title, handler in actions:
            action = file_menu.addAction(title)
            action.triggered.connect(handler)
        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.on_close)
        self.menu_bar.setVisible(True)
        self.window.setMenuBar(self.menu_bar)

    def build_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMinimumHeight(48)
        toolbar.setFont(QFont("Sans Serif", 12))
        self.options_action = toolbar.addAction("Settings")
        self.options_action.triggered.connect(self.on_options_button_clicked)
        self.white_balance_action = toolbar.addAction(
            "Disable WB" if self.prefs.auto_white_balance else "Enable WB"
        )
        self.white_balance_action.triggered.connect(self.on_toggle_auto_white_balance)
        toolbar.addWidget(QLabel(" Camera: "))
        self.switch_mode_combo = QComboBox()
        self.switch_mode_combo.addItems(("Stills", "Video", "Timelapse"))
        self.switch_mode_combo.setCurrentIndex(self.prefs.camera_mode.value)
        self.switch_mode_combo.currentIndexChanged.connect(
            lambda index: self.switch_camera_mode(CameraMode(index))
        )
        toolbar.addWidget(self.switch_mode_combo)
        self.white_balance_label = QLabel(" WB: ")
        toolbar.addWidget(self.white_balance_label)
        self.white_balance_mode_combo = QComboBox()
        self.white_balance_mode_combo.addItems(
            ("Auto", "Tungsten", "Fluorescent", "Indoor", "Daylight", "Cloudy", "Custom")
        )
        self.white_balance_mode_combo.setCurrentIndex(self.prefs.white_balance_mode.value)
        self.white_balance_mode_combo.currentIndexChanged.connect(
            lambda index: self.on_select_white_balance_mode(WhiteBalanceMode(index))
        )
        self.white_balance_mode_action = toolbar.addWidget(self.white_balance_mode_combo)
        self.update_white_balance_visibility()
        self.window.addToolBar(toolbar)

    def build_capture_controls(self):
        button_size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.record_button = QPushButton("Start recording")
        self.record_button.clicked.connect(self.on_record_button_clicked)
        self.record_button.setSizePolicy(button_size_policy)
        self.take_button = QPushButton("Start New Take")
        self.take_button.setEnabled(False)
        self.take_button.clicked.connect(self.on_take_button_clicked)
        self.take_button.setSizePolicy(button_size_policy)
        record_window = QWidget()
        record_layout = QVBoxLayout(record_window)
        record_layout.addWidget(self.record_button)
        record_layout.addWidget(self.take_button)
        self.capture_button = QPushButton("Capture")
        self.capture_button.clicked.connect(self.on_capture_button_clicked)
        self.capture_button.setSizePolicy(button_size_policy)
        self.stacked_layout.addWidget(self.capture_button)
        self.stacked_layout.addWidget(record_window)
        self.stacked_layout.addWidget(QLabel("Timelapse mode not implemented yet"))

    def build_video_options(self):
        self.options_tab_window = QTabWidget()
        options_layout = QVBoxLayout()
        self.add_framerate_control(options_layout, "Preview Frame Rate:", self.prefs.preview_frame_rate, self.on_select_preview_framerate)
        self.add_framerate_control(options_layout, "Video Frame Rate:", self.prefs.video_frame_rate, self.on_select_video_framerate)
        self.add_combo_control(options_layout, "Bitrate:", ("1.28 Mbps", "2.56 Mbps", "5.12 Mbps", "10.24 Mbps", "20.48 Mbps", "45 Mbps", "60 Mbps"), self.bitrate_list.index(self.prefs.bitrate), lambda index: change_prefs(self.prefs, bitrate=self.bitrate_list[index]))
        self.add_aspect_control(options_layout, "Video Aspect Ratio:", self.prefs.video_aspect_ratio, self.on_select_video_aspect_ratio)
        self.video_resolution_stacked_layout = self.add_resolution_control(options_layout, "Video Resolution:", self.prefs.video_aspect_ratio, self.prefs.video_resolution, self.on_select_video_resolution)
        self.add_aspect_control(options_layout, "Still Aspect Ratio:", self.prefs.still_aspect_ratio, self.on_select_still_aspect_ratio)
        self.still_resolution_stacked_layout = self.add_resolution_control(options_layout, "Still Resolution:", self.prefs.still_aspect_ratio, self.prefs.still_resolution, self.on_select_still_resolution)
        video_window = QWidget()
        video_window.setLayout(options_layout)
        self.options_tab_window.addTab(video_window, "Video")

    def build_autofocus_options(self):
        autofocus_layout = QVBoxLayout()
        self.autofocus_checkbox = QCheckBox("Enable autofocus")
        self.autofocus_checkbox.setChecked(self.prefs.autofocus_enabled)
        self.autofocus_checkbox.toggled.connect(self.on_toggle_autofocus)
        autofocus_layout.addWidget(self.autofocus_checkbox)

        speed_index = self.prefs.autofocus_speed
        if speed_index not in (0, 1):
            speed_index = 0
        self.autofocus_speed_combo = self.add_combo_control(
            autofocus_layout, "Autofocus speed:", ("Normal", "Fast"),
            speed_index, self.on_select_autofocus_speed,
        )
        tuning_group = QGroupBox("Lens tuning")
        tuning_layout = QVBoxLayout(tuning_group)
        tuning_index = (
            self.tuning_files.index(self.prefs.tuning_file)
            if self.prefs.tuning_file in self.tuning_files else -1
        )
        self.tuning_file_combo = self.add_combo_control(
            tuning_layout, "Tuning file:", self.tuning_files,
            tuning_index, self.on_select_tuning_file,
        )
        self.tuning_file_combo.setEnabled(bool(self.tuning_files))
        autofocus_layout.addWidget(tuning_group)
        autofocus_window = QWidget()
        autofocus_window.setLayout(autofocus_layout)
        self.options_tab_window.addTab(autofocus_window, "Autofocus")
        self.autofocus_speed_combo.setEnabled(False)

    def add_framerate_control(self, layout, label, value, handler):
        self.add_combo_control(layout, label, ("12 FPS", "24 FPS", "25 FPS", "30 FPS"), self.frame_rate_list.index(value), lambda index: handler(self.frame_rate_list[index]))

    @staticmethod
    def add_combo_control(layout, label, items, current_index, handler):
        combo = QComboBox()
        combo.addItems(items)
        combo.setCurrentIndex(current_index)
        combo.currentIndexChanged.connect(handler)
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(combo)
        layout.addLayout(row)
        return combo

    def add_aspect_control(self, layout, label, value, handler):
        self.add_combo_control(layout, label, ("16:9", "4:3", "1:1"), value.value, lambda index: handler(AspectRatio(index)))

    def add_resolution_control(self, layout, label, aspect_ratio, current_resolution, handler):
        combos = []
        self.resolution_values = [self.sixteen_nine_resolutions, self.four_three_resolutions, self.one_one_resolutions]
        names = (("3840x2160 (4K)", "2560x1440 (QHD)", "1920x1080 (HD)", "1280x720 (SD)", "960x540 (qHD)", "640x480 (480p)"), ("3840x2880 (4K)", "3200x2400 (QUXGA)", "2048x1536 (QXGA)", "1600x1200 (UXGA)", "1280x960", "1024x768 (XGA)", "800x600 (SVGA)", "640x480 (VGA)"), ("3840x3840 (4K)", "2560x2560 (QHD)", "1920x1920 (HD)", "1280x1280 (SD)", "960x960 (qHD)"))
        stacked = QStackedWidget()
        for index, values in enumerate(self.resolution_values):
            combo = QComboBox()
            combo.addItems(names[index])
            combo.setCurrentIndex(values.index(current_resolution) if index == aspect_ratio.value and current_resolution in values else 0)
            combo.currentIndexChanged.connect(lambda selected, values=values: handler(values[selected]))
            combos.append(combo)
            stacked.addWidget(combo)
        if label.startswith("Video"):
            self.video_resolution_combos = combos
        else:
            self.still_resolution_combos = combos
        stacked.setCurrentIndex(aspect_ratio.value)
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(stacked)
        layout.addLayout(row)
        return stacked

    def run(self):
        return self.app.exec()


def run():
    return CameraApplication().run()


if __name__ == "__main__":
    run()
