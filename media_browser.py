import json
import os
import signal
import subprocess

from PyQt5 import QtCore
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSizePolicy,
    QSlider, QStyle, QStyleOptionSlider, QVBoxLayout, QWidget,
)

class ScrubSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

    def slider_value_at(self, x_position):
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QStyle.CC_Slider, option, QStyle.SC_SliderGroove, self
        )
        handle = self.style().subControlRect(
            QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self
        )
        minimum = groove.x()
        maximum = groove.right() - handle.width() + 1
        position = x_position - handle.width() // 2 - minimum
        return QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), position,
            max(1, maximum - minimum), option.upsideDown,
        )

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            super().mousePressEvent(event)
            return
        self.setSliderDown(True)
        value = self.slider_value_at(event.pos().x())
        self.setSliderPosition(value)
        self.sliderMoved.emit(value)
        event.accept()

    def mouseMoveEvent(self, event):
        if self.isSliderDown() and event.buttons() & QtCore.Qt.LeftButton:
            value = self.slider_value_at(event.pos().x())
            self.setSliderPosition(value)
            self.sliderMoved.emit(value)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton or not self.isSliderDown():
            super().mouseReleaseEvent(event)
            return
        self.setValue(self.sliderPosition())
        self.setSliderDown(False)
        event.accept()


