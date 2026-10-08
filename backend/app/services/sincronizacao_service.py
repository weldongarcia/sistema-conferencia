from fastapi import HTTPException

from app.models.contagem import Contagem
from app.models.contagem_historico import ContagemHistorico

from app.services.divergencia_service import recalcular_divergencias
from app.services.estado_conferencia import (
    Operacao,
    buscar_conferencia_para_alteracao,
    exigir_operacao_permitida
)
from app.utils.codigo import normalizar_codigo


def sincronizar_contagem(
    db,
    conferencia_id,
    dados,
    usuario
):
    # ==========================================================
    # BUSCAR CONFERÊNCIA
    # ==========================================================

    # Trava a linha da conferência (SELECT ... FOR UPDATE)
    # antes de validar o estado.
    conferencia = buscar_conferencia_para_alteracao(
        db,
        conferencia_id
    )

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada."
        )

    # ==========================================================
    # VERIFICAR ACESSO
    # ==========================================================

    if usuario.perfil == "CONFERENTE":

        if usuario.estabelecimento_id is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Usuário não está vinculado "
                    "a um estabelecimento."
                )
            )

        if (
            conferencia.estabelecimento_id
            != usuario.estabelecimento_id
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Você não possui acesso "
                    "a esta conferência."
                )
            )

    # ==========================================================
    # VERIFICAR STATUS
    # ==========================================================

    # Mesma regra para /conferencias/{id}/sincronizar e
    # /contagens/sincronizar/{id}: ambas usam este service.
    exigir_operacao_permitida(
        conferencia,
        Operacao.SINCRONIZACAO
    )

    # ==========================================================
    # MONTAR SNAPSHOT RECEBIDO
    # ==========================================================

    snapshot = {}

    for item in dados.itens:

        codigo = normalizar_codigo(
            item.codigo
        )

        if item.quantidade < 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"A quantidade do produto "
                    f"{codigo} não pode ser negativa."
                )
            )

        snapshot[codigo] = item.quantidade

    # ==========================================================
    # BUSCAR CONTAGENS ATUAIS
    # ==========================================================

    contagens_existentes = (
        db.query(Contagem)
        .filter(
            Contagem.conferencia_id
            == conferencia_id
        )
        .all()
    )

    mapa_contagens = {
        normalizar_codigo(contagem.codigo): contagem
        for contagem in contagens_existentes
    }

    # ==========================================================
    # ZERAR ITENS QUE NÃO VIERAM NO SNAPSHOT
    #
    # O snapshot representa o estado COMPLETO da conferência.
    # Portanto, se um item anteriormente contado não vier,
    # sua quantidade atual passa a ser zero.
    # ==========================================================

    for codigo, contagem in mapa_contagens.items():

        if codigo not in snapshot:

            quantidade_anterior = (
                contagem.quantidade
            )

            if quantidade_anterior != 0:

                historico = ContagemHistorico(
                    conferencia_id=conferencia_id,
                    codigo=codigo,
                    valor_anterior=quantidade_anterior,
                    valor_novo=0,
                    versao=conferencia.versao,
                    usuario_id=usuario.id
                )

                db.add(historico)

                contagem.quantidade = 0

    # ==========================================================
    # INSERIR / ATUALIZAR SNAPSHOT
    # ==========================================================

    for codigo, quantidade_nova in snapshot.items():

        contagem = mapa_contagens.get(codigo)

        # ------------------------------------------------------
        # CONTAGEM JÁ EXISTE
        # ------------------------------------------------------

        if contagem:

            quantidade_anterior = (
                contagem.quantidade
            )

            if quantidade_anterior != quantidade_nova:

                historico = ContagemHistorico(
                    conferencia_id=conferencia_id,
                    codigo=codigo,
                    valor_anterior=quantidade_anterior,
                    valor_novo=quantidade_nova,
                    versao=conferencia.versao,
                    usuario_id=usuario.id
                )

                db.add(historico)

                contagem.quantidade = quantidade_nova

        # ------------------------------------------------------
        # NOVA CONTAGEM
        # ------------------------------------------------------

        else:

            # --------------------------------------------------
            # NOVA CONTAGEM
            #
            # Quantidade zero não precisa gerar uma linha de
            # Contagem nem um evento de histórico.
            #
            # Isso evita registros artificiais como:
            # "Produto 90852 alterado de 0 para 0".
            #
            # No snapshot completo, ausência de contagem equivale
            # a quantidade zero.
            # --------------------------------------------------

            if quantidade_nova == 0:
                continue

            contagem = Contagem(
                conferencia_id=conferencia_id,
                codigo=codigo,
                quantidade=quantidade_nova
            )

            db.add(contagem)

            historico = ContagemHistorico(
                conferencia_id=conferencia_id,
                codigo=codigo,
                valor_anterior=0,
                valor_novo=quantidade_nova,
                versao=conferencia.versao,
                usuario_id=usuario.id
            )

            db.add(historico)

    # ==========================================================
    # RECALCULAR DIVERGÊNCIAS DA VERSÃO ATUAL
    #
    # Mesma regra de calcular_comparacao. Considera as
    # contagens criadas neste snapshot e não altera
    # divergências de versões anteriores.
    # ==========================================================

    recalcular_divergencias(
        db,
        conferencia
    )

    # ==========================================================
    # COMMIT
    # ==========================================================

    db.commit()

    # ==========================================================
    # RESPOSTA
    # ==========================================================

    return {
        "msg": (
            "Conferência sincronizada "
            "com sucesso."
        ),
        "conferencia_id": conferencia_id,
        "itens_recebidos": len(snapshot),
        "usuario_id": usuario.id
    }