from datetime import datetime, timedelta, timezone
from os import name
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.admin.routers import generate_otp
from app.api.v1.auth.utils import get_current_user, set_otp_expiry, verify_admin
from app.api.v1.uploads.utils import validate_excel_file
from app.database import get_db
from app.models.models  import CoE, Directorate, Department, Grant, LeavePolicies, LeaveType, Position, PositionType, PublicHoliday, Role, Staff, StaffCoEAssignment, StaffDepartmentAssignment, StaffGrantsAssignment, StaffPositionAssignment, UserRoleAssignment, User, WorkGroup
import pandas as pd
import uuid
from app.config import settings
from app.utils.email_utils import send_otp_to_email
from app.utils.utils_schemas import EmailSendRequest

uploadsRouter = APIRouter(prefix="/api/v1/uploads", tags=["Admin - Manage Uploads"])


@uploadsRouter.post("/upload-directorates-departments")
def upload_directorates_departments(file: UploadFile, db: Session = Depends(get_db),
                # current_user: User = Depends(verify_admin)
                ):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Excel files are supported."
        )

    try:
        # Read the Excel file into a DataFrame
        df = pd.read_excel(file.file)

        # Validate the required columns
        required_columns = {"Directorate", "Department"}
        if not required_columns.issubset(df.columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Excel file must contain the following columns: {', '.join(required_columns)}"
            )

        # Deduplicate the data to avoid repeated processing
        df = df.drop_duplicates(subset=["Directorate", "Department"])

        # Iterate through the deduplicated DataFrame
        for _, row in df.iterrows():
            directorate_name = row["Directorate"].strip()
            department_name = row["Department"].strip()

            # Check if the directorate exists
            directorate = db.query(Directorate).filter_by(name=directorate_name).first()
            if not directorate:
                # Add a new directorate if it doesn't exist
                directorate = Directorate(
                    id=uuid.uuid4(),
                    name=directorate_name
                )
                db.add(directorate)
                db.flush()  # Ensure the directorate ID is available for the department

            # Check if the department exists under the directorate
            department_exists = db.query(Department).filter_by(
                name=department_name,
                directorate_id=directorate.id
            ).first()

            if not department_exists:
                # Add the department if it doesn't exist under the current directorate
                department = Department(
                    id=uuid.uuid4(),
                    name=department_name,
                    directorate_id=directorate.id
                )
                db.add(department)

        db.commit()
        return {"detail": "Directorates and departments uploaded successfully."}

    except Exception as e:
        db.rollback()
        if "duplicate key value violates unique constraint" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate entry found. Please ensure the file does not contain duplicate records."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )


@uploadsRouter.post("/upload-positions")
def upload_positions(file: UploadFile, db: Session = Depends(get_db),
                #current_user: User = Depends(verify_admin)
                ):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Excel files are supported."
        )

    try:
        # Read the Excel file into a DataFrame
        df = pd.read_excel(file.file)

        # Validate the required columns
        required_columns = {"position", "position_type"}
        if not required_columns.issubset(df.columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Excel file must contain the following columns: {', '.join(required_columns)}"
            )

        # Deduplicate the data to avoid repeated processing
        df = df.drop_duplicates(subset=["position", "position_type"])

        # Iterate through the deduplicated DataFrame
        for _, row in df.iterrows():
            position_name = row["position"].strip()
            position_type = row["position_type"].strip()

            position_type_exists = db.query(PositionType).filter_by(name=position_type).first()
            if not position_type_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Position type '{position_type}' not found in the database."
                )
            # Check if the position exists
            position = db.query(Position).filter_by(name=position_name).first()
            if not position:
                # Add a new position if it doesn't exist
                position = Position(
                    id=uuid.uuid4(),
                    name=position_name,
                    position_type_id=position_type_exists.id
                )
                db.add(position)

        db.commit()
        return {"detail": "Positions uploaded successfully."}

    except Exception as e:
        db.rollback()
        if "duplicate key value violates unique constraint" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate entry found. Please ensure the file does not contain duplicate records."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )
        

