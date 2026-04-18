from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.schemas.conferencia_schema import ConferenciaCreate, ConferenciaResponse
from app.services.conferencia_crud import criar_conferencia
from app.services.conferencia_service import fechar_conferencia

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/conferencias", response_model=ConferenciaResponse)
def criar(dados: ConferenciaCreate, db: Session = Depends(get_db)):
    return criar_conferencia(db, dados)

@router.post("/conferencia/{conferencia_id}/fechar")
def fechar(conferencia_id: int, db: Session = Depends(get_db)):
    return fechar_conferencia(db, conferencia_id)