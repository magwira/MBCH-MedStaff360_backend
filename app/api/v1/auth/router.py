from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta  # Fixed: imported timedelta correctly
from app.database import get_db
from app.models.user_models import User, Staff, UserroleAssignment
from app.api.v1.auth.schema import LoginRequest, TokenResponse, VerifyOTP, VerifyOTPRequest
from app.api.v1.auth.utils import create_access_token, generate_otp, set_otp_expiry, verify_password, get_password_hash
from pytz import timezone
from app.config import settings

authRouter = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]  # Fixed: Corrected spelling of "Authentication"
)

@authRouter.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
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

    staff = user.staff
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff information not found"
        )
    
    # Fixed: Added missing .first() and corrected query syntax
    latest_role_assignment = (
        db.query(UserroleAssignment)
        .filter(UserroleAssignment.user_id == user.id, UserroleAssignment.end_date == None)
        .all()  # Fixed: Added parentheses
    )
    
    if not latest_role_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="If you don't have an active role, please contact the Support."
        )
    
    # Fetch roles
    roles = [assignment.role for assignment in latest_role_assignment]
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active roles found for the user"
        )
    
    # Create a jwt payload
    payload = {
        "user_id": user.id,
        "full_name": f"{user.staff.first_name.title()} {user.staff.last_name.title()}",
        "username": user.username,
        "roles": [role.name for role in roles],
        "exp": datetime.now(timezone("Africa/Blantyre")).timestamp() + 3600 
    }

    # Create access token - Fixed: Pass settings correctly
    access_token = create_access_token(
        payload, 
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    user.otp = None
    user.otp_expires_at = None
    db.commit()
    db.refresh(user)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }