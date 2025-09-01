from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
import models, schemas
import time
from fastapi.responses import StreamingResponse
import cv2
import numpy as np
from PIL import Image, ImageDraw
import io

router = APIRouter(prefix="/workstations", tags=["Workstations"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def mjpeg_generator(rtsp_url: str, x:int, y:int, w:int, h:int):
    cap = cv2.VideoCapture(rtsp_url)


    if not cap.isOpened():
        # бесконечный поток "заглушек"
        while True:
            img = Image.new("RGB", (640, 480), color=(200, 200, 200))
            draw = ImageDraw.Draw(img)
            text = "Cant connect to: " + rtsp_url
            draw.text((100, 220), text, fill=(255, 0, 0), font_size=20)
            _, jpeg = cv2.imencode(".jpg", np.array(img))
            frame = jpeg.tobytes()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(1)  # каждая секунда
    else:
        while True:
            success, frame = cap.read()
            if not success:
                # если камера внезапно отвалилась — продолжаем заглушками
                img = Image.new("RGB", (640, 480), color=(200, 200, 200))
                draw = ImageDraw.Draw(img)
                text = "Cant connect to: " + rtsp_url
                draw.text((100, 220), text, fill=(255, 0, 0), font_size=20)


                _, jpeg = cv2.imencode(".jpg", np.array(img))
                frame = jpeg.tobytes()
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
                # time.sleep(1)
                continue

            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            _, jpeg = cv2.imencode(".jpg", frame)
            frame = jpeg.tobytes()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

    cap.release()

# 🔹 Создать рабочее место
@router.post("/", response_model=schemas.WorkstationOut)
def create_ws(payload: schemas.WorkstationCreate, db: Session = Depends(get_db)):
    ws = models.Workstation(**payload.dict())
    db.add(ws)
    db.commit()
    db.refresh(ws)

    # ensure presence state
    from models import PresenceState
    if not db.query(PresenceState).filter_by(workstation_id=ws.id).first():
        ps = PresenceState(workstation_id=ws.id, is_present=False)
        db.add(ps)
        db.commit()

    return ws

# 🔹 Список всех рабочих мест
@router.get("/", response_model=list[schemas.WorkstationOut])
def list_ws(db: Session = Depends(get_db)):
    return db.query(models.Workstation).all()

# 🔹 Получить одно рабочее место
@router.get("/{ws_id}", response_model=schemas.WorkstationOut)
def get_ws(ws_id: int, db: Session = Depends(get_db)):
    ws = db.query(models.Workstation).filter(models.Workstation.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    return ws

# 🔹 Обновить рабочее место
@router.put("/{ws_id}", response_model=schemas.WorkstationOut)
def update_ws(ws_id: int, payload: schemas.WorkstationCreate, db: Session = Depends(get_db)):
    ws = db.query(models.Workstation).filter(models.Workstation.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")

    for key, value in payload.dict().items():
        setattr(ws, key, value)

    db.commit()
    db.refresh(ws)
    return ws

# 🔹 Удалить рабочее место
@router.delete("/{ws_id}")
def delete_ws(ws_id: int, db: Session = Depends(get_db)):
    ws = db.query(models.Workstation).filter(models.Workstation.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")

    db.delete(ws)
    db.commit()
    return {"ok": True}

@router.get("/{ws_id}/snapshot")
def get_ws_snapshot(ws_id: int, db: Session = Depends(get_db)):
    ws = db.query(models.Workstation).filter(models.Workstation.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")

    cam = db.query(models.Camera).filter(models.Camera.id == ws.camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    cap = cv2.VideoCapture(cam.rtsp_url)
    success, frame = cap.read()
    cap.release()

    if not success or frame is None:
        # Заглушка
        img = Image.new("RGB", (640, 480), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)

        text = "Cant connect to: " + cam.rtsp_url
        draw.text((100, 220), text, fill=(255, 0, 0), font_size=20)

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/jpeg")

    # Рисуем красный прямоугольник (x, y, w, h)
    x, y, w, h = ws.x, ws.y, ws.w, ws.h
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # Кодируем и возвращаем как JPEG
    _, encoded = cv2.imencode(".jpg", frame)
    return StreamingResponse(io.BytesIO(encoded.tobytes()), media_type="image/jpeg")

@router.get("/{ws_id}/stream")
def stream_camera(ws_id: int, db: Session = Depends(get_db)):
    ws = db.query(models.Workstation).filter(models.Workstation.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")

    cam = db.query(models.Camera).filter(models.Camera.id == ws.camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    return StreamingResponse(
        mjpeg_generator(cam.rtsp_url, ws.x, ws.y, ws.w, ws.h),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
