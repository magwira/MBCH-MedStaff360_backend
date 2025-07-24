from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Enum, Integer
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from pytz import timezone

# Define ENUM types
TitleEnum = Enum("Mr", "Mrs", "Ms", "Miss", "Dr", "Prof", name="titles")
SexEnum = Enum("Male", "Female", "Other", name="sex_types")

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    userrole_assignments = relationship("UserroleAssignment", back_populates="role")

class Staff(Base):
    __tablename__ = 'staff'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    emp_number = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    title = Column(TitleEnum, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(15), nullable=True)
    sex = Column(SexEnum, nullable=False)
    date_of_birth = Column(DateTime, nullable=True)
    home_address = Column(Text, nullable=True)
    highest_qualification = Column(String(255), nullable=True)
    field_of_study = Column(String(255), nullable=True)
    date_enganged = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_terminated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone("Africa/Blantyre")))
    updated_at = Column(DateTime, default=datetime.now(timezone("Africa/Blantyre")), 
                       onupdate=datetime.now(timezone("Africa/Blantyre")))
    
    # Foreign key to User
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), unique=True, nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="staff")

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    otp = Column(String(255), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone("Africa/Blantyre")))
    updated_at = Column(DateTime, default=datetime.now(timezone("Africa/Blantyre")), 
                       onupdate=datetime.now(timezone("Africa/Blantyre")))

    # Relationships
    staff = relationship("Staff", back_populates="user", uselist=False, cascade="all, delete-orphan")
    userrole_assignments = relationship("UserroleAssignment", back_populates="user")

class UserroleAssignment(Base):
    __tablename__ = 'userrole_assignments'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    start_date = Column(DateTime, default=datetime.now(timezone("Africa/Blantyre")))
    end_date = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="userrole_assignments")
    role = relationship("Role", back_populates="userrole_assignments")