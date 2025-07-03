from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session, joinedload
from app.api.v1.admin.schemas import (
    CreateStaff,
    ResetUserPasswordResponse,
    StaffCreatedResponse,
    UpdateUserAndStaffSchema,
    UserResponse,
    ViewUserResponse
)
from app.api.v1.auth.utils import generate_otp, set_otp_expiry, verify_admin
from app.models.models  import (
    Department,
    Position, 
    PositionType, 
    Staff, 
    StaffDepartmentAssignment, 
    StaffGrantsAssignment, 
    StaffPositionAssignment, 
    StaffCoEAssignment, 
    CoE, User, 
    UserRoleAssignment)
from app.api.v1.users.schemas import MessageResponse
from app.database import get_db
from app.utils.email_utils import send_otp_to_email, send_reset_password_otp_to_email
from app.utils.helper import StaffManager
from app.utils.utils_schemas import EmailSendRequest

adminStaffManagementRouter = APIRouter(prefix="/api/v1/admin", tags=["Admin - User Management"])


    
@adminStaffManagementRouter.post("/create_staff", response_model=StaffCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    staff_data: CreateStaff, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(verify_admin)
    ):
    # Check for duplicate email or employee number
    existing_staff = db.query(Staff).filter(
        (Staff.email == staff_data.email) | (Staff.emp_number == staff_data.emp_number)
    ).first()
    if existing_staff:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staff with given email or employee number already exists.")
    
    # Create the Staff entry
    staff = Staff(
        emp_number=staff_data.emp_number,
        first_name=staff_data.first_name.title(),
        last_name=staff_data.last_name.title(),
        email=staff_data.email.lower(),
        gender=staff_data.gender.title(),
    )
    db.add(staff)
    db.flush() 

    
    # Assign the staff to a department
    department = db.query(Department).filter(Department.id == staff_data.department_id).one_or_none()
    if not department:
        raise HTTPException(detail=f"Department with ID {staff_data.department_id} not found", status_code=status.HTTP_404_NOT_FOUND)
    department_assignment = StaffDepartmentAssignment(
        staff_id=staff.id,
        department_id=department.id,
        start_date=datetime.now()
    )
    db.add(department_assignment)
    
    coe = db.query(CoE).filter(CoE.id == staff_data.work_station_id).one_or_none()
    if not coe:
        raise HTTPException(detail="CoE Not found", status_code=status.HTTP_404_NOT_FOUND)
    
    coe_assignment = StaffCoEAssignment(
        staff_id=staff.id,
        coe_id=coe.id,
        start_date=datetime.now(timezone.utc)
    )
    db.add(coe_assignment)
    
    position = db.query(Position).filter(Position.id == staff_data.position_id).one_or_none()
    if not position:
        raise HTTPException(detail=f"Position with ID {staff_data.position_id} not found", status_code=status.HTTP_404_NOT_FOUND)
    # Assign the staff to a position
    position_assignment = StaffPositionAssignment(
        staff_id=staff.id,
        position_id=staff_data.position_id,
        seniority = staff_data.position_seriority,
        start_date=datetime.now()
    )
    db.add(position_assignment)

    # Assign grants
    for grant in staff_data.grants:
        grant_assignment = StaffGrantsAssignment(
            staff_id=staff.id,
            grant_id=grant.grant_id,
            work_time_percentage=grant.time_allocated,
            start_date=datetime.now()
        )
        db.add(grant_assignment)
        
    username = f"{coe.coe_number}_{staff.emp_number}"
    
    user = User(
        username=username,
        staff_id=staff.id,
        otp=generate_otp(),
        hashed_password=None,
        is_active=False,
        otp_expires_at=set_otp_expiry()
    )
    db.add(user)
    db.flush()
    # Assign roles
    for role in staff_data.roles:
        role_assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=role.role_id,
            start_date=datetime.now()
        )
        db.add(role_assignment)
    
    email_data = EmailSendRequest(email=staff.email,username=username, otp=user.otp)
    send_otp_to_email(email_data=email_data, db=db)
        
  
    db.commit()
    db.refresh(staff)

    return StaffCreatedResponse(
        message="Staff created successfully",
        staff_id=staff.id
    )

@adminStaffManagementRouter.get("/users", response_model=List[UserResponse], status_code=status.HTTP_200_OK)
def get_users(
    db: Session = Depends(get_db),
    is_active: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None),
    is_terminated: Optional[bool] = Query(None),
    search: Optional[str] = Query(None), 
    current_user: User = Depends(verify_admin)
    ):
    query = db.query(User)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)
    
    if is_terminated is not None:
        query = query.join(Staff).filter(Staff.is_terminated == is_terminated)
    
    if search:
        search = f"%{search}%"
        query = query.join(Staff).filter(
            (User.username.ilike(search)) |
            (Staff.first_name.ilike(search)) |
            (Staff.last_name.ilike(search))
        )
    
    users = query.all()
    
    if not users:
        raise HTTPException(detail="No users found", status_code=status.HTTP_404_NOT_FOUND)
    
    user_responses = []
    for user in users:
        roles = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.end_date.is_(None),
        ).all()
        fullname = f"{user.staff.title}. {user.staff.first_name} {user.staff.last_name}" if user.staff.title else f"{user.staff.first_name} {user.staff.last_name}"
        user_responses.append(
            UserResponse(
                user_id=user.id,
                username=user.username,
                fullname=fullname,
                user_roles=[role.role.name if role else None for role in roles],
                is_active=user.is_active,
                is_verified=user.is_verified,
                is_terminated = user.staff.is_terminated,
                updated_at=user.updated_at.isoformat()
            )
        )
    
    return user_responses


