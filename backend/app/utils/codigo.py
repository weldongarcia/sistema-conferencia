def normalizar_codigo(codigo: str) -> str:
    codigo = str(codigo).strip()

    if len(codigo) <= 5:
        return codigo

    return codigo[-5:]