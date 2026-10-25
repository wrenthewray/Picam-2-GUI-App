import glob
import math
import os
import pickle
import re
import struct
import subprocess
import sys
import tempfile
import threading
from datetime import datetime

import av
from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import PyavOutput
from picamera2.previews.qt import QGlPicamera2

try:
    from ups import UPS
except ImportError:
    UPS = None

from config import (
    change_autofocus_controls, change_camera_config, change_controls,
    change_layout, change_prefs,
)
from constants import (
    AspectRatio, CameraMode, FourThreeResolution, OneOneResolution,
    SixteenNineResolution,
)
from media_browser import PhotoBrowser, VideoBrowser
from preferences import Prefs
from camera_ui import CameraUI

class RecordingStartSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)

class CameraApplication(CameraUI):
    def __init__(self):
        self.app = QApplication([])
        self.prefs = self.load_preferences()
        self.time_count = 0
        self.recording = False
        self.recording_starting = False
        self.recording_start_thread = None
        self.aperture_device, self.aperture_device_error = (
            self.find_aperture_device()
        )

        self.audio_device_warnings = []
        try:
            self.audio_recording_devices = self.list_alsa_capture_devices()
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            self.audio_recording_devices = [("Default ALSA device", "default")]
            self.audio_device_warnings.append(f"Recording devices: {error}")
        try:
            self.audio_playback_devices = self.list_alsa_playback_devices()
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            self.audio_playback_devices = [("Default ALSA device", "default")]
            self.audio_device_warnings.append(f"Playback devices: {error}")
        for devices, preference_name in (
            (self.audio_recording_devices, "audio_recording_device"),
            (self.audio_playback_devices, "audio_playback_device"),
        ):
            selected_device = getattr(self.prefs, preference_name, "default")
            device_ids = {device_id for _, device_id in devices}
            if isinstance(selected_device, str):
                device_match = re.fullmatch(
                    r"(?:hw|plughw):(\d+)[,.](\d+)", selected_device
                )
                if device_match:
                    normalized_device = (
                        f"plughw:{device_match.group(1)},{device_match.group(2)}"
                    )
                    if selected_device != normalized_device:
                        change_prefs(
                            self.prefs, **{preference_name: normalized_device}
                        )
                    selected_device = normalized_device
            if selected_device not in device_ids:
                if (
                    isinstance(selected_device, str)
                    and selected_device.startswith("alsa_input.")
                ):
                    selected_device = devices[1][1] if len(devices) == 2 else "default"
                    change_prefs(self.prefs, **{preference_name: selected_device})
                else:
                    devices.append((f"Configured device ({selected_device})", selected_device))
        self.audio_meter_process = None
        self.audio_meter_pending = bytearray()
        self.audio_meter_errors = bytearray()
        self.audio_test_process = None
        self.audio_test_path = None
        self.audio_test_phase = None
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
        self.recording_start_signals = RecordingStartSignals(self.window)
        self.recording_start_signals.finished.connect(
            self.handle_recording_start_finished
        )
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
        self.build_audio_meter(status_bar)
        status_bar.addPermanentWidget(self.battery_label)
        self.update_battery_display()
        self.battery_timer.start(2000)

        self.picam2.start()
        change_camera_config(self.picam2, self.prefs.camera_mode, self.prefs)
        self.update_autofocus_availability()
        self.start_audio_meter()
        self.window.showFullScreen()

    @staticmethod
    def load_preferences():
        try:
            with open("prefs.pkl", "rb") as preferences_file:
                return pickle.load(preferences_file)
        except FileNotFoundError:
            return Prefs()

    @staticmethod
    def list_alsa_capture_devices():
        result = subprocess.run(
            ["arecord", "-l"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        return CameraApplication.parse_alsa_devices(result.stdout)

    @staticmethod
    def list_alsa_playback_devices():
        result = subprocess.run(
            ["aplay", "-l"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        return CameraApplication.parse_alsa_devices(result.stdout)

    @staticmethod
    def parse_alsa_devices(output):
        pattern = re.compile(
            r"^card\s+(\d+):\s+([^\s\[]+)\s+\[([^\]]+)\],\s+"
            r"device\s+(\d+):\s+([^\[]+)\[([^\]]+)\]"
        )
        devices = []
        for line in output.splitlines():
            match = pattern.match(line.strip())
            if not match:
                continue
            card, _, card_description, device, _, device_description = (
                match.groups()
            )
            identifier = f"plughw:{card},{device}"
            label = (
                f"{identifier} — {card_description.strip()} / "
                f"{device_description.strip()}"
            )
            devices.append((label, identifier))
        if not devices:
            raise RuntimeError("ALSA reported no hardware devices")
        return [("Default ALSA device", "default")] + devices

    def start_audio_meter(self):
        self.stop_audio_meter()
        self.audio_peak_label.setText("...")
        self.audio_peak_label.setToolTip("")
        process = QtCore.QProcess(self.window)
        process.readyReadStandardOutput.connect(
            lambda process=process: self.read_audio_meter(process)
        )
        process.readyReadStandardError.connect(
            lambda process=process: self.read_audio_meter_error(process)
        )
        process.errorOccurred.connect(
            lambda error, process=process: self.handle_audio_meter_error(process)
        )
        process.finished.connect(
            lambda exit_code, exit_status, process=process:
                self.handle_audio_meter_finished(process, exit_code)
        )
        self.audio_meter_process = process
        self.audio_meter_pending.clear()
        self.audio_meter_errors.clear()
        process.start("ffmpeg", [
            "-nostdin", "-hide_banner", "-loglevel", "error",
            "-thread_queue_size", "256", "-f", "alsa", "-i",
            getattr(self.prefs, "audio_recording_device", "default"),
            "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1",
        ])

    def stop_audio_meter(self):
        if self.audio_meter_process is not None:
            process = self.audio_meter_process
            self.audio_meter_process = None
            process.kill()
            if not process.waitForFinished(1000):
                self.audio_peak_label.setToolTip(
                    "Microphone monitor did not stop within one second"
                )

    def read_audio_meter_error(self, process):
        if process is self.audio_meter_process:
            self.audio_meter_errors.extend(bytes(process.readAllStandardError()))

    def read_audio_meter(self, process):
        if process is not self.audio_meter_process:
            return
        self.audio_meter_pending.extend(bytes(process.readAllStandardOutput()))
        sample_count = len(self.audio_meter_pending) // 2
        if not sample_count:
            return
        sample_bytes = self.audio_meter_pending[:sample_count * 2]
        del self.audio_meter_pending[:sample_count * 2]
        samples = struct.unpack(f"<{sample_count}h", sample_bytes)
        peak = max(abs(sample) for sample in samples)
        rms = math.sqrt(sum(sample * sample for sample in samples) / sample_count)
        level = min(100, round(rms * 100 / 32768))
        self.audio_level_bar.setValue(level)
        self.audio_peak_label.setText("PEAK" if peak >= 32700 else " ")
        self.audio_level_bar.setStyleSheet(
            "QProgressBar::chunk { background-color: #d22; }"
            if peak >= 32700 else
            "QProgressBar::chunk { background-color: #3a6; }"
        )
        self.audio_level_bar.setToolTip(f"Peak level: {peak * 100 / 32768:.1f}%")

    def handle_audio_meter_error(self, process):
        if process is self.audio_meter_process:
            self.read_audio_meter_error(process)
            self.audio_peak_label.setText("N/A")
            self.audio_peak_label.setToolTip(
                self.audio_error_text(self.audio_meter_errors, process)
            )
            self.audio_meter_process = None

    def handle_audio_meter_finished(self, process, exit_code):
        if process is self.audio_meter_process:
            self.read_audio_meter_error(process)
            self.audio_meter_process = None
            if exit_code:
                self.audio_peak_label.setText("N/A")
                self.audio_peak_label.setToolTip(
                    self.audio_error_text(self.audio_meter_errors, process)
                )

    def on_audio_recording_device_changed(self, index):
        if index < 0:
            return
        device = self.audio_recording_device_combo.currentData()
        change_prefs(self.prefs, audio_recording_device=device)
        self.start_audio_meter()

    def on_audio_playback_device_changed(self, index):
        if index < 0:
            return
        device = self.audio_playback_device_combo.currentData()
        change_prefs(self.prefs, audio_playback_device=device)
        for viewer in self.media_viewers:
            viewer.set_playback_device(device)

    def on_audio_volume_changed(self, volume):
        change_prefs(self.prefs, playback_volume=volume)
        self.audio_volume_label.setText(f"{volume}%")
        for viewer in self.media_viewers:
            viewer.set_playback_volume(volume)

    def on_toggle_audio_recording(self, enabled):
        change_prefs(self.prefs, audio_mode=enabled)

    def on_test_audio_clicked(self):
        if self.audio_test_process is not None:
            return
        try:
            audio_file = tempfile.NamedTemporaryFile(
                prefix="picam-audio-test-", suffix=".wav", delete=False
            )
            self.audio_test_path = audio_file.name
            audio_file.close()
        except OSError as error:
            QMessageBox.critical(self.window, "Audio test failed", str(error))
            return

        self.audio_test_phase = "recording"
        self.audio_test_button.setEnabled(False)
        self.audio_test_button.setText("Recording 5 seconds...")
        self.stop_audio_meter()
        self.audio_test_process = QtCore.QProcess(self.window)
        self.audio_test_errors = bytearray()
        self.audio_test_process.readyReadStandardError.connect(
            lambda process=self.audio_test_process:
                self.audio_test_errors.extend(bytes(process.readAllStandardError()))
        )
        self.audio_test_process.finished.connect(self.handle_audio_test_finished)
        self.audio_test_process.errorOccurred.connect(self.handle_audio_test_error)
        self.audio_test_process.start("ffmpeg", [
            "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "alsa", "-i",
            getattr(self.prefs, "audio_recording_device", "default"),
            "-t", "5", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le",
            self.audio_test_path,
        ])

    def handle_audio_test_finished(self, exit_code, exit_status):
        if self.audio_test_process is None:
            return
        if self.audio_test_phase == "recording" and exit_code == 0:
            self.audio_test_phase = "playing"
            self.audio_test_button.setText("Playing test...")
            self.audio_test_process.start("ffmpeg", [
                "-nostdin", "-hide_banner", "-loglevel", "error",
                "-i", self.audio_test_path,
                "-af", f"volume={getattr(self.prefs, 'playback_volume', 80) / 100:.2f}",
                "-f", "alsa",
                getattr(self.prefs, "audio_playback_device", "default"),
            ])
            return
        if exit_code and self.audio_test_phase == "recording":
            QMessageBox.critical(
                self.window, "Audio test failed",
                "Could not record audio:\n"
                + self.audio_error_text(self.audio_test_errors),
            )
        elif exit_code:
            QMessageBox.critical(
                self.window, "Audio test failed",
                "Could not play audio. Check the selected playback device.",
            )
        self.finish_audio_test()

    def handle_audio_test_error(self, error):
        if self.audio_test_process is not None:
            QMessageBox.critical(
                self.window, "Audio test failed",
                self.audio_error_text(
                    self.audio_test_errors, self.audio_test_process
                ),
            )
        self.finish_audio_test()

    @staticmethod
    def audio_error_text(error_output, process=None):
        message = bytes(error_output).decode("utf-8", errors="replace").strip()
        if message:
            return message
        return process.errorString() if process is not None else "Unknown audio error"

    def finish_audio_test(self):
        if self.audio_test_path:
            try:
                os.remove(self.audio_test_path)
            except OSError as error:
                QMessageBox.warning(
                    self.window, "Audio test cleanup failed", str(error)
                )
            self.audio_test_path = None
        self.audio_test_process = None
        self.audio_test_phase = None
        self.audio_test_button.setText("Test")
        self.audio_test_button.setEnabled(True)
        self.start_audio_meter()

    def stop_audio_test(self):
        if self.audio_test_process is not None:
            process = self.audio_test_process
            self.audio_test_process = None
            MediaBrowser.terminate_process(process)
        if self.audio_test_path:
            try:
                os.remove(self.audio_test_path)
            except FileNotFoundError:
                pass
            except OSError as error:
                QMessageBox.warning(
                    self.window, "Audio test cleanup failed", str(error)
                )
            self.audio_test_path = None

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
        if self.recording_starting:
            return
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
            self.take_button.setEnabled(False)
            self.record_button.setText("Start recording")
            self.recording = False

    def on_take_button_clicked(self):
        if self.recording and not self.recording_starting:
            self.stop_recording(resume_audio_meter=False)
            self.recording = False
        self.start_recording()

    def stop_recording(self, resume_audio_meter=True):
        self.picam2.stop_encoder()
        self.timer.stop()
        self.timer_label.setText("00:00:00")
        if resume_audio_meter:
            self.start_audio_meter()

    def start_recording(self):
        if self.recording or self.recording_starting:
            return False
        try:
            self.stop_audio_meter()
            encoder = H264Encoder(bitrate=self.prefs.bitrate)
            if getattr(self.prefs, "audio_mode", False):
                encoder.audio = True
                encoder.audio_input = {
                    "file": getattr(
                        self.prefs, "audio_recording_device", "default"
                    ),
                    "format": "alsa",
                    "options": {"sample_rate": "48000"},
                }
                encoder.audio_output = {
                    "codec_name": "aac",
                    "rate": 48000,
                }
                # A negative offset delays audio; the current capture path leads by ~1 s.
                encoder.audio_sync = -500_000
            output = PyavOutput(self.get_video_file_path())
            self.recording_starting = True
            self.record_button.setEnabled(False)
            self.take_button.setEnabled(False)
            self.record_button.setText("Starting recording...")
            self.recording_start_thread = threading.Thread(
                target=self.start_recording_encoder,
                args=(encoder, output),
                daemon=True,
            )
            self.recording_start_thread.start()
            return True
        except (OSError, RuntimeError, ValueError, av.error.FFmpegError) as error:
            self.start_audio_meter()
            QMessageBox.critical(self.window, "Unable to record video", str(error))
            return False

    def start_recording_encoder(self, encoder, output):
        try:
            self.picam2.start_encoder(encoder, output)
        except (OSError, RuntimeError, ValueError, av.error.FFmpegError) as error:
            self.recording_start_signals.finished.emit(error)
            return
        self.recording_start_signals.finished.emit(None)

    def handle_recording_start_finished(self, error):
        if self.recording_start_thread is not None:
            self.recording_start_thread.join()
        self.recording_start_thread = None
        self.recording_starting = False
        self.record_button.setEnabled(True)
        if error is not None:
            self.record_button.setText("Start recording")
            self.take_button.setEnabled(False)
            self.recording = False
            self.start_audio_meter()
            QMessageBox.critical(
                self.window, "Unable to record video", str(error)
            )
            return
        self.time_count = 0
        self.timer.start(1000)
        self.recording = True
        self.record_button.setText("Stop recording")
        self.take_button.setEnabled(True)

    def wait_for_recording_start(self):
        if self.recording_start_thread is not None:
            self.recording_start_thread.join()
            self.app.processEvents()

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
        self.white_balance_toggle_button.setText(
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

    @staticmethod
    def find_aperture_device():
        errors = []
        for device in sorted(glob.glob("/dev/v4l-subdev*")):
            try:
                result = subprocess.run(
                    ["v4l2-ctl", "-d", device, "--list-ctrls"],
                    check=True, capture_output=True, text=True, timeout=3,
                )
            except (OSError, subprocess.SubprocessError) as error:
                errors.append(f"{device}: {error}")
                continue
            if re.search(r"^\s*iris_absolute\s", result.stdout, re.MULTILINE):
                return device, None
        if errors:
            return None, "; ".join(errors)
        return None, "No V4L2 lens device with iris_absolute was found"

    def set_aperture(self, value):
        self.aperture_value_label.setText(f"Aperture: f/{value / 100:.1f}")
        try:
            subprocess.run(
                [
                    "v4l2-ctl", "-d", self.aperture_device,
                    "-c", f"iris_absolute={value}",
                ],
                check=True, capture_output=True, text=True, timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as error:
            self.aperture_value_label.setText("Aperture: --")
            detail = (
                error.stderr.strip()
                if isinstance(error, subprocess.CalledProcessError)
                and error.stderr else str(error)
            )
            self.window.statusBar().showMessage(
                f"Unable to set lens aperture: {detail}"
            )

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
        self.wait_for_recording_start()
        if self.recording:
            self.stop_recording(resume_audio_meter=False)
            self.recording = False
        self.stop_audio_meter()
        self.stop_audio_test()
        for viewer in self.media_viewers:
            viewer.close()
        self.picam2.stop()
        self.app.quit()

    def on_restart(self):
        self.wait_for_recording_start()
        if self.recording:
            self.stop_recording(resume_audio_meter=False)
            self.recording = False
        self.stop_audio_meter()
        self.stop_audio_test()
        self.battery_timer.stop()
        self.picam2.stop()
        self.picam2.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def open_media_viewer(self, media_type):
        directory = (
            self.prefs.still_save_directory if media_type == "photos"
            else self.prefs.video_save_directory
        )
        if not os.path.isdir(directory):
            QMessageBox.critical(
                self.window, "Unable to browse media",
                f"The selected folder does not exist:\n{directory}",
            )
            return
        if media_type == "photos":
            viewer = PhotoBrowser(directory)
        else:
            viewer = VideoBrowser(
                directory,
                playback_device=getattr(
                    self.prefs, "audio_playback_device", "default"
                ),
                playback_volume=getattr(self.prefs, "playback_volume", 80),
            )
        if not viewer.media_files:
            QMessageBox.information(
                self.window, "No media found",
                f"No {media_type} were found in:\n{directory}",
            )
        viewer.show()
        self.media_viewers.append(viewer)

    def run(self):
        return self.app.exec()


def run():
    return CameraApplication().run()
