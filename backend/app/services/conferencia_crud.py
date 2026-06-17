from app.models.conferencia import Conferencia
from app.enums.conferencia_enums import StatusConferencia


def criar_conferencia(db, dados):
    conf = Conferencia(
        estabelecimento_id=dados.estabelecimento_id,
        usuario_id=dados.usuario_id,
        status=StatusConferencia.RASCUNHO
    )

    db.add(conf)
    db.commit()
    db.refresh(conf)

    return conf

def finalizar_conferencia(db, conferencia):
    conferencia.status = StatusConferencia.FINALIZADA
    db.commit()
    
    