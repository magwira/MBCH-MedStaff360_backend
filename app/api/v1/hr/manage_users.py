from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from datetime import date, datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.api.v1.admin.schemas import CreateStaff, GenderEnum, GeneralResponse, StaffCreatedResponse, ViewUserResponse
from app.api.v1.auth.utils import generate_otp, set_otp_expiry, verify_hr
from app.api.v1.hr.schemas import CoEDetails, DeptDetails, HRStaffDetails, HRStaffResponse, PositionDetails, UpdateUserAndStaffSchema
from app.models.models  import CoE, Department, Position, PositionType, Role, Staff, StaffCoEAssignment, StaffDepartmentAssignment, StaffGrantsAssignment, StaffPositionAssignment, User, UserRoleAssignment
from app.api.v1.users.schemas import MessageResponse
from app.database import get_db
from app.utils.email_utils import send_otp_to_email
from app.utils.helper import StaffManager
from app.utils.utils_schemas import EmailSendRequest
from app.api.v1.hr.hr_manage_leave import hr_leaveRouter

hrRouter = APIRouter(prefix="/api/v1/hr", tags=["HR-Management"])
hrRouter.include_router(hr_leaveRouter)


@hrRouter.post("/create_staff", response_model=StaffCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    staff_data: CreateStaff, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(verify_hr)
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

@hrRouter.get("/view_staffs", response_model=HRStaffResponse)
def get_all_staffs(
    search: Optional[str] = Query(None),
    page_number: int = Query(1, ge=1),
    num_of_staffs_per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_hr)
):
    query = db.query(User)
    
    if search:
        search = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search)) |
            (User.staff.has(Staff.first_name.ilike(search))) |
            (User.staff.has(Staff.last_name.ilike(search)))
        )
    
    total_users = query.count()
    users = query.offset((page_number - 1) * num_of_staffs_per_page).limit(num_of_staffs_per_page).all()
    

    user_responses = []
    if users:
        for user in users:
            staff = user.staff

            staff_details = None
            if staff:
                # Fetch assignments
                roles = db.query(UserRoleAssignment).filter(
                    UserRoleAssignment.user_id == user.id,
                    UserRoleAssignment.end_date.is_(None),
                ).all()
                # Construct roles for response
                role_details = [{
                    
                        "role_id":role.role.id,
                        "role_name":role.role.name
                    } for role in roles if role.role.name not in ["Admin"]
                ]
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
                user_responses.append(HRStaffDetails(
                        staff_id = staff.id,
                        first_name = staff.first_name,
                        last_name = staff.last_name,
                        fullname = fullname,
                        emp_number = staff.emp_number,
                        email = staff.email,
                        phone = staff.phone if staff.phone else None,
                        gender = staff.gender.value if staff.gender else None,
                        dob = staff.dob if staff.dob else None,
                        home_address = staff.home_address if staff.home_address else None,
                        highest_education = staff.highest_education if staff.highest_education else None,
                        field_of_study = staff.field_of_study if staff.field_of_study else None,
                        date_of_employment = staff.date_engaged.isoformat() if staff.date_engaged else None,
                        position= PositionDetails(
                            position_id=assignment.position.id if assignment else None,
                            position_name=assignment.position.name if assignment else None,
                            position_type_id= assignment.position.position_type.id if assignment else None,
                            position_type_name= assignment.position.position_type.name if assignment else None),
                        coe= CoEDetails(coe_id=coe.coe.id if coe else None,
                                                coe_name=coe.coe.name if coe else None,),
                        department= DeptDetails(department_id=department.department.id if department else None,
                                                        department_name=department.department.name if department else None,
                                                        directorate_id=department.department.directorate.id if department.department.directorate.id else None,
                                                        directorate_name=department.department.directorate.name if department.department.directorate.name else None,),
                        is_terminated = staff.is_terminated,
                        grants = grant_details,
                        roles = role_details
                ))
    total_number_of_pages = int(total_users/num_of_staffs_per_page)
    return HRStaffResponse(
        page_number=page_number,
        total_num_of_staffs=total_users,
        total_number_of_pages=total_number_of_pages,
        num_of_staffs_per_page=num_of_staffs_per_page,
        staffs=user_responses
    )
    

