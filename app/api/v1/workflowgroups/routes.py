from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from app.api.v1.admin.schemas import ApproverCreate
from app.api.v1.auth.utils import verify_admin
from app.models.models  import Approver, Position, PositionType, Role, Staff, StaffCoEAssignment, StaffPositionAssignment, StaffWorkgroupAssignment, User, UserRoleAssignment, WorkGroup
from app.api.v1.workflowgroups.constants import ALLOWED_POSITION_TYPES, APPROVER_ORDERS, APPROVER_ROLES, HR_ORDERS
from app.utils.helper import WorkFlowGroupsManager, get_full_name
from sqlalchemy.orm import Session, joinedload
from app.api.v1.workflowgroups.schemas import AddMemberRequest, ApproverCreateRequest, DeleteResponse, MembersQueryUsersResponse, UpdategroupResponse, ViewWorkgroupMembers, WorkGroupCreate, WorkGroupResponse, WorkGroupUpdate, WorkgroupApproverResponse, WorkgroupInfo, WorkgroupMemberResponse
from app.database import get_db
from uuid import UUID

workgroupRouter = APIRouter(prefix="/api/v1/workgroups", tags=["WorkGroups - Management"])



@workgroupRouter.post("/create_new", response_model=WorkGroupResponse, status_code=status.HTTP_201_CREATED)
def create_new_workgroup(workgroup_data: WorkGroupCreate, db: Session = Depends(get_db)):
    work_flow_group_manager = WorkFlowGroupsManager(db_session=db)
    new_workgroup = work_flow_group_manager.create_workgroup(
        coe_id=workgroup_data.coe_id,
        name=workgroup_data.workgroup_name,
        desc=workgroup_data.description
        )
    
    hr_officer_query = (
    db.query(Staff)
    .join(User, User.staff_id == Staff.id)
    .join(UserRoleAssignment, User.id == UserRoleAssignment.user_id)
    .join(Role, UserRoleAssignment.role_id == Role.id)
    .join(StaffPositionAssignment, Staff.id == StaffPositionAssignment.staff_id)
    .join(Position, StaffPositionAssignment.position_id == Position.id)
    .join(PositionType, Position.position_type_id == PositionType.id)
    .filter(
        Role.name == "HR",
        PositionType.name == "Officer",
        UserRoleAssignment.end_date.is_(None),
        StaffPositionAssignment.end_date.is_(None)
    )
    .one_or_none()
    )
    
    new_approver = Approver(
            workgroup_id=new_workgroup.id,
            staff_id=hr_officer_query.id,
            approver_order=3,
            notify_only=True,
            start_date=datetime.now(timezone.utc),
            end_date=None
        )
    db.add(new_approver)

    hr_manager_query = (
    db.query(Staff)
    .join(User, User.staff_id == Staff.id)
    .join(UserRoleAssignment, User.id == UserRoleAssignment.user_id)
    .join(Role, UserRoleAssignment.role_id == Role.id)
    .join(StaffPositionAssignment, Staff.id == StaffPositionAssignment.staff_id)
    .join(Position, StaffPositionAssignment.position_id == Position.id)
    .join(PositionType, Position.position_type_id == PositionType.id)
    .filter(
        Role.name == "HR",
        PositionType.name == "Manager",
        UserRoleAssignment.end_date.is_(None),
        StaffPositionAssignment.end_date.is_(None)
    )
    .one_or_none()
    )
    
    new_approver = Approver(
    workgroup_id=new_workgroup.id,
    staff_id=hr_manager_query.id,
    approver_order=4,
    notify_only=True,
    start_date=datetime.now(timezone.utc),
    end_date=None
    )
    db.add(new_approver)

    db.commit() 
    
    return WorkGroupResponse(
        message="Workgroup created successfully",
        workgroup_id=new_workgroup.id,
        coe_id=new_workgroup.coe_id
    )



