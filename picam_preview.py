from functools import partial
import threading
from time import sleep
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from picam import Picam

PICAM = Picam();

SIXTY_FPS = 1 / 60;
FIFTY_NINE_POINT_NINE_FOUR_FPS = 1 / 59.94;
FOURTY_EIGHT_FPS = 1 / 48;
THIRTY_FPS = 1 / 30;
TWENTY_FIVE_FPS = 1 / 25;
TWENTY_FOUR_FPS = 1 / 24;
TWELVE_FPS = 1 / 12;

class PicamPreview():
    PREVIEW_UPDATE_FRAME_RATE = SIXTY_FPS;
    allow_preview = True
    frame = None

    def GetPicamFrame(self, app):
        ''' Grabs frames from the camera and schedules 
        them to be displayed in the Kivy app. '''
        while(self.allow_preview):
            sleep(self.PREVIEW_UPDATE_FRAME_RATE)
            self.frame = PICAM.GetCurrentFrame()
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