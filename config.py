# config.py — small settings file for PC Brain v0.1
# Change the values here, or pass --source on the command line.

# VIDEO_SOURCE: what the brain watches.
#   0                               -> the PC webcam (camera number 0)
#   "tests/people.mp4"               -> a video file on disk
#   "http://192.168.1.50:81/stream"  -> MJPEG stream from the ESP32 robot camera
VIDEO_SOURCE = "tests/people.mp4"

# MODEL: the YOLO model file. "yolo11n.pt" is the smallest/fastest one.
# It downloads automatically on first run (~6 MB, needs internet once).
MODEL = "yolo11n.pt"

# CONFIDENCE: only detections at least this sure are reported (0.0 - 1.0).
CONFIDENCE = 0.5

# DETECT_EVERY: run YOLO on every Nth frame (1 = every frame).
# On a normal PC without a GPU, 5 is a good balance: fast enough, still catches things.
DETECT_EVERY = 5

# SHOW_WINDOW: show the video with boxes on screen (True on Windows).
# Set False on a server, or when there is no screen.
SHOW_WINDOW = True

# LINK_PORT: the WebSocket "phone line" port (see link.py).
LINK_PORT = 8765

# TRIGGER_COOLDOWN: seconds before the same label may trigger again.
# (Stops the log from filling with the same "person" trigger 30 times a second.)
TRIGGER_COOLDOWN = 2.0
