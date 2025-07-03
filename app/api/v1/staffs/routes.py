from fastapi import APIRouter

staffRouter = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@staffRouter.put("/update_staff/{staff_id}")
def update_staff(staff_id: str):
    pass
