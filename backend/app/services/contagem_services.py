from app.models.contagem import Contagem

def criar_contagem(db, dados):
    contagem = Contagem(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo,
        quantidade=dados.quantidade
    )

    db.add(contagem)
    db.commit()
    db.refresh(contagem)

    return contagem
