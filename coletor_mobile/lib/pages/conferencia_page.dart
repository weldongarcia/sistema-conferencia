import 'package:flutter/material.dart';

import 'package:flutter/services.dart';

import 'package:coletor_mobile/services/conferencia_service.dart';

import 'package:coletor_mobile/services/contagem_service.dart';

import 'package:coletor_mobile/services/conferencia_local_service.dart';

import 'package:coletor_mobile/models/conferencia_resumo.dart';

enum ModoContagem { itemAItem, quantidade }

enum OrigemEntrada { bipado, digitado }

class ConferenciaPage extends StatefulWidget {
  final int conferenciaId;

  const ConferenciaPage({super.key, required this.conferenciaId});

  @override
  State<ConferenciaPage> createState() => _ConferenciaPageState();
}

class _ConferenciaPageState extends State<ConferenciaPage> {
  final conferenciaService = ConferenciaService();
  final conferenciaLocalService = ConferenciaLocalService();
  final contagemService = ContagemService();

  final codigoController = TextEditingController();

  final quantidadeController = TextEditingController(text: '1');

  final codigoFocusNode = FocusNode();

  late Future<Map<String, dynamic>> futureConferencia;

  bool registrando = false;

  bool finalizando = false;

  ModoContagem modoContagem = ModoContagem.itemAItem;

  OrigemEntrada origemCodigo = OrigemEntrada.bipado;

  String? codigoAtual;

  Map<String, dynamic>? produtoAtual;

  String? ultimoCodigo;

  String? ultimaDescricao;

  int ultimaQuantidade = 0;

  OrigemEntrada? ultimaOrigem;

  ModoContagem? ultimoMetodo;

  bool get quantidadeSelecionada =>
      modoContagem == ModoContagem.quantidade && codigoAtual != null;

