from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class Camera(Base):
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    rtsp_url = Column(String(1000), nullable=False)
    poll_interval_s = Column(Integer, nullable=False, default=5)
    enabled = Column(Boolean, default=True)
    workstations = relationship('Workstation', back_populates='camera', cascade='all, delete-orphan')

class Workstation(Base):
    __tablename__ = "workstations"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    camera_id = Column(Integer, ForeignKey('cameras.id'), nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    w = Column(Integer, nullable=False)
    h = Column(Integer, nullable=False)
    camera = relationship('Camera', back_populates='workstations')
    enabled = Column(Boolean, default=True)

class Frame(Base):
    __tablename__ = "frames"
    id = Column(Integer, primary_key=True)
    workstation_id = Column(Integer, ForeignKey('workstations.id'), nullable=False)
    captured_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    trigger = Column(String(100), nullable=False)
    people_count = Column(Integer, nullable=False, default=0)
    thumb_path = Column(String(1000), nullable=True)
    conf = Column(Integer, nullable=False, default=0)

class PresenceState(Base):
    __tablename__ = "presence_state"
    id = Column(Integer, primary_key=True)
    workstation_id = Column(Integer, ForeignKey('workstations.id'), unique=True)
    is_present = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
