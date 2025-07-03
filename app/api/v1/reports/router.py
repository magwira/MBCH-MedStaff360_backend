from fastapi import APIRouter

reportRouter = APIRouter(prefix="/api/v1/reports", tags=["Reports"])

@reportRouter.get("/")
async def index():
    return {"message":"Reports tested"}