@workgroupRouter.post("/add-member-to-workgroup/{workgroup_id}")
def add_workgroup_member(workgroup_id: UUID, request: AddMemberRequest, db: Session = Depends(get_db)):
    # Check if the workgroup exists
    workgroup = db.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
    if not workgroup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

    # Check if the staff exists
    staff = db.query(Staff).filter(Staff.id == request.staff_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

    # # Check if the user assigning exists
    # assigned_by_user = db.query(User).filter(User.id == request.assigned_by).first()
    # if not assigned_by_user:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigning user not found")

    # Check if the staff is already a member of the workgroup
    existing_assignment = db.query(StaffWorkgroupAssignment).filter(
        StaffWorkgroupAssignment.workgroup_id == workgroup_id,
        StaffWorkgroupAssignment.staff_id == request.staff_id,
        StaffWorkgroupAssignment.end_date.is_(None)
    ).first()

    if existing_assignment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staff is already a member of the workgroup")

    # Add new member to the workgroup
    new_member = StaffWorkgroupAssignment(
        workgroup_id=workgroup_id,
        staff_id=request.staff_id,
        start_date=datetime.now(timezone.utc),
        # assigned_by=request.assigned_by
    )
    
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return {"message": "Member added successfully", "staff_id": str(request.staff_id)}


@workgroupRouter.post("/add-multiple-members-to-workgroup/{workgroup_id}")
def add_multiple_workgroup_members(workgroup_id: UUID, requests: List[AddMemberRequest], db: Session = Depends(get_db)):
    # Check if the workgroup exists
    workgroup = db.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
    if not workgroup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

    added_members = []
    for request in requests:
        # Check if the staff exists
        staff = db.query(Staff).filter(Staff.id == request.staff_id).first()
        if not staff:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staff with ID {request.staff_id} not found")

        # Check if the staff is already a member of the workgroup
        existing_assignment = db.query(StaffWorkgroupAssignment).filter(
            StaffWorkgroupAssignment.workgroup_id == workgroup_id,
            StaffWorkgroupAssignment.staff_id == request.staff_id,
            StaffWorkgroupAssignment.end_date.is_(None)
        ).first()

        if not existing_assignment:
           # Add new member to the workgroup
            new_member = StaffWorkgroupAssignment(
                workgroup_id=workgroup_id,
                staff_id=request.staff_id,
                start_date=datetime.now(timezone.utc),
            )
            
            db.add(new_member)
            added_members.append(request.staff_id)

    db.commit()

    return {"message": "Members added successfully", "staff_ids": [str(staff_id) for staff_id in added_members]}

   
@workgroupRouter.post("/add-approvers-to-workgroup/{workgroup_id}")
def add_approver_to_workgroup(
    workgroup_id: UUID, 
    approver_data: ApproverCreate, 
    db: Session = Depends(get_db)
):
    # Fetch staff member
    staff = db.query(Staff).filter(Staff.id == approver_data.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    roles = db.query(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == staff.user.id,
        UserRoleAssignment.end_date == None
    ).all()
    
   
    # Validate staff role

    staff_roles = {role.role.name for role in roles}

    if not APPROVER_ROLES.intersection(staff_roles):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staff does not have a valid approver role")

    # Validate position type
    position = db.query(StaffPositionAssignment).join(Position).join(PositionType).filter(
            StaffPositionAssignment.staff_id == staff.id,
            StaffPositionAssignment.end_date.is_(None)
        ).options(
            joinedload(StaffPositionAssignment.position).joinedload(Position.position_type)
        ).first()

    if not position or position.position.position_type.name not in ALLOWED_POSITION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staff does not hold an eligible position type")

    # Validate approver order
    if approver_data.approver_order in APPROVER_ORDERS and "Approver" in staff_roles:
        pass
    elif approver_data.approver_order in HR_ORDERS and "HR" in staff_roles:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid approver order for the given role")

    # Ensure notify_only applies only to orders 3 and 4
    if approver_data.notify_only and approver_data.approver_order not in HR_ORDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="notify_only can only be set for approvers with order 3 or 4")

    # Check if staff is already an approver in the workgroup
    existing_approver = (
        db.query(Approver)
        .filter(Approver.workgroup_id == workgroup_id, 
                Approver.staff_id == approver_data.staff_id,
                Approver.end_date.is_(None))
        .first()
    )

    if existing_approver:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staff is already an approver in this workgroup")

    # Add new approver with soft delete concept (end_date as None for active)
    new_approver = Approver(
        workgroup_id=workgroup_id,
        staff_id=approver_data.staff_id,
        approver_order=approver_data.approver_order,
        notify_only=approver_data.notify_only if approver_data.approver_order in HR_ORDERS else False,
        # assigned_by=approver_data.assigned_by,
        start_date=datetime.now(timezone.utc),
        end_date=None,  # Active approvers have end_date as NULL
    )
    db.add(new_approver)
    db.commit()
    db.refresh(new_approver)

    return {"message": "Approver added successfully", "approver_id": new_approver.id}



@workgroupRouter.get("/get_approvers_only/{workgroup_id}/", response_model=List[WorkgroupApproverResponse])
def get_workgroup_approvers_only(workgroup_id: UUID, db: Session = Depends(get_db)):
    # Check if the workgroup exists
    workgroup = db.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
    if not workgroup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

    # Fetch workgroup approvers with their approval levels
    approvers = (
    db.query(Staff, Approver.approver_order)
    .join(Approver, Staff.id == Approver.staff_id)
    .filter(
        Approver.workgroup_id == workgroup_id,
        Approver.end_date.is_(None)
    )
    .all()
    )

    if not approvers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No approvers found for this workgroup")

    approvers_response = []
    for approver in approvers:
        position = db.query(StaffPositionAssignment).join(Position).join(PositionType).filter(
            StaffPositionAssignment.staff_id == approver[0].id,
            StaffPositionAssignment.end_date.is_(None)
        ).options(
            joinedload(StaffPositionAssignment.position).joinedload(Position.position_type)
        ).first()

        approvers_response.append(
            WorkgroupApproverResponse(
                staff_id=approver[0].id,
                fullname=get_full_name(approver[0]),
                emp_number=approver[0].emp_number,
                email=approver[0].email,
                approval_level=approver[1],
                position_name=position.position.name if position else None,
                position_type_name=position.position.position_type.name if position else None
            )
        )

    return approvers_response


class WorkgroupInfoAll(BaseModel):
    workgroup_id: UUID
    workgroup_name: str
    coe_name: str
    coe_id: UUID
    approvers: Optional[List[WorkgroupApproverResponse]] = None


@workgroupRouter.get("/", response_model=List[WorkgroupInfoAll])
def get_all_workgroups(skip: int = 0, limit: int = 10, search: str = Query(None), db: Session = Depends(get_db)):
    work_flow_group_manager = WorkFlowGroupsManager(db_session=db)
    workgroups = work_flow_group_manager.get_workgroups(skip, limit, search=search)
    workgroups_response = []

    for workgroup in workgroups:
        # Fetch workgroup approvers
        approvers = (
            db.query(Staff, Approver.approver_order)
            .join(Approver, Staff.id == Approver.staff_id)
            .filter(
                Approver.workgroup_id == workgroup.id,
                Approver.end_date.is_(None)
            )
            .all()
        )

        approvers_response = []
        for approver in approvers:
            position = db.query(StaffPositionAssignment).join(Position).join(PositionType).filter(
                StaffPositionAssignment.staff_id == approver[0].id,
                StaffPositionAssignment.end_date.is_(None)
            ).options(
                joinedload(StaffPositionAssignment.position).joinedload(Position.position_type)
            ).first()

            approvers_response.append(
                WorkgroupApproverResponse(
                    staff_id=approver[0].id,
                    fullname=get_full_name(approver[0]),
                    emp_number=approver[0].emp_number,
                    email=approver[0].email,
                    approval_level=approver[1],
                    position_name=position.position.name if position else None,
                    position_type_name=position.position.position_type.name if position else None
                )
            )

        workgroups_response.append(WorkgroupInfoAll(
            workgroup_id=workgroup.id,
            workgroup_name=workgroup.name,
            coe_name=workgroup.coe.name,
            coe_id=workgroup.coe.id,
            approvers=approvers_response
        ))

    return workgroups_response

    

@workgroupRouter.get("/{workgroup_id}/members", response_model=ViewWorkgroupMembers)
def get_workgroup_members(workgroup_id: UUID, db: Session = Depends(get_db)):
    # Check if the workgroup exists
    workgroup = db.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
    if not workgroup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

    # Fetch workgroup members
    members = (
        db.query(Staff)
        .join(StaffWorkgroupAssignment, Staff.id == StaffWorkgroupAssignment.staff_id)
        .filter(StaffWorkgroupAssignment.workgroup_id == workgroup_id,
                StaffWorkgroupAssignment.end_date.is_(None))
        .all()
    )

    # Fetch workgroup approvers
    # Fetch workgroup approvers with their approval levels
    approvers = (
    db.query(Staff, Approver.approver_order)
    .join(Approver, Staff.id == Approver.staff_id)
    .filter(
        Approver.workgroup_id == workgroup_id,
        Approver.end_date.is_(None)
    )
    .all()
    )


    # Format response data
    members_response = []
    for member in members:
        position = db.query(StaffPositionAssignment).join(Position).join(PositionType).filter(
                    StaffPositionAssignment.staff_id == member.id,
                    StaffPositionAssignment.end_date.is_(None)  
                    ).options(
                        joinedload(StaffPositionAssignment.position).joinedload(Position.position_type)
                    ).first()
        fullname = get_full_name(member)
        members_response.append(
            WorkgroupMemberResponse(staff_id=member.id, 
                                    fullname=fullname,
                                    emp_number=member.emp_number, 
                                    email=member.email, 
                                    position_name=position.position.name if position else None,
                                    position_type_name= position.position.position_type.name if position else None))
        
    
    approvers_response = []
    for approver in approvers:
        position = db.query(StaffPositionAssignment).join(Position).join(PositionType).filter(
            StaffPositionAssignment.staff_id == approver[0].id,
            StaffPositionAssignment.end_date.is_(None)
        ).options(
            joinedload(StaffPositionAssignment.position).joinedload(Position.position_type)
        ).first()

        approvers_response.append(
            WorkgroupApproverResponse(
                staff_id=approver[0].id,
                fullname=get_full_name(approver[0]),
                emp_number=approver[0].emp_number,
                email=approver[0].email,
                approval_level=approver[1],
                position_name=position.position.name if position else None,
                position_type_name=position.position.position_type.name if position else None
            )
        )
        
   
   
    return ViewWorkgroupMembers(
        workgroup_info=WorkgroupInfo(
                                    workgroup_id=workgroup.id,
                                    workgroup_name=workgroup.name,
                                    coe_name=workgroup.coe.name,
            coe_id=workgroup.coe.id),
        members=[member.model_dump() for member in members_response],
        approvers=[approver.model_dump() for approver in approvers_response]
    )

class WorkGroupSummaryResponse(WorkgroupInfo):
    total_members:Optional[int]=None
    approvers:Optional[List[WorkgroupApproverResponse]]
    
@workgroupRouter.get("/summary/{workgroup_id}", response_model=WorkGroupSummaryResponse)
def get_workgroup_summary(workgroup_id: UUID, db: Session = Depends(get_db)):
    # Check if the workgroup exists
    workgroup = db.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
    if not workgroup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

    # Fetch total number of members
    total_members = (db.query(StaffWorkgroupAssignment)
                     .filter(StaffWorkgroupAssignment.workgroup_id == workgroup_id,
                                StaffWorkgroupAssignment.end_date.is_(None)
                             ).count())

    # Fetch workgroup approvers
    approvers = (
        db.query(Staff, Approver.approver_order)
        .join(Approver, Staff.id == Approver.staff_id)
        .filter(
            Approver.workgroup_id == workgroup_id,
            Approver.end_date.is_(None)
        )
        .all()
    )

    approvers_response = []
    for approver in approvers:
        position = db.query(StaffPositionAssignment).join(Position).join(PositionType).filter(
            StaffPositionAssignment.staff_id == approver[0].id,
            StaffPositionAssignment.end_date.is_(None)
        ).options(
            joinedload(StaffPositionAssignment.position).joinedload(Position.position_type)
        ).first()

        approvers_response.append(
            WorkgroupApproverResponse(
                staff_id=approver[0].id,
                fullname=get_full_name(approver[0]),
                emp_number=approver[0].emp_number,
                email=approver[0].email,
                approval_level=approver[1],
                position_name=position.position.name if position else None,
                position_type_name=position.position.position_type.name if position else None
            )
        )

    return WorkGroupSummaryResponse(
        workgroup_id=workgroup.id,
        workgroup_name=workgroup.name,
        coe_name=workgroup.coe.name,
        coe_id=workgroup.coe.id,
        total_members=total_members,
        approvers=[approver.model_dump() for approver in approvers_response]
    )
   
       
@workgroupRouter.get("/{workgroup_id}/members-only", response_model=MembersQueryUsersResponse)
def get_workgroup_members_only(workgroup_id: UUID, skip: int = 0, limit: int = 10, search: Optional[str] = None, db: Session = Depends(get_db)):
    # Check if the workgroup exists
    workgroup = db.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
    if not workgroup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

    # Base query for fetching members
    query = (db.query(Staff)
             .join(StaffWorkgroupAssignment, 
                   Staff.id == StaffWorkgroupAssignment.staff_id)
             .filter(StaffWorkgroupAssignment.workgroup_id == workgroup_id,
                     StaffWorkgroupAssignment.end_date.is_(None)))

    # Apply search filter if provided
    if search:
        search = f"%{search}%"
        query = query.filter(
            (Staff.first_name.ilike(search)) |
            (Staff.last_name.ilike(search)) |
            (Staff.emp_number.ilike(search))
        )

    total_users = query.count()
    total_number_of_pages = (total_users + limit - 1) // limit
    page_number = (skip // limit) + 1

    # Fetch workgroup members with pagination
    members = query.offset(skip).limit(limit).all()

    # Format response data
    members_response = []
    for member in members:
        position = db.query(StaffPositionAssignment).join(Position).join(PositionType).filter(
            StaffPositionAssignment.staff_id == member.id,
            StaffPositionAssignment.end_date.is_(None)
        ).options(
            joinedload(StaffPositionAssignment.position).joinedload(Position.position_type)
        ).first()
        fullname = get_full_name(member)
        members_response.append(
            WorkgroupMemberResponse(
                staff_id=member.id,
                fullname=fullname,
                emp_number=member.emp_number,
                email=member.email,
                position_name=position.position.name if position else None,
                position_type_name=position.position.position_type.name if position else None
            )
        )

    return MembersQueryUsersResponse(
        page_number=page_number,
        total_num_of_members=total_users,
        total_number_of_pages=total_number_of_pages,
        num_of_members_per_page=limit,
        members=members_response
    )

# route to edit workgroup name
@workgroupRouter.put("/{workgroup_id}/edit", response_model=UpdategroupResponse, status_code=status.HTTP_200_OK)
def edit_workgroup_name(workgroup_id: UUID, workgroup_data: WorkGroupUpdate, db: Session = Depends(get_db)):
    try:
        # Check if the workgroup exists
        workgroup = db.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
        if not workgroup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

        # Update the workgroup name
        workgroup.name = workgroup_data.name
        workgroup.description = workgroup_data.description
        db.commit()
        db.refresh(workgroup)

        return UpdategroupResponse(message="Workgroup name updated successfully", workgroup_id= workgroup_id)

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# route to remove member from a group
@workgroupRouter.delete("/{workgroup_id}/remove-member/{staff_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
def remove_workgroup_member(workgroup_id: UUID, staff_id: UUID, db: Session = Depends(get_db)):
    try:
        # Check if the workgroup exists
        workgroup = db.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
        if not workgroup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

        # Check if the staff exists
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

        # Check if the staff is a member of the workgroup
        existing_assignment = db.query(StaffWorkgroupAssignment).filter(
            StaffWorkgroupAssignment.workgroup_id == workgroup_id,
            StaffWorkgroupAssignment.staff_id == staff_id,
            StaffWorkgroupAssignment.end_date.is_(None)
        ).first()

        if not existing_assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff is not a member of the workgroup")

        # Soft delete the staff workgroup assignment
        existing_assignment.end_date = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_assignment)

        return DeleteResponse(message= "Member removed successfully", staff_id= staff_id)

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@workgroupRouter.delete("/delete-workgroup/{workgroup_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
def delete_workgroup(workgroup_id: UUID, db: Session = Depends(get_db),
                     current_user: User = Depends(verify_admin)):
    try:
        # Check if the workgroup exists
        workgroup = db.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
        if not workgroup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

        # Soft delete the workgroup
        workgroup.is_deleted = True
        db.commit()
        db.refresh(workgroup)

        return DeleteResponse(message="Workgroup deleted successfully", workgroup_id=workgroup_id)

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))