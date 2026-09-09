import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:coletor_mobile/services/auth_service.dart';

class ProdutoNaoEncontradoException implements Exception {
  final String codigo;
  final String mensagem;

  ProdutoNaoEncontradoException({required this.codigo, required this.mensagem});

  @override
  String toString() => mensagem;
}

class ContagemService {
  static const String baseUrl = 'http://192.168.1.205:8000';

  final AuthService authService = AuthService();

  Future<Map<String, dynamic>> registrarContagem({
    required int conferenciaId,
    required String codigo,
    required int quantidade,
    bool incluirNaConferencia = false,
  }) async {
    final token = authService.token;

    if (token == null || token.isEmpty) {
      throw Exception('Usuário não autenticado.');
    }

    final response = await http.post(
      Uri.parse('$baseUrl/contagens/'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'conferencia_id': conferenciaId,
        'codigo': codigo,
        'quantidade': quantidade,
        'incluir_na_conferencia': incluirNaConferencia,
      }),
    );

    dynamic body;

    try {
      body = jsonDecode(response.body);
    } catch (_) {
      body = null;
    }

    if (response.statusCode == 200) {
      if (body is Map<String, dynamic>) {
        return body;
      }

      return {};
    }

    // ======================================================
    // PRODUTO NÃO ENCONTRADO NA NF
    // ======================================================

    if (body is Map && body['detail'] is Map) {
      final detail = Map<String, dynamic>.from(body['detail']);

      final tipo = detail['tipo']?.toString();

      if (tipo == 'PRODUTO_NAO_ENCONTRADO_NA_NF') {
        throw ProdutoNaoEncontradoException(
          codigo: detail['codigo']?.toString() ?? codigo,
          mensagem:
              detail['mensagem']?.toString() ??
              'Produto não encontrado na nota.',
        );
      }

      throw Exception(
        detail['mensagem']?.toString() ?? 'Erro ao registrar contagem.',
      );
    }

    if (body is Map) {
      throw Exception(
        body['detail']?.toString() ?? 'Erro ao registrar contagem.',
      );
    }

    throw Exception(
      'Erro ao registrar contagem. '
      'Status: ${response.statusCode}',
    );
  }
}
