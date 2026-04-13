from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.schemas.contagem import ContagemCreate
from app.services.contagem_services import criar_contagem

router = APIRouter(prefix="/contagens", tags=["Contagens"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def criar(dados: ContagemCreate, db: Session = Depends(get_db)):
    return criar_contagem(db, dados)
