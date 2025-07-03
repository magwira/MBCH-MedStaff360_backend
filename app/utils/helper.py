from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from uuid import UUID
from fastapi import HTTPException, Query, status
from app.models.models  import (
    Department, Directorate, DirectorateDirectorAssignment, Grant, PositionType, PublicHoliday, Staff, CoE, Role, Position,
    StaffCoEAssignment, UserRoleAssignment,
    StaffPositionAssignment, StaffDepartmentAssignment, StaffGrantsAssignment, StaffWorkgroupAssignment, User, WorkGroup
)
from app.utils.email_utils import send_transfer_notification_email
from app.utils.utils_schemas import WorkGroupCreate, WorkGroupUpdate


class StaffManager:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def transfer_staff_coe(self, staff_id: UUID, new_coe_id: UUID):
        try:
            staff = self.db_session.query(Staff).filter(Staff.id == staff_id).one_or_none()
            if not staff:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staff with ID {staff_id} not found.")

            coe = self.db_session.query(CoE).filter(CoE.id == new_coe_id).one_or_none()
            if not coe:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"CoE with ID {new_coe_id} not found.")

            # Close current assignment
            current_assignment = (
                self.db_session.query(StaffCoEAssignment)
                .filter(StaffCoEAssignment.staff_id == staff_id, StaffCoEAssignment.end_date == None)
                .one_or_none()
            )

            if current_assignment:
                current_assignment.end_date = datetime.now(timezone.utc)
                self.db_session.add(current_assignment)  
            # Add new coe assignment
            new_coe_assignment = StaffCoEAssignment(
                staff_id=staff.id,
                coe_id=new_coe_id,
                start_date=datetime.now(timezone.utc),
            )
            self.db_session.add(new_coe_assignment)
            
            user = self.db_session.query(User).filter(User.staff_id == staff.id).one_or_none()
            if not user:
                raise HTTPException(detail="User not found", status_code=status.HTTP_404_NOT_FOUND)
    
            username = f"{coe.coe_number}_{staff.emp_number}"

            user.username = username
            self.db_session.add(user)
            
            self.db_session.commit()
            full_name = f"{staff.first_name} {staff.last_name}"
            send_transfer_notification_email(
                staff_email=staff.email, 
                full_name=full_name, 
                old_coe_name=current_assignment.coe.name,
                new_coe_name=coe.name, 
                new_username=username,
                center_name=coe.center_name
                )
        except Exception as e:
            self.db_session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")



    def assign_user_role(self, user_id: UUID, new_role_id: UUID):
        # Validate the user exists
        user = self.db_session.query(User).filter(User.id == user_id).one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found."
            )

        # Validate the role exists
        role = self.db_session.query(Role).filter(Role.id == new_role_id).one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {new_role_id} not found."
            )

        # Fetch the user's current active role assignments
        active_roles = (
            self.db_session.query(UserRoleAssignment)
            .filter(UserRoleAssignment.user_id == user_id, UserRoleAssignment.end_date == None)
            .all()
        )

        # Ensure the user has at least one role and does not exceed two roles
        if len(active_roles) >= 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user cannot be assigned more than two active roles."
            )

        if len(active_roles) == 1 and active_roles[0].role_id == new_role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user is already assigned this role."
            )

        # Create a new role assignment
        new_role_assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=new_role_id,
            start_date=datetime.now(timezone.utc),
        )
        self.db_session.add(new_role_assignment)

        # Commit the changes to the database
        self.db_session.commit()
        
    def terminate_staff_role(self, user_id: UUID, role_id: UUID):
        """
        Terminate a role assignment for a user.

        Args:
            user_id (UUID): The ID of the user.
            role_id (UUID): The ID of the role to terminate.
        """
        try:
            # Fetch the current role assignment
            current_role_assignment = (
                self.db_session.query(UserRoleAssignment)
                .filter(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.role_id == role_id,
                    UserRoleAssignment.end_date == None
                )
                .one_or_none()
            )

            if not current_role_assignment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No active role assignment found for user ID {user_id} and role ID {role_id}."
                )

            # Terminate the assignment
            current_role_assignment.end_date = datetime.now(timezone.utc)
            self.db_session.add(current_role_assignment)
            self.db_session.commit()
        except Exception as e:
            # self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error terminating role assignment: {str(e)}"
            )



    def assign_position(self, staff_id: UUID, position_id: UUID, assigned_by: Optional[UUID] = None):
        """
        Assign a position to a staff member. If the position type is 'Manager' or 'Director',
        handle the HoD or Director assignment logic accordingly.

        Args:
            staff_id (uuid.UUID): ID of the staff to assign the position to.
            position_id (uuid.UUID): ID of the position to assign.
            assigned_by (uuid.UUID): ID of the user making the assignment.

        Returns:
            str: Confirmation message.
        """
        # Fetch the position and related position type
        position = self.db_session.query(Position).filter(Position.id == position_id).first()
        if not position:
            raise ValueError("Position not found.")

        position_type = position.position_type

        # Fetch the staff
        staff = self.db_session.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise ValueError("Staff not found.")

        # End all previous position assignments for the staff
        current_position_assignments = (
            self.db_session.query(StaffPositionAssignment)
            .filter(StaffPositionAssignment.staff_id == staff_id, StaffPositionAssignment.end_date.is_(None))
            .all()
        )
        for assignment in current_position_assignments:
            assignment.end_date = datetime.now(timezone.utc)
            self.db_session.add(assignment)

        # Handle Manager (HoD) assignment
        if position_type.name.lower() == "manager":
            # Fetch current department assignment
            department_assignment = (
                self.db_session.query(StaffDepartmentAssignment)
                .filter(
                    StaffDepartmentAssignment.department_id == staff.department_assignments[0].department_id,
                    StaffDepartmentAssignment.is_hod.is_(True),
                    StaffDepartmentAssignment.end_date.is_(None)
                )
                .first()
            )
            if department_assignment:
                # End the current HoD assignment
                department_assignment.end_date = datetime.now(timezone.utc)
                self.db_session.add(department_assignment)

            # Assign the new HoD
            new_assignment = StaffDepartmentAssignment(
                staff_id=staff_id,
                department_id=staff.department_assignments[0].department_id,
                is_hod=True,
                start_date=datetime.now(timezone.utc),
                assigned_by=assigned_by
            )
            self.db_session.add(new_assignment)

        elif position_type.name.lower() == "director":
            # Fetch the directorate based on the staff's current department
            department = (
                self.db_session.query(Department)
                .filter(Department.id == staff.department_assignments[0].department_id)
                .first()
            )

            if not department or not department.directorate:
                raise ValueError(
                    f"Staff with ID {staff_id} belongs to a department without a directorate assignment."
                )

            directorate_id = department.directorate.id

            # End any existing Director assignment in this directorate
            director_assignment = (
                self.db_session.query(DirectorateDirectorAssignment)
                .filter(
                    DirectorateDirectorAssignment.directorate_id == directorate_id,
                    DirectorateDirectorAssignment.end_date.is_(None)
                )
                .first()
            )
            if director_assignment:
                director_assignment.end_date = datetime.now(timezone.utc)
                self.db_session.add(director_assignment)

            # Assign the new Director
            new_assignment = DirectorateDirectorAssignment(
                staff_id=staff_id,
                directorate_id=directorate_id,
                start_date=datetime.now(timezone.utc),
                assigned_by=assigned_by
            )
            self.db_session.add(new_assignment)

        # General position assignment
        new_position_assignment = StaffPositionAssignment(
            staff_id=staff_id,
            position_id=position_id,
            start_date=datetime.now(timezone.utc),
            assigned_by=assigned_by
        )
        self.db_session.add(new_position_assignment)

        # Commit the changes
        self.db_session.commit()




    def assign_staff_department(self, staff_id: UUID, new_department_id: UUID, is_hod: bool = False):
        staff = self.db_session.query(Staff).filter(Staff.id == staff_id).one_or_none()
        if not staff:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staff with ID {staff_id} not found.")
        
        department = self.db_session.query(Department).filter(Department.id == new_department_id).one_or_none()
        
        if not department:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Department with ID {new_department_id} not found.")
        
        current_department_assignment = (
            self.db_session.query(StaffDepartmentAssignment)
            .filter(StaffDepartmentAssignment.staff_id == staff_id, StaffDepartmentAssignment.end_date == None)
            .one_or_none()
        )
        if current_department_assignment:
            current_department_assignment.end_date = datetime.now(timezone.utc)

            self.db_session.add(current_department_assignment)
        self.db_session.commit()
        self.db_session.refresh(staff)

        new_department_assignment = StaffDepartmentAssignment(
            staff_id=staff.id,
            department_id=new_department_id,
            start_date=datetime.now(timezone.utc),
            is_hod=is_hod,
        )
        self.db_session.add(new_department_assignment)
        self.db_session.commit()


    def assign_staff_grant(self, staff_id: UUID, new_grant_id: UUID, work_time_percentage: float):
        try:
            if not (0 <= work_time_percentage <= 100):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Work time percentage must be between 0 and 100.")

            staff = self.db_session.query(Staff).filter(Staff.id == staff_id).one_or_none()
            if not staff:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staff with ID {staff_id} not found.")

            grant = self.db_session.query(Grant).filter(Grant.id == new_grant_id).one_or_none()
            if not grant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Grant with ID {new_grant_id} not found.")

            # Check for overlapping grants if necessary
            overlapping_grants = (
                self.db_session.query(StaffGrantsAssignment)
                .filter(StaffGrantsAssignment.staff_id == staff.id, StaffGrantsAssignment.grant_id == grant.id, StaffGrantsAssignment.end_date == None)
                .one_or_none()
            )
            if overlapping_grants:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grant already assigned to this staff.")

            # Assign the grant
            staff_grant_assignment = StaffGrantsAssignment(
                staff_id=staff.id,
                grant_id=grant.id,
                work_time_percentage=work_time_percentage,
                start_date=datetime.now(timezone.utc),
            )
            self.db_session.add(staff_grant_assignment)
            self.db_session.commit()
        except Exception as e:
            # self.db_session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error assigning grant: {str(e)}")
        
        
    def terminate_staff_grant(db_session: Session, staff_id: UUID, grant_id: UUID):
        """
        Terminate a grant assignment for a staff member.

        Args:
            db_session (Session): The database session.
            staff_id (UUID): The ID of the staff member.
            grant_id (UUID): The ID of the grant to terminate.
        """
        try:
            # Fetch the current grant assignment
            current_grant_assignment = (
                db_session.query(StaffGrantsAssignment)
                .filter(
                    StaffGrantsAssignment.staff_id == staff_id,
                    StaffGrantsAssignment.grant_id == grant_id,
                    StaffGrantsAssignment.end_date == None
                )
                .one_or_none()
            )

            if not current_grant_assignment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No active grant assignment found for staff ID {staff_id} and grant ID {grant_id}."
                )

            # Terminate the assignment
            current_grant_assignment.end_date = datetime.now(timezone.utc)
            db_session.add(current_grant_assignment)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error terminating grant assignment: {str(e)}"
            )

        
        
        # Assign Director to Directorate
    def assign_director(self, staff_id: UUID, directorate_id: UUID):
        try:
            # Validate staff and directorate
            staff = self.db_session.query(Staff).filter(Staff.id == staff_id).one_or_none()
            if not staff:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staff with ID {staff_id} not found.")

            directorate = self.db_session.query(Directorate).filter(Directorate.id == directorate_id).one_or_none()
            if not directorate:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Directorate with ID {directorate_id} not found.")

            # Check for existing director
            current_director = (
                self.db_session.query(DirectorateDirectorAssignment)
                .filter(
                    DirectorateDirectorAssignment.directorate_id == directorate_id,
                    DirectorateDirectorAssignment.end_date == None
                ).one_or_none()
            )
            if current_director:
                current_director.end_date = datetime.now(timezone.utc)

            # Assign new director
            new_director_assignment = DirectorateDirectorAssignment(
                staff_id=staff_id,
                directorate_id=directorate_id,
                start_date=datetime.now(timezone.utc),
            )
            self.db_session.add(new_director_assignment)
            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error assigning Director: {str(e)}")
        
    
    def assign_workgroup(self, staff_id: UUID, workgroup_id: UUID):
        try:
            # Validate staff and workgroup
            staff = self.db_session.query(Staff).filter(Staff.id == staff_id).one_or_none()
            if not staff:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staff with ID {staff_id} not found.")

            workgroup = self.db_session.query(WorkGroup).filter(WorkGroup.id == workgroup_id).one_or_none()
            if not workgroup:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workgroup with ID {workgroup_id} not found.")

            # Check for existing workgroup assignment
            current_workgroup = (
                self.db_session.query(StaffWorkgroupAssignment)
                .filter(
                    StaffWorkgroupAssignment.staff_id == staff_id,
                    StaffWorkgroupAssignment.end_date == None
                ).one_or_none()
            )
            if current_workgroup:
                current_workgroup.end_date = datetime.now(timezone.utc)

            # Assign new workgroup
            new_workgroup_assignment = StaffWorkgroupAssignment(
                staff_id=staff_id,
                workgroup_id=workgroup_id,
                start_date=datetime.now(timezone.utc),
            )
            self.db_session.add(new_workgroup_assignment)
            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error assigning Workgroup: {str(e)}")

    

