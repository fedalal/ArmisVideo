from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
import models, schemas

router = APIRouter(prefix='/api/workstations', tags=['workstations'])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post('/', response_model=schemas.WorkstationOut)
def create_ws(payload: schemas.WorkstationCreate, db: Session = Depends(get_db)):
    ws = models.Workstation(**payload.dict())
    db.add(ws)
    db.commit()
    db.refresh(ws)
    # ensure presence state
    from ..models import PresenceState
    if not db.query(PresenceState).filter_by(workstation_id=ws.id).first():
        ps = PresenceState(workstation_id=ws.id, is_present=False)
        db.add(ps); db.commit()
    return ws
