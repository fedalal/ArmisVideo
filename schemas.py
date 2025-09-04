from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CameraCreate(BaseModel):
    name: str
    rtsp_url: str
    poll_interval_s: int = Field(ge=1, default=5)
    enabled: bool = True

class CameraOut(CameraCreate):
    id: int
    model_config = {
        "from_attributes": True
    }

class WorkstationCreate(BaseModel):
    name: str
    camera_id: int
    x: int
    y: int
    w: int
    h: int
    enabled: bool
class WorkstationOut(WorkstationCreate):
    id: int
    model_config = {
        "from_attributes": True
    }

class FrameOut(BaseModel):
    id: int
    workstation_id: int
    captured_at: datetime
    trigger: str
    people_count: int
    thumb_path: Optional[str]
    conf: int
    model_config = {
        "from_attributes": True
    }
