class ProdutoLocal {
  final String codigo;
  final String? descricao;
  final int? quantidadeCaixa;
  final bool ativo;
  final int versao;
  final String? atualizadoEm;

  ProdutoLocal({
    required this.codigo,
    required this.descricao,
    required this.quantidadeCaixa,
    required this.ativo,
    required this.versao,
    required this.atualizadoEm,
  });

  factory ProdutoLocal.fromMap(Map<String, dynamic> map) {
    return ProdutoLocal(
      codigo: map['codigo']?.toString() ?? '',
      descricao: map['descricao']?.toString(),
      quantidadeCaixa: map['quantidade_caixa'] as int?,
      ativo: (map['ativo'] ?? 1) == 1,
      versao: map['versao'] ?? 0,
      atualizadoEm: map['atualizado_em']?.toString(),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'codigo': codigo,
      'descricao': descricao,
      'quantidade_caixa': quantidadeCaixa,
      'ativo': ativo ? 1 : 0,
      'versao': versao,
      'atualizado_em': atualizadoEm,
    };
  }
}
