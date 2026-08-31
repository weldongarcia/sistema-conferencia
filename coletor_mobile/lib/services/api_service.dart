import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'package:coletor_mobile/models/login_response.dart';
import 'package:coletor_mobile/models/conferencia_resumo.dart';

class ApiService {
  static const String baseUrl = 'http://192.168.3.41:8000';

  // ==========================================================
  // LOGIN
  // ==========================================================

  Future<LoginResponse?> login(String username, String senha) async {
    final url = Uri.parse('$baseUrl/login');

    debugPrint('========================================');
    debugPrint('TENTANDO LOGIN');
    debugPrint('URL: $url');
    debugPrint('USUARIO: $username');

    try {
      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'username': username, 'senha': senha}),
          )
          .timeout(const Duration(seconds: 10));

      debugPrint('STATUS LOGIN: ${response.statusCode}');

      debugPrint('BODY LOGIN: ${response.body}');

      debugPrint('========================================');

      if (response.statusCode == 200) {
        return LoginResponse.fromJson(jsonDecode(response.body));
      }

      return null;
    } catch (e, stackTrace) {
      debugPrint('ERRO LOGIN: $e');
      debugPrint('STACK TRACE: $stackTrace');
      debugPrint('========================================');

      rethrow;
    }
  }

  // ==========================================================
  // BUSCAR CONFERÊNCIA
  // ==========================================================

  Future<ConferenciaResumo?> buscarConferencia({
    required int conferenciaId,
    required String token,
  }) async {
    final url = Uri.parse('$baseUrl/conferencia/$conferenciaId');

    debugPrint('========================================');
    debugPrint('BUSCANDO CONFERÊNCIA');
    debugPrint('URL: $url');

    try {
      final response = await http
          .get(url, headers: {'Authorization': 'Bearer $token'})
          .timeout(const Duration(seconds: 10));

      debugPrint('STATUS CONFERÊNCIA: ${response.statusCode}');

      debugPrint('BODY CONFERÊNCIA: ${response.body}');

      debugPrint('========================================');

      if (response.statusCode == 200) {
        return ConferenciaResumo.fromJson(jsonDecode(response.body));
      }

      return null;
    } catch (e, stackTrace) {
      debugPrint('ERRO CONFERÊNCIA: $e');
      debugPrint('STACK TRACE: $stackTrace');

      rethrow;
    }
  }

  // ==========================================================
  // REGISTRAR CONTAGEM
  // ==========================================================

  Future<bool> registrarContagem({
    required String token,
    required int conferenciaId,
    required String codigo,
    required int quantidade,
  }) async {
    final url = Uri.parse('$baseUrl/contagens/');

    debugPrint('========================================');
    debugPrint('REGISTRANDO CONTAGEM');
    debugPrint('URL: $url');
    debugPrint('CONFERÊNCIA: $conferenciaId');
    debugPrint('CÓDIGO: $codigo');
    debugPrint('QUANTIDADE: $quantidade');

    try {
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

      debugPrint('CONTAGEM STATUS: ${response.statusCode}');

      debugPrint('CONTAGEM BODY: ${response.body}');

      debugPrint('========================================');

      return response.statusCode == 200;
    } catch (e, stackTrace) {
      debugPrint('ERRO CONTAGEM: $e');
      debugPrint('STACK TRACE: $stackTrace');

      rethrow;
    }
  }
}
