from fastapi import APIRouter, Depends

from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/usuario",
    tags=["Usuario"]
)


@router.get("/me")
def usuario_atual(
    usuario=Depends(get_current_user)
):
    return {
        "id": usuario.id,
        "username": usuario.username,
        "perfil": usuario.perfil,
        "estabelecimento_id": usuario.estabelecimento_id
    }