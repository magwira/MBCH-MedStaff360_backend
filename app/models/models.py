from sqlalchemy import  Enum, Integer, Column, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from enum import Enum as PyEnum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, UUID, DateTime, ForeignKey


# Roles table
class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)  
    # Relationship
    user_role_assignments = relationship('UserRoleAssignment', back_populates='role')
    
# Position Types table
class PositionType(Base):
    __tablename__ = 'position_types'
    
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)  
    # Relationship
    positions = relationship('Position', back_populates='position_type')
    leave_policies = relationship("LeavePolicies", back_populates="position_type")

# Positions table
class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    position_type_id = Column(UUID(as_uuid=True), ForeignKey('position_types.id', ondelete='CASCADE'))
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)  
    # Relationship
    staff_position_assignments = relationship('StaffPositionAssignment', back_populates='position')
    position_type = relationship('PositionType', back_populates='positions')

# CoEs table
class CoE(Base):
    __tablename__ = 'coes'
    
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    coe_number = Column(String(255), unique=True, nullable=False)
    center_name = Column(String(255), unique=True, nullable=True)
    description = Column(Text, nullable=True)  
    # Relationship
    staff_coe_assignments = relationship('StaffCoEAssignment', back_populates='coe')
    workgroups = relationship("WorkGroup", back_populates="coe")

# Directorates table
class Directorate(Base):
    __tablename__ = 'directorates'
    
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)  
    # Relationship
    departments = relationship('Department', back_populates='directorate')
    director_assignments = relationship("DirectorateDirectorAssignment", back_populates="directorate")

# Departments table
class Department(Base):
    __tablename__ = 'departments'
    
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    directorate_id = Column(UUID(as_uuid=True), ForeignKey('directorates.id', ondelete='CASCADE'))
    description = Column(Text, nullable=True)  
    # Relationship
    directorate = relationship('Directorate', back_populates='departments')
    staff_department_assignments = relationship('StaffDepartmentAssignment', back_populates='department')

class Gender(PyEnum):
    Male = "Male"
    Female = "Female"
    
# Staff Model
class Staff(Base):
    __tablename__ = 'staffs'
   
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    emp_number = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    title = Column(Enum("Mr", "Mrs", "Ms", "Dr", "Prof",name="titles"), nullable=True)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(15), unique=True)
    gender = Column(Enum(Gender), nullable=True)
    dob = Column(DateTime, nullable=True)
    home_address = Column(Text, nullable=True)
    highest_education = Column(String(255), nullable=True)
    field_of_study = Column(String(255), nullable=True)
    date_engaged = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False)
    is_terminated = Column(Boolean, default=False)
    date_created = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    

    # Relationships
    position_assignments = relationship('StaffPositionAssignment', back_populates='staff')
    coe_assignments = relationship('StaffCoEAssignment', back_populates='staff')
    department_assignments = relationship('StaffDepartmentAssignment', back_populates='staff')
    directorate_director_assignments = relationship("DirectorateDirectorAssignment", back_populates="staff")
    staff_workgroup_assignments = relationship("StaffWorkgroupAssignment", back_populates="staff")
    user = relationship('User', back_populates='staff', uselist=False)
    staff_grants_assignment = relationship('StaffGrantsAssignment', back_populates='staff')
    approver_assignments = relationship('Approver', back_populates='staff')
    leave_application = relationship("LeaveApplication", back_populates="staff")
    notifications = relationship('Notification', back_populates='recipient')
    leave_balances = relationship("LeaveBalances", back_populates="staff")
    timesheets = relationship("Timesheet", back_populates="staff", cascade="all, delete")    
    timesheet_config = relationship("TimesheetConfig", back_populates="staff", cascade="all, delete")