class WorkFlowGroupsManager:
    def __init__(self, db_session: Session):
        self.db_session = db_session

        # CRUD Helpers
    def get_workgroup(self, workgroup_id: UUID):
        workgroup = self.db_session.query(WorkGroup).filter(WorkGroup.id == workgroup_id).first()
        if not workgroup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkGroup not found")
        return workgroup

    def get_workgroups(self, skip: int = 0, limit: int = 10, search: Optional[str] = Query(None)):
        query = self.db_session.query(WorkGroup).join(CoE, WorkGroup.coe_id == CoE.id)
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    WorkGroup.name.ilike(search_filter),
                    CoE.name.ilike(search_filter)
                )
            )
        return query.offset(skip).limit(limit).all()
        # return self.db_session.query(WorkGroup).offset(skip).limit(limit).all()

    def create_workgroup(self,coe_id:UUID, name:str, desc:Optional[str]):
        workgroup = WorkGroup(
            name = name,
            coe_id = coe_id,
            description = desc,
            created_at = datetime.now(timezone.utc)
        )
        self.db_session.add(workgroup)
        self.db_session.commit()
        self.db_session.refresh(workgroup)
        return workgroup

    def update_workgroup(self, workgroup_id: UUID, update_data: WorkGroupUpdate):
        workgroup = self.get_workgroup(self.db_session, workgroup_id)
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(workgroup, key, value)
        self.db_session.commit()
        self.db_session.refresh(workgroup)
        return workgroup

    def delete_workgroup(self, workgroup_id: UUID):
        workgroup = self.get_workgroup(self.db_session, workgroup_id)
        self.db_session.delete(workgroup)
        self.db_session.commit()
        return {"message": "WorkGroup deleted successfully"}

def get_public_holidays(start_date, end_date, db: Session):
    return db.query(PublicHoliday).filter(
        PublicHoliday.date.between(start_date, end_date)
    ).all()
    

def get_full_name(staff:Staff):
    fullname = f"{staff.title}. {staff.first_name} {staff.last_name}" if staff.title else f"{staff.first_name} {staff.last_name}"
    return fullname