class MediaBrowser(QMainWindow):
    VIDEO_WIDTH = 800
    VIDEO_HEIGHT = 480
    VIDEO_FRAME_BYTES = VIDEO_WIDTH * VIDEO_HEIGHT * 3
    PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}

    def __init__(
        self, directory, media_type, playback_device="default", playback_volume=80
    ):
        super().__init__()
        self.directory = directory
        self.media_type = media_type
        self.playback_device = playback_device
        self.playback_volume = playback_volume
        self.media_files = self.get_media_files()
        self.current_index = 0
        self.video_process = None
        self.audio_process = None
        self.seek_frame_process = None
        self.seek_frame_buffer = bytearray()
        self.stopping_video = False
        self.video_paused = True
        self.video_buffer = bytearray()
        self.current_image = None
        self.video_position_ms = 0
        self.video_duration_ms = 0
        self.video_has_audio = False
        self.video_elapsed_timer = QtCore.QElapsedTimer()

        self.setWindowTitle(f"Browse {media_type.title()}")
        self.resize(self.VIDEO_WIDTH, self.VIDEO_HEIGHT + 130)
        self.media_label = QLabel("No media found")
        self.media_label.setAlignment(QtCore.Qt.AlignCenter)
        self.media_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        viewer_widget = QWidget()
        viewer_layout = QVBoxLayout(viewer_widget)
        viewer_layout.setContentsMargins(8, 8, 8, 8)
        viewer_layout.addWidget(self.media_label, 1)
        if media_type == "videos":
            self.build_video_controls(viewer_layout)
        self.setCentralWidget(viewer_widget)

        previous_button = QPushButton("← Previous")
        previous_button.clicked.connect(lambda: self.show_media(-1))
        next_button = QPushButton("Next →")
        next_button.clicked.connect(lambda: self.show_media(1))
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.delete_current_media)

        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.addWidget(previous_button)
        controls_layout.addWidget(next_button)
        controls_layout.addWidget(delete_button)
        self.setMenuWidget(controls)
        self.statusBar().showMessage(directory)

        if self.media_files:
            self.display_current_media()

    def build_video_controls(self, layout):
        self.seek_slider = ScrubSlider(QtCore.Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setEnabled(False)
        self.seek_slider.setTracking(False)
        self.seek_slider.setFixedHeight(36)
        self.seek_slider.sliderPressed.connect(self.on_seek_started)
        self.seek_slider.sliderReleased.connect(self.on_seek_finished)
        self.seek_slider.sliderMoved.connect(self.update_video_time_label)
        self.seek_slider.valueChanged.connect(self.update_video_time_label)
        layout.addWidget(self.seek_slider)

        controls_widget = QWidget()
        controls_widget.setFixedHeight(42)
        controls_layout = QHBoxLayout(controls_widget)
        self.pause_button = QPushButton("Play")
        self.pause_button.clicked.connect(self.toggle_video_pause)
        self.pause_button.setEnabled(False)
        self.video_time_label = QLabel("00:00 / 00:00")
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.video_time_label)
        controls_layout.addStretch(1)
        layout.addWidget(controls_widget)

        self.playback_timer = QtCore.QTimer(self)
        self.playback_timer.setInterval(200)
        self.playback_timer.timeout.connect(self.update_video_position)
        self.seek_was_playing = False

    @staticmethod
    def format_time(milliseconds):
        seconds = max(0, milliseconds // 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"

    def probe_video(self, path):
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries",
                    "format=duration:stream=codec_type",
                    "-of", "json", path,
                ],
                check=True, capture_output=True, text=True, timeout=10,
            )
            metadata = json.loads(result.stdout)
            self.video_duration_ms = int(
                float(metadata["format"]["duration"]) * 1000
            )
            self.video_has_audio = any(
                stream.get("codec_type") == "audio"
                for stream in metadata.get("streams", [])
            )
        except (OSError, subprocess.SubprocessError, ValueError, KeyError) as error:
            self.video_duration_ms = 0
            self.video_has_audio = False
            self.statusBar().showMessage(f"Could not read video duration: {error}")
        self.seek_slider.setRange(0, self.video_duration_ms)
        self.seek_slider.setEnabled(self.video_duration_ms > 0)
        self.update_video_time_label()

    def get_media_files(self):
        extensions = (
            self.PHOTO_EXTENSIONS if self.media_type == "photos"
            else self.VIDEO_EXTENSIONS
        )
        try:
            files = [
                os.path.join(self.directory, name)
                for name in os.listdir(self.directory)
                if os.path.splitext(name)[1].lower() in extensions
                and os.path.isfile(os.path.join(self.directory, name))
            ]
            return sorted(files, key=os.path.getmtime, reverse=True)
        except OSError as error:
            QMessageBox.critical(None, "Unable to browse media", str(error))
            return []

    def display_current_media(self):
        self.stop_video()
        if not self.media_files:
            self.current_image = None
            self.media_label.clear()
            self.media_label.setText("No media found")
            self.setWindowTitle(f"Browse {self.media_type.title()}")
            if self.media_type == "videos":
                self.pause_button.setEnabled(False)
                self.seek_slider.setEnabled(False)
            return

        path = self.media_files[self.current_index]
        self.setWindowTitle(os.path.basename(path))
        self.statusBar().showMessage(
            f"{self.current_index + 1} of {len(self.media_files)} — {path}"
        )
        if self.media_type == "videos":
            self.probe_video(path)
            self.show_video_frame_at(0)
        else:
            image = QImage(path)
            if image.isNull():
                QMessageBox.critical(self, "Unable to open photo", path)
                return
            self.current_image = image
            self.update_image_display()

    def show_media(self, offset):
        if not self.media_files:
            return
        self.current_index = (self.current_index + offset) % len(self.media_files)
        self.display_current_media()

    def delete_current_media(self):
        if not self.media_files:
            return
        path = self.media_files[self.current_index]
        answer = QMessageBox.question(
            self,
            "Delete media",
            f"Delete {os.path.basename(path)}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.stop_video()
        try:
            os.remove(path)
        except OSError as error:
            QMessageBox.critical(self, "Unable to delete media", str(error))
            self.display_current_media()
            return

        self.media_files.pop(self.current_index)
        if self.current_index >= len(self.media_files):
            self.current_index = max(0, len(self.media_files) - 1)
        self.display_current_media()

    def start_video(self, path, position_ms=0, play=False):
        self.video_position_ms = min(position_ms, self.video_duration_ms)
        self.video_paused = not play
        self.pause_button.setText("Pause" if play else "Play")
        self.pause_button.setEnabled(True)
        self.seek_slider.setValue(self.video_position_ms)
        self.video_buffer.clear()
        process = QtCore.QProcess(self)
        process.setStandardErrorFile(os.devnull)
        process.started.connect(
            lambda process=process, play=play: self.handle_video_started(process, play)
        )
        process.readyReadStandardOutput.connect(
            lambda process=process: self.read_video_frames(process)
        )
        process.errorOccurred.connect(
            lambda error, process=process: self.handle_video_error(process, error)
        )
        process.finished.connect(
            lambda exit_code, exit_status, process=process:
                self.handle_video_finished(process, exit_code)
        )
        process.finished.connect(process.deleteLater)
        self.video_process = process
        process.start("ffmpeg", [
            "-nostdin", "-loglevel", "error", "-re",
            "-ss", f"{self.video_position_ms / 1000:.3f}", "-i", path,
            "-an", "-sn",
            "-vf",
            f"scale={self.VIDEO_WIDTH}:{self.VIDEO_HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={self.VIDEO_WIDTH}:{self.VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
        ])

    def show_video_frame_at(self, position_ms):
        if not self.media_files:
            return
        if self.seek_frame_process is not None:
            self.seek_frame_process.kill()
        self.video_position_ms = max(
            0, min(position_ms, self.video_duration_ms)
        )
        self.video_paused = True
        self.pause_button.setText("Play")
        self.pause_button.setEnabled(True)
        self.seek_slider.setValue(self.video_position_ms)
        self.update_video_time_label()
        self.seek_frame_buffer.clear()
        process = QtCore.QProcess(self)
        process.setStandardErrorFile(os.devnull)
        process.readyReadStandardOutput.connect(
            lambda process=process: self.read_seek_frame(process)
        )
        process.finished.connect(
            lambda exit_code, exit_status, process=process:
                self.handle_seek_frame_finished(process, exit_code)
        )
        process.finished.connect(process.deleteLater)
        process.errorOccurred.connect(
            lambda error, process=process: self.handle_seek_frame_error(process)
        )
        self.seek_frame_process = process
        process.start("ffmpeg", [
            "-nostdin", "-hide_banner", "-loglevel", "error",
            "-ss", f"{self.video_position_ms / 1000:.3f}",
            "-i", self.media_files[self.current_index],
            "-frames:v", "1",
            "-vf",
            f"scale={self.VIDEO_WIDTH}:{self.VIDEO_HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={self.VIDEO_WIDTH}:{self.VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
        ])

    def read_seek_frame(self, process):
        if process is self.seek_frame_process:
            self.seek_frame_buffer.extend(bytes(process.readAllStandardOutput()))

    def handle_seek_frame_finished(self, process, exit_code):
        if process is not self.seek_frame_process:
            return
        self.read_seek_frame(process)
        self.seek_frame_process = None
        if exit_code or len(self.seek_frame_buffer) < self.VIDEO_FRAME_BYTES:
            self.statusBar().showMessage("Unable to display the selected video frame")
            return
        self.current_image = QImage(
            bytes(self.seek_frame_buffer[:self.VIDEO_FRAME_BYTES]),
            self.VIDEO_WIDTH, self.VIDEO_HEIGHT, QImage.Format_RGB888,
        ).copy()
        self.update_image_display()

    def handle_seek_frame_error(self, process):
        if process is self.seek_frame_process:
            self.seek_frame_process = None
            self.statusBar().showMessage(
                f"Unable to seek video: {process.errorString()}"
            )

    def handle_video_started(self, process, play):
        if process is not self.video_process or self.stopping_video:
            return
        if play:
            self.begin_video_clock()
        else:
            try:
                self.pause_process(process)
            except OSError as error:
                QMessageBox.critical(self, "Unable to control video", str(error))
                return
        if self.video_has_audio and play:
            self.start_audio_playback()

    def start_audio_playback(self):
        if not self.video_files_current() or self.video_paused:
            return
        process = QtCore.QProcess(self)
        process.setStandardErrorFile(os.devnull)
        process.errorOccurred.connect(
            lambda error, process=process:
                self.handle_audio_process_error(process, error)
        )
        process.finished.connect(
            lambda exit_code, exit_status, process=process:
                self.handle_audio_finished(process, exit_code)
        )
        process.finished.connect(process.deleteLater)
        self.audio_process = process
        process.start("ffmpeg", [
            "-nostdin", "-hide_banner", "-loglevel", "error",
            "-ss", f"{self.video_position_ms / 1000:.3f}",
            "-i", self.media_files[self.current_index], "-vn",
            "-af", f"volume={self.playback_volume / 100:.2f}",
            "-f", "alsa", self.playback_device,
        ])

    def set_playback_volume(self, volume):
        self.playback_volume = volume
        self.restart_audio_playback_if_needed()

    def set_playback_device(self, device):
        self.playback_device = device
        self.restart_audio_playback_if_needed()

    def restart_audio_playback_if_needed(self):
        if self.audio_process is None or self.video_process is None:
            return
        self.update_video_position()
        was_playing = not self.video_paused
        self.stop_audio_playback()
        if was_playing:
            self.start_audio_playback()

    def stop_audio_playback(self):
        if self.audio_process is None:
            return
        process = self.audio_process
        self.audio_process = None
        MediaBrowser.terminate_process(process)

    def video_files_current(self):
        return bool(self.media_files and self.video_process is not None)

    def handle_audio_process_error(self, process, error):
        if process is self.audio_process:
            self.statusBar().showMessage(
                f"Video audio unavailable: {process.errorString()}"
            )
            self.audio_process = None

    def handle_audio_finished(self, process, exit_code):
        if process is self.audio_process:
            self.audio_process = None
            if exit_code:
                self.statusBar().showMessage("Video audio playback failed")

    def read_video_frames(self, process):
        if process is not self.video_process:
            return
        self.video_buffer.extend(bytes(process.readAllStandardOutput()))
        frame_count = len(self.video_buffer) // self.VIDEO_FRAME_BYTES
        if not frame_count:
            return
        frame_offset = (frame_count - 1) * self.VIDEO_FRAME_BYTES
        frame = bytes(self.video_buffer[frame_offset:frame_offset + self.VIDEO_FRAME_BYTES])
        del self.video_buffer[:frame_count * self.VIDEO_FRAME_BYTES]
        self.current_image = QImage(
            frame, self.VIDEO_WIDTH, self.VIDEO_HEIGHT, QImage.Format_RGB888
        ).copy()
        self.update_image_display()

    def update_image_display(self):
        if self.current_image is None:
            return
        self.media_label.setPixmap(QPixmap.fromImage(self.current_image).scaled(
            self.media_label.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        ))

    def toggle_video_pause(self):
        if self.video_process is None:
            if not self.media_files:
                return
            if self.video_duration_ms and self.video_position_ms >= self.video_duration_ms:
                self.video_position_ms = 0
            self.start_video(
                self.media_files[self.current_index],
                position_ms=self.video_position_ms,
                play=True,
            )
            return
        if self.video_paused:
            self.resume_video(self.video_process)
        else:
            self.pause_video(self.video_process)

    def pause_process(self, process):
        process_id = int(process.processId())
        if process_id:
            os.kill(process_id, signal.SIGSTOP)

    def pause_video(self, process):
        if process is not self.video_process:
            return
        try:
            self.update_video_position()
            self.pause_process(process)
        except OSError as error:
            QMessageBox.critical(self, "Unable to control video", str(error))
            return
        self.video_paused = True
        self.stop_audio_playback()
        self.playback_timer.stop()
        self.pause_button.setText("Play")

    def resume_video(self, process):
        if process is not self.video_process:
            return
        process_id = int(process.processId())
        if not process_id:
            return
        try:
            os.kill(process_id, signal.SIGCONT)
        except OSError as error:
            QMessageBox.critical(self, "Unable to control video", str(error))
            return
        self.video_paused = False
        self.pause_button.setText("Pause")
        self.begin_video_clock()
        if self.video_has_audio:
            self.start_audio_playback()

    def begin_video_clock(self):
        self.video_paused = False
        self.video_elapsed_timer.start()
        self.playback_timer.start()

    def update_video_position(self):
        if not self.video_paused and self.video_elapsed_timer.isValid():
            self.video_position_ms += self.video_elapsed_timer.restart()
            if self.video_duration_ms:
                self.video_position_ms = min(
                    self.video_position_ms, self.video_duration_ms
                )
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(self.video_position_ms)
        self.seek_slider.blockSignals(False)
        self.update_video_time_label()

    def update_video_time_label(self, position=None):
        if self.media_type != "videos":
            return
        if position is None:
            position = self.video_position_ms
        self.video_time_label.setText(
            f"{self.format_time(position)} / "
            f"{self.format_time(self.video_duration_ms)}"
        )

    def on_seek_started(self):
        self.seek_was_playing = not self.video_paused
        if self.seek_was_playing and self.video_process is not None:
            self.pause_video(self.video_process)
        self.update_video_time_label(self.seek_slider.value())

    def on_seek_finished(self):
        position = self.seek_slider.value()
        resume = self.seek_was_playing and self.video_process is not None
        self.stop_video()
        if resume:
            self.start_video(
                self.media_files[self.current_index],
                position_ms=position, play=True,
            )
        else:
            self.show_video_frame_at(position)

    def stop_video(self):
        if self.media_type == "videos":
            self.playback_timer.stop()
        self.stopping_video = True
        for process in (
            self.video_process, self.audio_process, self.seek_frame_process
        ):
            if process is not None:
                self.terminate_process(process)
        if self.video_process is not None:
            self.video_process = None
        self.audio_process = None
        self.seek_frame_process = None
        self.video_buffer.clear()
        self.video_paused = True
        if self.media_type == "videos":
            self.pause_button.setText("Play")
            self.pause_button.setEnabled(True)
        self.stopping_video = False

    @staticmethod
    def terminate_process(process):
        if process.state() == QtCore.QProcess.Starting:
            process.waitForStarted(1000)
        if process.state() != QtCore.QProcess.NotRunning:
            process.kill()

    def handle_video_error(self, process, error):
        if process is self.video_process:
            QMessageBox.critical(
                self, "Unable to play video",
                f"Could not start FFmpeg: {process.errorString()}",
            )
            self.stop_video()

    def handle_video_finished(self, process, exit_code):
        if process is not self.video_process:
            return
        self.video_process = None
        if self.audio_process is not None:
            self.audio_process.kill()
            self.audio_process = None
        self.video_paused = True
        self.pause_button.setText("Play")
        self.pause_button.setEnabled(True)
        self.playback_timer.stop()
        if not exit_code:
            self.video_position_ms = self.video_duration_ms
            self.update_video_position()
        if exit_code:
            self.statusBar().showMessage("Video playback failed")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image_display()

    def closeEvent(self, event):
        self.stop_video()
        super().closeEvent(event)


class PhotoBrowser(MediaBrowser):
    def __init__(self, directory):
        super().__init__(directory, "photos")


class VideoBrowser(MediaBrowser):
    def __init__(self, directory, playback_device="default", playback_volume=80):
        super().__init__(
            directory, "videos", playback_device=playback_device,
            playback_volume=playback_volume,
        )

