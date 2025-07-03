from datetime import date
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID

from app.api.v1.admin.schemas import GenderEnum, TitleEnum


class StaffRoleDetails(BaseModel):
    role_id:UUID
    role_name:str

class StaffGrantDetails(BaseModel):
    grant_id: UUID
    grant_name: str
    grant_number: str
    work_time_percentage: float


class StaffDetails(BaseModel):
    staff_id: UUID
    first_name: str
    last_name: str
    fullname: Optional[str]  
    emp_number: str
    email: EmailStr
    phone:Optional[str] = None
    gender: Optional[str] = None
    dob:Optional[date]  = None
    home_address :Optional[str] = None
    highest_education:Optional[str] = None
    field_of_study :Optional[str] = None
    date_of_employment: Optional[str] = None  
    position: Optional[str] = None
    position_type: Optional[str] = None
    coe: Optional[str] = None
    department: Optional[str] = None
    directorate:Optional[str] = None
    grants: List[StaffGrantDetails]



class UserResponse(BaseModel):
    user_id: UUID
    username: str
    roles:List[StaffRoleDetails]
    is_active: bool
    is_verified: bool
    created_at: str
    updated_at: str
    staff_details: Optional[StaffDetails]




class UpdateUserSchema(BaseModel):
    new_password: str = Field(..., min_length=8, example="password1234")
    verify_password:str = Field(..., min_length=8, example="password1234")

class UpdateStaffSchema(BaseModel):
    title:Optional[TitleEnum]
    phone: Optional[str]
    gender: Optional[GenderEnum]
    home_address: Optional[str]
    highest_education: Optional[str]
    field_of_study: Optional[str]


class MessageResponse(BaseModel):
    message:str