@uploadsRouter.post("/upload-staff")
def upload_staff(file: UploadFile, db: Session = Depends(get_db), 
                #current_user: User = Depends(verify_admin)
                 ):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Excel files are supported."
        )

    try:
        df = pd.read_excel(file.file)

        required_columns = {"emp_number", "first_name", "last_name", "email", "role_name", "coe_name"}
        if not required_columns.issubset(df.columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Excel file must contain the following columns: {', '.join(required_columns)}"
            )

        df = df.drop_duplicates(subset=["emp_number", "email"])
        skipped_entries = []  # To keep track of skipped entries

        for _, row in df.iterrows():
            emp_number = str(row["emp_number"])
            email = row["email"]

            # Check if staff already exists in the database
            existing_staff = db.query(Staff).filter(
                (Staff.emp_number == emp_number) | (Staff.email == email)
            ).first()

            if existing_staff:
                skipped_entries.append({"emp_number": emp_number, "email": email})
                continue  # Skip this entry if it already exists

            first_name = row["first_name"].strip().title()
            last_name = row["last_name"].strip().title()
            role_name = row["role_name"]
            coe_name = row["coe_name"]
            date_engaged = row["date_engaged"]


            # Fetch related entities
            role = db.query(Role).filter_by(name=role_name).first()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role '{role_name}' not found in the database."
                )

            coe = db.query(CoE).filter_by(name=coe_name).first()
            if not coe:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"CoE '{coe_name}' not found in the database."
                )

            position = None
            if "position_name" in df.columns:
                position_name = row["position_name"].strip()
                position = db.query(Position).filter_by(name=position_name).first()
                if not position:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Position '{position_name}' not found in the database."
                    )

            department = None
            if "department_name" in df.columns:
                department_name = row["department_name"].strip()
                department = db.query(Department).filter_by(name=department_name).first()
                if not department:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Department '{department_name}' not found in the database."
                    )

            grant = None
            if "grant_name" in df.columns:
                grant_name = row["grant_name"].strip()
                grant = db.query(Grant).filter_by(name=grant_name).first()
                if not grant:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Grant '{grant_name}' not found in the database."
                    )
            # Create new staff
            staff = Staff(
                id=uuid.uuid4(),
                emp_number=emp_number,
                first_name=first_name,
                last_name=last_name,
                email=email,
                date_engaged=date_engaged
            )
            db.add(staff)
            db.flush()

            coe_assignment = StaffCoEAssignment(
                id=uuid.uuid4(),
                staff_id=staff.id,
                coe_id=coe.id,
                start_date=datetime.now(timezone.utc)
            )
            db.add(coe_assignment)

            if position:
                position_assignment = StaffPositionAssignment(
                    id=uuid.uuid4(),
                    staff_id=staff.id,
                    position_id=position.id,
                    start_date=datetime.now(timezone.utc)
                )
                db.add(position_assignment)

            if department:
                department_assignment = StaffDepartmentAssignment(
                    id=uuid.uuid4(),
                    staff_id=staff.id,
                    department_id=department.id,
                    start_date=datetime.now(timezone.utc)
                )
                db.add(department_assignment)

            if grant:
                staff_grant = StaffGrantsAssignment(
                    id=uuid.uuid4(),
                    staff_id=staff.id,
                    grant_id=grant.id,
                    start_date=datetime.now(timezone.utc),
                    work_time_percentage=100.0
                )
                db.add(staff_grant)

            # Create user account
            username = f"{coe.coe_number}_{emp_number}"
            
            user = User(
                id=uuid.uuid4(),
                username=username,
                staff_id=staff.id,
                otp=generate_otp(),
                hashed_password=None,
                is_active=False,
                otp_expires_at=set_otp_expiry()
            )
            db.add(user)
            db.flush()
             # Assign relationships using assignment tables
            role_assignment = UserRoleAssignment(
                id=uuid.uuid4(),
                user_id=user.id,
                role_id=role.id,
                start_date=datetime.now(timezone.utc)
            )
            db.add(role_assignment)
           
            # email_data = EmailSendRequest(email=email,username=username, otp=user.otp)
            # send_otp_to_email(email_data=email_data, db=db)
            
        db.commit()

        return {
            "detail": "Staff uploaded successfully.",
            "skipped_entries": skipped_entries
        }

    except Exception as e:
        db.rollback()
        if "duplicate key value violates unique constraint" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate entry found. Please ensure the file does not contain duplicate records."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )


