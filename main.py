from fastapi import FastAPI, Depends, HTTPException, status
# from database import engine
from models import Base
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi.responses import RedirectResponse
from app.middleware import add_cors_middleware
from app.tasks.lifespan import lifespan
from fastapi_pagination import add_pagination

app = FastAPI(
    version="1.0.0",
    title="MBCH-MedStaff360",
    description="Electronic rostering and leave management system for medical staff",
    lifespan=lifespan
)
add_cors_middleware(app)

@app.get("/", include_in_schema=False, status_code=status.HTTP_200_OK)
def read_root():
    return RedirectResponse("/docs")

app.include_router(router=authRouter)
app.include_router(router=usersRouter)
app.include_router(router=leavesRouter)
add_pagination(app)
