
from picam import PICAM2

class ConfigType():
    STILL = 0;
    PREVIEW = 1;
    VIDEO = 2;

SIX_NINE_ASPECT_RATIO_4K = (3840, 2160);
SIX_NINE_ASPECT_RATIO_QHD = (2560, 1440);
SIX_NINE_ASPECT_RATIO_HD = (1920, 1080);
SIX_NINE_ASPECT_RATIO_SD = (1280, 720);
SIX_NINE_ASPECT_RATIO_qHD = (960, 540);
SIX_NINE_ASPECT_RATIO_NHD = (640, 360);
SIX_NINE_ASPECT_RATIO_144P = (256, 144);

FOUR_THREE_ASPECT_RATIO_QUXGA = (3200, 2400);
FOUR_THREE_ASPECT_RATIO_QXGA = (2048, 1536);
FOUR_THREE_ASPECT_RATIO_UXGA = (1600, 1200);
FOUR_THREE_ASPECT_RATIO_1280_960 = (1280, 960);
FOUR_THREE_ASPECT_RATIO_XGA = (1024, 768);
FOUR_THREE_ASPECT_RATIO_SVGA = (800, 600);
FOUR_THREE_ASPECT_RATIO_VGA = (640, 480);

CONFIG_MAP = {
    ConfigType.STILL: PICAM2.create_still_configuration(main={
        "format": 'RGB888', 
        "size": SIX_NINE_ASPECT_RATIO_HD,
    }),
    ConfigType.PREVIEW: PICAM2.create_preview_configuration(main={
        "format": 'RGB888', 
        "size": SIX_NINE_ASPECT_RATIO_qHD,
    }),
    ConfigType.VIDEO: PICAM2.create_video_configuration(main={
        "format": 'RGB888', 
        "size": SIX_NINE_ASPECT_RATIO_HD,
    }),
};
DEFAULT_CONFIG = ConfigType.PREVIEW;

class PicamConfig():
    def __init__(self,config_type=DEFAULT_CONFIG):
        self.config = config_type;
    def SetConfig(self, config_type):
        PICAM2.stop();
        PICAM2.configure(CONFIG_MAP[config_type]);
        PICAM2.start();
    def UpdateConfig(self, config_type, config):
        CONFIG_MAP[config_type] = config;
