from constants import *
from libcamera import controls
import os

class Prefs():
    preview_frame_rate = FrameRate.TWENTY_FOUR_FPS
    still_aspect_ratio = AspectRatio.SIXTEEN_BY_NINE
    still_resolution = SixteenNineResolution.SIXTEEN_NINE_ASPECT_RATIO_HD

    video_frame_rate = FrameRate.TWENTY_FOUR_FPS
    video_aspect_ratio = AspectRatio.SIXTEEN_BY_NINE
    video_resolution = SixteenNineResolution.SIXTEEN_NINE_ASPECT_RATIO_HD

    auto_white_balance = False
    white_balance_mode = WhiteBalanceMode.AUTO
    camera_mode = CameraMode.VIDEO # Default to video mode

    autofocus_mode = controls.AfModeEnum.Manual
    autofocus_speed = controls.AfSpeedEnum.Normal
    autofocus_range = controls.AfRangeEnum.Normal

    audio_mode = False
    bitrate = BitRate.TWENTY_POINT_FOUR_MBPS
    brightness = 0
    contrast = 0
    saturation = 0

    still_save_directory = os.path.expanduser("~/Pictures")
    video_save_directory = os.path.expanduser("~/Videos")