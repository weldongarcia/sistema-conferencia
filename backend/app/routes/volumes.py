from fastapi import APIRouter

router = APIRouter()

@router.get("/volumes")
def listar():
    return {"msg": "lista volumes"}