from fastapi import HTTPException


def normalizar_codigo(codigo: str) -> str:
    codigo = codigo.strip()

    if not codigo.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Código inválido"
        )

    # Código já reduzido
    if len(codigo) == 5:
        return codigo

    # EAN-13 lido pelo coletor
    if len(codigo) == 13:
        return codigo[7:12]

    raise HTTPException(
        status_code=400,
        detail="O código deve possuir 5 ou 13 dígitos"
    )