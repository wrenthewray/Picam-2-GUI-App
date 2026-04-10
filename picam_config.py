


from constants import AspectRatio, ConfigType

class PicamConfig():
    PICAM2 = None;
    CONFIG_MAP = None;
    DEFAULT_CONFIG = ConfigType.PREVIEW;

    def __init__(self,picam2,config_type=DEFAULT_CONFIG):
        self.PICAM2 = picam2;
        self.CONFIG_MAP = {
            ConfigType.STILL: self.PICAM2.create_still_configuration(main={
                "format": 'RGB888', 
                "size": AspectRatio.SIX_NINE_ASPECT_RATIO_HD,
            }),
            ConfigType.PREVIEW: self.PICAM2.create_preview_configuration(main={
                "format": 'RGB888', 
                "size": AspectRatio.SIX_NINE_ASPECT_RATIO_qHD,
            }),
            ConfigType.VIDEO: self.PICAM2.create_video_configuration(main={
                "format": 'RGB888', 
                "size": AspectRatio.SIX_NINE_ASPECT_RATIO_HD,
            }),
        };
        self.config = config_type;
        
    def SetConfig(self, config_type):
        self.PICAM2.switch_mode(self.CONFIG_MAP[config_type]);
    def UpdateConfig(self, config_type, config):
        self.CONFIG_MAP[config_type] = config;
