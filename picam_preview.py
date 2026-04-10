from functools import partial
import threading
from time import sleep
from kivy.clock import Clock
from kivy.graphics.texture import Texture

from constants import FrameRate

class PicamPreview():
    PICAM_CONTROL = None;
    PREVIEW_UPDATE_FRAME_RATE = FrameRate.TWELVE_FPS;
    allow_preview = True
    frame = None

    def __init__(self, picam_control):
        self.PICAM_CONTROL = picam_control;
    
    def GetPicamFrame(self, app):
        ''' Grabs frames from the camera and schedules 
        them to be displayed in the Kivy app. '''
        while(self.allow_preview):
            sleep(self.PREVIEW_UPDATE_FRAME_RATE)
            self.frame = self.PICAM_CONTROL.GetCurrentFrame()
            Clock.schedule_once(partial(app.display_frame, self.frame))

    def CreateThread(self, app):
        ''' Creates a thread for the camera frame method.'''
        threading.Thread(target=self.GetPicamFrame, args=(app,), daemon=True).start()

    def GenerateTexture(self, frame):
        ''' Converts a camera frame to a Kivy texture. 
        Used to display the camera preview in the Kivy app.'''
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(frame.tobytes(order=None), colorfmt='bgr', bufferfmt='ubyte')
        texture.flip_vertical()
        return texture
    
    def OnDestroy(self):
        self.allow_preview = False