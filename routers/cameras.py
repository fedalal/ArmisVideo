from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
import models, schemas
import time
from fastapi.responses import StreamingResponse

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io

router = APIRouter(prefix="/cameras", tags=["Cameras"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def mjpeg_generator(rtsp_url: str):
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
                time.sleep(1)
                continue

            _, jpeg = cv2.imencode(".jpg", frame)
            frame = jpeg.tobytes()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

    cap.release()
@router.get("/{camera_id}/stream")
def stream_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    return StreamingResponse(
        mjpeg_generator(cam.rtsp_url),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/", response_model=list[schemas.CameraOut])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(models.Camera).all()

@router.post("/", response_model=schemas.CameraOut)
def create_camera(payload: schemas.CameraCreate, db: Session = Depends(get_db)):
    cam = models.Camera(**payload.dict())
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam

@router.put("/{camera_id}", response_model=schemas.CameraOut)
def update_camera(camera_id: int, payload: schemas.CameraCreate, db: Session = Depends(get_db)):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    for key, value in payload.dict().items():
        setattr(cam, key, value)
    db.commit()
    db.refresh(cam)
    return cam

@router.delete("/{camera_id}")
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(cam)
    db.commit()
    return {"ok": True}

@router.get("/{camera_id}/snapshot")
def get_snapshot(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    cap = cv2.VideoCapture(cam.rtsp_url)
    success, frame = cap.read()
    cap.release()

    if not success or frame is None:
        # если не удалось подключиться → генерим картинку с текстом
        img = Image.new("RGB", (640, 480), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)
        text = "Cant connect to: " + cam.rtsp_url
        draw.text((100, 220), text, fill=(255, 0, 0), font_size=20)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/jpeg")

    # если удалось подключиться → отдаем кадр
    _, encoded = cv2.imencode(".jpg", frame)
    return StreamingResponse(io.BytesIO(encoded.tobytes()), media_type="image/jpeg")