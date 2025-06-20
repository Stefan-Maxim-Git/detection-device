from src.gst_v2_detection_app import GstDetectionApp
from src.callbacks import DetectionEventHandler

if __name__ == "__main__":
    event_handler = DetectionEventHandler()
    app = GstDetectionApp(
        event_handler.__call__,
        event_handler
        )
    try:
        app.run()
    except Exception as e:
        print(f"[main.py]\tAn error occured:\n {e}")
    