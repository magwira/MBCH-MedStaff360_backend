# WorkGroup Schemas
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, field_validator


class WorkGroupBase(BaseModel):
    workgroup_name: str
    description: Optional[str] = None
    coe_id: UUID
    coe_name:str

class WorkGroupCreate(BaseModel):
    workgroup_name: str
    coe_id: UUID
    description:Optional[str]

class WorkGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class MessageResponse(BaseModel):
    message:str
    
class WorkGroupResponse(MessageResponse):
    workgroup_id: UUID
    coe_id:UUID

    class Config:
        from_attributes = True
        
class WorkgroupMemberResponse(BaseModel):
    staff_id: UUID
    fullname: str
    emp_number:str
    email: str
    position_name:str
    position_type_name:str

class WorkgroupApproverResponse(BaseModel):
    staff_id: Optional[UUID]
    fullname: Optional[str]
    emp_number: Optional[str]
    email: Optional[str]
    position_name: Optional[str]
    position_type_name: Optional[str]
    approval_level: Optional[int]

class WorkgroupInfo(BaseModel):
    workgroup_id:UUID
    workgroup_name:str
    coe_name:str
    coe_id:UUID
    
class AddMemberRequest(BaseModel):
    staff_id: UUID
    # assigned_by: UUID
    
    
class ApproverCreateRequest(BaseModel):
    staff_id: UUID
    approver_order: int
    notify_only: bool = False
    # assigned_by: UUID
class ViewWorkgroupMembers(BaseModel):
    workgroup_info:Optional[WorkgroupInfo] = None
    members:List[Optional[WorkgroupMemberResponse]] = None
    approvers:List[Optional[WorkgroupApproverResponse]] = None
    
    
class ApproverCreate(BaseModel):
    staff_id: UUID
    approver_order: int
    notify_only: Optional[bool] = False
    # assigned_by: UUID


    @field_validator("approver_order")
    def validate_approver_order(cls, value):
        if value not in {1, 2, 3, 4}:
            raise ValueError("Approver order must be 1, 2, 3, or 4")
        return value
    
class MembersQueryUsersResponse(BaseModel):
    page_number:Optional[int]
    total_num_of_members:Optional[int]
    total_number_of_pages:Optional[int]
    num_of_members_per_page:Optional[int]
    members:List[Optional[WorkgroupMemberResponse]] 
    
class DeleteResponse(BaseModel):
    message: str
    staff_id: UUID
    


class UpdategroupResponse(BaseModel):
    message: str
    workgroup_id: UUID