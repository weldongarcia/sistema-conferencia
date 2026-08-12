import 'package:flutter/material.dart';

import 'package:coletor_mobile/services/conferencia_service.dart';
import 'package:coletor_mobile/pages/conferencia_page.dart';

class ConferenciaResumoPage extends StatefulWidget {
  final int conferenciaId;

  const ConferenciaResumoPage({super.key, required this.conferenciaId});

  @override
  State<ConferenciaResumoPage> createState() => _ConferenciaResumoPageState();
}

class _ConferenciaResumoPageState extends State<ConferenciaResumoPage> {
  final conferenciaService = ConferenciaService();

  late Future<Map<String, dynamic>> futureConferencia;

  @override
  void initState() {
    super.initState();

    futureConferencia = conferenciaService.buscarConferencia(
      widget.conferenciaId,
    );
  }

  Future<void> recarregar() async {
    setState(() {
      futureConferencia = conferenciaService.buscarConferencia(
        widget.conferenciaId,
      );
    });

    await futureConferencia;
  }

  void iniciarConferencia() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) =>
            ConferenciaPage(conferenciaId: widget.conferenciaId),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Conferência')),
      body: FutureBuilder<Map<String, dynamic>>(
        future: futureConferencia,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, size: 60),
                    const SizedBox(height: 16),
                    Text(
                      'Erro ao carregar conferência:\n${snapshot.error}',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton(
                      onPressed: recarregar,
                      child: const Text('Tentar novamente'),
                    ),
                  ],
                ),
              ),
            );
          }

          final dados = snapshot.data;

          if (dados == null) {
            return const Center(child: Text('Nenhum dado encontrado.'));
          }

          final total = dados['total_itens'] ?? 0;
          final divergentes = dados['divergentes'] ?? 0;
          final status = dados['status']?.toString() ?? '';

          final itens = dados['itens'] as List<dynamic>? ?? [];

          final conferidos = itens.where((item) {
            final contado = item['contado'];

            return contado != null && contado > 0;
          }).length;

          final percentual = total > 0 ? conferidos / total : 0.0;

          return RefreshIndicator(
            onRefresh: recarregar,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _CardStatus(
                  status: status,
                  conferenciaId: widget.conferenciaId,
                ),

                const SizedBox(height: 16),

                Row(
                  children: [
                    Expanded(
                      child: _Indicador(
                        titulo: 'Itens',
                        valor: '$total',
                        icone: Icons.inventory_2_outlined,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _Indicador(
                        titulo: 'Conferidos',
                        valor: '$conferidos',
                        icone: Icons.check_circle_outline,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 12),

                Row(
                  children: [
                    Expanded(
                      child: _Indicador(
                        titulo: 'Divergências',
                        valor: '$divergentes',
                        icone: Icons.warning_amber_outlined,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _Indicador(
                        titulo: 'Progresso',
                        valor: '${(percentual * 100).toInt()}%',
                        icone: Icons.trending_up,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                const Text(
                  'Progresso da conferência',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),

                const SizedBox(height: 10),

                LinearProgressIndicator(value: percentual, minHeight: 10),

                const SizedBox(height: 8),

                Text(
                  '$conferidos de $total itens conferidos',
                  textAlign: TextAlign.center,
                ),

                const SizedBox(height: 32),

                SizedBox(
                  height: 54,
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: iniciarConferencia,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text(
                      'INICIAR CONFERÊNCIA',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _CardStatus extends StatelessWidget {
  final String status;
  final int conferenciaId;

  const _CardStatus({required this.status, required this.conferenciaId});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            const Icon(Icons.assignment_outlined, size: 40),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Conferência #$conferenciaId',
                    style: const TextStyle(fontSize: 24),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Status: ${status.toLowerCase()}',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Indicador extends StatelessWidget {
  final String titulo;
  final String valor;
  final IconData icone;

  const _Indicador({
    required this.titulo,
    required this.valor,
    required this.icone,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 10),
        child: Column(
          children: [
            Icon(icone, size: 30),
            const SizedBox(height: 8),
            Text(
              valor,
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(titulo, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
