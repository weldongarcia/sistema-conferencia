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

  final apiService = ApiService();
  final authService = AuthService();

  @override
  void dispose() {
    usuarioController.dispose();
    senhaController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Sistema de Conferência')),

      body: Padding(
        padding: const EdgeInsets.all(20),

        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,

          children: [
            TextField(
              controller: usuarioController,
              decoration: const InputDecoration(
                labelText: 'Usuário',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 20),

            TextField(
              controller: senhaController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Senha',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 20),

            SizedBox(
              width: double.infinity,

              child: ElevatedButton(
                onPressed: () async {
                  final login = await apiService.login(
                    usuarioController.text,
                    senhaController.text,
                  );

                  if (login != null) {
                    authService.salvarLogin(login);

                    debugPrint('=== LOGIN REALIZADO ===');
                    debugPrint('Token: ${authService.token}');

                    if (!mounted) return;

                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const ConferenciaListPage(),
                      ),
                    );

                    return;
                  }

                  if (!mounted) return;

                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Usuário ou senha inválidos')),
                  );
                },

                child: const Text('Entrar'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
