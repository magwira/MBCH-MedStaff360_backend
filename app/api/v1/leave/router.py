from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import UUID
from app.models.models  import Approver, Notification, Staff, StaffWorkgroupAssignment, WorkGroup
from app.api.v1.auth.utils import get_current_user
from app.models.models  import LeaveType, LeaveApplication, LeavePolicies, User
from app.database import get_db


leaveRouter = APIRouter(prefix="/api/v1/leave", tags=["Leave"])

def get_current_approver(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approver = db.query(Approver).filter_by(staff_id=current_user.staff_id).first()
    if not approver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an approver."
        )

    return current_user

@leaveRouter.get("/types")
def get_leave_types(db: Session = Depends(get_db)):
    leave_types = db.query(LeaveType).all()
    return leave_types


class LeaveApplicationCreate(BaseModel):
    leave_type_id: UUID
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None

def validate_leave_balance(staff_id: UUID, leave_request: LeaveApplicationCreate, db: Session):
    # Check if leave balance exists
    leave_balance = db.query(leave_balance).filter_by(staff_id=staff_id, leave_type_id=leave_request.leave_type_id).first()
    
    if not leave_balance:
        return False

    # Check if days requested are within the allowed limits
    leave_policy = db.query(LeavePolicies).filter_by(leave_type_id=leave_request.leave_type_id).first()
    if not leave_policy:
        return False

    # Calculate days requested
    days_requested = (leave_request.end_date - leave_request.start_date).days + 1

    # Check if days requested exceed the allowed limits
    if days_requested > leave_policy.max_days or days_requested < leave_policy.min_days:
        return False

    # Check if days requested exceed the leave balance
    if days_requested > leave_balance.balance:
        return False

    return True

@leaveRouter.post("/apply-leave", status_code=status.HTTP_201_CREATED)
def apply_leave(
    leave_request: LeaveApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    leave_type = db.query(LeaveType).filter_by(id=leave_request.leave_type_id).first()
    if not leave_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid leave type."
        )
        
    # Check if staff belongs to a workgroup with approvers
    workgroup = (
        db.query(WorkGroup)
        .join(StaffWorkgroupAssignment)
        .filter(StaffWorkgroupAssignment.staff_id == current_user.staff_id)
        .first()
    )
    if not workgroup or not workgroup.approvers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not part of a workgroup with approvers."
        )

    # Validate leave balance and accumulated days
    if not validate_leave_balance(current_user.staff_id, leave_request, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient leave balance or days exceed allowed limits."
        )
    

    # Create leave application
    leave_application = LeaveApplication(
        id=uuid.uuid4(),
        staff_id=current_user.staff_id,
        leave_type_id=leave_type.id,
        start_date=leave_request.start_date,
        end_date=leave_request.end_date,
        comment=leave_request.reason,
        status="Pending",
        created_at=datetime.now()
    )
    db.add(leave_application)
    db.commit()

    # Notify first approver
    first_approver = workgroup.approvers[0]
    send_notification(
        recipient_id=first_approver.staff_id,
        subject="New Leave Request",
        message=f"Staff {current_user.staff.first_name} {current_user.staff.last_name} has applied for leave."
    )

    return {"message": "Leave request submitted successfully."}

@leaveRouter.put("/cancel-leave/{leave_id}", status_code=status.HTTP_200_OK)
def cancel_leave(
    leave_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    leave_application = db.query(LeaveApplication).filter_by(id=leave_id, staff_id=current_user.staff_id).first()
    if not leave_application or leave_application.status != "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel this leave request."
        )

    db.delete(leave_application)
    db.commit()

    return {"message": "Leave request canceled successfully."}


class LeaveApplicationUpdate(BaseModel):
    action: str
    reason: str = None
    



def send_notification(recipient_id: UUID, subject: str, message: str, db: Session):
    notification = Notification(
        id=uuid.uuid4(),
        recipient_id=recipient_id,
        subject=subject,
        message=message,
        created_at=datetime.now()
    )
    db.add(notification)
    db.commit()
    
    print(notification)

@leaveRouter.put("/approve-leave/{leave_id}", status_code=status.HTTP_200_OK)
def approve_leave(
    leave_id: uuid.UUID,
    approval_data: LeaveApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_approver),
):
    leave_application = db.query(LeaveApplication).filter_by(id=leave_id).first()
    if not leave_application or leave_application.status != "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave request is not valid for approval."
        )

    approver = db.query(Approver).filter_by(workgroup_id=leave_application.workgroup_id, staff_id=current_user.staff_id).first()
    if not approver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to approve this request."
        )

    if approval_data.action == "approve":
        if approver.order == 1:
            leave_application.status = "Pending Second Approval"
            send_notification(
                recipient_id=approver.next_approver.staff_id,
                subject="Leave Request Pending",
                message=f"Staff {leave_application.staff.first_name} {leave_application.staff.last_name} has a leave request Pending your approval."
            )
        elif approver.order == 2:
            leave_application.status = "Approved"
            send_notification(
                recipient_id=leave_application.staff_id,
                subject="Leave Request Approved",
                message=f"Your leave request has been Approved."
            )
    elif approval_data.action == "decline":
        leave_application.status = "Declined"
        leave_application.decline_reason = approval_data.reason
        send_notification(
            recipient_id=leave_application.staff_id,
            subject="Leave Request Declined",
            message=f"Your leave request has been declined by {current_user.staff.first_name} {current_user.staff.last_name}: {approval_data.reason}."
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action."
        )

    db.commit()
    return {"message": f"Leave request {approval_data.action}d successfully."}
