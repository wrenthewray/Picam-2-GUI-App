from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedLayout, QComboBox

from constants import CameraMode
from preferences import Prefs
from picamera2 import Picamera2
from libcamera import controls

import pickle

def change_camera_config(picam2: Picamera2, mode:CameraMode, prefs: Prefs):
    if mode == CameraMode.VIDEO:
        picam2.configure(picam2.create_video_configuration(buffer_count=8, main={"size": prefs.video_resolution}, controls={"FrameRate": prefs.video_frame_rate}))
    elif mode == CameraMode.STILL:
        picam2.configure(picam2.create_preview_configuration(buffer_count=4, main={"size": prefs.still_resolution}, controls={"FrameRate": prefs.preview_frame_rate}))

def change_layout(stacked_layout : QStackedLayout, index: int):
    stacked_layout.setCurrentIndex(index)

def change_controls(prefs: Prefs):
    picam2.set_controls({
        "FrameRate": prefs.video_frame_rate if prefs.camera_mode == CameraMode.VIDEO else prefs.preview_frame_rate,
        "BitRate": prefs.bitrate,
        "AfMode": prefs.autofocus_mode, 
        "Brightness": prefs.brightness, 
        "Contrast": prefs.contrast, 
        "Saturation": prefs.saturation
    })

def change_prefs(
    prefs: Prefs, 
    preview_frame_rate: int = None,
    still_aspect_ratio: int = None,
    still_resolution: tuple = None,
    video_frame_rate: int = None,
    video_aspect_ratio: int = None,
    video_resolution: tuple = None,
    autofocus: controls.AfModeEnum = None, 
    autofocus_speed: controls.AfSpeedEnum = None, 
    autofocus_range: controls.AfRangeEnum = None, 
    audio_mode: bool = None, 
    bitrate: int = None,
    brightness: int = None, 
    contrast: int = None, 
    saturation: int = None, 
    still_save_directory: str = None, 
    video_save_directory: str = None):
    if preview_frame_rate is not None:
        prefs.preview_frame_rate = preview_frame_rate
    if still_aspect_ratio is not None:
        prefs.still_aspect_ratio = still_aspect_ratio
    if still_resolution is not None:
        prefs.still_resolution = still_resolution
    if video_frame_rate is not None:
        prefs.video_frame_rate = video_frame_rate
    if video_aspect_ratio is not None:
        prefs.video_aspect_ratio = video_aspect_ratio
    if video_resolution is not None:    
        prefs.video_resolution = video_resolution
    if autofocus is not None:
        prefs.autofocus_mode = autofocus
    if autofocus_speed is not None:
        prefs.autofocus_speed = autofocus_speed
    if autofocus_range is not None:
        prefs.autofocus_range = autofocus_range
    if audio_mode is not None:
        prefs.audio_mode = audio_mode
    if bitrate is not None:
        prefs.bitrate = bitrate
    if brightness is not None:
        prefs.brightness = brightness
    if contrast is not None:
        prefs.contrast = contrast
    if saturation is not None:
        prefs.saturation = saturation
    if still_save_directory is not None:
        prefs.still_save_directory = still_save_directory
    if video_save_directory is not None:
        prefs.video_save_directory = video_save_directory
    try:
        with open("prefs.pkl", "wb") as f:
            pickle.dump(prefs, f)
    except Exception as e:
        print(f"Error saving preferences: {e}")
