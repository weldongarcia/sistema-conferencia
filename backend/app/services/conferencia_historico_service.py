from app.models.conferencia_historico import ConferenciaHistorico


def registrar_historico(
    db,
    conferencia_id: int,
    usuario_id: int,
    acao: str,
    versao: int,
    motivo: str = None
):

    historico = ConferenciaHistorico(
        conferencia_id=conferencia_id,
        usuario_id=usuario_id,
        acao=acao,
        versao=versao,
        motivo=motivo
    )

    db.add(historico)
    db.commit()

    return historico
