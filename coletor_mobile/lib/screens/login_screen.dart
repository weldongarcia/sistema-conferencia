import 'package:flutter/material.dart';

import 'package:coletor_mobile/services/api_service.dart';
import 'package:coletor_mobile/services/auth_service.dart';
import 'package:coletor_mobile/pages/conferencia_list_page.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final usuarioController = TextEditingController();
  final senhaController = TextEditingController();

  final usuarioFocusNode = FocusNode();
  final senhaFocusNode = FocusNode();

  final apiService = ApiService();
  final authService = AuthService();

  bool entrando = false;

  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      FocusScope.of(context).requestFocus(usuarioFocusNode);
    });
  }

  @override
  void dispose() {
    usuarioController.dispose();
    senhaController.dispose();

    usuarioFocusNode.dispose();
    senhaFocusNode.dispose();

    super.dispose();
  }

  Future<void> realizarLogin() async {
    if (entrando) return;

    final usuario = usuarioController.text.trim();
    final senha = senhaController.text;

    if (usuario.isEmpty) {
      _mostrarMensagem('Informe o usuário.', erro: true);

      FocusScope.of(context).requestFocus(usuarioFocusNode);

      return;
    }

    if (senha.isEmpty) {
      _mostrarMensagem('Informe a senha.', erro: true);

      FocusScope.of(context).requestFocus(senhaFocusNode);

      return;
    }

    setState(() {
      entrando = true;
    });

    try {
      final login = await apiService.login(usuario, senha);

      if (!mounted) return;

      if (login != null) {
        authService.salvarLogin(login);

        debugPrint('=== LOGIN REALIZADO ===');
        debugPrint('Token: ${authService.token}');

        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => const ConferenciaListPage()),
        );

        return;
      }

      _mostrarMensagem('Usuário ou senha inválidos.', erro: true);

      FocusScope.of(context).requestFocus(senhaFocusNode);
    } catch (e) {
      if (!mounted) return;

      final mensagem = e.toString().replaceFirst('Exception: ', '');

      _mostrarMensagem(mensagem, erro: true);
    } finally {
      if (mounted) {
        setState(() {
          entrando = false;
        });
      }
    }
  }

  void _mostrarMensagem(String mensagem, {bool erro = false}) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(mensagem),
          backgroundColor: erro ? Colors.red : null,
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Sistema de Conferência')),

      resizeToAvoidBottomInset: true,

      body: SafeArea(
        child: SingleChildScrollView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,

          padding: const EdgeInsets.all(20),

          child: Column(
            children: [
              const SizedBox(height: 80),

              const Icon(Icons.inventory_2_outlined, size: 70),

              const SizedBox(height: 30),

              TextField(
                controller: usuarioController,
                focusNode: usuarioFocusNode,
                autofocus: true,
                keyboardType: TextInputType.text,
                textInputAction: TextInputAction.next,
                enabled: !entrando,

                decoration: const InputDecoration(
                  labelText: 'Usuário',
                  hintText: 'Digite seu usuário',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.person),
                ),

                onSubmitted: (_) {
                  FocusScope.of(context).requestFocus(senhaFocusNode);
                },
              ),

              const SizedBox(height: 20),

              TextField(
                controller: senhaController,
                focusNode: senhaFocusNode,
                obscureText: true,
                keyboardType: TextInputType.visiblePassword,
                textInputAction: TextInputAction.done,
                enabled: !entrando,

                decoration: const InputDecoration(
                  labelText: 'Senha',
                  hintText: 'Digite sua senha',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.lock),
                ),

                onSubmitted: (_) {
                  realizarLogin();
                },
              ),

              const SizedBox(height: 20),

              SizedBox(
                width: double.infinity,
                height: 52,

                child: ElevatedButton(
                  onPressed: entrando ? null : realizarLogin,

                  child: entrando
                      ? const SizedBox(
                          width: 22,
                          height: 22,

                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text(
                          'ENTRAR',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                ),
              ),

              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }
}
