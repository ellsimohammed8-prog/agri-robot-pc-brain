#!/usr/bin/env python3
"""brain.py — PC Brain v0.1 (practice version of the robot project's PC side).

What it does:
  1. Reads a video source (webcam, video file, or MJPEG stream URL).
  2. Detects objects in the video with YOLO11n (a small, fast AI model).
  3. Draws boxes around what it sees and prints a TRIGGER line for each
     detection — that TRIGGER is the "signal" that will later tell the
     robot to act (move a part, open a door, sound an alarm).

No robot hardware is needed to run this. No cloud calls are made.
Everything runs locally on this PC.

Usage:
  python brain.py                          # uses config.VIDEO_SOURCE
  python brain.py --source 0               # webcam
  python brain.py --source tests/people.mp4  # video file (no webcam needed)
  python brain.py --source http://192.168.1.50:81/stream  # robot camera
  python brain.py --link                   # also broadcast triggers on WebSocket
  python brain.py --no-show --max-frames 200  # headless test run
"""

import argparse
import sys
import time

import cv2

import config


def parse_source(value):
    """Turn the --source text into something OpenCV understands.

    "0"          -> webcam number 0 (an int)
    "video.mp4"  -> a video file path (a string)
    "http://..." -> an MJPEG stream URL (a string)
    """
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def on_detected(label, confidence, bbox):
    """TRIGGER: called when something is detected.

    In v0.2 this is where the signal is sent to the robot.
    For now it prints one clear line (and, with --link, it is also
    broadcast over the WebSocket 'phone line' — see link.py).
    """
    x1, y1, x2, y2 = (int(v) for v in bbox)
    print(f"TRIGGER: {label} ({confidence:.2f}) at [{x1}, {y1}, {x2}, {y2}]",
          flush=True)


def main():
    parser = argparse.ArgumentParser(description="PC Brain v0.1 — see, detect, trigger.")
    parser.add_argument("--source", default=config.VIDEO_SOURCE,
                        help="0 = webcam, a file path, or an MJPEG URL "
                             f"(default: {config.VIDEO_SOURCE})")
    parser.add_argument("--model", default=config.MODEL,
                        help=f"YOLO model file (default: {config.MODEL})")
    parser.add_argument("--conf", type=float, default=config.CONFIDENCE,
                        help=f"minimum confidence 0-1 (default: {config.CONFIDENCE})")
    parser.add_argument("--every", type=int, default=config.DETECT_EVERY,
                        help=f"run YOLO every Nth frame (default: {config.DETECT_EVERY})")
    parser.add_argument("--no-show", action="store_true",
                        help="do not open a video window (headless / server)")
    parser.add_argument("--max-frames", type=int, default=0,
                        help="stop after N frames (0 = run until the video ends)")
    parser.add_argument("--link", action="store_true",
                        help="also broadcast triggers on WebSocket (see link.py)")
    args = parser.parse_args()

    show_window = config.SHOW_WINDOW and not args.no_show

    # --- Load the model (downloads yolo11n.pt on first run, ~6 MB) ---
    print(f"Loading model {args.model} ... (first run downloads it, ~6 MB)")
    from ultralytics import YOLO
    model = YOLO(args.model)
    print(f"Model ready. Labels it knows: {len(model.names)} "
          f"(person, car, dog, chair, ...).")

    # --- Open the video source ---
    source = parse_source(str(args.source))
    print(f"Opening video source: {args.source!r}")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"ERROR: could not open video source {args.source!r}")
        print("  - webcam? try --source 0 and close other apps using the camera")
        print("  - file? check the path exists: ls tests/")
        print("  - MJPEG URL? check the robot is on and the URL is right")
        sys.exit(1)

    # --- Optional: start the WebSocket 'phone line' in the background ---
    link = None
    if args.link:
        from link import start_link_server_in_thread
        link = start_link_server_in_thread(config.LINK_PORT)
        print(f"Link server started on ws://localhost:{config.LINK_PORT}")

    print("Running — press 'q' in the video window to stop (or Ctrl+C).")
    print("---")

    last_trigger = {}   # label -> time of its last TRIGGER (cooldown)
    frames_read = 0
    frames_checked = 0
    detections = 0
    triggers = 0
    started = time.time()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("End of video (or stream lost).")
                break
            frames_read += 1
            if args.max_frames and frames_read >= args.max_frames:
                print(f"Reached --max-frames {args.max_frames}.")
                break

            # Only run the (slow) AI on every Nth frame; other frames are
            # just shown. This is what keeps it fast on a normal CPU.
            if frames_read % args.every != 0:
                if show_window:
                    cv2.imshow("PC Brain v0.1 - press q to stop", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                continue

            frames_checked += 1
            results = model(frame, conf=args.conf, verbose=False)
            for box in results[0].boxes:
                label = model.names[int(box.cls[0])]
                confidence = float(box.conf[0])
                bbox = [float(v) for v in box.xyxy[0]]
                detections += 1

                # Draw the box + label on the frame.
                x1, y1, x2, y2 = (int(v) for v in bbox)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} {confidence:.2f}",
                            (x1, max(y1 - 8, 0)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 0), 2)

                # TRIGGER, but at most once per label per cooldown period.
                now = time.time()
                if now - last_trigger.get(label, 0) >= config.TRIGGER_COOLDOWN:
                    last_trigger[label] = now
                    triggers += 1
                    on_detected(label, confidence, bbox)
                    if link is not None:
                        link.send_trigger(label, confidence)

            if show_window:
                try:
                    cv2.imshow("PC Brain v0.1 - press q to stop", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                except cv2.error:
                    print("No screen available — continuing without a window.")
                    show_window = False
    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C).")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    elapsed = max(time.time() - started, 0.001)
    print("---")
    print(f"Done. Frames read: {frames_read}, frames checked by YOLO: "
          f"{frames_checked}, detections: {detections}, triggers: {triggers}, "
          f"speed: {frames_checked / elapsed:.1f} checked frames/second.")


if __name__ == "__main__":
    main()
