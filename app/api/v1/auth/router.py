from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.auth.schemas import LoginRequest, TokenResponse, VerifyOTP, VerifyOTPRequest
from app.api.v1.auth.utils import create_access_token, generate_otp, set_otp_expiry, verify_password, get_password_hash
from app.api.v1.users.schemas import MessageResponse
from app.database import get_db
from app.models.models  import UserRoleAssignment, User
from datetime import datetime, timedelta, timezone
from app.config import settings

from app.utils.email_utils import send_account_verified_email, send_reset_password_otp_to_email
from app.utils.utils_schemas import EmailSendRequest


authRouter = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@authRouter.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Fetch user by username
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid username or password"
        )
        
    if user.staff.is_terminated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to use this account! Contact the Admin."
        ) 
        
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not verified. Please verify your account."
        )
        
        
    # Verify the password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )
        
    # Get the latest role assignment for the user by checking end_date
    staff = user.staff
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff record not found for this user."
        )
    
    latest_role_assignments = (
        db.query(UserRoleAssignment)
        .filter(UserRoleAssignment.user_id == user.id, UserRoleAssignment.end_date.is_(None))
        .all()
    )
    
    if not latest_role_assignments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have not been assigned any active role. Please contact support."
        )

    # Fetch the role details
    roles = [latest_role_assignment.role for latest_role_assignment in latest_role_assignments]
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned roles not found. Please contact support."
        )
    
    # Create the JWT payload
    payload = {
        "user_id": str(user.id),
        "full_name":f"{user.staff.first_name.title()} {user.staff.last_name.title()}",
        "username": user.username,
        "roles": [role.name for role in roles],
    }
    
    # print(payload)
    # Generate access token
    access_token = create_access_token(payload, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    user.otp = None
    user.otp_expires_at = None
    db.commit()
    db.refresh(user)
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@authRouter.post("/verify-otp", response_model=bool)
def verify_otp(request: VerifyOTP, db: Session = Depends(get_db)):
    # Fetch the user by email
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if not user.otp or not user.otp_expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your account is already verified.")
    
    # Check if the OTP matches
    if user.otp != request.otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    # Check if the OTP is expired (optional, add an expiration field to the database if needed)
    if user.otp_expires_at and user.otp_expires_at < datetime.now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP has expired")


    return True

@authRouter.post("/verify-account", response_model=MessageResponse)
def set_new_password(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    # Fetch the user by email
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
     
    if not user.otp or not user.otp_expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your account is already verified.")
    
    # Check if the OTP matches
    if user.otp != request.otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    # Check if the OTP is expired
    if user.otp_expires_at and user.otp_expires_at < datetime.now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP has expired")

    # Update the user's password and clear the OTP
    fullname = f"{user.staff.title}. {user.staff.first_name} {user.staff.last_name}" if user.staff.title else f"{user.staff.first_name} {user.staff.last_name}"
    user.hashed_password = get_password_hash(request.new_password)  
    user.otp = None 
    user.otp_expires_at = None
    user.is_active = True
    user.is_verified = True
    fullname = fullname
    send_account_verified_email(email=user.staff.email, fullname=fullname)
    db.commit()

    return MessageResponse(message= "Password reset successfully. You can now log in with your new password.")



@authRouter.post("/forgot-password", response_model=MessageResponse)
def forgot_password(username: str, db: Session = Depends(get_db)):
    """
    Generates an OTP for password reset and sends it to the user's email.
    """
    # Fetch the user by username
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )

      # Set OTP and its expiration time
    user.otp = generate_otp()
    user.otp_expires_at = set_otp_expiry()
    email_data  =   EmailSendRequest(email=user.staff.email, username=user.username, otp=user.otp)

    db.commit()
    send_reset_password_otp_to_email(email_data=email_data, db=db)
    
    return MessageResponse(message= "OTP has been sent to the registered email address.")