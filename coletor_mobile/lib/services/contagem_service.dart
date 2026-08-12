import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:coletor_mobile/services/auth_service.dart';

class ContagemService {
  static const String baseUrl = 'http://127.0.0.1:8000';

  final authService = AuthService();

  Future<Map<String, dynamic>> registrarContagem({
    required int conferenciaId,
    required String codigo,
    required int quantidade,
  }) async {
    final token = authService.token;

    if (token == null) {
      throw Exception('Usuário não autenticado');
    }

    final response = await http.post(
      Uri.parse('$baseUrl/contagens/'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'conferencia_id': conferenciaId,
        'codigo': codigo,
        'quantidade': quantidade,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }

    if (response.statusCode == 401) {
      throw Exception('Sessão expirada');
    }

    final body = jsonDecode(response.body);

    throw Exception(body['detail'] ?? 'Erro ao registrar contagem');
  }
}
