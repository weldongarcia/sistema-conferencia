import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'package:coletor_mobile/models/login_response.dart';
import 'package:coletor_mobile/models/conferencia_resumo.dart';
import '../models/produto_model.dart';

import 'dart:convert';
import '../models/produto_model.dart';

class ApiService {
  static const String baseUrl = 'http://192.168.1.205:8000';

  Future<LoginResponse?> login(String username, String senha) async {
    final url = Uri.parse('$baseUrl/login');
    final response = await http
        .post(
          url,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'username': username, 'senha': senha}),
        )
        .timeout(const Duration(seconds: 10));

    debugPrint('STATUS LOGIN: ${response.statusCode}');
    debugPrint('BODY LOGIN: ${response.body}');

    if (response.statusCode == 200) {
      return LoginResponse.fromJson(jsonDecode(response.body));
    }
    return null;
  }

  Future<Map<String, dynamic>?> buscarUsuarioAtual({
    required String token,
  }) async {
    final url = Uri.parse('$baseUrl/usuario/me');
    final response = await http
        .get(url, headers: {'Authorization': 'Bearer $token'})
        .timeout(const Duration(seconds: 10));

    debugPrint('STATUS USUÁRIO: ${response.statusCode}');
    debugPrint('BODY USUÁRIO: ${response.body}');

    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(jsonDecode(response.body));
    }
    return null;
  }

  Future<ConferenciaResumo?> buscarConferencia({
    required int conferenciaId,
    required String token,
  }) async {
    final url = Uri.parse('$baseUrl/conferencia/$conferenciaId');
    final response = await http
        .get(url, headers: {'Authorization': 'Bearer $token'})
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return ConferenciaResumo.fromJson(jsonDecode(response.body));
    }
    return null;
  }

  Future<bool> registrarContagem({
    required String token,
    required int conferenciaId,
    required String codigo,
    required int quantidade,
  }) async {
    final url = Uri.parse('$baseUrl/contagens/');
    final response = await http
        .post(
          url,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
          body: jsonEncode({
            'conferencia_id': conferenciaId,
            'codigo': codigo,
            'quantidade': quantidade,
          }),
        )
        .timeout(const Duration(seconds: 10));

    return response.statusCode == 200;
  }

  Future<CatalogoProdutosResponse> buscarProdutosParaSincronizar({
    required String token,
    required int versaoLocal,
    int offset = 0,
    int limite = 500,
  }) async {
    final uri = Uri.parse('$baseUrl/produtos/sincronizar/$versaoLocal').replace(
      queryParameters: {
        'offset': offset.toString(),
        'limite': limite.toString(),
      },
    );

    final response = await http
        .get(
          uri,
          headers: {
            'Authorization': 'Bearer $token',
            'Accept': 'application/json',
          },
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode == 200) {
      return CatalogoProdutosResponse.fromJson(jsonDecode(response.body));
    }

    if (response.statusCode == 401) {
      throw Exception('Sessão expirada.');
    }

    if (response.statusCode == 403) {
      throw Exception('Usuário sem permissão para sincronizar o catálogo.');
    }

    try {
      final body = jsonDecode(response.body);
      throw Exception(
        body['detail']?.toString() ??
            'Erro ao sincronizar catálogo de produtos.',
      );
    } catch (e) {
      if (e is Exception) rethrow;

      throw Exception(
        'Erro ${response.statusCode} ao sincronizar catálogo de produtos.',
      );
    }
  }
}
