

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, constr


class EmailSendRequest(BaseModel):
    email: EmailStr
    username: str
    otp: str = constr(min_length=6, max_length=6) 

    class Config:
        from_attributes = True
        

# WorkGroup Schemas
class WorkGroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    coe_id: UUID

class WorkGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    coe_id: UUID

class WorkGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    coe_id: Optional[UUID] = None

class WorkGroupResponse(WorkGroupBase):
    id: UUID

    class Config:
        from_attributes = True