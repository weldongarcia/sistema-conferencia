from fastapi import APIRouter

router = APIRouter()

@router.get("/notas")
def listar_notas():
    return {"msg": "lista de notas"}