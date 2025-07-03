

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, constr
from sqlalchemy.orm import Session, joinedload
from app.api.v1.admin.schemas import GenderEnum
from app.database import get_db
from app.models.models import Position, PositionType, StaffDepartmentAssignment, StaffGrantsAssignment, StaffPositionAssignment, UserRoleAssignment, StaffCoEAssignment, User, Staff
from app.api.v1.users.schemas import  MessageResponse, StaffDetails, StaffGrantDetails, StaffRoleDetails, UpdateStaffSchema, UpdateUserSchema, UserResponse
from app.api.v1.auth.utils import get_current_user, get_password_hash


userRouter = APIRouter(prefix="/api/v1/users", tags=["Users"])


@userRouter.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    staff = user.staff
    
    staff_details = None
    if staff:
        # Fetch the most recent active assignments
        roles = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.end_date == None
        ).all()
        
        assignment = db.query(StaffPositionAssignment).join(Position).join(PositionType).filter(
                    StaffPositionAssignment.staff_id == staff.id,
                    StaffPositionAssignment.end_date.is_(None)  
                    ).options(
                        joinedload(StaffPositionAssignment.position).joinedload(Position.position_type)
                    ).first()

        if not assignment:
                return {"message": "No active position found for the given staff"}
        
        coe = db.query(StaffCoEAssignment).filter(
            StaffCoEAssignment.staff_id == staff.id,
            StaffCoEAssignment.end_date == None
        ).one_or_none()
        
        department = db.query(StaffDepartmentAssignment).filter(
            StaffDepartmentAssignment.staff_id == staff.id,
            StaffDepartmentAssignment.end_date == None
        ).one_or_none()

        # Fetch all grants for the staff
        grants = db.query(StaffGrantsAssignment).filter(
            StaffGrantsAssignment.staff_id == staff.id
        ).all()

        fullname = f"{staff.title}. {staff.first_name} {staff.last_name}" if staff.title else f"{staff.first_name} {staff.last_name}"
           
        staff_details = StaffDetails(
                    staff_id= staff.id,
                    first_name= staff.first_name,
                    last_name= staff.last_name,
                    fullname= fullname,
                    emp_number= staff.emp_number,
                    email= staff.email,
                    phone=staff.phone if staff.phone else None,
                    gender= staff.gender.value if staff.gender else None,
                    dob=staff.dob if staff.dob else None,
                    home_address=staff.home_address if staff.home_address else None,
                    highest_education=staff.highest_education if staff.highest_education else None,
                    field_of_study=staff.field_of_study if staff.field_of_study else None,
                    date_of_employment= staff.date_engaged.isoformat() if staff.date_engaged else None,
                    position= assignment.position.name if assignment else None,
                    position_type= assignment.position.position_type.name if assignment else None,
                    coe= coe.coe.name if coe else None,
                    department= department.department.name if department else None,
                    directorate=department.department.directorate.name if department.department.directorate.name else None,
                    grants= [StaffGrantDetails(
                        grant_id= grant.grant.id, 
                        rant_name= grant.grant.name, 
                        grant_number= grant.grant.grant_number, 
                        work_time_percentage= grant.work_time_percentage) for grant in grants],
            )
    
    return UserResponse(
                user_id = user.id,
                username = user.username,
                roles = [StaffRoleDetails(role_id=role.role.id, role_name=role.role.name) for role in roles],
                is_active = user.is_active,
                is_verified = user.is_verified,
                created_at = user.created_at.isoformat(),
                updated_at = user.updated_at.isoformat(),
                staff_details = staff_details
            )
    
