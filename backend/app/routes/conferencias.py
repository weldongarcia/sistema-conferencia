from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.schemas.conferencia_schema import ConferenciaCreate, ConferenciaResponse
from app.services.conferencia_service import criar_conferencia

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