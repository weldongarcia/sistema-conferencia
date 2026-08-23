from fastapi import HTTPException

from app.models.contagem import Contagem
from app.models.conferencia import Conferencia
from app.models.item_nf import ItemNF
from app.models.contagem_historico import ContagemHistorico

from app.utils.codigo import normalizar_codigo


# ==========================================================
# REDUZIR CÓDIGO DE BARRAS
# ==========================================================

def reduzir_codigo_barras(
    codigo_barras: str
) -> str:

    codigo_barras = codigo_barras.strip()

    if not codigo_barras.isdigit():

        raise HTTPException(
            400,
            "Código de barras inválido"
        )

    if len(codigo_barras) != 13:

        raise HTTPException(
            400,
            "O código de barras deve possuir 13 dígitos"
        )

    return codigo_barras[7:12]


# ==========================================================
# CRIAR / ATUALIZAR CONTAGEM
# ==========================================================

def criar_contagem(
    db,
    dados,
    usuario
):

    codigo = normalizar_codigo(
        dados.codigo
    )

    # ======================================================
    # BUSCAR CONFERÊNCIA
    # ======================================================

    conferencia = db.query(
        Conferencia
    ).filter_by(
        id=dados.conferencia_id
    ).first()

    if not conferencia:

        raise HTTPException(
            404,
            "Conferência não encontrada"
        )

    # ======================================================
    # VERIFICAR STATUS
    # ======================================================

    if conferencia.status == "FINALIZADA":

        raise HTTPException(
            400,
            "Conferência finalizada"
        )

    # ======================================================
    # VERIFICAR SE O PRODUTO EXISTE NA NF
    # ======================================================

    item_existe = db.query(
        ItemNF
    ).filter_by(
        conferencia_id=dados.conferencia_id,
        codigo=codigo
    ).first()

    # ======================================================
    # VERIFICAR SE JÁ EXISTE CONTAGEM
    #
    # Isso é importante para produtos que já foram
    # incluídos anteriormente na conferência.
    # ======================================================

    contagem_existente = db.query(
        Contagem
    ).filter_by(
        conferencia_id=dados.conferencia_id,
        codigo=codigo
    ).first()

    # ======================================================
    # PRODUTO NÃO ESTÁ NA NF
    # ======================================================

    if not item_existe:

        # --------------------------------------------------
        # PRODUTO JÁ FOI INCLUÍDO ANTERIORMENTE
        # --------------------------------------------------

        if contagem_existente:

            # O produto já foi autorizado anteriormente.
            # Portanto, podemos atualizar sua quantidade
            # normalmente.

            pass

        # --------------------------------------------------
        # PRODUTO NOVO E SEM AUTORIZAÇÃO
        # --------------------------------------------------

        elif not dados.incluir_na_conferencia:

            raise HTTPException(
                status_code=400,
                detail={
                    "codigo": codigo,
                    "tipo": "PRODUTO_NAO_ENCONTRADO_NA_NF",
                    "mensagem": (
                        "Produto não encontrado na nota. "
                        "É necessário confirmar a inclusão "
                        "na conferência."
                    )
                }
            )

        # --------------------------------------------------
        # PRODUTO NOVO COM AUTORIZAÇÃO
        # --------------------------------------------------

        else:

            # A criação da contagem ocorrerá abaixo.
            #
            # A existência da Contagem passa a representar
            # que o produto foi incluído na conferência.

            pass

    # ======================================================
    # ATUALIZAR CONTAGEM EXISTENTE
    # ======================================================

    if contagem_existente:

        if (
            contagem_existente.quantidade
            == dados.quantidade
        ):

            return contagem_existente

        # --------------------------------------------------
        # HISTÓRICO DA ALTERAÇÃO
        # --------------------------------------------------

        historico = ContagemHistorico(

            conferencia_id=dados.conferencia_id,

            codigo=codigo,

            valor_anterior=(
                contagem_existente.quantidade
            ),

            valor_novo=dados.quantidade,

            versao=conferencia.versao,

            usuario_id=usuario.id,
        )

        db.add(historico)

        # --------------------------------------------------
        # ATUALIZAR
        # --------------------------------------------------

        contagem_existente.quantidade = (
            dados.quantidade
        )

        db.commit()

        db.refresh(
            contagem_existente
        )

        return contagem_existente

    # ======================================================
    # CRIAR NOVA CONTAGEM
    # ======================================================

    contagem = Contagem(

        conferencia_id=dados.conferencia_id,

        codigo=codigo,

        quantidade=dados.quantidade

    )

    db.add(contagem)

    # ======================================================
    # HISTÓRICO DA PRIMEIRA CONTAGEM
    # ======================================================

    historico = ContagemHistorico(

        conferencia_id=dados.conferencia_id,

        codigo=codigo,

        valor_anterior=0,

        valor_novo=dados.quantidade,

        versao=conferencia.versao,

        usuario_id=usuario.id

    )

    db.add(historico)

    # ======================================================
    # COMMIT
    # ======================================================

    db.commit()

    db.refresh(
        contagem
    )

    return contagem