from app.models.conferencia import Conferencia
from app.enums.conferencia_enums import StatusConferencia


def criar_conferencia(db, dados, usuario):
    """
    Cria uma conferência vinculada ao estabelecimento
    do usuário autenticado.

    O estabelecimento_id e usuario_id enviados pelo cliente
    NÃO são utilizados para definir a propriedade da conferência.
    """

    if usuario.estabelecimento_id is None:
        raise ValueError(
            "Usuário não está vinculado a um estabelecimento."
        )

    conf = Conferencia(
        estabelecimento_id=usuario.estabelecimento_id,
        usuario_id=usuario.id,
        status=StatusConferencia.RASCUNHO
    )

    db.add(conf)
    db.commit()
    db.refresh(conf)

    return conf


def finalizar_conferencia(db, conferencia):
    conferencia.status = StatusConferencia.FINALIZADA

    db.commit()

    return conferencia