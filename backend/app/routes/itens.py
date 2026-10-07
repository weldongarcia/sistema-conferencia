from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.conferencia import Conferencia
from app.models.item_nf import ItemNF
from app.routes.conferencia import verificar_acesso_conferencia
from app.utils.auth import get_current_user

router = APIRouter(prefix="/itens", tags=["Itens"])


@router.get("/")
def listar_itens(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    # Mesma regra de acesso do GET /conferencia/{id}.
    conferencia = db.query(Conferencia).filter(
        Conferencia.id == conferencia_id
    ).first()

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada."
        )

    verificar_acesso_conferencia(conferencia, usuario)

    itens = db.query(ItemNF).filter(
        ItemNF.conferencia_id == conferencia_id
    ).all()

    return itens