# User Model
class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    otp = Column(String(255), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    # Foreign Key 
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staffs.id', ondelete='CASCADE'), index=True)
    
    # Relationship
    staff = relationship('Staff', back_populates='user')
    role_assignments = relationship('UserRoleAssignment', back_populates='user')
    staff_position_assignments = relationship('StaffPositionAssignment', back_populates='user')
    staff_coe_assignments = relationship('StaffCoEAssignment', back_populates='user')
    staff_department_assignments = relationship('StaffDepartmentAssignment', back_populates='user')
    directorate_director_assignments = relationship("DirectorateDirectorAssignment", back_populates="user")
    staff_grants_assignment = relationship('StaffGrantsAssignment', back_populates='user')
    approver_assignments = relationship('Approver', back_populates='user')
    staff_workgroup_assignments = relationship("StaffWorkgroupAssignment", back_populates="user")
    delegations = relationship("Delegation", back_populates="delegatee")

# Staff Role Assignments table
class UserRoleAssignment(Base):
    __tablename__ = 'user_role_assignments'
    
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), index=True)
    start_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    end_date = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship('User', back_populates='role_assignments')
    role = relationship('Role', back_populates='user_role_assignments')

# Staff Position Assignment with Overlap Prevention
class StaffPositionAssignment(Base):
    __tablename__ = 'staff_position_assignments'

    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staffs.id', ondelete='CASCADE'), index=True)
    position_id = Column(UUID(as_uuid=True), ForeignKey('positions.id', ondelete='CASCADE'), index=True)
    seniority = Column(Boolean, default=False, nullable=True)
    start_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    end_date = Column(DateTime, nullable=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True)
    
    # relationships
    staff = relationship('Staff', back_populates='position_assignments')
    position = relationship('Position', back_populates='staff_position_assignments')
    user = relationship('User', back_populates='staff_position_assignments')

   
# Staff CoE Assignment with Overlap Prevention
class StaffCoEAssignment(Base):
    __tablename__ = 'staff_coe_assignments'

    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staffs.id', ondelete='CASCADE'),index=True)
    coe_id = Column(UUID(as_uuid=True), ForeignKey('coes.id', ondelete='CASCADE'), index=True)
    start_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    end_date = Column(DateTime, nullable=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True)
    
    staff = relationship('Staff', back_populates='coe_assignments')
    coe = relationship('CoE', back_populates='staff_coe_assignments')
    user = relationship('User', back_populates='staff_coe_assignments')


# Staff Department Assignments table
class StaffDepartmentAssignment(Base):
    __tablename__ = "staff_department_assignments"

    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staffs.id", ondelete="CASCADE"), index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), index=True)
    start_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    end_date = Column(DateTime, nullable=True)
    is_hod = Column(Boolean, default=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True)

    # Relationships
    staff = relationship("Staff", back_populates="department_assignments")
    department = relationship("Department", back_populates="staff_department_assignments")
    user = relationship('User', back_populates='staff_department_assignments')


# Directorates Director Assignments table
class DirectorateDirectorAssignment(Base):
    __tablename__ = "directorate_director_assignments"

    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staffs.id", ondelete="CASCADE"))
    directorate_id = Column(UUID(as_uuid=True), ForeignKey("directorates.id", ondelete="SET NULL"))
    start_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    end_date = Column(DateTime, nullable=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True)

    # Relationships
    staff = relationship("Staff", back_populates="directorate_director_assignments")
    directorate = relationship("Directorate", back_populates="director_assignments")
    user = relationship('User', back_populates='directorate_director_assignments')

# Grants table
class Grant(Base):
    __tablename__ = 'grants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    grant_number = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Relationships
    staff_grants_assignment = relationship('StaffGrantsAssignment', back_populates='grant')

# Staff Grants table
class StaffGrantsAssignment(Base):
    __tablename__ = 'staff_grants_assignment'

    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staffs.id', ondelete='CASCADE'))
    grant_id = Column(UUID(as_uuid=True), ForeignKey('grants.id', ondelete='CASCADE'))
    start_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    end_date = Column(DateTime, nullable=True)
    work_time_percentage = Column(Float, nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True)
    
    # relationships
    staff = relationship('Staff', back_populates='staff_grants_assignment')
    grant = relationship('Grant', back_populates='staff_grants_assignment')
    user = relationship('User', back_populates='staff_grants_assignment')

