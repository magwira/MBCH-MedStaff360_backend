from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=8, example="royal@gmail.com")
    password: str = Field(..., min_length=8, example="password1234")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class VerifyOTP(BaseModel):
    username:str = Field(..., min_length=8, example="royal@gmail.com")  
    otp: str = Field(..., min_length=6, max_length=6, example="123456")

class VerifyOTPRequest(BaseModel):
    username:str = Field(..., min_length=8, example="royal@gmail.com")  
    otp: str = Field(..., min_length=6, max_length=6, example="123456")
    new_password: str = Field(..., min_length=8, example="password1234")