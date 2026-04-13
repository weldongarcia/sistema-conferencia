from fastapi import APIRouter, UploadFile, File, Depends, Query, Form
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.services.nfe_service import importar_xml
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
    db: Session = Depends(get_db)
):
    return importar_xml(db, file, conferencia_id)