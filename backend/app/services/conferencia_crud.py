from app.models.conferencia import Conferencia

def criar_conferencia(db, dados):
    conf = Conferencia(
        estabelecimento_id=dados.estabelecimento_id,
        usuario_id=dados.usuario_id
    )

    db.add(conf)
    db.commit()
    db.refresh(conf)

    return conf