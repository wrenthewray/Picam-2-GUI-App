import asyncio

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
import time
from camera import UpdateCamera, CleanupCamera


class CameraWidget(BoxLayout):
    def capture(self):
        '''
        Function to capture the images and give them the names
        according to their captured time and date.
        '''
        camera = self.ids['camera']
        timestr = time.strftime("%Y%m%d_%H%M%S")
        camera.export_to_png("IMG_{}.png".format(timestr))
        print("Captured")


class CameraApp(App):
    update_camera_feed = True;
    def build(self):
        return CameraWidget()

    async def StartUpdateAsync(self):
        while self.update_camera_feed:
            UpdateCamera()

if __name__ == '__main__':
    asyncio.run(CameraApp().StartUpdateAsync())
    CameraApp().run()

def CleanupApp():
    CleanupCamera();