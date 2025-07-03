from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import date, datetime

# from sqlalchemy import Float

class AssignStaffRequest(BaseModel):
    staff_id: UUID
    new_assign_id: UUID

class AssignUserRequest(BaseModel):
    user_id: UUID
    new_assign_id: UUID
    
    
class AssignStaffGrantRequest(BaseModel):
    staff_id: UUID
    new_assign_id: UUID
    work_time_percentage: float = Field(..., ge=0, le=100, description="Percentage of work time assigned (0-100%)")
    
class AssignmentResponse(BaseModel):
    success: bool
    detail: str


# Pydantic Schema for Staff Creation
class StaffCreateSchema(BaseModel):
    first_name: str
    last_name: str
    email: str
    gender: str
    directorate_id: UUID
    department_id: UUID
    position_id: UUID
    employment_number: str
    coe_id: UUID
    grants: List[UUID]  # List of grant UUIDs

    class Config:
        from_attribute = True
        
        
class StaffWorkgroupAssignmentCreate(BaseModel):
    workgroup_id: UUID
    staff_id: UUID
    
    
class ApproverCreate(BaseModel):
    workgroup_id: UUID
    staff_id: UUID
    approver_order: int = Field(..., ge=1, description="Order of the approver in the approval chain")
    notify_only: bool = Field(default=False)
    

class GrantResponse(BaseModel):
    id: UUID
    name: str
    grant_number: str
    description:Optional[str]

class GeneralResponse(BaseModel):
    id:UUID
    name:str
    description:Optional[str]
    

class CoEResponse(BaseModel):
    id: UUID
    coe_number:str
    name:str
    center_name:str
    description:Optional[str]

class DeptResponse(BaseModel):
    department_id:UUID
    department_name:str
    directorate_id:UUID
    directorate_name:str
    

class PositionResponse(BaseModel):
    position_id:UUID
    position_name:str
    position_category:str
    position_category_id:UUID
    description:Optional[str]
    



class PublicHolidayResponse(BaseModel):
    id: UUID
    date: datetime
    name: str
    

   
class GenderEnum(str,Enum):
    Male = "Male"
    Female = "Female"

class StaffGrants(BaseModel):
    grant_id:UUID
    time_allocated:int

class UserRoles(BaseModel):
    role_id:UUID
    
    
class CreateStaff(BaseModel):
    emp_number:str
    first_name:str
    last_name:str
    email: EmailStr
    gender:GenderEnum
    department_id: UUID
    position_id:UUID
    position_seriority:Optional[bool] = False
    work_station_id:UUID
    grants:List[StaffGrants]
    roles:List[UserRoles]
    
class StaffCreatedResponse(BaseModel):
    message: str
    staff_id: UUID
    

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
    

class StaffRoleDetails(BaseModel):
    role_id:UUID
    role_name:str



class AdminUserResponse(BaseModel):
    user_id: UUID
    username: str
    fullname:str
    roles: List[StaffRoleDetails]
    is_active: bool
    is_verified:bool
    is_terminated:bool
    updated_at: datetime

    class Config:
        from_attribute = True

class ResetUserPasswordResponse(BaseModel):
    message:str

class UserResponse(BaseModel):
    user_id: UUID
    username: str
    roles:List[StaffRoleDetails]
    is_active: bool
    is_verified: bool
    has_otp:bool
    otp:Optional[str] = None
    created_at: str
    updated_at: str
    staff_details: Optional[StaffDetails]
    
    class Config:
        from_attribute = True
class ViewUserResponse(BaseModel):
    user_id: UUID
    username: str
    roles:List[StaffRoleDetails]
    is_active: bool
    is_verified: bool
    has_otp:bool
    otp:Optional[str] = None
    created_at: str
    updated_at: str
    staff_details: Optional[StaffDetails]
    
    class Config:
        from_attribute = True
        
        
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

class AdminQueryUsersResponse(BaseModel):
    page_number:Optional[int]
    total_num_of_users:Optional[int]
    total_number_of_pages:Optional[int]
    num_of_staffs_per_page:Optional[int]
    users:List[Optional[AdminUserResponse]]