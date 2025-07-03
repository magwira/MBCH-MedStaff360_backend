from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import Date
from sqlalchemy.orm import Session
from uuid import UUID
from app.api.v1.admin.schemas import (
    ApproverCreate,
    AssignStaffGrantRequest,
    AssignStaffRequest,
    AssignUserRequest,
    AssignmentResponse,
    CoEResponse,
    DeptResponse,
    GrantResponse,
    GeneralResponse,
    PositionResponse,
    PublicHolidayResponse,
    StaffCreateSchema,
    StaffWorkgroupAssignmentCreate
)

from app.api.v1.auth.utils import generate_otp, set_otp_expiry, verify_admin
from app.models.models  import Approver, Department, Directorate, Grant, Position, PositionType, PublicHoliday, Role, Staff, StaffDepartmentAssignment, StaffGrantsAssignment, StaffPositionAssignment, StaffCoEAssignment, CoE, StaffWorkgroupAssignment, User, UserRoleAssignment, WorkGroup
from app.database import get_db
from app.utils.email_utils import send_otp_to_email
from app.utils.helper import StaffManager
from app.utils.utils_schemas import EmailSendRequest

adminRouter = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@adminRouter.get("/position-category", status_code=status.HTTP_200_OK, response_model=List[GeneralResponse])
def get_position_categories(db:Session = Depends(get_db), 
                            current_user: User = Depends(verify_admin)):
    categories = db.query(PositionType).all()
    return categories


@adminRouter.get("/positions", response_model=List[PositionResponse], status_code=status.HTTP_200_OK)
async def get_positions(
    q: Optional[str] = None, 
    position_type_id: Optional[UUID] = None,
    db: Session = Depends(get_db), 
    current_user: User = Depends(verify_admin)
):
    query = db.query(Position, PositionType).join(
        PositionType, Position.position_type_id == PositionType.id
    )

    if position_type_id:
        query = query.filter(Position.position_type_id == position_type_id)
    if q:
        query = query.filter(Position.name.ilike(f"%{q}%"))

    positions = query.all()

    result = [
        {
            "position_id": pos.id,
            "position_name": pos.name,
            "description": pos.description,
            "position_category": pos_type.name,
            "position_category_id": pos_type.id,
        }
        for pos, pos_type in positions
    ]

    return result



@adminRouter.get("/departments", response_model=List[DeptResponse], status_code=status.HTTP_200_OK)
def get_departments(q: str = None, db: Session = Depends(get_db),
                    current_user: User = Depends(verify_admin)):
    query = db.query(Department)
    if q:
        query = query.filter(Department.name.ilike(f"%{q}%"))
    departments = query.all()
    
    # Include directorate name in the response
    result = []
    for department in departments:
        directorate = db.query(Directorate).filter(Directorate.id == department.directorate_id).first()
        result.append({
            "department_id": department.id,
            "department_name": department.name,
            "directorate_name": directorate.name if directorate else None,
            "directorate_id": department.directorate_id
        })
    
    return result

@adminRouter.get("/directorates", response_model=List[GeneralResponse],status_code=status.HTTP_200_OK)
async def get_directorates(q: str = None, db: Session = Depends(get_db),
                           current_user: User = Depends(verify_admin)):
    query = db.query(Directorate)
    if q:
        query = query.filter(Directorate.name.ilike(f"%{q}%"))
    directorates = query.all()
    return directorates

@adminRouter.get("/coes", response_model=List[CoEResponse], status_code=status.HTTP_200_OK)
async def get_coes(q: str = None, db: Session = Depends(get_db),
                   current_user: User = Depends(verify_admin)):
    query = db.query(CoE)
    if q:
        query = query.filter(
            (CoE.name.ilike(f"%{q}%")) |
            (CoE.coe_number.ilike(f"%{q}%"))
        )
    coes = query.all()
    return coes

@adminRouter.get("/grants", response_model=List[GrantResponse], status_code=status.HTTP_200_OK)
async def get_grants(q: str = None, db: Session = Depends(get_db),
                     current_user: User = Depends(verify_admin)):
    query = db.query(Grant)
    if q:
        query = query.filter(
            (Grant.name.ilike(f"%{q}%")) |
            (Grant.grant_number.ilike(f"%{q}%")))
    grants = query.all()
    return grants


@adminRouter.get("/roles", response_model=List[GeneralResponse], status_code=status.HTTP_200_OK)
async def get_roles(q: str = None, db: Session = Depends(get_db)
                    ,current_user: User = Depends(verify_admin)
                    ):
    query = db.query(Role)
    if q:
        query = query.filter(Role.name.ilike(f"%{q}%"))
    roles = query.all()
    return roles



@adminRouter.get("/public-holidays", response_model=List[PublicHolidayResponse])
def get_public_holidays(db: Session = Depends(get_db),
                        # current_user: User = Depends(verify_admin)
                        ):
    public_holidays = db.query(PublicHoliday).all()
    return [
        PublicHolidayResponse(
            id=ph.id,
            date=ph.date,
            name=ph.name
        ) for ph in public_holidays
    ]
 