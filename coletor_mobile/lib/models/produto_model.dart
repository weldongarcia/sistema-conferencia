class ProdutoModel {
  final int id;
  final String codigo;
  final String descricao;
  final int? quantidadeCaixa;
  final bool ativo;
  final int versao;
  final DateTime atualizadoEm;

  const ProdutoModel({required this.id, required this.codigo, required this.descricao,
    required this.quantidadeCaixa, required this.ativo, required this.versao,
    required this.atualizadoEm});

  factory ProdutoModel.fromJson(Map<String, dynamic> json) => ProdutoModel(
    id: _int(json['id']), codigo: json['codigo']?.toString() ?? '',
    descricao: json['descricao']?.toString() ?? '',
    quantidadeCaixa: _nullableInt(json['quantidade_caixa']),
    ativo: json['ativo'] == true || json['ativo'] == 1,
    versao: _int(json['versao']),
    atualizadoEm: DateTime.tryParse(json['atualizado_em']?.toString() ?? '') ??
        DateTime.fromMillisecondsSinceEpoch(0));

  static int _int(dynamic v) => v is num ? v.toInt() : int.tryParse(v?.toString() ?? '') ?? 0;
  static int? _nullableInt(dynamic v) => v == null ? null : (v is num ? v.toInt() : int.tryParse(v.toString()));
}

class CatalogoProdutosResponse {
  final int versao, offset, limite, total;
  final bool temMais;
  final List<ProdutoModel> produtos;

  const CatalogoProdutosResponse({required this.versao, required this.offset,
    required this.limite, required this.total, required this.temMais, required this.produtos});

  factory CatalogoProdutosResponse.fromJson(Map<String, dynamic> json) {
    final lista = json['produtos'];
    return CatalogoProdutosResponse(
      versao: ProdutoModel._int(json['versao']),
      offset: ProdutoModel._int(json['offset']),
      limite: ProdutoModel._int(json['limite']),
      total: ProdutoModel._int(json['total']),
      temMais: json['tem_mais'] == true,
      produtos: lista is List ? lista.whereType<Map>().map((e) =>
        ProdutoModel.fromJson(Map<String, dynamic>.from(e))).toList() : const []);
  }
}
