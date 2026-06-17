from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session


from app.database.connection import SessionLocal
from app.models.divergencia import Divergencia
from app.schemas.divergencia import JustificarDivergencia

router = APIRouter(
    prefix="/divergencias",
    tags=["Divergências"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

        
@router.post("/{divergencia_id}/justificar")
def justificar_divergencia(
    divergencia_id: int,
    dados: JustificarDivergencia,
    db: Session = Depends(get_db)
):

    divergencia = db.query(Divergencia).filter_by(
        id=divergencia_id
    ).first()

    if not divergencia:
        raise HTTPException(
            404,
            "Divergência não encontrada"
        )

    divergencia.justificativa_tipo = dados.justificativa_tipo
    divergencia.justificativa_descricao = dados.justificativa_descricao

    db.commit()

    return {
        "msg": "Divergência justificada com sucesso"
    }


@router.get("/{conferencia_id}")
def listar_divergencias(
    conferencia_id: int,
    db: Session = Depends(get_db)
):

    divergencias = db.query(Divergencia).filter_by(
        conferencia_id=conferencia_id
    ).all()

    return divergencias