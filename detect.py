import os
import time
import datetime
import cv2
import numpy as np
from ultralytics import YOLO
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import json

# загружаем модель
model = YOLO("yolov10s.pt")
model_work = YOLO("last_armis_cls_22Nov2025.pt")

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

            # === ROI ===
            polygon = None
            poly_data = getattr(ws, "polygon_points", None)

            if poly_data:
                try:
                    # 1️⃣ если пришло как строка JSON — парсим
                    if isinstance(poly_data, str):
                        poly_data = json.loads(poly_data)

                    # 2️⃣ если это список словарей — превращаем в список координат
                    if isinstance(poly_data, list) and all(isinstance(p, dict) for p in poly_data):
                        polygon = [[int(p["x"]), int(p["y"])] for p in poly_data]

                    # 3️⃣ если это список списков — используем напрямую
                    elif isinstance(poly_data, list) and all(isinstance(p, (list, tuple)) for p in poly_data):
                        polygon = [[int(p[0]), int(p[1])] for p in poly_data]

                    if polygon and len(polygon) >= 3:
                        pts = np.array(polygon, np.int32)

                        # создаём маску и заполняем полигон
                        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
                        cv2.fillPoly(mask, [pts], 255)

                        # накладываем маску
                        masked = cv2.bitwise_and(frame, frame, mask=mask)

                        # обрезаем по bounding box
                        x, y, w, h = cv2.boundingRect(pts)
                        roi = masked[y:y + h, x:x + w]
                    else:
                        raise ValueError("polygon_points пуст или некорректен")

                except Exception as e:
                    print(f"⚠️ Ошибка polygon_points для ws {ws.id}: {e}")
                    roi = frame[ws.y:ws.y + ws.h, ws.x:ws.x + ws.w]
            else:
                roi = frame[ws.y:ws.y + ws.h, ws.x:ws.x + ws.w]

            # запускаем модель
            results = model.predict(roi, verbose=False)

            person_found = 0
            conf_percent = 0.0
            job_type = 0
            for r in results:
                for box, cls, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                    if int(cls) == 0:  # класс 0 = "person"

                        curr_persent = float(conf.item()) * 100
                        if curr_persent > conf_percent:
                            conf_percent = curr_persent

                        if curr_persent > 50:
                            person_found += 1
                            # рисуем рамку
                            x1, y1, x2, y2 = map(int, box)

                            crop = roi[y1:y2, x1:x2]
                            cv2.imwrite("test1.jpg", crop)
                            cls_results = model_work.predict(crop)

                            try:
                                cr = cls_results[0]
                                cls_id = int(cr.probs.top1)
                                cls_name = cr.names[cls_id]
                                cls_conf = float(cr.probs.top1conf)
                            except Exception as e:
                                cls_id = -1
                                cls_name = ""
                                cls_conf = 0


                            if cls_name == "work_cropped":
                                job_color = (0, 255, 0)
                                cur_job_type = 3
                            elif cls_name == "phone_cropped":
                                job_color = (0, 0, 255)
                                cur_job_type = 2
                            else:
                                job_color = (255, 0, 0)
                                cur_job_type = 1

                            if cur_job_type > job_type:
                                job_type = cur_job_type

                            cv2.rectangle(roi, (x1, y1), (x2, y2), job_color, 2)
                            cv2.putText(
                                roi,
                                f"{conf_percent:.1f}%",
                                (x1, max(y1-10, 0)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                2, (0,255,0), 4
                            )

                            # проверяем, работает человек на вырезанном фрагменте или нет

                            # break

            BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # корень проекта (где лежит скрипт)
            images_root = os.path.join(BASE_DIR, "images")  # папка images внутри проекта



            # создаём запись в frames

            frame_rec = models.Frame(
                workstation_id=ws.id,
                captured_at=datetime.datetime.now(),
                trigger="Поиск сотрудников",
                people_count=person_found,
                conf=conf_percent,
                job_type = job_type
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
            frame_rec.thumb_path = date_folder + '/' +filename
            db.commit()



            print(f"💾 Сохранён фрагмент {filepath}, person_found={person_found}, job_type={job_type}")

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