@adminStaffManagementRouter.get("/users/{user_id}", response_model=ViewUserResponse)
def get_user_by_id(user_id: UUID, db: Session = Depends(get_db), 
    current_user: User = Depends(verify_admin)):
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
        grant_details = [
            {"grant_id": grant.grant.id, "grant_name": grant.grant.name, "grant_number": grant.grant.grant_number,"work_time_percentage": grant.work_time_percentage}
            for grant in grants
        ]
        fullname = f"{user.staff.title}. {user.staff.first_name} {user.staff.last_name}" if user.staff.title else f"{user.staff.first_name} {user.staff.last_name}"
        staff_details = {
            "staff_id": staff.id,
            "first_name": staff.first_name,
            "last_name": staff.last_name,
            "fullname": fullname,
            "emp_number": staff.emp_number,
            "email": staff.email,
            "phone":staff.phone if staff.phone else None,
            "gender": staff.gender.value if staff.gender else None,
            "dob": staff.dob if staff.dob else None,
            "home_address":staff.home_address if staff.home_address else None,
            "highest_education":staff.highest_education if staff.highest_education else None,
            "field_of_study":staff.field_of_study if staff.field_of_study else None,
            "date_of_employment": staff.date_engaged.isoformat() if staff.date_engaged else None,
            "position": assignment.position.name if assignment else None,
            "position_type": assignment.position.position_type.name if assignment else None,
            "coe": coe.coe.name if coe else None,
            "department": department.department.name if department else None,
            "is_terminated": staff.is_terminated,
            "grants": grant_details,
        }
    
    return {
        "user_id": user.id,
        "username": user.username,
        "roles": [role.role.name if role else None for role in roles],
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "has_otp":True if user.otp else False,
        "otp":user.otp if user.otp else None,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "staff_details": staff_details,
    }


@adminStaffManagementRouter.post("/reset-user-password/{user_id}",response_model=ResetUserPasswordResponse, status_code=status.HTTP_200_OK)
def reset_user_password(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin)
):
    user = db.query(User).filter(User.id == user_id).one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Generate new OTP and set expiry
    user.otp = generate_otp()
    user.otp_expires_at = set_otp_expiry()
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send OTP to user's email
    email_data  =   EmailSendRequest(email=user.staff.email, username=user.username, otp=user.otp)
    send_reset_password_otp_to_email(email_data=email_data, db=db)
    
    return {"message": "Password reset successfully. An OTP has been sent to the user's email."}

@adminStaffManagementRouter.put("/update-user_info/{user_id}", response_model=MessageResponse)
def update_user_info(
    user_id: UUID,
    update_data: UpdateUserAndStaffSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin),
):
    # Fetch the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Update User information
    if update_data.user:
        user_data = update_data.user.model_dump(exclude_unset=True)
        for key, value in user_data.items():
            setattr(user, key, value)

    # Update Staff information
    if update_data.staff:
        if not user.staff:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated staff record not found.")
        staff_data = update_data.staff.model_dump(exclude_unset=True)
        for key, value in staff_data.items():
            setattr(user.staff, key, value)

    # Initialize the StaffManager
    staff_manager = StaffManager(db_session=db)

    # Update Department
    if update_data.depertments:
        staff_manager.assign_staff_department(
            staff_id=user.staff.id,
            new_department_id=update_data.depertments.new_dept_id,
            is_hod=False,  # Adjust as needed
        )

    # Update CoE
    if update_data.coe:
        staff_manager.transfer_staff_coe(
            staff_id=user.staff.id, new_coe_id=update_data.coe.new_coe_id
        )

    # Update Roles
    if update_data.roles:
        for role in update_data.roles:
            if role.terminate:
                staff_manager.terminate_staff_role(user_id = user.id, role_id = role.new_role_id)
            else:
                staff_manager.assign_user_role(user_id=user.id, new_role_id=role.new_role_id)

    # Update Grants
    if update_data.grants:
        for grant in update_data.grants:
            if grant.terminate:
                staff_manager.terminate_staff_grant(staff_id=user.staff.id, grant_id=grant.new_grant_id)
            else:
                staff_manager.assign_staff_grant(
                    staff_id=user.staff.id,
                    new_grant_id=grant.new_grant_id,
                    work_time_percentage=grant.work_time_percentage,
                )

    # Update Position
    if update_data.position:
        staff_manager.assign_position(
            staff_id=user.staff.id, 
            position_id=update_data.position.new_position_id,
            assigned_by=current_user.id
        )

    # Commit changes and refresh
    db.commit()
    db.refresh(user)

    return MessageResponse(message="User and staff information updated successfully.")


@adminStaffManagementRouter.delete("/user/{user_id}", response_model= MessageResponse)
def delete_user(
    user_id:Optional[UUID],
    db:Session= Depends(get_db),
     current_user: User = Depends(verify_admin)):
    user = db.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(detail=f"User with {user_id} not found.", status_code=status.HTTP_404_NOT_FOUND)
    
    if user.staff.is_terminated:
        raise HTTPException(detail=f"User {user.staff.first_name} {user.staff.last_name} is already deleted.", status_code=status.HTTP_404_NOT_FOUND)
    
    user.staff.is_terminated = True
    user.staff.is_active = False
    user.is_active = False
    user.is_verified = False
    user.hashed_password = None
    db.commit()
    db.refresh(user)
    return MessageResponse(message="User deleted successfully")