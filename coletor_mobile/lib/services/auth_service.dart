import '../models/login_response.dart';

class AuthService {
  static final AuthService _instance = AuthService._internal();

  factory AuthService() => _instance;
  AuthService._internal();

  LoginResponse? _login;
  int? _usuarioId;
  String? _username;
  String? _perfil;
  int? _estabelecimentoId;

  void salvarLogin(LoginResponse login) => _login = login;

  void salvarUsuario({
    required int id,
    required String username,
    required String perfil,
    int? estabelecimentoId,
  }) {
    _usuarioId = id;
    _username = username;
    _perfil = perfil;
    _estabelecimentoId = estabelecimentoId;
  }

  LoginResponse? get login => _login;
  String? get token => _login?.accessToken;
  bool get autenticado => _login != null;
  int? get usuarioId => _usuarioId;
  String? get username => _username;
  String? get perfil => _perfil;
  int? get estabelecimentoId => _estabelecimentoId;

  void logout() {
    _login = null;
    _usuarioId = null;
    _username = null;
    _perfil = null;
    _estabelecimentoId = null;
  }
}
