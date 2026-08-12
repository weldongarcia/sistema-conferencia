import 'package:flutter/material.dart';
import 'package:coletor_mobile/models/conferencia.dart';
import 'package:coletor_mobile/services/conferencia_service.dart';
import 'package:coletor_mobile/pages/conferencia_resumo_page.dart';

class ConferenciaListPage extends StatefulWidget {
  const ConferenciaListPage({super.key});

  @override
  State<ConferenciaListPage> createState() => _ConferenciaListPageState();
}

class _ConferenciaListPageState extends State<ConferenciaListPage> {
  final conferenciaService = ConferenciaService();

  late Future<List<Conferencia>> futureConferencias;

  @override
  void initState() {
    super.initState();

    futureConferencias = conferenciaService.listarConferencias();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Conferências')),

      body: FutureBuilder<List<Conferencia>>(
        future: futureConferencias,

        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Text(
                'Erro ao carregar conferências:\n${snapshot.error}',
                textAlign: TextAlign.center,
              ),
            );
          }

          final conferencias = snapshot.data ?? [];

          if (conferencias.isEmpty) {
            return const Center(child: Text('Nenhuma conferência encontrada.'));
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: conferencias.length,

            itemBuilder: (context, index) {
              final conferencia = conferencias[index];

              return Card(
                margin: const EdgeInsets.only(bottom: 12),

                child: ListTile(
                  title: Text('Conferência #${conferencia.id}'),

                  subtitle: Text(
                    'Estabelecimento: ${conferencia.estabelecimentoId}\n'
                    'Status: ${conferencia.status}\n'
                    'Início: ${conferencia.dataInicio}',
                  ),

                  trailing: const Icon(Icons.arrow_forward_ios),

                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => ConferenciaResumoPage(
                          conferenciaId: conferencia.id,
                        ),
                      ),
                    );
                  },
                ),
              );
            },
          );
        },
      ),
    );
  }
}
