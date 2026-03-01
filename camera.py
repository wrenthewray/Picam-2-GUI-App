from time import sleep
from picamera2 import Picamera2, Preview
import os
import cv2

home_dir = os.environ['HOME'];
picam2 = Picamera2();
camera_config = picam2.create_preview_configuration();

picam2.configure(camera_config);
picam2.start();

def UpdateCamera():
    sleep(0.1);
    frame = picam2.capture_array();
    cv2.imshow("Camera", frame);
    if cv2.waitKey(1) & 0xFF == ord('q'):
        pass;

def CleanupCamera():
    cv2.destroyAllWindows();
    picam2.stop();