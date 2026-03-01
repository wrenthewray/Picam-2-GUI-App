from datetime import datetime
from picamera2 import Picamera2
from picam_config import ConfigType, PicamConfig
import os

DEFAULT_IMG_PATH = f"{os.environ['HOME']}/Pictures/IMG_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.jpg";
PICAM2 = Picamera2();
PICAM_CONFIG = PicamConfig();

class Picam():
    last_frame = None;

    def OnInit(self):
        PICAM_CONFIG.SetConfig(ConfigType.PREVIEW);
        PICAM2.start();

    def GetCurrentFrame(self):
        if PICAM2.started:
            self.last_frame = PICAM2.capture_array("main");
        return self.last_frame;

    def OnDestroy(self):
        PICAM2.stop();

    def CaptureStill(self):
        PICAM_CONFIG.SetConfig(ConfigType.STILL);
        PICAM2.capture_file(DEFAULT_IMG_PATH);
        PICAM_CONFIG.SetConfig(ConfigType.PREVIEW);
