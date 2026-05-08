def criar_divergencia_fora_nota(item_id, usuario_id):

    return Divergencia(
        conferencia_item_id=item_id,
        tipo="PRODUTO_A_MAIS",
        justificativa_tipo="OUTROS",
        origem="FORA_NOTA",
        usuario_id=usuario_id
    )