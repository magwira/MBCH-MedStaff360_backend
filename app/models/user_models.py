from sqlalchemy import Enum, Integer, UniqueConstraint, Column, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from pytz import timezone
from enum import Enum as PyEnum

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    otp = Column(String(255), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone("Africa/Blantyre")))
    updated_at = Column(DateTime, default=datetime.now(timezone("Africa/Blantyre")), onupdate=datetime.now(timezone("Africa/Blantyre")))

