# Minimal wrapper for ultralytics YOLO model
from ultralytics import YOLO
import numpy as np

class PersonDetector:
    def __init__(self, model_path: str):
        try:
            self.model = YOLO(model_path)
        except Exception:
            self.model = None

    def people_in_roi(self, frame_bgr, roi):
        x,y,w,h = roi
        crop = frame_bgr[y:y+h, x:x+w]
        if crop.size == 0 or self.model is None:
            return 0
        results = self.model.predict(source=crop[:,:,::-1], imgsz=640, conf=0.4, classes=[0], verbose=False)
        if not results or results[0].boxes is None:
            return 0
        return len(results[0].boxes)
