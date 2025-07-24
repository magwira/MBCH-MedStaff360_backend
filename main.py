from typing import Annotated
from fastapi import Depends, FastAPI, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from app.api.v1.auth.router import authRouter
from app.middleware import add_cors_middleware

app = FastAPI(
    version="1.0.0",
    title="Mbch-medsatff360",
    description="E-rostering and Leave Management API"
)
add_cors_middleware(app)

@app.get("/", include_in_schema=False, status_code= status.HTTP_200_OK)
def read_root():
    return RedirectResponse("/docs")

app.include_router(router=authRouter)
