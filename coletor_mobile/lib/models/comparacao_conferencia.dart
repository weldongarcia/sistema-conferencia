class ItemComparacao {
  final String codigo;
  final double xml;
  final double contado;
  final double diferenca;

  ItemComparacao({
    required this.codigo,
    required this.xml,
    required this.contado,
    required this.diferenca,
  });

  factory ItemComparacao.fromJson(Map<String, dynamic> json) {
    return ItemComparacao(
      codigo: json['codigo'].toString(),
      xml: (json['xml'] as num).toDouble(),
      contado: (json['contado'] as num).toDouble(),
      diferenca: (json['diferenca'] as num).toDouble(),
    );
  }
}

class ComparacaoConferencia {
  final String status;
  final int totalItens;
  final int divergentes;
  final List<ItemComparacao> itens;

  ComparacaoConferencia({
    required this.status,
    required this.totalItens,
    required this.divergentes,
    required this.itens,
  });

  factory ComparacaoConferencia.fromJson(Map<String, dynamic> json) {
    return ComparacaoConferencia(
      status: json['status'],
      totalItens: json['total_itens'],
      divergentes: json['divergentes'],
      itens: (json['itens'] as List)
          .map((item) => ItemComparacao.fromJson(item))
          .toList(),
    );
  }
}
