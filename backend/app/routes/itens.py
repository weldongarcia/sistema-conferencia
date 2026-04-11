from fastapi import APIRouter

router = APIRouter()

@router.get("/itens")
def listar():
    return {"msg": "lista itens"}