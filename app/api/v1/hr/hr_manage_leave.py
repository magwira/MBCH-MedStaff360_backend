from fastapi import APIRouter

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models  import Position, StaffPositionAssignment, LeaveApplication
from app.api.v1.auth.utils import verify_hr
from app.models.models  import User
from typing import List
from pydantic import BaseModel
from datetime import date
from uuid import UUID


hr_leaveRouter = APIRouter(prefix="/api/v1/hr", tags=["HR Leave Management"])


class LeaveApplicationResponse(BaseModel):
    leave_application_id: UUID
    staff_id: UUID
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: str

    class Config:
        from_attribute = True

@hr_leaveRouter.get("/staff-leave-history/{staff_id}", response_model=List[LeaveApplicationResponse], status_code=status.HTTP_200_OK)
def get_staff_leave_history(staff_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(verify_hr)):
   
    staff = db.query(User).filter(User.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

    leave_applications = db.query(LeaveApplication).filter(LeaveApplication.staff_id == staff.id).all()
    if not leave_applications:
        return []

    return [
        LeaveApplicationResponse(
            leave_application_id=leave.id,
            staff_id=leave.staff_id,
            leave_type=leave.leave_type.name,
            start_date=leave.start_date,
            end_date=leave.end_date,
            reason=leave.comment,
            status=leave.status
        ) for leave in leave_applications
    ]