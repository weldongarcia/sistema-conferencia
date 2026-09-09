from fastapi import HTTPException

from app.models.contagem import Contagem
from app.models.conferencia import Conferencia
from app.models.item_nf import ItemNF
from app.models.divergencia import Divergencia
from app.models.contagem_historico import ContagemHistorico

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

    conferencia = (
        db.query(Conferencia)
        .filter(
            Conferencia.id == conferencia_id
        )
        .first()
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

    if conferencia.status == "FINALIZADA":
        raise HTTPException(
            status_code=400,
            detail="Conferência finalizada."
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
    # FLUSH
    #
    # Garante que os UPDATE/INSERT anteriores sejam enviados
    # para a sessão antes do recálculo das divergências.
    # ==========================================================

    db.flush()

    # ==========================================================
    # BUSCAR ITENS DA NF
    # ==========================================================

    itens_nf = (
        db.query(ItemNF)
        .filter(
            ItemNF.conferencia_id
            == conferencia_id
        )
        .all()
    )

    mapa_nf = {}

    for item_nf in itens_nf:

        codigo = normalizar_codigo(
            item_nf.codigo
        )

        try:
            quantidade_nf = int(
                float(item_nf.quantidade)
            )
        except (
            TypeError,
            ValueError
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Quantidade inválida na NF "
                    f"para o produto {codigo}."
                )
            )

        mapa_nf[codigo] = quantidade_nf

    # ==========================================================
    # BUSCAR DIVERGÊNCIAS ATUAIS
    # ==========================================================

    divergencias = (
        db.query(Divergencia)
        .filter(
            Divergencia.conferencia_id
            == conferencia_id
        )
        .all()
    )

    mapa_divergencias = {
        normalizar_codigo(divergencia.codigo): divergencia
        for divergencia in divergencias
    }

    # ==========================================================
    # RECALCULAR PRODUTOS DA NF
    # ==========================================================

    for codigo, quantidade_nf in mapa_nf.items():

        contagem = mapa_contagens.get(codigo)

        quantidade_contada = (
            contagem.quantidade
            if contagem
            else 0
        )

        diferenca = (
            quantidade_contada
            - quantidade_nf
        )

        divergencia = mapa_divergencias.get(
            codigo
        )

        # ------------------------------------------------------
        # SEM DIVERGÊNCIA
        # ------------------------------------------------------

        if diferenca == 0:

            if divergencia:

                db.delete(
                    divergencia
                )

            continue

        # ------------------------------------------------------
        # DETERMINAR TIPO
        # ------------------------------------------------------

        if diferenca > 0:
            tipo = "QUANTIDADE_MAIOR"
        else:
            tipo = "QUANTIDADE_MENOR"

        # ------------------------------------------------------
        # ATUALIZAR DIVERGÊNCIA
        # ------------------------------------------------------

        if divergencia:

            divergencia.xml = quantidade_nf
            divergencia.contado = quantidade_contada
            divergencia.diferenca = diferenca
            divergencia.tipo = tipo
            divergencia.versao = conferencia.versao

        # ------------------------------------------------------
        # CRIAR DIVERGÊNCIA
        # ------------------------------------------------------

        else:

            divergencia = Divergencia(
                conferencia_id=conferencia_id,
                codigo=codigo,
                xml=quantidade_nf,
                contado=quantidade_contada,
                diferenca=diferenca,
                tipo=tipo,
                origem="NOTA",
                versao=conferencia.versao
            )

            db.add(divergencia)

    # ==========================================================
    # PRODUTOS FORA DA NF
    # ==========================================================

    for codigo, contagem in mapa_contagens.items():

        if codigo in mapa_nf:
            continue

        quantidade_contada = (
            contagem.quantidade
        )

        divergencia = mapa_divergencias.get(
            codigo
        )

        # ------------------------------------------------------
        # PRODUTO EXTRA COM QUANTIDADE ZERO
        # ------------------------------------------------------

        if quantidade_contada == 0:

            if divergencia:

                db.delete(
                    divergencia
                )

            continue

        # ------------------------------------------------------
        # PRODUTO EXTRA
        # ------------------------------------------------------

        if divergencia:

            divergencia.xml = 0
            divergencia.contado = quantidade_contada
            divergencia.diferenca = quantidade_contada
            divergencia.tipo = "PRODUTO_A_MAIS"
            divergencia.origem = "FORA_NOTA"
            divergencia.versao = conferencia.versao

        else:

            divergencia = Divergencia(
                conferencia_id=conferencia_id,
                codigo=codigo,
                xml=0,
                contado=quantidade_contada,
                diferenca=quantidade_contada,
                tipo="PRODUTO_A_MAIS",
                origem="FORA_NOTA",
                versao=conferencia.versao
            )

            db.add(divergencia)

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