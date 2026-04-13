from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.services.conferencia_service import comparar_conferencia
from app.services.conferencia_crud import criar_conferencia

router = APIRouter(prefix="/conferencia", tags=["Conferencia"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{conferencia_id}")
def comparar(conferencia_id: int, db: Session = Depends(get_db)):
    return comparar_conferencia(db, conferencia_id)