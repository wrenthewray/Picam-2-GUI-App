from datetime import datetime
from constants import ConfigType
from picamera2.encoders import H264Encoder, Quality
import os


class PicamControl():
    PICAM2 = None;
    PICAM_CONFIG = None;
    DEFAULT_IMG_PATH = f"{os.environ['HOME']}/Pictures/IMG_";
    DEFAULT_VID_PATH = f"{os.environ['HOME']}/Videos/VID_";

    encoder = H264Encoder(framerate=12);
    last_frame = None;
    recording = False;

    def __init__(self, picam2, picam_config):
        self.PICAM2 = picam2;
        self.PICAM_CONFIG = picam_config;
    
    def OnInit(self):
        self.PICAM_CONFIG.SetConfig(ConfigType.PREVIEW);
        self.PICAM2.start();

    def GetCurrentFrame(self):
        if self.PICAM2.started:
            self.last_frame = self.PICAM2.capture_array("main");
        return self.last_frame;

    def OnDestroy(self):
        self.PICAM2.stop();

    def CaptureStill(self):
        self.PICAM_CONFIG.SetConfig(ConfigType.STILL);
        self.PICAM2.capture_file(self.DEFAULT_IMG_PATH + f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.jpg");
        self.PICAM_CONFIG.SetConfig(ConfigType.PREVIEW);
    
    def ToggleRecording(self, image):
        self.recording = not self.recording;
        if self.recording:
            self.StartRecording();
            image.source = "images/stop_button.png"
        else:
            self.StopRecording();
            image.source = "images/record_button.png"
    
    def StartRecording(self):
        self.PICAM_CONFIG.SetConfig(ConfigType.VIDEO);
        self.PICAM2.start_encoder(self.encoder, self.DEFAULT_VID_PATH + f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.h264", quality=Quality.HIGH);
    
    def StopRecording(self):
        self.PICAM2.stop_encoder();
        self.PICAM_CONFIG.SetConfig(ConfigType.PREVIEW);