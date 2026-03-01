from functools import partial
import threading
from time import sleep
from kivy.config import Config

from picam_preview import PicamPreview

Config.set('graphics', 'resizable', 0)
Config.set('graphics', 'window_state', 'maximized')
Config.set('graphics', 'borderless', 1)
Config.set('graphics', 'vsync', 1);

from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager
from picam import *

SCREEN_MANAGER = ScreenManager()
PICAM = Picam();
PICAM_PREVIEW = PicamPreview();

class PicamWidget(Screen):
    def capture(self):
        PICAM.CaptureStill()

class CameraApp(App):
    def Initialize(self):
        PICAM.OnInit();
        self.run();
    def OnDestroy(self):
        PICAM_PREVIEW.OnDestroy();
        PICAM.OnDestroy();
    def build(self):
        PICAM_PREVIEW.CreateThread(app=self);
        SCREEN_MANAGER.add_widget(PicamWidget(name='camera'))
        return SCREEN_MANAGER   
    
    def display_frame(self, frame, dt):
        self.root.get_screen('picam').ids['preview'].texture = PICAM_PREVIEW.GenerateTexture(frame);

if __name__ == '__main__':
    CameraApp().Initialize();