@uploadsRouter.post("/upload-coes")
async def upload_coes(file: UploadFile, db: Session = Depends(get_db),
                #current_user: User = Depends(verify_admin)
                ):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Excel files are supported."
        )

    try:
        # Read the Excel file into a DataFrame
        df = pd.read_excel(file.file)

        # Validate the required columns
        required_columns = {"coe", "coe_code", "center_name"}
        if not required_columns.issubset(df.columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Excel file must contain the following columns: {', '.join(required_columns)}"
            )

        # Deduplicate the data to avoid repeated processing
        df = df.drop_duplicates(subset=["coe", "coe_code", "center_name"])

        # Iterate through the deduplicated DataFrame
        for _, row in df.iterrows():
            coe_name = row["coe"].strip()
            coe_code = f"00{str(row['coe_code']).strip()}"
            center_name = row["center_name"].strip()

            # Check if the CoE exists
            coe = db.query(CoE).filter_by(name=coe_name).first()
            if coe:
                # Update the existing CoE
                coe.coe_number = coe_code
                coe.center_name = center_name
            else:
                # Add a new CoE if it doesn't exist
                coe = CoE(
                    id=uuid.uuid4(),
                    name=coe_name,
                    coe_number=coe_code,
                    center_name=center_name
                )
                db.add(coe)

        db.commit()
        return {"detail": "CoEs uploaded successfully."}

    except Exception as e:
        db.rollback()
        if "duplicate key value violates unique constraint" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate entry found. Please ensure the file does not contain duplicate records."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )
  
@uploadsRouter.post("/upload-grants")
async def upload_grants(file: UploadFile, db: Session = Depends(get_db),
                # current_user: User = Depends(verify_admin)
                ):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only Excel files are supported."
        )

    try:
        # Read the Excel file into a DataFrame
        df = pd.read_excel(file.file)

        # Validate the required columns
        required_columns = {"grant"}
        if not required_columns.issubset(df.columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Excel file must contain the following columns: {', '.join(required_columns)}"
            )

        # Deduplicate the data to avoid repeated processing
        df = df.drop_duplicates(subset=["grant", "grant_code"])

        # Iterate through the deduplicated DataFrame
        for _, row in df.iterrows():
            grant_name = row["grant"].strip()
            grant_code = f"00{str(row['grant_code']).strip()}"

            # Check if the grant exists
            grant = db.query(Grant).filter_by(name=grant_name).first()
            if not grant:
                # Add a new grant if it doesn't exist
                grant = Grant(
                    id=uuid.uuid4(),
                    name=grant_name,
                    grant_number=grant_code
                )
                db.add(grant)

        db.commit()
        return {"detail": "Grants uploaded successfully."}

    except Exception as e:
        db.rollback()
        if "duplicate key value violates unique constraint" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate entry found. Please ensure the file does not contain duplicate records."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )

    
