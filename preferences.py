from constants import *
from libcamera import controls

class Prefs():
    preview_frame_rate = FrameRate.TWENTY_FOUR_FPS
    preview_aspect_ratio = AspectRatio.SIX_BY_NINE
    preview_resolution = AspectRatioResolution.SIX_NINE_ASPECT_RATIO_HD

    video_frame_rate = FrameRate.TWENTY_FOUR_FPS
    video_aspect_ratio = AspectRatio.SIX_BY_NINE
    video_resolution = AspectRatioResolution.SIX_NINE_ASPECT_RATIO_HD

    still_aspect_ratio = AspectRatio.SIX_BY_NINE
    still_resolution = AspectRatioResolution.SIX_NINE_ASPECT_RATIO_HD

    white_balance_mode = WhiteBalanceMode.AUTO
    camera_mode = CameraMode.VIDEO # Default to video mode

    autofocus_mode = controls.AfModeEnum.Manual
    autofocus_speed = controls.AfSpeedEnum.Normal
    autofocus_range = controls.AfRangeEnum.Normal

    brightness = 0
    contrast = 0
    saturation = 0

    still_save_directory = "./home/"
    video_save_directory = "./home/"