  @override
  void initState() {
    super.initState();

    futureConferencia = _carregarConferencia();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      focarCodigo();
    });
  }

  @override
  void dispose() {
    codigoController.dispose();

    quantidadeController.dispose();

    codigoFocusNode.dispose();

    super.dispose();
  }

  Future<Map<String, dynamic>> _carregarConferencia() async {
    // 1. Tenta carregar do SQLite
    final conferenciaLocal = await conferenciaLocalService.buscarConferencia(
      widget.conferenciaId,
    );

    if (conferenciaLocal != null) {
      final itens = await conferenciaLocalService.listarItens(
        widget.conferenciaId,
      );

      return {
        'id': widget.conferenciaId,
        'status': conferenciaLocal['status'],
        'status_conferencia': conferenciaLocal['status_conferencia'],
        'versao': conferenciaLocal['versao'],
        'itens': itens,
        'total_itens': itens.length,
        'divergentes': itens.where((item) {
          return (item['divergente'] ?? 0) == 1;
        }).length,
      };
    }

    // 2. Se não existe localmente, baixa do servidor
    final dadosServidor = await conferenciaService.buscarConferencia(
      widget.conferenciaId,
    );

    // 3. Converte para o model
    final conferencia = ConferenciaResumo.fromJson(dadosServidor);

    // 4. Salva no SQLite
    await conferenciaLocalService.salvarConferencia(
      conferenciaId: widget.conferenciaId,
      conferencia: conferencia,
    );

    // 5. Retorna os dados locais
    final conferenciaSalva = await conferenciaLocalService.buscarConferencia(
      widget.conferenciaId,
    );

    if (conferenciaSalva == null) {
      throw Exception('Não foi possível salvar a conferência localmente.');
    }

    final itens = await conferenciaLocalService.listarItens(
      widget.conferenciaId,
    );

    return {
      'id': widget.conferenciaId,
      'status': conferenciaSalva['status'],
      'status_conferencia': conferenciaSalva['status_conferencia'],
      'versao': conferenciaSalva['versao'],
      'itens': itens,
      'total_itens': itens.length,
      'divergentes': itens.where((item) {
        return (item['divergente'] ?? 0) == 1;
      }).length,
    };
  }
  // ==========================================================

  // FOCO / TECLADO ANDROID

  // ==========================================================

  void focarCodigo() {
    if (!mounted) return;

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted || registrando || finalizando) return;

      FocusScope.of(context).requestFocus(codigoFocusNode);

      await Future.delayed(const Duration(milliseconds: 80));

      if (!mounted) return;

      // Mantém o teclado do Android fechado.

      await SystemChannels.textInput.invokeMethod('TextInput.hide');
    });
  }

  Future<void> fecharTecladoAndroid() async {
    await SystemChannels.textInput.invokeMethod('TextInput.hide');
  }

  // ==========================================================
  // RECARREGAR
  // ==========================================================

  Future<void> recarregar() async {
    if (registrando || finalizando) return;

    setState(() {
      futureConferencia = _carregarConferencia();
    });

    try {
      await futureConferencia;

      if (!mounted) return;

      focarCodigo();
    } catch (_) {
      if (!mounted) return;
      focarCodigo();
    }
  }

  // ==========================================================

  // FEEDBACK

  // ==========================================================

  void feedbackSucesso() {
    SystemSound.play(SystemSoundType.click);

    HapticFeedback.lightImpact();
  }

  void feedbackAlerta() {
    SystemSound.play(SystemSoundType.alert);

    HapticFeedback.heavyImpact();
  }

  // ==========================================================

  // TECLADO NA TELA

  // ==========================================================

  TextEditingController get controladorTeclado =>
      quantidadeSelecionada ? quantidadeController : codigoController;

  void adicionarNumero(String numero) {
    final controller = controladorTeclado;

    final atual = controller.text;

    if (quantidadeSelecionada) {
      if (atual == '0' || atual == '1') {
        controller.text = numero;
      } else {
        controller.text = '$atual$numero';
      }
    } else {
      controller.text = '$atual$numero';
    }

    controller.selection = TextSelection.collapsed(
      offset: controller.text.length,
    );

    setState(() {});

    fecharTecladoAndroid();
  }

  void apagarNumero() {
    final controller = controladorTeclado;

    final atual = controller.text;

    if (atual.isEmpty) return;

    controller.text = atual.length == 1
        ? ''
        : atual.substring(0, atual.length - 1);

    controller.selection = TextSelection.collapsed(
      offset: controller.text.length,
    );

    setState(() {});

    fecharTecladoAndroid();
  }

  void limparCampo() {
    controladorTeclado.clear();

    setState(() {});

    fecharTecladoAndroid();
  }

  void teclaConfirmar() {
    if (quantidadeSelecionada) {
      registrar();
    } else {
      processarCodigo();
    }
  }

  // ==========================================================

  // CÓDIGO

  // ==========================================================

  void marcarEntradaDigitada() {
    if (registrando || finalizando) return;

    if (codigoController.text.isNotEmpty) {
      origemCodigo = OrigemEntrada.digitado;
    }
  }

  void processarCodigo() {
    if (registrando || finalizando) return;

    final codigo = codigoController.text.trim();

    if (codigo.isEmpty) {
      mostrarMensagem('Leia ou informe o código do produto.', erro: true);

      focarCodigo();

      return;
    }

    buscarProduto(codigo);
  }

  Future<void> buscarProduto(String codigo) async {
    if (registrando || finalizando) return;

    try {
      final dados = await futureConferencia;

      if (!mounted) return;

      final itens = dados['itens'] as List<dynamic>? ?? [];

      Map<String, dynamic>? encontrado;

      for (final item in itens) {
        final codigoItem = item['codigo']?.toString().trim();

        if (codigoItem == codigo.trim()) {
          encontrado = Map<String, dynamic>.from(item);

          break;
        }
      }

      setState(() {
        codigoAtual = codigo.trim();

        produtoAtual = encontrado;
      });

      if (encontrado == null) {
        feedbackAlerta();

        await perguntarIncluirNaConferencia(codigo.trim());

        return;
      }

      // ITEM A ITEM:

      // encontrou -> registra automaticamente 1 unidade.

      if (modoContagem == ModoContagem.itemAItem) {
        await registrar(codigoForcado: codigo.trim(), quantidadeForcada: 1);

        return;
      }

      // QUANTIDADE:

      // encontrou -> fica aguardando a quantidade.

      quantidadeController.text = '1';

      await fecharTecladoAndroid();

      if (!mounted) return;

      setState(() {});
    } catch (e) {
      if (!mounted) return;

      feedbackAlerta();

      mostrarMensagem(e.toString().replaceFirst('Exception: ', ''), erro: true);

      focarCodigo();
    }
  }

  // ==========================================================

  // REGISTRAR

  // ==========================================================

  Future<void> registrar({
    String? codigoForcado,

    int? quantidadeForcada,

    bool incluirNaConferencia = false,
  }) async {
    if (registrando) return;

    final codigo = (codigoForcado ?? codigoController.text).trim();

    final quantidade =
        quantidadeForcada ?? int.tryParse(quantidadeController.text.trim());

    if (codigo.isEmpty) {
      mostrarMensagem('Leia ou informe o código de barras.', erro: true);

      focarCodigo();

      return;
    }

    if (quantidade == null || quantidade <= 0) {
      mostrarMensagem('Informe uma quantidade válida.', erro: true);

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

        incluirNaConferencia: incluirNaConferencia,
      );

      if (!mounted) return;

      final codigoRegistrado = resultado['codigo']?.toString() ?? codigo;

      String? descricaoRegistrada;

      if (produtoAtual != null &&
          produtoAtual!['codigo']?.toString() == codigoRegistrado) {
        descricaoRegistrada = produtoAtual!['descricao']?.toString();
      }

      final metodoRegistro = modoContagem;

      final origemRegistro = origemCodigo;

      setState(() {
        ultimoCodigo = codigoRegistrado;

        ultimaDescricao = descricaoRegistrada;

        ultimaQuantidade = quantidade;

        ultimaOrigem = origemRegistro;

        ultimoMetodo = metodoRegistro;

        codigoController.clear();

        quantidadeController.text = '1';

        codigoAtual = null;

        produtoAtual = null;

        futureConferencia = conferenciaService.buscarConferencia(
          widget.conferenciaId,
        );
      });

      feedbackSucesso();

      if (incluirNaConferencia) {
        mostrarMensagem('Produto $codigoRegistrado incluído.');
      } else if (metodoRegistro == ModoContagem.itemAItem) {
        mostrarMensagem('Bip registrado: $codigoRegistrado');
      } else {
        mostrarMensagem('Quantidade registrada: $quantidade');
      }

      await futureConferencia;

      if (!mounted) return;

      focarCodigo();
    } on ProdutoNaoEncontradoException catch (e) {
      if (!mounted) return;

      setState(() {
        registrando = false;
      });

      feedbackAlerta();

      await perguntarIncluirNaConferencia(e.codigo);

      return;
    } catch (e) {
      if (!mounted) return;

      feedbackAlerta();

      mostrarMensagem(e.toString().replaceFirst('Exception: ', ''), erro: true);

      focarCodigo();
    } finally {
      if (mounted) {
        setState(() {
          registrando = false;
        });
      }
    }
  }

  // ==========================================================

  // PRODUTO NÃO ENCONTRADO

  // ==========================================================

  Future<void> perguntarIncluirNaConferencia(String codigo) async {
    if (!mounted) return;

    final incluir = await showDialog<bool>(
      context: context,

      barrierDismissible: false,

      builder: (context) {
        return AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.warning_amber_rounded),

              SizedBox(width: 8),

              Expanded(child: Text('Produto não encontrado')),
            ],
          ),

          content: Column(
            mainAxisSize: MainAxisSize.min,

            crossAxisAlignment: CrossAxisAlignment.start,

            children: [
              const Text('Este produto não está presente na nota fiscal.'),

              const SizedBox(height: 12),

              Text(
                'Código: $codigo',

                style: const TextStyle(
                  fontWeight: FontWeight.bold,

                  fontSize: 16,
                ),
              ),

              const SizedBox(height: 12),

              const Text('Deseja incluir este produto na conferência?'),
            ],
          ),

          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop(false);
              },

              child: const Text('CANCELAR'),
            ),

            ElevatedButton(
              onPressed: () {
                Navigator.of(context).pop(true);
              },

              child: const Text('INCLUIR'),
            ),
          ],
        );
      },
    );

    if (!mounted) return;

    if (incluir != true) {
      setState(() {
        codigoController.clear();

        quantidadeController.text = '1';

        codigoAtual = null;

        produtoAtual = null;
      });

      focarCodigo();

      return;
    }

    codigoController.text = codigo;

    await registrar(incluirNaConferencia: true);
  }

  // ==========================================================

  // PESQUISA DE PRODUTOS JÁ REGISTRADOS
  // ============================================================

  Future<void> _abrirPesquisaBipados(List<dynamic> itens) async {
    if (!mounted) return;

    final registrados = itens
        .where((item) => numero(item['contado']) > 0)
        .map((item) => Map<String, dynamic>.from(item))
        .toList();

    final pesquisaController = TextEditingController();

    try {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          return StatefulBuilder(
            builder: (context, setDialogState) {
              final termo = pesquisaController.text.trim().toLowerCase();

              final filtrados = registrados.where((item) {
                final codigo = item['codigo']?.toString().toLowerCase() ?? '';
                final descricao =
                    item['descricao']?.toString().toLowerCase() ?? '';
                return termo.isEmpty ||
                    codigo.contains(termo) ||
                    descricao.contains(termo);
              }).toList();

              return AlertDialog(
                titlePadding: const EdgeInsets.fromLTRB(18, 14, 10, 8),
                contentPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                title: Row(
                  children: [
                    const Expanded(
                      child: Text(
                        'Produtos conferidos',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(dialogContext).pop(),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
                content: SizedBox(
                  width: double.maxFinite,
                  height: MediaQuery.of(context).size.height * 0.55,
                  child: Column(
                    children: [
                      TextField(
                        controller: pesquisaController,
                        autofocus: true,
                        decoration: const InputDecoration(
                          hintText: 'Código ou descrição',
                          prefixIcon: Icon(Icons.search),
                          border: OutlineInputBorder(),
                          isDense: true,
                        ),
                        onChanged: (_) => setDialogState(() {}),
                      ),
                      const SizedBox(height: 8),
                      Expanded(
                        child: filtrados.isEmpty
                            ? const Center(
                                child: Text(
                                  'Nenhum produto já conferido encontrado.',
                                  textAlign: TextAlign.center,
                                ),
                              )
                            : ListView.separated(
                                itemCount: filtrados.length,
                                separatorBuilder: (_, _) =>
                                    const Divider(height: 1),
                                itemBuilder: (_, index) {
                                  final item = filtrados[index];
                                  return ListTile(
                                    dense: true,
                                    contentPadding: const EdgeInsets.symmetric(
                                      horizontal: 4,
                                    ),
                                    leading: const Icon(
                                      Icons.check_circle_outline,
                                      size: 21,
                                    ),
                                    title: Text(
                                      item['descricao']?.toString() ??
                                          'Produto',
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    subtitle: Text(
                                      'Cód. ${item['codigo'] ?? ''}',
                                      style: const TextStyle(fontSize: 9),
                                    ),
                                    trailing: Text(
                                      'Qtd. ${numero(item['contado'])}',
                                      style: const TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  );
                                },
                              ),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      );
    } finally {
      pesquisaController.dispose();
    }
  }

  // MODO

  // ==========================================================

  void alterarModo(ModoContagem novoModo) {
    if (registrando || finalizando) return;

    setState(() {
      modoContagem = novoModo;

      codigoController.clear();

      quantidadeController.text = '1';

      codigoAtual = null;

      produtoAtual = null;

      origemCodigo = OrigemEntrada.bipado;
    });

    focarCodigo();
  }

  // ==========================================================

  // FINALIZAR

  // ==========================================================

  Future<void> finalizarConferencia() async {
    if (finalizando) return;

    setState(() {
      finalizando = true;
    });

    try {
      await conferenciaService.fecharConferencia(widget.conferenciaId);

      if (!mounted) return;

      mostrarMensagem('Conferência finalizada com sucesso.');

      setState(() {
        futureConferencia = _carregarConferencia();
      });

      await futureConferencia;
    } catch (e) {
      if (!mounted) return;

      feedbackAlerta();

      mostrarMensagem(e.toString().replaceFirst('Exception: ', ''), erro: true);
    } finally {
      if (mounted) {
        setState(() {
          finalizando = false;
        });
      }
    }
  }

  // ==========================================================

  // MENSAGEM

  // ==========================================================

  void mostrarMensagem(String mensagem, {bool erro = false}) {
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

  // ==========================================================

  // CONVERSÃO

  // ==========================================================

  int numero(dynamic valor) {
    if (valor is num) return valor.toInt();

    return num.tryParse(valor?.toString() ?? '')?.toInt() ?? 0;
  }

  // ==========================================================

  // BUILD

  // ==========================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: false,

      appBar: AppBar(
        toolbarHeight: 46,

        title: Text(
          'Conferência #${widget.conferenciaId}',

          style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
        ),

        actions: [
          IconButton(
            tooltip: 'Atualizar',

            onPressed: registrando || finalizando ? null : recarregar,

            icon: const Icon(Icons.refresh, size: 21),
          ),
        ],
      ),

      body: FutureBuilder<Map<String, dynamic>>(
        future: futureConferencia,

        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(20),

                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,

                  children: [
                    const Icon(Icons.error_outline, size: 50),

                    const SizedBox(height: 12),

                    Text(
                      'Erro ao carregar conferência:\n'
                      '${snapshot.error}',

                      textAlign: TextAlign.center,
                    ),

                    const SizedBox(height: 16),

                    ElevatedButton(
                      onPressed: recarregar,

                      child: const Text('TENTAR NOVAMENTE'),
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

          final total = numero(dados['total_itens']);

          final divergentes = numero(dados['divergentes']);

          final status = dados['status_conferencia']?.toString() ?? '';

          final finalizada = status.toUpperCase() == 'FINALIZADA';

          final itens = dados['itens'] as List<dynamic>? ?? [];

          final conferidos = itens.where((item) {
            return numero(item['contado']) > 0;
          }).length;

          final percentual = total > 0 ? conferidos / total : 0.0;

          return SafeArea(
            child: Column(
              children: [
                _CabecalhoCompacto(
                  percentual: percentual,
                  status: status,
                  ultimoCodigo: ultimoCodigo,
                  ultimaDescricao: ultimaDescricao,
                  ultimaQuantidade: ultimaQuantidade,
                  ultimaOrigem: ultimaOrigem,
                  ultimoMetodo: ultimoMetodo,
                  onPesquisar: finalizada
                      ? null
                      : () => _abrirPesquisaBipados(itens),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(8, 1, 8, 3),
                  child: _SeletorModo(
                    modo: modoContagem,
                    enabled: !registrando && !finalizada,
                    onChanged: alterarModo,
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: _CampoCodigo(
                    controller: codigoController,
                    focusNode: codigoFocusNode,
                    enabled: !registrando && !finalizada,
                    onChanged: (_) {
                      if (codigoController.text.isNotEmpty) {
                        origemCodigo = OrigemEntrada.digitado;
                      }
                    },
                    onSubmitted: (_) => processarCodigo(),
                    onBuscar: processarCodigo,
                  ),
                ),
                if (modoContagem == ModoContagem.quantidade &&
                    produtoAtual != null)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(8, 3, 8, 0),
                    child: _ProdutoSelecionado(
                      codigo: codigoAtual ?? '',
                      descricao: produtoAtual?['descricao']?.toString() ?? '',
                    ),
                  ),
                const SizedBox(height: 3),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: SizedBox(
                    width: double.infinity,
                    height: 38,
                    child: ElevatedButton.icon(
                      onPressed: (!registrando && !finalizada)
                          ? teclaConfirmar
                          : null,
                      icon: Icon(
                        modoContagem == ModoContagem.quantidade &&
                                produtoAtual != null
                            ? Icons.check
                            : Icons.search,
                        size: 17,
                      ),
                      label: Text(
                        modoContagem == ModoContagem.quantidade &&
                                produtoAtual != null
                            ? 'REGISTRAR QUANTIDADE'
                            : 'BUSCAR / REGISTRAR',
                        style: const TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 3),
                Expanded(
                  child: _TecladoNumerico(
                    titulo: quantidadeSelecionada ? 'QUANTIDADE' : 'CÓDIGO',
                    valor: controladorTeclado.text,
                    enabled: !registrando && !finalizada,
                    modoQuantidade: quantidadeSelecionada,
                    onNumero: adicionarNumero,
                    onApagar: apagarNumero,
                    onLimpar: limparCampo,
                    onConfirmar: teclaConfirmar,
                  ),
                ),
                if (!finalizada &&
                    conferidos == total &&
                    total > 0 &&
                    divergentes == 0)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(8, 2, 8, 4),
                    child: SizedBox(
                      width: double.infinity,
                      height: 38,
                      child: ElevatedButton.icon(
                        onPressed: finalizando ? null : finalizarConferencia,
                        icon: finalizando
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.lock_outline, size: 17),
                        label: Text(
                          finalizando
                              ? 'FINALIZANDO...'
                              : 'FINALIZAR CONFERÊNCIA',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ),
                  ),
                if (finalizada)
                  const Padding(
                    padding: EdgeInsets.fromLTRB(8, 2, 8, 4),
                    child: _FinalizadaCompacto(),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ============================================================

// CABEÇALHO
// ============================================================

class _CabecalhoCompacto extends StatelessWidget {
  final double percentual;
  final String status;
  final String? ultimoCodigo;
  final String? ultimaDescricao;
  final int ultimaQuantidade;
  final OrigemEntrada? ultimaOrigem;
  final ModoContagem? ultimoMetodo;
  final VoidCallback? onPesquisar;

  const _CabecalhoCompacto({
    required this.percentual,
    required this.status,
    required this.ultimoCodigo,
    required this.ultimaDescricao,
    required this.ultimaQuantidade,
    required this.ultimaOrigem,
    required this.ultimoMetodo,
    required this.onPesquisar,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 3, 8, 2),
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(9),
              border: Border.all(
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  ultimoCodigo == null
                      ? Icons.qr_code_scanner
                      : (ultimaOrigem == OrigemEntrada.bipado
                            ? Icons.qr_code_scanner
                            : Icons.keyboard_alt_outlined),
                  size: 19,
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: ultimoCodigo == null
                      ? const Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'ÚLTIMO REGISTRO',
                              style: TextStyle(
                                fontSize: 8,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              'Aguardando o primeiro registro',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        )
                      : Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'ÚLTIMO REGISTRO',
                              style: TextStyle(
                                fontSize: 8,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              ultimaDescricao?.isNotEmpty == true
                                  ? ultimaDescricao!
                                  : 'Produto não identificado',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            Text(
                              'Cód. $ultimoCodigo',
                              style: const TextStyle(fontSize: 9),
                            ),
                          ],
                        ),
                ),
                if (ultimoCodigo != null)
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        'Qtd. $ultimaQuantidade',
                        style: const TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        ultimaOrigem == OrigemEntrada.bipado
                            ? 'BIPADO'
                            : 'DIGITADO',
                        style: const TextStyle(
                          fontSize: 7,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                IconButton(
                  tooltip: 'Pesquisar produtos já conferidos',
                  onPressed: onPesquisar,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(
                    minWidth: 38,
                    minHeight: 38,
                  ),
                  icon: const Icon(Icons.search, size: 22),
                ),
              ],
            ),
          ),
          const SizedBox(height: 3),
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: percentual,
                    minHeight: 5,
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Text(
                '${(percentual * 100).toInt()}%',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          Align(
            alignment: Alignment.centerRight,
            child: Text(
              status,
              style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

// SELETOR DE MODO

// ============================================================

class _SeletorModo extends StatelessWidget {
  final ModoContagem modo;

  final bool enabled;

  final ValueChanged<ModoContagem> onChanged;

  const _SeletorModo({
    required this.modo,

    required this.enabled,

    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 38,

      child: SegmentedButton<ModoContagem>(
        segments: const [
          ButtonSegment<ModoContagem>(
            value: ModoContagem.itemAItem,

            icon: Icon(Icons.qr_code_scanner, size: 15),

            label: Text(
              'ITEM A ITEM',

              style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
            ),
          ),

          ButtonSegment<ModoContagem>(
            value: ModoContagem.quantidade,

            icon: Icon(Icons.calculate_outlined, size: 15),

            label: Text(
              'QUANTIDADE',

              style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
            ),
          ),
        ],

        selected: {modo},

        onSelectionChanged: enabled
            ? (selecionado) {
                onChanged(selecionado.first);
              }
            : null,

        showSelectedIcon: false,

        style: ButtonStyle(
          visualDensity: VisualDensity.compact,

          padding: WidgetStateProperty.all(
            const EdgeInsets.symmetric(horizontal: 5),
          ),
        ),
      ),
    );
  }
}

// ============================================================

// CAMPO DE CÓDIGO

// ============================================================

class _CampoCodigo extends StatelessWidget {
  final TextEditingController controller;

  final FocusNode focusNode;

  final bool enabled;

  final ValueChanged<String> onChanged;

  final ValueChanged<String> onSubmitted;

  final VoidCallback onBuscar;

  const _CampoCodigo({
    required this.controller,

    required this.focusNode,

    required this.enabled,

    required this.onChanged,

    required this.onSubmitted,

    required this.onBuscar,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 50,

      child: TextField(
        controller: controller,

        focusNode: focusNode,

        enabled: enabled,

        keyboardType: TextInputType.none,

        showCursor: true,

        textInputAction: TextInputAction.done,

        onChanged: onChanged,

        onSubmitted: onSubmitted,

        decoration: InputDecoration(
          labelText: 'Código do produto',

          hintText: 'Bipe ou digite o código',

          prefixIcon: const Icon(Icons.qr_code_scanner, size: 20),

          suffixIcon: IconButton(
            onPressed: enabled ? onBuscar : null,

            icon: const Icon(Icons.search),
          ),

          border: const OutlineInputBorder(),

          contentPadding: const EdgeInsets.symmetric(
            horizontal: 10,

            vertical: 7,
          ),
        ),
      ),
    );
  }
}

// ============================================================

// PRODUTO SELECIONADO

// ============================================================

class _ProdutoSelecionado extends StatelessWidget {
  final String codigo;

  final String descricao;

  const _ProdutoSelecionado({required this.codigo, required this.descricao});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,

      constraints: const BoxConstraints(minHeight: 52),

      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),

      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(9),

        color: Theme.of(context).colorScheme.surfaceContainerHighest,
      ),

      child: Row(
        children: [
          Icon(
            Icons.inventory_2_outlined,

            size: 20,

            color: Theme.of(context).colorScheme.primary,
          ),

          const SizedBox(width: 8),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,

              children: [
                const Text(
                  'PRODUTO',

                  style: TextStyle(fontSize: 8, fontWeight: FontWeight.bold),
                ),

                Text(
                  descricao,

                  maxLines: 2,

                  overflow: TextOverflow.ellipsis,

                  style: const TextStyle(
                    fontSize: 12,

                    fontWeight: FontWeight.w600,
                  ),
                ),

                Text('Cód. $codigo', style: const TextStyle(fontSize: 9)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================

// ÚLTIMO REGISTRO

// ============================================================

class _UltimoRegistro extends StatelessWidget {
  final String codigo;

  final String? descricao;

  final int quantidade;

  final OrigemEntrada? origem;

  final ModoContagem? metodo;

  const _UltimoRegistro({
    required this.codigo,

    required this.descricao,

    required this.quantidade,

    required this.origem,

    required this.metodo,
  });

  @override
  Widget build(BuildContext context) {
    final bipado = origem == OrigemEntrada.bipado;

    return Container(
      width: double.infinity,

      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),

      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(9),

        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),

      child: Row(
        children: [
          Icon(
            bipado ? Icons.qr_code_scanner : Icons.keyboard_alt_outlined,

            size: 18,
          ),

          const SizedBox(width: 7),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,

              children: [
                const Text(
                  'ÚLTIMO REGISTRO',

                  style: TextStyle(fontSize: 8, fontWeight: FontWeight.bold),
                ),

                Text(
                  descricao?.isNotEmpty == true ? descricao! : 'Código $codigo',

                  maxLines: 1,

                  overflow: TextOverflow.ellipsis,

                  style: const TextStyle(
                    fontSize: 10,

                    fontWeight: FontWeight.w600,
                  ),
                ),

                Text('Cód. $codigo', style: const TextStyle(fontSize: 8)),
              ],
            ),
          ),

          Column(
            crossAxisAlignment: CrossAxisAlignment.end,

            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),

                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(6),

                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                ),

                child: Text(
                  bipado ? 'BIPADO' : 'DIGITADO',

                  style: const TextStyle(
                    fontSize: 8,

                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),

              const SizedBox(height: 2),

              Text(
                'Qtd. $quantidade',

                style: const TextStyle(
                  fontSize: 9,

                  fontWeight: FontWeight.bold,
                ),
              ),

              if (metodo != null)
                Text(
                  metodo == ModoContagem.itemAItem
                      ? 'ITEM A ITEM'
                      : 'QUANTIDADE',

                  style: const TextStyle(fontSize: 7),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

// ============================================================

// TECLADO NUMÉRICO

// ============================================================

class _TecladoNumerico extends StatelessWidget {
  final String titulo;

  final String valor;

  final bool enabled;

  final bool modoQuantidade;

  final ValueChanged<String> onNumero;

  final VoidCallback onApagar;

  final VoidCallback onLimpar;

  final VoidCallback onConfirmar;

  const _TecladoNumerico({
    required this.titulo,

    required this.valor,

    required this.enabled,

    required this.modoQuantidade,

    required this.onNumero,

    required this.onApagar,

    required this.onLimpar,

    required this.onConfirmar,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 0, 8, 0),

      child: Column(
        children: [
          Container(
            height: 42,

            width: double.infinity,

            padding: const EdgeInsets.symmetric(horizontal: 10),

            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(9),

              color: Theme.of(context).colorScheme.surfaceContainerHighest,
            ),

            child: Row(
              children: [
                Icon(
                  modoQuantidade
                      ? Icons.calculate_outlined
                      : Icons.keyboard_alt_outlined,

                  size: 18,
                ),

                const SizedBox(width: 7),

                Text(
                  titulo,

                  style: const TextStyle(
                    fontSize: 9,

                    fontWeight: FontWeight.bold,
                  ),
                ),

                const Spacer(),

                Flexible(
                  child: Text(
                    valor.isEmpty ? '0' : valor,

                    overflow: TextOverflow.ellipsis,

                    style: const TextStyle(
                      fontSize: 22,

                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 2),

          Expanded(
            child: Column(
              children: [
                Expanded(
                  child: Row(
                    children: [
                      _Tecla(
                        texto: '1',

                        enabled: enabled,

                        onPressed: () => onNumero('1'),
                      ),

                      _Tecla(
                        texto: '2',

                        enabled: enabled,

                        onPressed: () => onNumero('2'),
                      ),

                      _Tecla(
                        texto: '3',

                        enabled: enabled,

                        onPressed: () => onNumero('3'),
                      ),
                    ],
                  ),
                ),

                Expanded(
                  child: Row(
                    children: [
                      _Tecla(
                        texto: '4',

                        enabled: enabled,

                        onPressed: () => onNumero('4'),
                      ),

                      _Tecla(
                        texto: '5',

                        enabled: enabled,

                        onPressed: () => onNumero('5'),
                      ),

                      _Tecla(
                        texto: '6',

                        enabled: enabled,

                        onPressed: () => onNumero('6'),
                      ),
                    ],
                  ),
                ),

                Expanded(
                  child: Row(
                    children: [
                      _Tecla(
                        texto: '7',

                        enabled: enabled,

                        onPressed: () => onNumero('7'),
                      ),

                      _Tecla(
                        texto: '8',

                        enabled: enabled,

                        onPressed: () => onNumero('8'),
                      ),

                      _Tecla(
                        texto: '9',

                        enabled: enabled,

                        onPressed: () => onNumero('9'),
                      ),
                    ],
                  ),
                ),

                Expanded(
                  child: Row(
                    children: [
                      _Tecla(texto: 'C', enabled: enabled, onPressed: onLimpar),

                      _Tecla(
                        texto: '0',

                        enabled: enabled,

                        onPressed: () => onNumero('0'),
                      ),

                      _Tecla(texto: '⌫', enabled: enabled, onPressed: onApagar),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 2),

          SizedBox(
            width: double.infinity,

            height: 40,

            child: ElevatedButton.icon(
              onPressed: enabled ? onConfirmar : null,

              icon: Icon(modoQuantidade ? Icons.check : Icons.search, size: 17),

              label: Text(
                modoQuantidade ? 'CONFIRMAR QUANTIDADE' : 'BUSCAR / REGISTRAR',

                style: const TextStyle(
                  fontSize: 10,

                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Tecla extends StatelessWidget {
  final String texto;

  final bool enabled;

  final VoidCallback onPressed;

  const _Tecla({
    required this.texto,

    required this.enabled,

    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.all(2),

        child: SizedBox.expand(
          child: OutlinedButton(
            onPressed: enabled ? onPressed : null,

            style: OutlinedButton.styleFrom(
              padding: EdgeInsets.zero,

              minimumSize: Size.zero,

              tapTargetSize: MaterialTapTargetSize.shrinkWrap,

              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),

            child: Text(
              texto,

              style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
            ),
          ),
        ),
      ),
    );
  }
}

// ============================================================

// FINALIZADA

// ============================================================

class _FinalizadaCompacto extends StatelessWidget {
  const _FinalizadaCompacto();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,

      height: 36,

      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),

        border: Border.all(color: Colors.green),
      ),

      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,

        children: [
          Icon(Icons.check_circle, color: Colors.green, size: 17),

          SizedBox(width: 6),

          Text(
            'CONFERÊNCIA FINALIZADA',

            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
