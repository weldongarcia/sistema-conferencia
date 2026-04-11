from fastapi import APIRouter

router = APIRouter()

@router.get("/irregularidades")
def listar():
    return {"msg": "lista irregularidades"}