from app.models.conferencia import Conferencia
from sqlalchemy.orm import Session

def criar_conferencia(db: Session, dados):
    nova_conferencia = Conferencia(
        estabelecimento_id=dados.estabelecimento_id,
        usuario_id=dados.usuario_id,
        status="aberto"  # regra de negócio
    )

    db.add(nova_conferencia)
    db.commit()
    db.refresh(nova_conferencia)

    return nova_conferencia