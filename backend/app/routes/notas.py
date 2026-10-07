from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.core.perfis import CONFERENTE
from app.core.security import exigir_perfil
from app.models.conferencia import Conferencia
from app.routes.conferencia import verificar_acesso_conferencia
from app.services.nfe_service import importar_xml
from app.utils.auth import get_current_user
router = APIRouter(prefix="/notas", tags=["Notas"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/importar-xml")
def importar_xml_endpoint(
    conferencia_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    # Importação é operação do conferente da loja da conferência.
    exigir_perfil(usuario, [CONFERENTE])

    conferencia = (
        db.query(Conferencia)
        .filter(Conferencia.id == conferencia_id)
        .first()
    )

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada."
        )

    verificar_acesso_conferencia(conferencia, usuario)

    return importar_xml(db, file, conferencia_id)