@uploadsRouter.post("/upload-roles")
async def upload_roles(file: UploadFile, db: Session = Depends(get_db),
                #current_user: User = Depends(verify_admin)
                ):
    try:
        df = validate_excel_file(file, {"role"})
        for _, row in df.iterrows():
            role_name = row["role"].strip()
            if not db.query(Role).filter_by(name=role_name).first():
                role = Role(id=uuid.uuid4(), name=role_name)
                db.add(role)
        db.commit()
        return {"detail": "Roles uploaded successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )


@uploadsRouter.post("/upload-workgroups")
async def upload_workgroups(file: UploadFile, db: Session = Depends(get_db),
                # current_user: User = Depends(verify_admin)
                ):
    try:
        df = validate_excel_file(file, {"workgroup", "coe_name"})
        for _, row in df.iterrows():
            workgroup_name = row["workgroup"].strip()
            coe_name = row["coe_name"].strip()
            coe = db.query(CoE).filter_by(name=coe_name).first()
            if not coe:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"CoE '{coe_name}' not found in the database."
                )
            
            
            if not db.query(WorkGroup).filter_by(name=workgroup_name, coe_id = coe.id).first():
                workgroup = WorkGroup(id=uuid.uuid4(), name=workgroup_name, coe_id=coe.id)
                db.add(workgroup)
        db.commit()
        return {"detail": "Workgroups uploaded successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )
        
        
# upload position types
@uploadsRouter.post("/upload-position-types")
async def upload_position_types(file: UploadFile, db: Session = Depends(get_db),
                #current_user: User = Depends(verify_admin)
                ):
    try:
        df = validate_excel_file(file, {"name", "description"})
        for _, row in df.iterrows():
            name = row["name"].strip()
            description = row["description"].strip()
            if not db.query(PositionType).filter_by(name=name).first():
                position = PositionType(id=uuid.uuid4(), 
                                    name=name, 
                                    description=str()
                                    
                                    )
                db.add(position)
        db.commit()
        return {"detail": "Position types uploaded successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )
        
# upload leave types
@uploadsRouter.post("/upload-leave-types")
async def upload_leave_types(file: UploadFile, db: Session = Depends(get_db),
                # current_user: User = Depends(verify_admin)
                ):
    try:
        df = validate_excel_file(file, {"leave_type", "description"})
        for _, row in df.iterrows():
            leave_type = row["leave_type"].strip()
            description = row["description"].strip()
            if not db.query(LeaveType).filter_by(name=leave_type).first():
                leave = LeaveType(id=uuid.uuid4(), 
                                    name=leave_type,
                                    description=description                                    
                                    )
                db.add(leave)
        db.commit()
        return {"detail": "Leave types uploaded successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )
    

# upload public holidays
@uploadsRouter.post("/upload-public-holidays")
async def upload_public_holidays(file: UploadFile, db: Session = Depends(get_db),
                #current_user: User = Depends(verify_admin)
                ):
    try:
        df = validate_excel_file(file, {"date", "holiday_name"})
        for _, row in df.iterrows():
            date = row["date"]
            holiday_name = row["holiday_name"].strip()
            if not db.query(PublicHoliday).filter_by(name=holiday_name).first():
                holidays = PublicHoliday(id=uuid.uuid4(), 
                                    name=holiday_name,
                                    date=date,                                  
                                    )
                db.add(holidays)
        db.commit()
        return {"detail": "Public holidays uploaded successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )
        

# upload leave policies
@uploadsRouter.post("/upload-leave-policies")
async def upload_leave_policies(file: UploadFile, db: Session = Depends(get_db),
                # current_user: User = Depends(verify_admin)
                ):
    try:
        df = validate_excel_file(file, {"position_type", "leave_type", "max_days", "description"})
        for _, row in df.iterrows():
            position_type = row["position_type"].strip()
            leave_type = row["leave_type"].strip()
            max_days = row["max_days"]
            description = row["description"].strip()
            position = db.query(PositionType).filter_by(name=position_type).first()
            leave = db.query(LeaveType).filter_by(name=leave_type).first()
            if not position:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Position type '{position_type}' not found in the database."
                )
            if not leave:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Leave type '{leave_type}' not found in the database."
                )
            if not db.query(LeavePolicies).filter_by(leave_type_id=leave.id, position_type_id =position.id ).first():
                leave_policy = LeavePolicies(id=uuid.uuid4(), 
                                    leave_type_id=leave.id,
                                    position_type_id=position.id,
                                    max_days=max_days,
                                    description=description                                    
                                    )
                db.add(leave_policy)
        db.commit()
        return {"detail": "Leave policies uploaded successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing the file: {str(e)}"
        )