# Picam-2-GUI-App
This is a work in progress camera app for the Raspberry Pi HQ Camera Module, built using Python and PyQt5. It uses the Picam2 Python library to control the camera module.

## Audio and media playback

The Audio settings tab lets you enable audio on new video recordings, select
hardware devices listed by `arecord -l` and `aplay -l`, test the devices with a
five-second recording/playback, and set the app's video playback volume. Audio
recording uses Picamera2's timestamped PyAV pipeline to mux ALSA audio and video
into one MP4. Video frame timing uses the selected camera frame rate. The
main status bar shows the live microphone level and marks a near-full-scale input
as `PEAK`.

The toolbar aperture slider is enabled when a V4L2 lens subdevice with
`iris_absolute` control is detected. On compatible
[cef168 adapters](https://github.com/pinefeat/cef168), the control value is the
f-number multiplied by 100 (for example, f/5.6 is 560). The lens does not report
its current aperture, so the displayed value updates after the slider sends a
setting.

Photos and videos open in separate browsers. Video playback includes a seek
timeline, play/pause control, and elapsed/duration display. FFmpeg/ffprobe,
ALSA capture and playback support are required for the corresponding
audio and video playback features.
