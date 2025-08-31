from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import csv, io

router = APIRouter(prefix='/api/export', tags=['export'])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/events.csv')
def export_csv(db: Session = Depends(get_db), limit: int = Query(1000, ge=1, le=10000)):
    rows = db.query(models.Frame).order_by(models.Frame.captured_at.desc()).limit(limit).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id','workstation_id','captured_at','trigger','people_count','thumb_path'])
    for r in rows:
        writer.writerow([r.id, r.workstation_id, r.captured_at, r.trigger, r.people_count, r.thumb_path])
    return Response(content=output.getvalue(), media_type='text/csv')
