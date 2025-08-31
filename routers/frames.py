from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import SessionLocal
import models, schemas

router = APIRouter(prefix='/api/frames', tags=['frames'])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/', response_model=list[schemas.FrameOut])
def recent_frames(db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=1000)):
    return db.query(models.Frame).order_by(models.Frame.captured_at.desc()).limit(limit).all()
