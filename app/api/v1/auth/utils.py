from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import random, string
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from app.models.models  import UserRoleAssignment, User
from app.config import settings
from jose import jwt

# pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
from app.database import get_db
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
header = {'alg': ALGORITHM}



def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generate a JWT token."""
    to_encode = data.copy()
    
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY)
        # print(f"Decoded JWT: {payload}")
        username: str = payload.get("username")
        if username is None:
            raise credentials_exception
    except Exception as e:
        raise credentials_exception
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

def verify_admin(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    current_roles = db.query(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == current_user.id,
        UserRoleAssignment.end_date == None).all()
    
    if not any(role.role.name and role.role.name.lower() == "admin" for role in current_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the required permissions to perform this action"
        )
        
    return current_user

def verify_hr(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    current_roles = db.query(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == current_user.id,
        UserRoleAssignment.end_date == None).all()
    
    if not any(role.role.name and role.role.name.lower() == "hr" for role in current_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the required permissions to perform this action"
        )
        
    return current_user

def verify_approver(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    current_roles = db.query(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == current_user.id,
        UserRoleAssignment.end_date == None).all()
    
    if not any(role.role.name and role.role.name.lower() == "approver" for role in current_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the required permissions to perform this action"
        )
        
    return current_user


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))



def set_otp_expiry(otp_lifetime: int = settings.OTP_EXPIRY_MINUTES) -> datetime:
    """Set OTP expiry time (in minutes)"""
    return datetime.now(timezone.utc) + timedelta(minutes=otp_lifetime)