# WorkGroup table
class WorkGroup(Base):
    __tablename__ = "workgroups"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    name = Column(String(255), unique=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    coe_id = Column(UUID(as_uuid=True), ForeignKey("coes.id", ondelete="SET NULL"))
    description = Column(Text, nullable=True) 

    # Relationships
    approvers = relationship("Approver", back_populates="workgroup", cascade="all, delete-orphan")
    members = relationship("StaffWorkgroupAssignment", back_populates="workgroup", cascade="all, delete-orphan")
    coe = relationship("CoE", back_populates="workgroups")

# Approver table
class Approver(Base):
    __tablename__ = "approvers"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    workgroup_id = Column(UUID(as_uuid=True), ForeignKey("workgroups.id", ondelete="CASCADE"),index=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staffs.id", ondelete="CASCADE"),index=True)
    approver_order = Column(Integer, nullable=False)
    notify_only = Column(Boolean, default=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True)
    start_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Relationships
    workgroup = relationship("WorkGroup", back_populates="approvers")
    staff = relationship("Staff", back_populates="approver_assignments")
    delegations = relationship("Delegation", foreign_keys="[Delegation.approver_id]", back_populates="approver")
    leave_approval_status = relationship("LeaveApprovalStatus", back_populates="approver")
    user = relationship('User', back_populates='approver_assignments')
    timesheet_approval_status = relationship("TimesheetApprovalStatus", back_populates="approver")
    
# Linked Staffs Table
class StaffWorkgroupAssignment(Base):
    __tablename__ = "staff_workgroup_assignments"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    workgroup_id = Column(UUID(as_uuid=True), ForeignKey("workgroups.id", ondelete="CASCADE"),index=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staffs.id", ondelete="CASCADE"),index=True)
    start_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    end_date = Column(DateTime, nullable=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True)

    # Relationships
    workgroup = relationship("WorkGroup", back_populates="members")
    staff = relationship("Staff", back_populates="staff_workgroup_assignments")
    user = relationship('User', back_populates='staff_workgroup_assignments')


# Delegation table
class Delegation(Base):
    __tablename__ = "delegations"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("approvers.id", ondelete="CASCADE"), nullable=False)
    delegatee_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # Ensure correct table name
    start_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    end_date = Column(DateTime, nullable=True)

    # Relationships
    approver = relationship("Approver", back_populates="delegations")
    delegatee = relationship("User", back_populates="received_delegations")

# Notification table
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("staffs.id", ondelete="CASCADE"))
    subject = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    recipient = relationship("Staff", back_populates="notifications")
    
    
# Leave Types table
class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    leave_application = relationship("LeaveApplication", back_populates="leave_type")
    leave_policies = relationship("LeavePolicies", back_populates="leave_type")
    leave_balances = relationship("LeaveBalances", back_populates="leave_type")

# Leave Applications table
class LeaveApplication(Base):
    __tablename__ = "leave_applications"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staffs.id", ondelete="CASCADE"))
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="CASCADE"))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(Enum("Pending", "Approved", "Rejected", "Cancelled",name="status"), default="Pending")
    comment = Column(Text, nullable=True)
    applied_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    staff = relationship("Staff", back_populates="leave_application")
    leave_type = relationship("LeaveType", back_populates="leave_application")
    leave_approval_status = relationship("LeaveApprovalStatus", back_populates="leave_application")


# Leave Policies table
class LeavePolicies(Base):
    __tablename__ = "leave_policies"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="CASCADE"))
    position_type_id = Column(UUID(as_uuid=True), ForeignKey("position_types.id", ondelete="CASCADE"))
    max_days = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    leave_type = relationship("LeaveType", back_populates="leave_policies")
    position_type = relationship("PositionType", back_populates="leave_policies")
    
# Leave Balances table
class LeaveBalances(Base):
    __tablename__ = "leave_balances"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staffs.id", ondelete="CASCADE"))
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="CASCADE"))
    accumulated_days = Column(Integer, nullable=True)
    taken_days = Column(Integer, nullable=False)
    remaining_days = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    staff = relationship("Staff", back_populates="leave_balances")
    leave_type = relationship("LeaveType", back_populates="leave_balances")
    
