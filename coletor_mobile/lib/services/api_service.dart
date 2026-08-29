import 'dart:convert';

import 'package:coletor_mobile/models/login_response.dart';
import 'package:coletor_mobile/models/conferencia_resumo.dart';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://192.168.1.223:8000';

  Future<LoginResponse?> login(String username, String senha) async {
    final response = await http.post(
      Uri.parse('$baseUrl/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'senha': senha}),
    );

    if (response.statusCode == 200) {
      return LoginResponse.fromJson(jsonDecode(response.body));
    }

    return null;
  }

  Future<ConferenciaResumo?> buscarConferencia(int conferenciaId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/conferencia/$conferenciaId'),
    );

    print('STATUS: ${response.statusCode}');
    print('BODY: ${response.body}');

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
      }),
    );

    print('CONTAGEM STATUS: ${response.statusCode}');
    print('CONTAGEM BODY: ${response.body}');

    return response.statusCode == 200;
  }
}
