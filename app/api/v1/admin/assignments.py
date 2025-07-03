from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.api.v1.admin.schemas import (
    ApproverCreate,
    AssignStaffGrantRequest,
    AssignStaffRequest,
    AssignUserRequest,
    AssignmentResponse,
    StaffWorkgroupAssignmentCreate
)

from app.api.v1.auth.utils import verify_admin
from app.models.models  import Approver,Role, Staff,  StaffWorkgroupAssignment, User, WorkGroup
from app.database import get_db
from app.utils.helper import StaffManager

adminAssignRouter = APIRouter(prefix="/api/v1/admin", tags=["Admin Staffs Assignments"])


@adminAssignRouter.post("/assign_role", response_model=AssignmentResponse)
def assign_role(request: AssignUserRequest, db_session: Session = Depends(get_db),
                # current_user: User = Depends(verify_admin)
                ):
    try:
        staff_manager = StaffManager(db_session)
        staff_manager.assign_user_role(request.user_id, request.new_assign_id)
        return AssignmentResponse(success=True, detail="User role assigned successfully.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@adminAssignRouter.post("/assign_position", response_model=AssignmentResponse)
def assign_position(request: AssignStaffRequest, db_session: Session = Depends(get_db),
                    #current_user: User = Depends(verify_admin)
                    ):
    try:
        staff_manager = StaffManager(db_session)
        staff_manager.assign_staff_position(request.staff_id, request.new_assign_id)
        return AssignmentResponse(success=True, detail="Staff position assigned successfully.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@adminAssignRouter.post("/assign_coe", response_model=AssignmentResponse)
def assign_coe(request: AssignStaffRequest, db_session: Session = Depends(get_db),
               #current_user: User = Depends(verify_admin)
               ):
    try:
        staff_manager = StaffManager(db_session)
        staff_manager.transfer_staff_coe(request.staff_id, request.new_assign_id)
        return AssignmentResponse(success=True, detail="Staff coe transferred successfully.")
    except HTTPException as http_exc:
        raise http_exc  # Forward FastAPI exceptions
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")


@adminAssignRouter.post("/assign_department", response_model=AssignmentResponse)
def assign_department(request: AssignStaffRequest, db_session: Session = Depends(get_db),
                      #current_user: User = Depends(verify_admin)
                      ):
    try:
        staff_manager = StaffManager(db_session)
       
        staff_manager.assign_staff_department(request.staff_id, request.new_assign_id)
        return AssignmentResponse(success=True, detail="Staff department assigned successfully.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



@adminAssignRouter.post("/assign_grants", response_model=AssignmentResponse)
def assign_grants(request: AssignStaffGrantRequest, db_session: Session = Depends(get_db),
                  #current_user: User = Depends(verify_admin)
                  ):
    try:
        staff_manager = StaffManager(db_session)
        staff_manager.assign_staff_grant(
            staff_id=request.staff_id,
            new_grant_id=request.new_assign_id,
            work_time_percentage=request.work_time_percentage
        )
        return AssignmentResponse(success=True, detail="Staff grant assigned successfully.")
    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) 
    
    


# add staff to workgroup
@adminAssignRouter.post("/assign-staff-workgroup", status_code=status.HTTP_201_CREATED)
def add_staff_to_workgroup(
    request: StaffWorkgroupAssignmentCreate,
    db: Session = Depends(get_db),
   # current_user: User = Depends(verify_admin)
):
    # Validate the workgroup exists
    workgroup = db.query(WorkGroup).filter(WorkGroup.id == request.workgroup_id).first()
    if not workgroup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

    # Validate the staff exists
    staff = db.query(Staff).filter(Staff.id == request.staff_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

    # Check if staff is already assigned to the workgroup
    existing_assignment = db.query(StaffWorkgroupAssignment).filter(
        StaffWorkgroupAssignment.staff_id == request.staff_id,
        StaffWorkgroupAssignment.workgroup_id == request.workgroup_id
    ).first()

    if existing_assignment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staff already assigned to this workgroup")

    # Create the new staff-workgroup assignment
    new_assignment = StaffWorkgroupAssignment(
        staff_id=request.staff_id,
        workgroup_id=request.workgroup_id,
        start_date=datetime.now(timezone.utc),
        end_date=None
    )

    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)

    return {"message": "Staff successfully added to workgroup", "assignment": new_assignment}



@adminAssignRouter.post("/assign-workgroup-approver", status_code=status.HTTP_201_CREATED)
def add_approver_to_workgroup(
    request: ApproverCreate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(verify_admin)
):
    # Validate the workgroup exists
    workgroup = db.query(WorkGroup).filter(WorkGroup.id == request.workgroup_id).first()
    if not workgroup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workgroup not found")

    # Validate the staff exists
    staff = db.query(Staff).filter(Staff.id == request.staff_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

    # Check if the staff is already an approver for the workgroup
    existing_approver = db.query(Approver).filter(
        Approver.workgroup_id == request.workgroup_id,
        Approver.staff_id == request.staff_id
    ).first()

    if existing_approver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Staff is already an approver for this workgroup"
        )

    # Restrict approver orders to 1 and 2 for actual approvers
    if request.approver_order in [1, 2]:
        # Check if the approver slot for the given order is already occupied
        existing_order = db.query(Approver).filter(
            Approver.workgroup_id == request.workgroup_id,
            Approver.approver_order == request.approver_order
        ).first()

        if existing_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approver order {request.approver_order} is already occupied. Remove the existing approver to assign a new one."
            )

    # Restrict approver orders 3 and 4 to HR users (notify-only)
    if request.approver_order in [3, 4]:
        hr_role = db.query(Role).filter(Role.name == "HR").first()
        if hr_role not in [role_assignment.role for role_assignment in staff.user.role_assignments]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with the HR role can be assigned approver orders 3 and 4"
            )

    # Create the new approver
    new_approver = Approver(
        workgroup_id=request.workgroup_id,
        staff_id=request.staff_id,
        approver_order=request.approver_order,
        notify_only=request.notify_only
    )

    db.add(new_approver)
    db.commit()
    db.refresh(new_approver)

    return {"message": "Approver successfully added to workgroup", "approver": new_approver}