class ConferenciaResumo {
  final String status;
  final String statusConferencia;
  final int totalItens;
  final int divergentes;
  final int versao;
  final List<ItemConferencia> itens;

  ConferenciaResumo({
    required this.status,
    required this.statusConferencia,
    required this.totalItens,
    required this.divergentes,
    required this.versao,
    required this.itens,
  });

  factory ConferenciaResumo.fromJson(Map<String, dynamic> json) {
    return ConferenciaResumo(
      status: json['status']?.toString() ?? '',
      statusConferencia: json['status_conferencia']?.toString() ?? '',
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

    if (valor is num) {
      return valor.toInt();
    }

    return int.tryParse(valor.toString()) ?? 0;
  }
}

class ItemConferencia {
  final String codigo;
  final String? descricao;
  final int xml;
  final int contado;
  final int diferenca;

  final bool divergente;
  final int? divergenciaId;
  final String? tipoDivergencia;

  final bool justificado;
  final String? justificativaTipo;
  final String? justificativaDescricao;

  ItemConferencia({
    required this.codigo,
    required this.descricao,
    required this.xml,
    required this.contado,
    required this.diferenca,
    required this.divergente,
    required this.divergenciaId,
    required this.tipoDivergencia,
    required this.justificado,
    required this.justificativaTipo,
    required this.justificativaDescricao,
  });

  factory ItemConferencia.fromJson(Map<String, dynamic> json) {
    return ItemConferencia(
      codigo: json['codigo']?.toString() ?? '',
      descricao: json['descricao']?.toString(),
      xml: _toInt(json['xml']),
      contado: _toInt(json['contado']),
      diferenca: _toInt(json['diferenca']),
      divergente: json['divergente'] == true,
      divergenciaId: _toNullableInt(json['divergencia_id']),
      tipoDivergencia: json['tipo_divergencia']?.toString(),
      justificado: json['justificado'] == true,
      justificativaTipo: json['justificativa_tipo']?.toString(),
      justificativaDescricao: json['justificativa_descricao']?.toString(),
    );
  }

  static int _toInt(dynamic valor) {
    if (valor == null) return 0;

    if (valor is num) {
      return valor.toInt();
    }

    return int.tryParse(valor.toString()) ?? 0;
  }

  static int? _toNullableInt(dynamic valor) {
    if (valor == null) return null;

    if (valor is num) {
      return valor.toInt();
    }

    return int.tryParse(valor.toString());
  }
}