@userRouter.get("/", response_model=list[UserResponse])
def get_all_users(search: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(User)
    
    if search:
        search = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search)) |
            (User.staff.has(Staff.first_name.ilike(search))) |
            (User.staff.has(Staff.last_name.ilike(search)))
        )
    
    users = query.all()
    
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No users found"
        )

    user_responses = []
    for user in users:
        staff = user.staff

        staff_details = None
        if staff:
            # Fetch assignments
            roles = db.query(UserRoleAssignment).filter(
                UserRoleAssignment.user_id == user.id,
                UserRoleAssignment.end_date.is_(None),
            ).all()

            assignment = db.query(StaffPositionAssignment).join(Position).join(PositionType).filter(
                    StaffPositionAssignment.staff_id == staff.id,
                    StaffPositionAssignment.end_date.is_(None)  
                    ).options(
                        joinedload(StaffPositionAssignment.position).joinedload(Position.position_type)
                    ).first()

            if not assignment:
                return {"message": "No active position found for the given staff"}
            
            coe = db.query(StaffCoEAssignment).filter(
                StaffCoEAssignment.staff_id == staff.id,
                StaffCoEAssignment.end_date.is_(None),
            ).one_or_none()

            department = db.query(StaffDepartmentAssignment).filter(
                StaffDepartmentAssignment.staff_id == staff.id,
                StaffDepartmentAssignment.end_date.is_(None),
            ).one_or_none()
            
            grants = db.query(StaffGrantsAssignment).filter(
                StaffGrantsAssignment.staff_id == staff.id
            ).all()
            grant_details = [
                {"grant_id": grant.grant.id, "grant_name": grant.grant.name, "grant_number": grant.grant.grant_number, "work_time_percentage": grant.work_time_percentage}
                for grant in grants
            ]
            fullname = f"{staff.title}. {staff.first_name} {staff.last_name}" if staff.title else f"{staff.first_name} {staff.last_name}"
            staff_details = StaffDetails(
                    staff_id= staff.id,
                    first_name= staff.first_name,
                    last_name= staff.last_name,
                    fullname= fullname,
                    emp_number= staff.emp_number,
                    email= staff.email,
                    phone=staff.phone if staff.phone else None,
                    gender= staff.gender.value if staff.gender else None,
                    dob=staff.dob if staff.dob else None,
                    home_address=staff.home_address if staff.home_address else None,
                    highest_education=staff.highest_education if staff.highest_education else None,
                    field_of_study=staff.field_of_study if staff.field_of_study else None,
                    date_of_employment= staff.date_engaged.isoformat() if staff.date_engaged else None,
                    position= assignment.position.name if assignment else None,
                    position_type= assignment.position.position_type.name if assignment else None,
                    coe= coe.coe.name if coe else None,
                    department= department.department.name if department else None,
                    directorate=department.department.directorate.name if department.department.directorate.name else None,
                    grants= [StaffGrantDetails(
                        grant_id= grant.grant.id, 
                        grant_name= grant.grant.name, 
                        grant_number= grant.grant.grant_number, 
                        work_time_percentage= grant.work_time_percentage) for grant in grants],
            )
        
        user_responses.append(
            UserResponse(
                user_id = user.id,
                username = user.username,
                roles = [StaffRoleDetails(role_id=role.role.id, role_name=role.role.name) for role in roles],
                is_active = user.is_active,
                is_verified = user.is_verified,
                created_at = user.created_at.isoformat(),
                updated_at = user.updated_at.isoformat(),
                staff_details = staff_details
            )
        )
    return user_responses


@userRouter.put("/update-me/", response_model=MessageResponse)
def update_me(
    update_data: UpdateStaffSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Fetch the user record
    user = db.query(User).filter(User.id == user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Update Staff fields
    if update_data:
        if not user.staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated staff record not found."
            )
        staff_data = update_data.model_dump(exclude_unset=True)
        for key, value in staff_data.items():
            setattr(user.staff, key, value)

    # Commit changes
    db.commit()
    db.refresh(user)

    return MessageResponse(
        message= "User and staff information updated successfully."
        )



@userRouter.put("/update-my-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def update_my_password(
    user_data: UpdateUserSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user_data.new_password.strip() != user_data.verify_password.strip():
        raise HTTPException(
            detail="Passwords do not match.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    user.hashed_password = get_password_hash(user_data.new_password)
    
    db.commit()
    db.refresh(user)
    
    return MessageResponse(
        message="Password updated successfully."
    )