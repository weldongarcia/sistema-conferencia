class LoginResponse {
  final String accessToken;
  final String tokenType;
  final int usuarioId;

  LoginResponse({
    required this.accessToken,
    required this.tokenType,
    required this.usuarioId,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    return LoginResponse(
      accessToken: json['access_token'],
      tokenType: json['token_type'],
      usuarioId: json['usuario_id'],
    );
  }
}
