import xml.etree.ElementTree as ET
from decimal import Decimal

from fastapi import HTTPException

from app.models.nota_fiscal import NotaFiscal
from app.models.item_nf import ItemNF
from app.models.conferencia import Conferencia

from app.enums.conferencia_enums import StatusConferencia
from app.utils.codigo import normalizar_codigo


NS = {
    "nfe": "http://www.portalfiscal.inf.br/nfe"
}


def importar_xml(db, file, conferencia_id):

    # ==========================================================
    # BUSCAR CONFERÊNCIA
    # ==========================================================

    conferencia = (
        db.query(Conferencia)
        .filter_by(id=conferencia_id)
        .first()
    )

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada."
        )

    # ==========================================================
    # VALIDAR STATUS
    # ==========================================================

    status_permitidos = {
        StatusConferencia.RASCUNHO,
        StatusConferencia.REABERTA,
    }

    if conferencia.status not in status_permitidos:
        raise HTTPException(
            status_code=400,
            detail=(
                "Não é possível importar XML para uma "
                f"conferência com status {conferencia.status}."
            )
        )

    # ==========================================================
    # VERIFICAR SE JÁ EXISTE NOTA NA CONFERÊNCIA
    # ==========================================================

    nota_existente = (
        db.query(NotaFiscal)
        .filter_by(
            conferencia_id=conferencia_id
        )
        .first()
    )

    if nota_existente:
        raise HTTPException(
            status_code=400,
            detail=(
                "Já existe uma nota fiscal importada "
                "para esta conferência."
            )
        )

    # ==========================================================
    # LER XML
    # ==========================================================

    try:

        conteudo = file.file.read()

        if not conteudo:
            raise HTTPException(
                status_code=400,
                detail="O arquivo XML está vazio."
            )

        root = ET.fromstring(conteudo)

    except ET.ParseError:

        raise HTTPException(
            status_code=400,
            detail="Arquivo XML inválido."
        )

    # ==========================================================
    # LOCALIZAR INFNFE
    # ==========================================================

    inf_nfe = root.find(
        ".//nfe:infNFe",
        NS
    )

    if inf_nfe is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "XML inválido: estrutura da NF-e "
                "não encontrada."
            )
        )

    # ==========================================================
    # CHAVE DE ACESSO
    # ==========================================================

    chave = (
        inf_nfe.attrib
        .get("Id", "")
        .replace("NFe", "")
    )

    if not chave:
        raise HTTPException(
            status_code=400,
            detail=(
                "Não foi possível identificar a chave "
                "de acesso da NF-e."
            )
        )

    # ==========================================================
    # VERIFICAR DUPLICIDADE DA NF
    # ==========================================================

    nota_existente = (
        db.query(NotaFiscal)
        .filter_by(
            chave_acesso=chave
        )
        .first()
    )

    if nota_existente:
        raise HTTPException(
            status_code=400,
            detail=(
                "Esta nota fiscal já foi importada "
                "anteriormente."
            )
        )

    # ==========================================================
    # NÚMERO DA NF
    # ==========================================================

    ide = inf_nfe.find(
        "nfe:ide",
        NS
    )

    numero_nf = "NÃO INFORMADO"

    if ide is not None:

        numero_elemento = ide.find(
            "nfe:nNF",
            NS
        )

        if (
            numero_elemento is not None
            and numero_elemento.text
        ):
            numero_nf = (
                numero_elemento.text.strip()
            )

    # ==========================================================
    # LOCALIZAR ITENS
    # ==========================================================

    detalhes = root.findall(
        ".//nfe:det",
        NS
    )

    if not detalhes:
        raise HTTPException(
            status_code=400,
            detail=(
                "A NF-e não possui produtos "
                "para conferência."
            )
        )

    # ==========================================================
    # CONSOLIDAR PRODUTOS
    #
    # Um mesmo código pode aparecer em várias linhas
    # do XML. A conferência trabalhará com uma única
    # linha por código.
    # ==========================================================

    produtos = {}

    for det in detalhes:

        prod = det.find(
            "nfe:prod",
            NS
        )

        if prod is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Foi encontrado um item da NF-e "
                    "sem informações do produto."
                )
            )

        codigo_elemento = prod.find(
            "nfe:cProd",
            NS
        )

        descricao_elemento = prod.find(
            "nfe:xProd",
            NS
        )

        quantidade_elemento = prod.find(
            "nfe:qCom",
            NS
        )

        if (
            codigo_elemento is None
            or not codigo_elemento.text
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Foi encontrado um produto "
                    "sem código."
                )
            )

        if (
            descricao_elemento is None
            or not descricao_elemento.text
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Foi encontrado um produto "
                    "sem descrição."
                )
            )

        if (
            quantidade_elemento is None
            or not quantidade_elemento.text
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Foi encontrado um produto "
                    "sem quantidade."
                )
            )

        codigo = normalizar_codigo(
            codigo_elemento.text
        )

        descricao = (
            descricao_elemento.text.strip()
        )

        quantidade_texto = (
            quantidade_elemento.text.strip()
        )

        # ------------------------------------------------------
        # Converter quantidade
        # ------------------------------------------------------

        try:

            quantidade = Decimal(
                quantidade_texto
            )

        except Exception:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Quantidade inválida para o "
                    f"produto {codigo}."
                )
            )

        # ------------------------------------------------------
        # Primeiro registro do código
        # ------------------------------------------------------

        if codigo not in produtos:

            produtos[codigo] = {
                "descricao": descricao,
                "quantidade": quantidade,
            }

        # ------------------------------------------------------
        # Código já encontrado no XML
        # ------------------------------------------------------

        else:

            produtos[codigo]["quantidade"] += (
                quantidade
            )

    # ==========================================================
    # CRIAR NOTA
    # ==========================================================

    nota = NotaFiscal(
        chave_acesso=chave,
        numero=numero_nf,
        conferencia_id=conferencia_id,
    )

    db.add(nota)

    # ==========================================================
    # SALVAR ITENS CONSOLIDADOS
    # ==========================================================

    db.flush()

    itens_processados = []

    for codigo, produto in produtos.items():

        quantidade = produto["quantidade"]

        item = ItemNF(
            nota_id=nota.id,
            codigo=codigo,
            descricao=produto["descricao"],
            quantidade=str(quantidade),
            conferencia_id=conferencia_id,
        )

        db.add(item)

        itens_processados.append(item)

    # ==========================================================
    # COMMIT ÚNICO
    # ==========================================================

    try:

        db.commit()

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Não foi possível salvar "
                "a nota fiscal."
            )
        )

    # ==========================================================
    # RETORNO
    # ==========================================================

    return {
        "msg": "Nota importada com sucesso",
        "nota_id": nota.id,
        "conferencia_id": conferencia_id,
        "numero_nf": numero_nf,
        "chave_acesso": chave,
        "total_itens": len(itens_processados),
    }