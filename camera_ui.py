from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMenuBar, QPushButton, QSizePolicy, QStackedLayout, QStackedWidget,
    QTabWidget, QToolBar, QVBoxLayout, QWidget, QDockWidget, QGroupBox,
    QProgressBar, QSlider,
)

from config import change_prefs
from constants import (
    AspectRatio, BitRate, CameraMode, FrameRate, WhiteBalanceMode,
)


class CameraUI:
    def build_audio_meter(self, status_bar):
        meter_widget = QWidget()
        meter_layout = QHBoxLayout(meter_widget)
        meter_layout.setContentsMargins(6, 0, 6, 0)
        meter_layout.addWidget(QLabel("Mic"))
        self.audio_level_bar = QProgressBar()
        self.audio_level_bar.setRange(0, 100)
        self.audio_level_bar.setValue(0)
        self.audio_level_bar.setFixedWidth(110)
        self.audio_level_bar.setTextVisible(False)
        meter_layout.addWidget(self.audio_level_bar)
        self.audio_peak_label = QLabel(" ")
        self.audio_peak_label.setMinimumWidth(44)
        meter_layout.addWidget(self.audio_peak_label)
        status_bar.addWidget(meter_widget)

    def build_interface(self):
        self.media_viewers = []
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
        self.build_lens_options()
        self.build_audio_options()

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
        restart_action = file_menu.addAction("Restart")
        restart_action.triggered.connect(self.on_restart)
        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.on_close)
        view_menu = self.menu_bar.addMenu("View")
        browse_photos_action = view_menu.addAction("Browse Photos")
        browse_photos_action.triggered.connect(
            lambda: self.open_media_viewer("photos")
        )
        browse_videos_action = view_menu.addAction("Browse Videos")
        browse_videos_action.triggered.connect(
            lambda: self.open_media_viewer("videos")
        )
        self.menu_bar.setVisible(True)
        self.window.setMenuBar(self.menu_bar)

    def build_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMinimumHeight(48)
        toolbar.setFont(QFont("Sans Serif", 12))
        self.options_action = toolbar.addAction("Settings")
        self.options_action.triggered.connect(self.on_options_button_clicked)
        self.aperture_toggle_action = toolbar.addAction("Show Aperture")
        self.aperture_toggle_action.setCheckable(True)
        toolbar.addWidget(QLabel(" Mode: "))
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
        self.window.addToolBarBreak(QtCore.Qt.TopToolBarArea)
        self.aperture_toolbar = QToolBar("Lens aperture")
        self.aperture_toolbar.setMinimumHeight(72)
        self.aperture_toolbar.setFont(QFont("Sans Serif", 12))
        self.aperture_value_label = QLabel(" Aperture: -- ")
        self.aperture_toolbar.addWidget(self.aperture_value_label)
        self.aperture_slider = QSlider(QtCore.Qt.Horizontal)
        self.aperture_slider.setRange(100, 3200)
        self.aperture_slider.setSingleStep(10)
        self.aperture_slider.setPageStep(100)
        self.aperture_slider.setTracking(False)
        self.aperture_slider.setMinimumWidth(240)
        self.aperture_slider.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self.aperture_slider.setMinimumHeight(56)
        self.aperture_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 14px; background: #777; }"
            "QSlider::handle:horizontal { width: 44px; height: 56px; "
            "margin: -21px 0; background: #d8d8d8; "
            "border: 2px solid #555; border-radius: 8px; }"
        )
        self.aperture_slider.setValue(1650)
        self.aperture_slider.setToolTip(
            "Set lens aperture (f-number × 100); the lens does not report its current value"
        )
        self.aperture_slider.setEnabled(self.aperture_device is not None)
        if self.aperture_device is None:
            self.aperture_slider.setToolTip(
                f"Aperture control unavailable: {self.aperture_device_error}"
            )
        self.aperture_slider.valueChanged.connect(self.set_aperture)
        self.aperture_toolbar.addWidget(self.aperture_slider)
        self.window.addToolBar(self.aperture_toolbar)
        self.aperture_toolbar.hide()
        self.aperture_toggle_action.toggled.connect(
            self.set_aperture_toolbar_visible
        )

    def set_aperture_toolbar_visible(self, visible):
        self.aperture_toolbar.setVisible(visible)
        self.aperture_toggle_action.setText(
            "Hide Aperture" if visible else "Show Aperture"
        )

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
        self.add_framerate_control(
            options_layout, "Preview Frame Rate:",
            self.prefs.preview_frame_rate, self.on_select_preview_framerate,
        )
        self.add_framerate_control(
            options_layout, "Video Frame Rate:",
            self.prefs.video_frame_rate, self.on_select_video_framerate,
        )
        self.add_bitrate_control(
            options_layout, "Video bitrate:", self.prefs.bitrate
        )
        self.add_aspect_control(
            options_layout, "Video Aspect Ratio:",
            self.prefs.video_aspect_ratio, self.on_select_video_aspect_ratio,
        )
        self.video_resolution_stacked_layout = self.add_resolution_control(
            options_layout, "Video Resolution:",
            self.prefs.video_aspect_ratio, self.prefs.video_resolution,
            self.on_select_video_resolution,
        )
        self.add_aspect_control(
            options_layout, "Still Aspect Ratio:",
            self.prefs.still_aspect_ratio, self.on_select_still_aspect_ratio,
        )
        self.still_resolution_stacked_layout = self.add_resolution_control(
            options_layout, "Still Resolution:",
            self.prefs.still_aspect_ratio, self.prefs.still_resolution,
            self.on_select_still_resolution,
        )
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

    def build_lens_options(self):
        lens_layout = QVBoxLayout()
        self.white_balance_toggle_button = QPushButton(
            "Disable WB" if self.prefs.auto_white_balance else "Enable WB"
        )
        self.white_balance_toggle_button.clicked.connect(
            self.on_toggle_auto_white_balance
        )
        lens_layout.addWidget(self.white_balance_toggle_button)
        lens_window = QWidget()
        lens_window.setLayout(lens_layout)
        self.options_tab_window.addTab(lens_window, "Lens")

    def build_audio_options(self):
        audio_layout = QVBoxLayout()
        self.audio_recording_checkbox = QCheckBox("Record audio with video")
        self.audio_recording_checkbox.setChecked(
            getattr(self.prefs, "audio_mode", False)
        )
        self.audio_recording_checkbox.toggled.connect(
            self.on_toggle_audio_recording
        )
        audio_layout.addWidget(self.audio_recording_checkbox)
        self.audio_recording_device_combo = self.add_device_combo_control(
            audio_layout, "Recording device:",
            self.audio_recording_devices,
            getattr(self.prefs, "audio_recording_device", "default"),
            self.on_audio_recording_device_changed,
        )
        self.audio_playback_device_combo = self.add_device_combo_control(
            audio_layout, "Playback device:",
            self.audio_playback_devices,
            getattr(self.prefs, "audio_playback_device", "default"),
            self.on_audio_playback_device_changed,
        )

        test_row = QHBoxLayout()
        test_row.addWidget(QLabel("Record and play a 5-second test:"))
        self.audio_test_button = QPushButton("Test")
        self.audio_test_button.clicked.connect(self.on_test_audio_clicked)
        test_row.addWidget(self.audio_test_button)
        audio_layout.addLayout(test_row)

        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("App playback volume:"))
        self.audio_volume_slider = QSlider(QtCore.Qt.Horizontal)
        self.audio_volume_slider.setRange(0, 100)
        self.audio_volume_slider.setTickInterval(10)
        self.audio_volume_slider.setValue(
            max(0, min(100, getattr(self.prefs, "playback_volume", 80)))
        )
        self.audio_volume_slider.valueChanged.connect(self.on_audio_volume_changed)
        volume_row.addWidget(self.audio_volume_slider, 1)
        self.audio_volume_label = QLabel(
            f"{self.audio_volume_slider.value()}%"
        )
        volume_row.addWidget(self.audio_volume_label)
        audio_layout.addLayout(volume_row)
        if self.audio_device_warnings:
            warning = QLabel("Device discovery issue:\n" + "\n".join(
                self.audio_device_warnings
            ))
            warning.setWordWrap(True)
            audio_layout.addWidget(warning)

        audio_window = QWidget()
        audio_window.setLayout(audio_layout)
        self.options_tab_window.addTab(audio_window, "Audio")

    @staticmethod
    def add_device_combo_control(layout, label, devices, selected_device, handler):
        combo = QComboBox()
        selected_index = 0
        for index, (name, device_id) in enumerate(devices):
            combo.addItem(name, device_id)
            if device_id == selected_device:
                selected_index = index
        combo.setCurrentIndex(selected_index)
        combo.currentIndexChanged.connect(handler)
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(combo)
        layout.addLayout(row)
        return combo

    def add_framerate_control(self, layout, label, value, handler):
        frame_rates = (
            FrameRate.TWELVE_FPS,
            FrameRate.TWENTY_FOUR_FPS,
            FrameRate.TWENTY_FIVE_FPS,
            FrameRate.THIRTY_FPS,
        )
        combo = QComboBox()
        for frame_rate in frame_rates:
            combo.addItem(f"{frame_rate} FPS", frame_rate)
        combo.setCurrentIndex(frame_rates.index(value))
        combo.currentIndexChanged.connect(
            lambda index: handler(combo.itemData(index))
        )
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(combo)
        layout.addLayout(row)

    def add_bitrate_control(self, layout, label, value):
        bitrates = (
            (BitRate.ONE_POINT_TWENTY_EIGHT_MBPS, "1.28 Mbps"),
            (BitRate.TWO_POINT_FIVE_SIX_MBPS, "2.56 Mbps"),
            (BitRate.FIVE_POINT_ONE_TWO_MBPS, "5.12 Mbps"),
            (BitRate.TEN_POINT_TWO_FOUR_MBPS, "10.24 Mbps"),
            (BitRate.TWENTY_POINT_FOUR_MBPS, "20.48 Mbps"),
            (BitRate.FOURTY_FIVE_MBPS, "45 Mbps"),
            (BitRate.SIXTY_MBPS, "60 Mbps"),
        )
        combo = QComboBox()
        for bitrate, text in bitrates:
            combo.addItem(text, bitrate)
        combo.setCurrentIndex(
            next(index for index, (bitrate, _) in enumerate(bitrates) if bitrate == value)
        )
        combo.currentIndexChanged.connect(
            lambda index: change_prefs(
                self.prefs, bitrate=combo.itemData(index)
            )
        )
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(combo)
        layout.addLayout(row)

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
        self.add_combo_control(
            layout, label, ("16:9", "4:3", "1:1"), value.value,
            lambda index: handler(AspectRatio(index)),
        )

    def add_resolution_control(self, layout, label, aspect_ratio, current_resolution, handler):
        combos = []
        self.resolution_values = [
            self.sixteen_nine_resolutions,
            self.four_three_resolutions,
            self.one_one_resolutions,
        ]
        names = (
            (
                "3840x2160 (4K)", "2560x1440 (QHD)", "1920x1080 (HD)",
                "1280x720 (SD)", "960x540 (qHD)", "640x480 (480p)",
            ),
            (
                "3840x2880 (4K)", "3200x2400 (QUXGA)",
                "2048x1536 (QXGA)", "1600x1200 (UXGA)", "1280x960",
                "1024x768 (XGA)", "800x600 (SVGA)", "640x480 (VGA)",
            ),
            (
                "3840x3840 (4K)", "2560x2560 (QHD)", "1920x1920 (HD)",
                "1280x1280 (SD)", "960x960 (qHD)",
            ),
        )
        stacked = QStackedWidget()
        for index, values in enumerate(self.resolution_values):
            combo = QComboBox()
            combo.addItems(names[index])
            selected_index = (
                values.index(current_resolution)
                if index == aspect_ratio.value and current_resolution in values
                else 0
            )
            combo.setCurrentIndex(selected_index)
            combo.currentIndexChanged.connect(
                lambda selected, values=values: handler(values[selected])
            )
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
