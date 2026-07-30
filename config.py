from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedLayout, QComboBox

from constants import CameraMode, SixteenNineResolution
from preferences import Prefs
from picamera2 import Picamera2
from libcamera import controls, ColorSpace

import pickle

def change_camera_config(picam2: Picamera2, mode:CameraMode, prefs: Prefs):
    picam2.stop()
    if mode == CameraMode.VIDEO:
        picam2.configure(picam2.create_video_configuration(
            buffer_count=8, 
            main={"size": prefs.video_resolution}, 
            lores={"size": (640,480)},
            controls={"FrameRate": prefs.video_frame_rate}, 
            display="lores",
            encode="main"
        ))
    elif mode == CameraMode.STILL:
        picam2.configure(picam2.create_preview_configuration(
            buffer_count=4, 
            main={"size": (640,480)}, 
            controls={"FrameRate": prefs.preview_frame_rate}
        ))
    picam2.start()

def change_layout(stacked_layout : QStackedLayout, index: int):
    stacked_layout.setCurrentIndex(index)

def change_controls(picam2: Picamera2, prefs: Prefs):
    picam2.stop()
    picam2.set_controls({
        "FrameRate": prefs.video_frame_rate if prefs.camera_mode == CameraMode.VIDEO else prefs.preview_frame_rate,
    })
    picam2.start()

def change_prefs(
    prefs: Prefs, 
    preview_frame_rate: int = None,
    still_aspect_ratio: int = None,
    still_resolution: tuple = None,
    video_frame_rate: int = None,
    video_aspect_ratio: int = None,
    video_resolution: tuple = None,
    camera_mode: CameraMode = None,
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
    if camera_mode is not None:
        prefs.camera_mode = camera_mode
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
    
