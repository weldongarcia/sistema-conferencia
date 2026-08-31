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
    # ISOLAMENTO POR ESTABELECIMENTO
    # ======================================================

    if usuario.perfil == "CONFERENTE":

        if usuario.estabelecimento_id is None:

            raise HTTPException(
                403,
                "Usuário não está vinculado a um estabelecimento."
            )

        if (
            conferencia.estabelecimento_id
            != usuario.estabelecimento_id
        ):

            raise HTTPException(
                403,
                "Você não possui acesso a esta conferência."
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

            pass

    # ======================================================
    # ATUALIZAR CONTAGEM EXISTENTE
    #
    # IMPORTANTE:
    # A nova quantidade é SOMADA à quantidade existente.
    #
    # Exemplo:
    #
    # existente = 3
    # nova      = 1
    #
    # resultado = 4
    # ======================================================

    if contagem_existente:

        quantidade_anterior = (
            contagem_existente.quantidade
        )

        quantidade_nova = (
            quantidade_anterior
            + dados.quantidade
        )

        # --------------------------------------------------
        # HISTÓRICO DA ALTERAÇÃO
        # --------------------------------------------------

        historico = ContagemHistorico(

            conferencia_id=dados.conferencia_id,

            codigo=codigo,

            valor_anterior=(
                quantidade_anterior
            ),

            valor_novo=(
                quantidade_nova
            ),

            versao=conferencia.versao,

            usuario_id=usuario.id,
        )

        db.add(historico)

        # --------------------------------------------------
        # ATUALIZAR
        # --------------------------------------------------

        contagem_existente.quantidade = (
            quantidade_nova
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