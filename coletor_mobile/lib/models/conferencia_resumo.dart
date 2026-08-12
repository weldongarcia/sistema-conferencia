class ConferenciaResumo {
  final String status;
  final int totalItens;
  final int divergentes;
  final int versao;
  final List<ItemConferencia> itens;

  ConferenciaResumo({
    required this.status,
    required this.totalItens,
    required this.divergentes,
    required this.versao,
    required this.itens,
  });

  factory ConferenciaResumo.fromJson(Map<String, dynamic> json) {
    return ConferenciaResumo(
      status: json['status']?.toString() ?? '',
      totalItens: _toInt(json['total_itens']),
      divergentes: _toInt(json['divergentes']),
      versao: _toInt(json['versao']),
      itens: (json['itens'] as List<dynamic>? ?? [])
          .map((item) => ItemConferencia.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  static int _toInt(dynamic valor) {
    if (valor == null) return 0;

    if (valor is int) {
      return valor;
    }

    if (valor is double) {
      return valor.toInt();
    }

    if (valor is num) {
      return valor.toInt();
    }

    return int.tryParse(valor.toString()) ?? 0;
  }
}

class ItemConferencia {
  final String codigo;
  final int xml;
  final int contado;
  final int diferenca;

  ItemConferencia({
    required this.codigo,
    required this.xml,
    required this.contado,
    required this.diferenca,
  });

  factory ItemConferencia.fromJson(Map<String, dynamic> json) {
    return ItemConferencia(
      codigo: json['codigo']?.toString() ?? '',
      xml: _toInt(json['xml']),
      contado: _toInt(json['contado']),
      diferenca: _toInt(json['diferenca']),
    );
  }

  static int _toInt(dynamic valor) {
    if (valor == null) return 0;

    if (valor is int) {
      return valor;
    }

    if (valor is double) {
      return valor.toInt();
    }

    if (valor is num) {
      return valor.toInt();
    }

    return int.tryParse(valor.toString()) ?? 0;
  }
}
