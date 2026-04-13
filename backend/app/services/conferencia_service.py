from sqlalchemy.orm import Session
from app.models.item_nf import ItemNF
from app.models.contagem import Contagem
from collections import defaultdict

def comparar_conferencia(db: Session, conferencia_id: int):

    # 🔹 Buscar itens do XML
    itens_nf = db.query(ItemNF).filter_by(conferencia_id=conferencia_id).all()

    # 🔹 Buscar contagens
    contagens = db.query(Contagem).filter_by(conferencia_id=conferencia_id).all()

    # 🔹 Agrupar XML
    mapa_xml = defaultdict(float)

    for item in itens_nf:
        qtd = float(item.quantidade)
        mapa_xml[item.codigo] += qtd

    # 🔹 Agrupar contagem
    mapa_contagem = defaultdict(float)

    for c in contagens:
        mapa_contagem[c.codigo] += c.quantidade

    # 🔹 Comparar
    resultado = []

    codigos = set(mapa_xml.keys()) | set(mapa_contagem.keys())

    for codigo in codigos:
        xml_qtd = mapa_xml.get(codigo, 0)
        cont_qtd = mapa_contagem.get(codigo, 0)

        resultado.append({
            'codigo': codigo,
            'xml': xml_qtd,
            'contado': cont_qtd,
            'diferenca': cont_qtd - xml_qtd
        })

    tem_divergencia = any(item['diferenca'] != 0 for item in resultado)

    total_itens = len(resultado)
    divergentes = sum(1 for item in resultado if item["diferenca"] != 0)

# ✅ ÚNICO RETURN

    return {
    "status": "divergente" if divergentes > 0 else "ok",
    "total_itens": total_itens,
    "divergentes": divergentes,
    "itens": resultado
}

