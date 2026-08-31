import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:coletor_mobile/models/conferencia.dart';
import 'package:coletor_mobile/services/auth_service.dart';

class ConferenciaService {
  static const String baseUrl = 'http://192.168.3.41:8000';
  final authService = AuthService();

  Future<List<Conferencia>> listarConferencias() async {
    final token = authService.token;

    if (token == null) {
      throw Exception('Usuário não autenticado');
    }

    final response = await http.get(
      Uri.parse('$baseUrl/conferencias'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      final List<dynamic> dados = jsonDecode(response.body);

      return dados.map((item) => Conferencia.fromJson(item)).toList();
    }

    if (response.statusCode == 401) {
      throw Exception('Sessão expirada');
    }

    throw Exception('Erro ao carregar conferências: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> buscarConferencia(int conferenciaId) async {
    final token = authService.token;

    if (token == null) {
      throw Exception('Usuário não autenticado');
    }

    final response = await http.get(
      Uri.parse('$baseUrl/conferencia/$conferenciaId'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }

    if (response.statusCode == 401) {
      throw Exception('Sessão expirada');
    }

    throw Exception('Erro ao carregar conferência: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> fecharConferencia(int conferenciaId) async {
    final token = authService.token;

    if (token == null) {
      throw Exception('Usuário não autenticado');
    }

    final response = await http.post(
      Uri.parse('$baseUrl/conferencia/$conferenciaId/fechar'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }

    if (response.statusCode == 401) {
      throw Exception('Sessão expirada');
    }

    final body = jsonDecode(response.body);

    throw Exception(body['detail'] ?? 'Erro ao finalizar conferência');
  }
}
