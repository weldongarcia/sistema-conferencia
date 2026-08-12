import 'package:coletor_mobile/models/login_response.dart';

class AuthService {
  static final AuthService _instance = AuthService._internal();

  factory AuthService() {
    return _instance;
  }

  AuthService._internal();

  LoginResponse? _login;

  void salvarLogin(LoginResponse login) {
    _login = login;
  }

  LoginResponse? get login => _login;

  String? get token => _login?.accessToken;

  bool get autenticado => _login != null;

  void logout() {
    _login = null;
  }
}
