from constants import AspectRatio, FrameRate

class Preferences():
    preview_frame_rate = FrameRate.TWELVE_FPS;
    preview_aspect_ratio = AspectRatio.SIX_NINE_ASPECT_RATIO_qHD;

    video_frame_rate = FrameRate.TWENTY_FOUR_FPS;
    video_aspect_ratio = AspectRatio.SIX_NINE_ASPECT_RATIO_HD;

    still_aspect_ratio = AspectRatio.SIX_NINE_ASPECT_RATIO_HD;

    white_balance_mode = 'auto';
    autofocus = False; # currently not implemented, will be added in the future

    brightness = 0;
    contrast = 0;
    saturation = 0;