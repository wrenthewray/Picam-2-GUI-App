from picamera2 import Picamera2
from picam_config import PicamConfig
from picam_control import PicamControl
from picam_preview import PicamPreview

class Globals():
    PICAM2 = Picamera2();
    PICAM_CONFIG = PicamConfig(PICAM2);
    PICAM_CONTROL = PicamControl(PICAM2, PICAM_CONFIG);
    PICAM_PREVIEW = PicamPreview(PICAM_CONTROL);