@hrRouter.get("/staff/{staff_id}", response_model=HRStaffDetails)
def get_staff_by_id(staff_id: UUID, db: Session = Depends(get_db), 
    current_user: User = Depends(verify_hr)
    ):
    staff = db.query(Staff).filter(Staff.id == staff_id).one_or_none()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff with ID {staff_id} not found"
        )
    
    staff_details = None
    if staff:
        # Fetch the most recent active assignments
        roles = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == staff.user.id,
            UserRoleAssignment.end_date == None
        ).all()
        
        # Construct roles for response
        role_details = [{
            
                "role_id":role.role.id,
                "role_name":role.role.name
            } for role in roles if role.role.name not in ["Admin"]
        ]
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
        fullname = f"{staff.title}. {staff.first_name} {staff.last_name}" if staff.title else f"{staff.first_name} {staff.last_name}"
        staff_details = HRStaffDetails(
            staff_id = staff.id,
            first_name = staff.first_name,
            last_name = staff.last_name,
            fullname = fullname,
            emp_number = staff.emp_number,
            email = staff.email,
            phone = staff.phone if staff.phone else None,
            gender = staff.gender.value if staff.gender else None,
            dob = staff.dob if staff.dob else None,
            home_address = staff.home_address if staff.home_address else None,
            highest_education = staff.highest_education if staff.highest_education else None,
            field_of_study = staff.field_of_study if staff.field_of_study else None,
            date_of_employment = staff.date_engaged.isoformat() if staff.date_engaged else None,
            position= PositionDetails(
                        position_id=assignment.position.id if assignment else None,
                        position_name=assignment.position.name if assignment else None,
                        position_type_id= assignment.position.position_type.id if assignment else None,
                        position_type_name= assignment.position.position_type.name if assignment else None),
            coe= CoEDetails(coe_id=coe.coe.id if coe else None,
                                    coe_name=coe.coe.name if coe else None,),
            department= DeptDetails(department_id=department.department.id if department else None,
                                            department_name=department.department.name if department else None,
                                            directorate_id=department.department.directorate.id if department.department.directorate.id else None,
                                            directorate_name=department.department.directorate.name if department.department.directorate.name else None,),
            is_terminated= staff.is_terminated,
            grants= grant_details,
            roles=role_details
        )
    
    return staff_details



@hrRouter.put("/update-staff_info/{staff_id}", response_model=MessageResponse)
def update_user_info(
    staff_id: UUID,
    update_data: UpdateUserAndStaffSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_hr),
):
    # Fetch the user
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found.")
    
    user:User = staff.user

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
            staff_id=staff.id,
            new_department_id=update_data.depertments.new_dept_id,
            is_hod=False,  # Adjust as needed
        )

    # Update CoE
    if update_data.coe:
        staff_manager.transfer_staff_coe(
            staff_id=staff.id, new_coe_id=update_data.coe.new_coe_id
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
                    staff_id=staff.id,
                    new_grant_id=grant.new_grant_id,
                    work_time_percentage=grant.work_time_percentage,
                )

    # Update Position
    if update_data.position:
        staff_manager.assign_position(
            staff_id=staff.id, 
            position_id=update_data.position.new_position_id,
            # assigned_by=current_user.id
        )

    # Commit changes and refresh
    db.commit()
    db.refresh(user)

    return MessageResponse(message="User and staff information updated successfully.")


@hrRouter.delete("/staff/{staff_id}", response_model= MessageResponse)
def delete_staff(
    staff_id:Optional[UUID],
    db:Session= Depends(get_db),
     current_user: User = Depends(verify_hr)):
    staff = db.query(Staff).filter(Staff.id==staff_id).first()
    if not staff:
        raise HTTPException(detail=f"Staff with {staff_id} not found.", status_code=status.HTTP_404_NOT_FOUND)
    
    if staff.is_terminated:
        raise HTTPException(detail=f"Staff {staff.first_name} {staff.last_name} is already deleted.", status_code=status.HTTP_404_NOT_FOUND)
    
    staff.is_terminated = True
    staff.is_active = False
    staff.user.is_active = False
    staff.user.is_verified = False
    staff.user.hashed_password = None
    db.commit()
    db.refresh(staff)
    return MessageResponse(message="Staff deleted successfully")


@hrRouter.get("/roles", response_model=List[GeneralResponse], status_code=status.HTTP_200_OK)
async def get_roles(q: str = None, db: Session = Depends(get_db), 
                    current_user: User = Depends(verify_hr)
                    ):
    query = db.query(Role)
    if q:
        query = query.filter(Role.name.ilike(f"%{q}%"))
    roles = query.all()
    filtered_roles = [role for role in roles if role.name not in ["Admin", "User"]]
    return filtered_roles