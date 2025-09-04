import os
import time
import datetime
import cv2
import numpy as np
from ultralytics import YOLO
from sqlalchemy.orm import Session
from database import SessionLocal
import models

# загружаем модель
model = YOLO("yolov10s.pt")

def process_workstations():
    db: Session = SessionLocal()
    try:
        # получаем рабочие места с enabled=True
        workstations = (
            db.query(models.Workstation)
            .filter(models.Workstation.enabled == True)
            .all()
        )

        for ws in workstations:
            camera = db.query(models.Camera).filter_by(id=ws.camera_id, enabled=True).first()
            if not camera:
                continue

            # захватываем кадр с камеры
            cap = cv2.VideoCapture(camera.rtsp_url)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                print(f"⚠️ Не удалось получить кадр с камеры {camera.name}")
                continue

            # ROI
            roi = frame[ws.y:ws.y+ws.h, ws.x:ws.x+ws.w]

            # запускаем модель
            results = model.predict(roi, verbose=False)

            person_found = 0
            conf_percent = 0.0
            for r in results:
                for box, cls, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                    if int(cls) == 0:  # класс 0 = "person"
                        person_found += 1
                        conf_percent = float(conf.item()) * 100
                        # рисуем рамку
                        x1, y1, x2, y2 = map(int, box)
                        cv2.rectangle(roi, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(
                            roi,
                            f"{conf_percent:.1f}%",
                            (x1, max(y1-10, 0)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            2, (0,255,0), 4
                        )
                        # break

            BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # корень проекта (где лежит скрипт)
            images_root = os.path.join(BASE_DIR, "images")  # папка images внутри проекта



            # создаём запись в frames

            frame_rec = models.Frame(
                workstation_id=ws.id,
                captured_at=datetime.datetime.now(),
                trigger="Поиск сотрудников",
                people_count=person_found,
                conf=conf_percent
            )
            db.add(frame_rec)
            db.commit()
            db.refresh(frame_rec)

            # имя подкаталога по дате
            date_folder = datetime.datetime.utcnow().strftime("%d%b%Y")
            folder = os.path.join(images_root, date_folder)

            # создаём папку если её нет
            os.makedirs(folder, exist_ok=True)

            # сохраняем только ROI
            filename = f"{ws.id}_{frame_rec.id}.jpg"
            filepath = os.path.join(folder, filename)
            cv2.imwrite(filepath, roi)

            # обновляем запись с путём
            frame_rec.thumb_path = filename
            db.commit()



            print(f"💾 Сохранён фрагмент {filepath}, person_found={person_found}")

    finally:
        db.close()

def main():
    while True:
        now = datetime.datetime.now().time()
        start = datetime.time(5, 30)
        end = datetime.time(20, 0)

        if start <= now <= end:
            process_workstations()
        else:
            print("⏸ Вне рабочего интервала (05:30-20:00)")

        # спим минимальный интервал
        time.sleep(10)

if __name__ == "__main__":
    main()
