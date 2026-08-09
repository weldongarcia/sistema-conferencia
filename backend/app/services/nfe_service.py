import xml.etree.ElementTree as ET
from app.models.nota_fiscal import NotaFiscal
from app.models.item_nf import ItemNF
from app.models.conferencia import Conferencia
from fastapi import HTTPException
from app.models.nota_fiscal import NotaFiscal
from app.enums.conferencia_enums import StatusConferencia
from app.utils.codigo import normalizar_codigo


def importar_xml(db, file, conferencia_id):
    conferencia = db.query(Conferencia).filter_by(id=conferencia_id).first()
    if not conferencia:
        return {'erro': 'Conferência não encontrada'}
    
    if conferencia.status == StatusConferencia.FINALIZADA:
        return {'erro': 'Conferência finalizada. Não pode importar XML.'}
    
    nota_existente = db.query(NotaFiscal).filter_by(
    conferencia_id=conferencia_id
).first()

    if nota_existente:
        raise HTTPException(
        status_code=400,
        detail="XML já importado para esta conferência."
    )
    
    conteudo = file.file.read()
    root = ET.fromstring(conteudo)

    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

    # 🔑 pegar chave de acesso
    chave = root.find(".//nfe:infNFe", ns).attrib.get("Id", "").replace("NFe", "")

    # 🔍 validar duplicidade
    nota_existente = db.query(NotaFiscal).filter_by(
        chave_acesso=chave,
        conferencia_id=conferencia_id
    ).first()
    if nota_existente:
        return {"erro": "Nota já importada"}

    # 🧾 criar nota
    nota = NotaFiscal(
        chave_acesso=chave,
        numero="1",  # depois vamos melhorar isso
        conferencia_id=conferencia_id
    )

    db.add(nota)
    db.commit()
    db.refresh(nota)

    itens_salvos = []

    # 📦 itens
    for det in root.findall(".//nfe:det", ns):
        prod = det.find("nfe:prod", ns)

        codigo_xml = prod.find("nfe:cProd", ns).text

        codigo = normalizar_codigo(codigo_xml)

        item = ItemNF(
            nota_id=nota.id,
            codigo=codigo,
            descricao=prod.find("nfe:xProd", ns).text,
            quantidade=prod.find("nfe:qCom", ns).text,
            conferencia_id=conferencia_id,
        )

        db.add(item)
        itens_salvos.append(item)

    db.commit()

    return {
        "msg": "Nota importada com sucesso",
        "nota_id": nota.id,
        "total_itens": len(itens_salvos)
    }

