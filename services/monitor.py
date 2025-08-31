import cv2, os, time
from datetime import datetime, timezone, timedelta
from .detector import PersonDetector
from ..database import SessionLocal
from .. import models

class CameraWorker:
    def __init__(self, camera_id, model_path, thumbs_dir, poll_interval=5, absence_threshold_min=10):
        self.camera_id = camera_id
        self.model_path = model_path
        self.thumbs_dir = thumbs_dir
        self.poll_interval = poll_interval
        self.detector = PersonDetector(model_path)
        self.absence_threshold_min = absence_threshold_min

    def poll_once(self):
        with SessionLocal() as db:
            cam = db.get(models.Camera, self.camera_id)
            if not cam or not cam.enabled:
                return
            cap = cv2.VideoCapture(cam.rtsp_url)
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                return
            for ws in cam.workstations:
                people = self.detector.people_in_roi(frame, (ws.x, ws.y, ws.w, ws.h))
                now = datetime.now(timezone.utc)
                thumb = None
                if people > 0:
                    os.makedirs(self.thumbs_dir, exist_ok=True)
                    thumb = os.path.join(self.thumbs_dir, f"ws{ws.id}_{int(now.timestamp())}.jpg")
                    roi = frame[ws.y:ws.y+ws.h, ws.x:ws.x+ws.w]
                    cv2.imwrite(thumb, roi)
                # log frame
                f = models.Frame(workstation_id=ws.id, captured_at=now, trigger='heartbeat', people_count=people, thumb_path=thumb)
                db.add(f)
            db.commit()
