from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.api.v1.admin.schemas import (
    GenderEnum,
    StaffGrantDetails,
    StaffRoleDetails,
    )


class TitleEnum(str,Enum):
    Mr = "Mr" 
    Mrs = "Mrs"
    Ms = "Ms"
    Dr = "Dr"
    Prof = "Prof"
    
class UpdateUserSchema(BaseModel):
    is_active:Optional[bool]
    is_verified:Optional[bool]
    
   
class UpdateStaffSchema(BaseModel):
    first_name:Optional[str] = None
    last_name:Optional[str] = None
    email:Optional[str] = None
    emp_number:Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[GenderEnum] = None
    home_address: Optional[str] = None
    highest_education: Optional[str] = None
    field_of_study: Optional[str] = None
    title:Optional[TitleEnum] = None

class UpdateUserRoles(BaseModel):
    new_role_id: Optional[UUID]
    terminate:Optional[bool] = False
    
class UpdateStaffDept(BaseModel):
    new_dept_id: Optional[UUID]
    
class UpdateStaffGrants(BaseModel):
    new_grant_id: Optional[UUID]
    work_time_percentage:Optional[float]
    terminate: Optional[bool] = False
    
class UpdateStaffCoE(BaseModel):
    new_coe_id:Optional[UUID]
    
class UpdateStaffPosition(BaseModel):
    new_position_id:Optional[UUID]
    
    
class UpdateUserAndStaffSchema(BaseModel):
    staff: Optional[UpdateStaffSchema] = None
    user: Optional[UpdateUserSchema] = None
    position:Optional[UpdateStaffPosition] = None
    roles:Optional[List[UpdateUserRoles]] = None
    depertments:Optional[UpdateStaffDept] = None
    coe:Optional[UpdateStaffCoE] = None
    grants:Optional[List[UpdateStaffGrants]] = None



class CoEDetails(BaseModel):
    coe_id:UUID
    coe_name:str
    
class DeptDetails(BaseModel):
    department_id:UUID
    department_name:str
    directorate_id:UUID
    directorate_name:str

class PositionDetails(BaseModel):
    position_id:UUID
    position_name:str
    position_type_id:UUID
    position_type_name:str
    
class HRStaffDetails(BaseModel):
    staff_id: UUID
    first_name: str
    last_name: str
    fullname: Optional[str]  
    emp_number: str
    email: EmailStr
    phone:Optional[str]
    gender: Optional[str] = None  
    dob:Optional[date]
    home_address:Optional[str]
    highest_education:Optional[str]
    field_of_study:Optional[str]
    date_of_employment: Optional[str] = None  
    position: Optional[PositionDetails] = None
    coe: Optional[CoEDetails] = None
    department: Optional[DeptDetails] = None
    is_terminated:Optional[bool]
    grants: List[StaffGrantDetails]
    roles:List[StaffRoleDetails]
    

class HRStaffResponse(BaseModel):
    page_number:Optional[int]
    total_num_of_staffs:Optional[int]
    total_number_of_pages:Optional[int]
    num_of_staffs_per_page:Optional[int]
    staffs:List[Optional[HRStaffDetails]]
    