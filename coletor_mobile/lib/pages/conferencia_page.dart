import 'package:flutter/material.dart';

import 'package:coletor_mobile/services/conferencia_service.dart';
import 'package:coletor_mobile/services/contagem_service.dart';

class ConferenciaPage extends StatefulWidget {
  final int conferenciaId;

  const ConferenciaPage({super.key, required this.conferenciaId});

  @override
  State<ConferenciaPage> createState() => _ConferenciaPageState();
}

class _ConferenciaPageState extends State<ConferenciaPage> {
  final conferenciaService = ConferenciaService();
  final contagemService = ContagemService();

  final codigoController = TextEditingController();
  final quantidadeController = TextEditingController(text: '1');

  final codigoFocusNode = FocusNode();

  late Future<Map<String, dynamic>> futureConferencia;

  bool registrando = false;
  bool finalizando = false;

  @override
  void initState() {
    super.initState();

    futureConferencia = conferenciaService.buscarConferencia(
      widget.conferenciaId,
    );

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focarCodigo();
    });
  }

  @override
  void dispose() {
    codigoController.dispose();
    quantidadeController.dispose();
    codigoFocusNode.dispose();

    super.dispose();
  }

  void _focarCodigo() {
    if (!mounted) return;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      FocusScope.of(context).requestFocus(codigoFocusNode);
    });
  }

  Future<void> recarregar() async {
    setState(() {
      futureConferencia = conferenciaService.buscarConferencia(
        widget.conferenciaId,
      );
    });

    await futureConferencia;

    if (!mounted) return;

    _focarCodigo();
  }

  Future<void> registrar() async {
    if (registrando) return;

    final codigo = codigoController.text.trim();

    final quantidade = int.tryParse(quantidadeController.text.trim());

    if (codigo.isEmpty) {
      _mostrarMensagem('Leia ou informe o código de barras.');

      _focarCodigo();
      return;
    }

    if (quantidade == null || quantidade <= 0) {
      _mostrarMensagem('Informe uma quantidade válida.', erro: true);

      return;
    }

    setState(() {
      registrando = true;
    });

    try {
      final resultado = await contagemService.registrarContagem(
        conferenciaId: widget.conferenciaId,
        codigo: codigo,
        quantidade: quantidade,
      );

      if (!mounted) return;

      final codigoRegistrado = resultado['codigo']?.toString() ?? codigo;

      _mostrarMensagem('Contagem registrada: $codigoRegistrado');

      codigoController.clear();
      quantidadeController.text = '1';

      setState(() {
        futureConferencia = conferenciaService.buscarConferencia(
          widget.conferenciaId,
        );
      });

      await futureConferencia;

      if (!mounted) return;

      _focarCodigo();
    } catch (e) {
      if (!mounted) return;

      final mensagem = e.toString().replaceFirst('Exception: ', '');

      _mostrarMensagem(mensagem, erro: true);

      _focarCodigo();
    } finally {
      if (mounted) {
        setState(() {
          registrando = false;
        });
      }
    }
  }

  Future<void> finalizarConferencia() async {
    if (finalizando) return;

    setState(() {
      finalizando = true;
    });

    try {
      await conferenciaService.fecharConferencia(widget.conferenciaId);

      if (!mounted) return;

      _mostrarMensagem('Conferência finalizada com sucesso.');

      setState(() {
        futureConferencia = conferenciaService.buscarConferencia(
          widget.conferenciaId,
        );
      });

      await futureConferencia;
    } catch (e) {
      if (!mounted) return;

      final mensagem = e.toString().replaceFirst('Exception: ', '');

      _mostrarMensagem(mensagem, erro: true);
    } finally {
      if (mounted) {
        setState(() {
          finalizando = false;
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
          duration: const Duration(seconds: 2),
        ),
      );
  }

  int _numero(dynamic valor) {
    if (valor is num) {
      return valor.toInt();
    }

    return num.tryParse(valor?.toString() ?? '')?.toInt() ?? 0;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Conferência #${widget.conferenciaId}')),
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
                      'Erro ao carregar conferência:\n'
                      '${snapshot.error}',
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

          final total = _numero(dados['total_itens']);

          final divergentes = _numero(dados['divergentes']);

          final status = dados['status']?.toString() ?? '';

          final statusConferencia =
              dados['status_conferencia']?.toString() ?? '';

          final finalizada = statusConferencia.toUpperCase() == 'FINALIZADA';

          final itens = dados['itens'] as List<dynamic>? ?? [];

          final conferidos = itens.where((item) {
            final contado = _numero(item['contado']);

            return contado > 0;
          }).length;

          final percentual = total > 0 ? conferidos / total : 0.0;

          return Column(
            children: [
              _CabecalhoResumo(
                total: total,
                conferidos: conferidos,
                divergentes: divergentes,
                percentual: percentual,
                status: status,
              ),

              const Divider(height: 1),

              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    TextField(
                      controller: codigoController,
                      focusNode: codigoFocusNode,
                      autofocus: true,
                      keyboardType: TextInputType.number,
                      textInputAction: TextInputAction.done,
                      enabled: !registrando && !finalizada,
                      decoration: const InputDecoration(
                        labelText: 'Código de barras',
                        hintText: 'Leia o código de barras',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.qr_code_scanner),
                      ),
                      onSubmitted: (_) {
                        registrar();
                      },
                    ),

                    const SizedBox(height: 12),

                    TextField(
                      controller: quantidadeController,
                      keyboardType: TextInputType.number,
                      textInputAction: TextInputAction.done,
                      enabled: !registrando && !finalizada,
                      decoration: const InputDecoration(
                        labelText: 'Quantidade',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.numbers),
                      ),
                      onSubmitted: (_) {
                        registrar();
                      },
                    ),

                    const SizedBox(height: 12),

                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: registrando || finalizada ? null : registrar,
                        icon: registrando
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.check),
                        label: Text(
                          registrando ? 'REGISTRANDO...' : 'REGISTRAR',
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const Divider(height: 1),

              if (!finalizada &&
                  conferidos == total &&
                  total > 0 &&
                  divergentes == 0)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                  child: SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: ElevatedButton.icon(
                      onPressed: finalizando ? null : finalizarConferencia,
                      icon: finalizando
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.lock_outline),
                      label: Text(
                        finalizando
                            ? 'FINALIZANDO...'
                            : 'FINALIZAR CONFERÊNCIA',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                ),

              if (finalizada)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.green),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.check_circle, color: Colors.green),
                        SizedBox(width: 8),
                        Text(
                          'CONFERÊNCIA FINALIZADA',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                ),

              Expanded(
                child: RefreshIndicator(
                  onRefresh: recarregar,
                  child: ListView.builder(
                    padding: const EdgeInsets.only(top: 8, bottom: 24),
                    itemCount: itens.length,
                    itemBuilder: (context, index) {
                      final item = itens[index];

                      return _ItemConferencia(
                        codigo: item['codigo']?.toString() ?? '',
                        esperado: _numero(item['xml']),
                        contado: _numero(item['contado']),
                        diferenca: _numero(item['diferenca']),
                      );
                    },
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _CabecalhoResumo extends StatelessWidget {
  final int total;
  final int conferidos;
  final int divergentes;
  final double percentual;
  final String status;

  const _CabecalhoResumo({
    required this.total,
    required this.conferidos,
    required this.divergentes,
    required this.percentual,
    required this.status,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: _ResumoItem(
                  titulo: 'Itens',
                  valor: '$total',
                  icone: Icons.inventory_2_outlined,
                ),
              ),
              Expanded(
                child: _ResumoItem(
                  titulo: 'Conferidos',
                  valor: '$conferidos',
                  icone: Icons.check_circle_outline,
                ),
              ),
              Expanded(
                child: _ResumoItem(
                  titulo: 'Divergentes',
                  valor: '$divergentes',
                  icone: Icons.warning_amber_outlined,
                ),
              ),
              Expanded(
                child: _ResumoItem(
                  titulo: 'Status',
                  valor: status,
                  icone: Icons.assignment_outlined,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          Row(
            children: [
              Expanded(
                child: LinearProgressIndicator(value: percentual, minHeight: 8),
              ),
              const SizedBox(width: 12),
              Text(
                '${(percentual * 100).toInt()}%',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),

          const SizedBox(height: 4),

          Align(
            alignment: Alignment.centerRight,
            child: Text(
              '$conferidos de $total conferidos',
              style: const TextStyle(fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }
}

class _ResumoItem extends StatelessWidget {
  final String titulo;
  final String valor;
  final IconData icone;

  const _ResumoItem({
    required this.titulo,
    required this.valor,
    required this.icone,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icone, size: 22),
        const SizedBox(height: 4),
        Text(
          valor,
          textAlign: TextAlign.center,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 2),
        Text(
          titulo,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 11),
        ),
      ],
    );
  }
}

class _ItemConferencia extends StatelessWidget {
  final String codigo;
  final int esperado;
  final int contado;
  final int diferenca;

  const _ItemConferencia({
    required this.codigo,
    required this.esperado,
    required this.contado,
    required this.diferenca,
  });

  @override
  Widget build(BuildContext context) {
    final bool conferido = contado > 0;

    final bool correto = conferido && diferenca == 0;

    final bool divergente = conferido && diferenca != 0;

    final IconData icone;
    final String situacao;

    if (correto) {
      icone = Icons.check_circle;
      situacao = 'CONFERIDO';
    } else if (divergente) {
      icone = Icons.warning_amber;
      situacao = 'DIVERGÊNCIA';
    } else {
      icone = Icons.radio_button_unchecked;
      situacao = 'NÃO CONFERIDO';
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Icon(icone, size: 32),

            const SizedBox(width: 12),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Código: $codigo',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),

                  const SizedBox(height: 6),

                  Text(
                    'Esperado: $esperado   |   '
                    'Contado: $contado',
                  ),

                  const SizedBox(height: 4),

                  Text(
                    situacao,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),

            Text(
              diferenca > 0 ? '+$diferenca' : '$diferenca',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }
}
