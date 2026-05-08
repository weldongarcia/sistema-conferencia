from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.item_nf import ItemNF

router = APIRouter(prefix="/itens", tags=["Itens"])


@router.get("/")
def listar_itens(conferencia_id: int, db: Session = Depends(get_db)):

    itens = db.query(ItemNF).filter(
        ItemNF.conferencia_id == conferencia_id
    ).all()

    return itens