class PublicHoliday(Base):
    __tablename__ = "public_holidays"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    

# aproval status for staff leave application status by approvers
class LeaveApprovalStatus(Base):
    __tablename__ = "leave_approval_status"
    id = Column(UUID(as_uuid=True),primary_key=True, index = True, default=uuid.uuid4)
    leave_application_id = Column(UUID(as_uuid=True), ForeignKey("leave_applications.id", ondelete="CASCADE"))
    approver_id = Column(UUID(as_uuid=True), ForeignKey("approvers.id", ondelete="CASCADE"))
    status = Column(Enum("Pending", "Approved", "Rejected", "Cancelled",name="status"), default="Pending")
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    leave_application = relationship("LeaveApplication", back_populates="leave_approval_status")
    approver = relationship("Approver", back_populates="leave_approval_status")
    


# Enum for Timesheet Status
class TimesheetStatus(PyEnum):
    Draft = "Draft"
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"



class Timesheet(Base):
    __tablename__ = "timesheets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staffs.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    month = Column(String(7), nullable=False)  # Format: YYYY-MM
    status = Column(Enum(TimesheetStatus), default=TimesheetStatus.Pending, nullable=False)
    total_hours_per_day = Column(Float, default=0.0)
    total_hours_per_month = Column(Float, default=0.0)
    reject_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    staff = relationship("Staff", back_populates="timesheets")
    entries = relationship("TimesheetEntry", back_populates="timesheet", cascade="all, delete")
    timesheet_action_logs = relationship("TimesheetActionLog", back_populates="timesheet")
    approvals = relationship("TimesheetApprovalStatus", back_populates="timesheet")

class TimesheetEntry(Base):
    __tablename__ = "timesheet_entry"

    id = Column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    timesheet_id = Column(UUID(as_uuid=True), ForeignKey("timesheets.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    month = Column(String(7), nullable=False)
    total_hours_per_day = Column(Float, default=7.5)
    public_holiday = Column(Boolean, default=False)
    public_holiday_hours = Column(Float, default=7.5)
    leave_type = Column(Boolean, default=False)
    leave_hours = Column(Float, default=7.5)

    # Relationships
    timesheet = relationship("Timesheet", back_populates="entries")

class TimesheetApprovalStatus(Base):
    __tablename__ = "timesheet_approval_status"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timesheet_id = Column(UUID(as_uuid=True), ForeignKey("timesheets.id"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("approvers.id"), nullable=False)
    status = Column(Enum(TimesheetStatus), nullable=False, default=TimesheetStatus.Pending)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    timesheet = relationship("Timesheet", back_populates="approvals")
    approver = relationship("Approver", back_populates="timesheet_approval_status")
class TimesheetActionLog(Base):
    __tablename__ = "timesheet_action_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timesheet_id = Column(UUID(as_uuid=True), ForeignKey("timesheets.id"), nullable=False)
    staff_id = Column(UUID, ForeignKey("staffs.id"), nullable=False)
    staff_name = Column(String(255), nullable=False)
    period = Column(String(255), nullable=False) 
    status = Column(Enum(TimesheetStatus), nullable=False, default=TimesheetStatus.Pending)
    action = Column(Enum(TimesheetStatus), nullable=True)  # Approve or Reject
    action_taken_by = Column(UUID, ForeignKey("staffs.id"), nullable=True)
    action_timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    comments = Column(Text, nullable=True)

    # Relationships
    timesheet = relationship("Timesheet", back_populates="timesheet_action_logs")
    staff = relationship(Staff, foreign_keys=[staff_id])
    action_taker = relationship(Staff, foreign_keys=[action_taken_by])
   

class TimesheetConfig(Base):
    __tablename__ = "timesheet_config"
    
    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    is_open = Column(Boolean, default=True)
    open_date = Column(DateTime, nullable=True)
    close_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    created_by = Column(UUID(as_uuid=True), ForeignKey("staffs.id", ondelete="SET NULL"), nullable=False)

    # Relationships
    staff = relationship("Staff", back_populates="timesheet_config")