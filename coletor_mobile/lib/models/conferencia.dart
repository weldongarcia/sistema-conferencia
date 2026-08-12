class Conferencia {
  final int id;
  final int estabelecimentoId;
  final int usuarioId;
  final String status;
  final DateTime dataInicio;

  Conferencia({
    required this.id,
    required this.estabelecimentoId,
    required this.usuarioId,
    required this.status,
    required this.dataInicio,
  });

  factory Conferencia.fromJson(Map<String, dynamic> json) {
    return Conferencia(
      id: json['id'],
      estabelecimentoId: json['estabelecimento_id'],
      usuarioId: json['usuario_id'],
      status: json['status'],
      dataInicio: DateTime.parse(json['data_inicio']),
    );
  }
}
