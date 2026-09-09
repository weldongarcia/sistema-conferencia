import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:coletor_mobile/models/conferencia_resumo.dart';
import 'package:coletor_mobile/services/auth_service.dart';
import 'package:coletor_mobile/services/conferencia_local_service.dart';
import 'package:coletor_mobile/services/conferencia_service.dart';
import 'package:coletor_mobile/services/contagem_local_service.dart';

enum ModoContagem { unidade, quantidade }

enum OrigemEntrada { bipado, digitado }

class ConferenciaPage extends StatefulWidget {
  final int conferenciaId;
  const ConferenciaPage({super.key, required this.conferenciaId});
  @override
  State<ConferenciaPage> createState() => _ConferenciaPageState();
}

class _ConferenciaPageState extends State<ConferenciaPage> {
  final local = ConferenciaLocalService();
  final conferenciaService = ConferenciaService();
  final contagem = ContagemLocalService();
  final auth = AuthService();
  final codigo = TextEditingController();
  final quantidade = TextEditingController();
  final foco = FocusNode();

  late Future<Map<String, dynamic>> dadosFuture;
  ModoContagem modo = ModoContagem.unidade;
  OrigemEntrada origem = OrigemEntrada.bipado;
  bool caixaFechada = false;
  bool ocupado = false;
  bool finalizando = false;
  String volume = '0000';
  String? ultimoCodigo;
  String? ultimaDescricao;
  int ultimaQuantidade = 0;

  // Estado do modo quantidade.
  // Quando preenchido, significa que o código já foi pesquisado
  // e estamos aguardando a quantidade.
  String? codigoQuantidadePendente;
  String? descricaoQuantidadePendente;

  bool get aguardandoQuantidade => codigoQuantidadePendente != null;

  @override
  void initState() {
    super.initState();
    dadosFuture = _carregar();
    WidgetsBinding.instance.addPostFrameCallback((_) => _focar());
  }

  @override
  void dispose() {
    codigo.dispose();
    quantidade.dispose();
    foco.dispose();
    super.dispose();
  }

  int _int(dynamic v) {
    if (v is int) return v;
    if (v is num) return v.toInt();
    return int.tryParse(v?.toString() ?? '') ?? 0;
  }

  Future<Map<String, dynamic>> _carregar() async {
    final localConf = await local.buscarConferencia(widget.conferenciaId);
    if (localConf != null) return _dadosLocais(localConf);

    final json = await conferenciaService.buscarConferencia(
      widget.conferenciaId,
    );
    final conf = ConferenciaResumo.fromJson(json);
    await local.salvarConferencia(
      conferenciaId: widget.conferenciaId,
      conferencia: conf,
    );
    final salva = await local.buscarConferencia(widget.conferenciaId);
    if (salva == null)
      throw Exception('Não foi possível salvar a conferência localmente.');
    return _dadosLocais(salva);
  }

  Future<Map<String, dynamic>> _dadosLocais(Map<String, dynamic> conf) async {
    final bruto = await local.listarItens(widget.conferenciaId);
    final itens = bruto.map((e) {
      final m = Map<String, dynamic>.from(e);
      m['contado'] = _int(m['quantidade_contada']);
      m['esperado'] = _int(m['quantidade_esperada']);
      m['id'] = _int(m['id']);
      return m;
    }).toList();
    final nf = itens
        .where((e) => e['origem']?.toString().toUpperCase() == 'NF')
        .toList();
    return {
      'status_conferencia': conf['status_conferencia'],
      'status': conf['status'],
      'versao': conf['versao'],
      'itens': itens,
      'total': nf.length,
      'conferidos': nf.where((e) => _int(e['contado']) > 0).length,
      'divergentes': itens.where((e) => _int(e['divergente']) == 1).length,
    };
  }

  void _focar() {
    if (!mounted || finalizando || aguardandoQuantidade) return;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || finalizando || aguardandoQuantidade) return;

      foco.requestFocus();

      SystemChannels.textInput.invokeMethod<void>('TextInput.hide');
    });
  }

  void _numero(String n) {
    if (ocupado || finalizando) return;

    final controller = aguardandoQuantidade ? quantidade : codigo;

    controller.text += n;

    controller.selection = TextSelection.collapsed(
      offset: controller.text.length,
    );

    if (!aguardandoQuantidade) {
      origem = OrigemEntrada.digitado;
    }

    setState(() {});
  }

  void _apagar() {
    if (ocupado || finalizando) return;

    final controller = aguardandoQuantidade ? quantidade : codigo;

    if (controller.text.isEmpty) return;

    controller.text = controller.text.substring(0, controller.text.length - 1);

    controller.selection = TextSelection.collapsed(
      offset: controller.text.length,
    );

    if (!aguardandoQuantidade) {
      origem = OrigemEntrada.digitado;
    }

    setState(() {});
  }

  void _limpar() {
    if (ocupado || finalizando) return;

    if (aguardandoQuantidade) {
      quantidade.clear();
    } else {
      codigo.clear();
      origem = OrigemEntrada.bipado;
    }

    setState(() {});
  }

  Future<void> _principal() async {
    if (ocupado || finalizando) return;

    // ==========================================================
    // MODO QUANTIDADE
    // ==========================================================

    if (modo == ModoContagem.quantidade) {
      // Já pesquisou o produto?
      // Então o botão agora é GRAVAR.
      if (aguardandoQuantidade) {
        final q = int.tryParse(quantidade.text.trim());

        if (q == null || q <= 0) {
          _msg('Informe uma quantidade válida.', erro: true);
          return;
        }

        await _registrarQuantidade(codigoQuantidadePendente!, q);

        return;
      }

      // Ainda não pesquisou.
      // O botão é BUSCAR.
      final c = codigo.text.trim();

      if (c.isEmpty) {
        _msg('Bipe ou informe o código.', erro: true);
        _focar();
        return;
      }

      await _buscarProdutoParaQuantidade(c);

      return;
    }

    // ==========================================================
    // MODO ITEM A ITEM
    // ==========================================================

    final c = codigo.text.trim();

    if (c.isEmpty) {
      _msg('Bipe ou informe o código.', erro: true);
      _focar();
      return;
    }

    await _registrar(
      c,
      1,
      caixaFechada ? TipoContagem.caixaFechada : TipoContagem.unidade,
    );
  }

  Future<void> _buscarProdutoParaQuantidade(String c) async {
    if (ocupado || finalizando) return;

    final itens = await local.listarItens(widget.conferenciaId);

    Map<String, dynamic>? itemAtual;

    for (final item in itens) {
      if (item['codigo']?.toString().trim() == c.trim()) {
        itemAtual = Map<String, dynamic>.from(item);
        break;
      }
    }

    if (!mounted) return;

    if (itemAtual == null) {
      _msg('Produto não encontrado na conferência.', erro: true);
      return;
    }

    final descricao = itemAtual['descricao']?.toString();

    setState(() {
      codigoQuantidadePendente = c;

      descricaoQuantidadePendente = descricao != null && descricao.isNotEmpty
          ? descricao
          : 'Produto não identificado';

      codigo.clear();
      quantidade.clear();
    });

    // Não queremos mais o foco no campo do código.
    // Agora os números do teclado serão quantidade.
    FocusScope.of(context).unfocus();

    SystemChannels.textInput.invokeMethod<void>('TextInput.hide');
  }

  Future<void> _quantidadeDialog(String c) async {
    quantidade.clear();
    final q = await showDialog<int>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => _QuantidadeDialog(
        codigo: c,
        caixas: caixaFechada,
        controller: quantidade,
        cancelar: () => Navigator.pop(ctx),
        gravar: () {
          final n = int.tryParse(quantidade.text.trim());
          if (n != null && n > 0) Navigator.pop(ctx, n);
        },
      ),
    );
    if (q == null || !mounted) {
      _focar();
      return;
    }
    await _registrarQuantidade(c, q);
  }

  Future<void> _registrarQuantidade(String c, int q) async {
    if (ocupado || finalizando) return;

    setState(() => ocupado = true);

    try {
      final r = await contagem.registrarQuantidade(
        conferenciaId: widget.conferenciaId,
        codigo: c,
        quantidade: q,
        tipoContagem: caixaFechada
            ? TipoContagem.caixaFechada
            : TipoContagem.unidade,
        origem: origem == OrigemEntrada.bipado
            ? 'BIPAGEM_QUANTIDADE'
            : 'DIGITACAO_QUANTIDADE',
      );

      // Busca novamente no SQLite.
      final itens = await local.listarItens(widget.conferenciaId);

      Map<String, dynamic>? itemAtual;

      for (final item in itens) {
        if (item['codigo']?.toString().trim() == c.trim()) {
          itemAtual = Map<String, dynamic>.from(item);
          break;
        }
      }

      if (!mounted) return;

      final descricao = itemAtual?['descricao']?.toString();

      final quantidadeAtual = itemAtual == null
          ? r.quantidadeContada
          : _int(itemAtual['quantidade_contada']);

      setState(() {
        ultimoCodigo = c;

        ultimaDescricao = descricao?.isNotEmpty == true
            ? descricao
            : 'Produto não identificado';

        ultimaQuantidade = quantidadeAtual;

        codigo.clear();
        quantidade.clear();

        codigoQuantidadePendente = null;
        descricaoQuantidadePendente = null;

        origem = OrigemEntrada.bipado;
      });

      SystemSound.play(SystemSoundType.click);
      HapticFeedback.lightImpact();

      _msg(
        caixaFechada
            ? '$c: +${r.quantidadeAdicionada} unidades'
            : '$c: +$q unidades',
      );

      await _atualizar();
    } catch (e) {
      if (mounted) {
        SystemSound.play(SystemSoundType.alert);

        _msg(e.toString().replaceFirst('Exception: ', ''), erro: true);
      }
    } finally {
      if (mounted) {
        setState(() => ocupado = false);
        _focar();
      }
    }
  }

  Future<void> _registrar(String c, int q, TipoContagem tipo) async {
    if (ocupado || finalizando) return;

    setState(() => ocupado = true);

    try {
      final r = await contagem.registrarBipagem(
        conferenciaId: widget.conferenciaId,
        codigo: c,
        tipoContagem: tipo,
      );

      // Busca o item novamente no SQLite para garantir
      // que descrição e quantidade exibidas sejam as atuais.
      final itens = await local.listarItens(widget.conferenciaId);

      Map<String, dynamic>? itemAtual;

      for (final item in itens) {
        if (item['codigo']?.toString().trim() == c.trim()) {
          itemAtual = Map<String, dynamic>.from(item);
          break;
        }
      }

      if (!mounted) return;

      final descricao = itemAtual?['descricao']?.toString();

      final quantidadeAtual = itemAtual == null
          ? r.quantidadeContada
          : _int(itemAtual['quantidade_contada']);

      setState(() {
        ultimoCodigo = c;
        ultimaDescricao = descricao?.isNotEmpty == true
            ? descricao
            : 'Produto não identificado';

        // IMPORTANTE:
        // mostra o acumulado, não somente o acréscimo.
        ultimaQuantidade = quantidadeAtual;

        codigo.clear();
        origem = OrigemEntrada.bipado;
      });

      SystemSound.play(SystemSoundType.click);
      HapticFeedback.lightImpact();

      _msg(
        tipo == TipoContagem.caixaFechada
            ? '$c: +${r.quantidadeAdicionada} unidades'
            : '$c: +1 unidade',
      );

      await _atualizar();
    } catch (e) {
      if (mounted) {
        SystemSound.play(SystemSoundType.alert);

        _msg(e.toString().replaceFirst('Exception: ', ''), erro: true);
      }
    } finally {
      if (mounted) {
        setState(() => ocupado = false);
        _focar();
      }
    }
  }

  Future<void> _atualizar() async {
    final c = await local.buscarConferencia(widget.conferenciaId);
    if (c == null || !mounted) return;
    final d = await _dadosLocais(c);
    if (mounted) setState(() => dadosFuture = Future.value(d));
  }

  void _trocarModo() {
    if (ocupado || finalizando) return;
    setState(() {
      modo = modo == ModoContagem.unidade
          ? ModoContagem.quantidade
          : ModoContagem.unidade;
      codigo.clear();
      quantidade.clear();
      origem = OrigemEntrada.bipado;
    });
    _focar();
  }

  void _trocarCaixa() {
    if (ocupado || finalizando) return;
    setState(() {
      caixaFechada = !caixaFechada;
      codigo.clear();
      quantidade.clear();
      origem = OrigemEntrada.bipado;
    });
    _focar();
  }

  Future<void> _volume() async {
    final c = TextEditingController();
    final v = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => _NumeroDialog(
        titulo: 'Número do volume',
        hint: volume,
        controller: c,
        confirmarTexto: 'OK',
        cancelar: () => Navigator.pop(ctx),
        confirmar: () => c.text.isNotEmpty ? Navigator.pop(ctx, c.text) : null,
      ),
    );
    c.dispose();
    if (v != null && mounted) {
      final n = int.tryParse(v);
      setState(() => volume = n == null ? v : n.toString().padLeft(4, '0'));
      _focar();
    }
  }

  Future<void> _pesquisa() async {
    if (ocupado || finalizando) return;
    final c = TextEditingController();
    final v = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => _NumeroDialog(
        titulo: 'Pesquisar produto',
        hint: 'Código',
        controller: c,
        confirmarTexto: 'OK',
        cancelar: () => Navigator.pop(ctx),
        confirmar: () => c.text.isNotEmpty ? Navigator.pop(ctx, c.text) : null,
      ),
    );
    c.dispose();
    if (v == null || !mounted) {
      _focar();
      return;
    }

    final itens = await local.listarItens(widget.conferenciaId);
    Map<String, dynamic>? item;
    for (final e in itens) {
      if (e['codigo']?.toString().trim() == v.trim()) {
        item = Map<String, dynamic>.from(e);
        break;
      }
    }
    if (!mounted) return;
    if (item == null || _int(item['quantidade_contada']) <= 0) {
      _msg('Produto não encontrado ou sem contagem.', erro: true);
      _focar();
      return;
    }
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ManutencaoContagemPage(
          item: item!,
          conferenciaId: widget.conferenciaId,
          usuarioId: auth.usuarioId ?? 0,
        ),
      ),
    );
    if (mounted) {
      await _atualizar();
      _focar();
    }
  }

  Future<void> _finalizar() async {
    if (ocupado || finalizando) return;
    final d = await dadosFuture;
    if (_int(d['conferidos']) < _int(d['total'])) {
      _msg('Ainda existem produtos da NF sem contagem.', erro: true);
      return;
    }
    if (_int(d['divergentes']) > 0) {
      _msg('Não é possível finalizar com divergências.', erro: true);
      return;
    }
    setState(() => finalizando = true);
    try {
      await conferenciaService.fecharConferencia(widget.conferenciaId);
      if (!mounted) return;
      _msg('Conferência finalizada com sucesso.');
      setState(() => dadosFuture = _carregar());
      await dadosFuture;
    } catch (e) {
      if (mounted)
        _msg(e.toString().replaceFirst('Exception: ', ''), erro: true);
    } finally {
      if (mounted) setState(() => finalizando = false);
    }
  }

  void _msg(String text, {bool erro = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(text),
          backgroundColor: erro ? Colors.red.shade700 : null,
          duration: const Duration(seconds: 2),
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Conferência #${widget.conferenciaId}'),
        actions: [
          IconButton(
            onPressed: ocupado || finalizando
                ? null
                : () async {
                    final futuro = _carregar();

                    setState(() {
                      dadosFuture = futuro;
                    });

                    try {
                      await futuro;

                      if (mounted) {
                        _focar();
                      }
                    } catch (e) {
                      if (mounted) {
                        _msg(
                          e.toString().replaceFirst('Exception: ', ''),
                          erro: true,
                        );
                      }
                    }
                  },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: dadosFuture,
        builder: (context, s) {
          if (s.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (s.hasError) {
            return Center(child: Text('Erro: ${s.error}'));
          }
          final d = s.data ?? {};
          final total = _int(d['total']);
          final conferidos = _int(d['conferidos']);
          final divergentes = _int(d['divergentes']);
          final finalizada =
              d['status_conferencia']?.toString().toUpperCase() == 'FINALIZADA';
          final p = total == 0 ? 0.0 : (conferidos / total).clamp(0.0, 1.0);

          return SafeArea(
            child: Column(
              children: [
                _UltimoRegistro(
                  codigo: ultimoCodigo,
                  descricao: ultimaDescricao,
                  quantidade: ultimaQuantidade,
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Column(
                    children: [
                      LinearProgressIndicator(value: p, minHeight: 6),
                      const SizedBox(height: 3),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Itens: $conferidos/$total'),
                          Text(
                            'Div.: $divergentes',
                            style: TextStyle(
                              color: divergentes > 0
                                  ? Colors.red
                                  : Colors.green,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                _Ferramentas(
                  quantidade: modo == ModoContagem.quantidade,
                  caixa: caixaFechada,
                  volume: volume,
                  enabled: !finalizada && !ocupado && !finalizando,
                  onQuantidade: _trocarModo,
                  onCaixa: _trocarCaixa,
                  onVolume: _volume,
                  onPesquisa: _pesquisa,
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(8, 4, 8, 4),
                  child: TextField(
                    controller: aguardandoQuantidade ? quantidade : codigo,

                    focusNode: aguardandoQuantidade ? null : foco,

                    enabled: !finalizada && !ocupado && !finalizando,

                    keyboardType: TextInputType.none,

                    readOnly: aguardandoQuantidade,

                    showCursor: true,

                    onChanged: (_) {
                      if (!aguardandoQuantidade) {
                        origem = OrigemEntrada.digitado;
                      }

                      setState(() {});
                    },

                    decoration: InputDecoration(
                      hintText: aguardandoQuantidade
                          ? 'Quantidade...'
                          : 'Código do item...',
                      filled: true,
                      fillColor: Colors.white,
                      border: const OutlineInputBorder(),
                    ),

                    style: const TextStyle(fontSize: 24),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: SizedBox(
                    width: double.infinity,
                    height: 46,
                    child: ElevatedButton(
                      onPressed: !finalizada && !ocupado && !finalizando
                          ? _principal
                          : null,
                      child: Text(
                        modo == ModoContagem.unidade ? 'BUSCAR' : 'GRAVAR',
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                Expanded(
                  child: _Teclado(
                    enabled: !finalizada && !ocupado && !finalizando,
                    numero: _numero,
                    apagar: _apagar,
                    limpar: _limpar,
                    confirmar: _principal,
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(8, 4, 8, 6),
                  child: SizedBox(
                    width: double.infinity,
                    height: 42,
                    child: ElevatedButton(
                      onPressed: !finalizada && !ocupado && !finalizando
                          ? _finalizar
                          : null,
                      child: Text(
                        finalizada
                            ? 'CONFERÊNCIA FINALIZADA'
                            : 'FINALIZAR CONFERÊNCIA',
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

class _UltimoRegistro extends StatelessWidget {
  final String? codigo;
  final String? descricao;
  final int quantidade;
  const _UltimoRegistro({
    required this.codigo,
    required this.descricao,
    required this.quantidade,
  });
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(8, 6, 8, 4),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          const Icon(Icons.shopping_cart_outlined, size: 30),
          const SizedBox(width: 8),
          Expanded(
            child: codigo == null
                ? const Text(
                    'Aguardando bipagem',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'ÚLTIMO REGISTRO',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        descricao?.isNotEmpty == true
                            ? descricao!
                            : 'Produto não identificado',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        'Cód. $codigo',
                        style: const TextStyle(fontSize: 11),
                      ),
                    ],
                  ),
          ),
          if (codigo != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
              decoration: BoxDecoration(
                color: Colors.red.shade700,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'Qtd: $quantidade',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _Ferramentas extends StatelessWidget {
  final bool quantidade, caixa, enabled;
  final String volume;
  final VoidCallback onQuantidade, onCaixa, onVolume, onPesquisa;
  const _Ferramentas({
    required this.quantidade,
    required this.caixa,
    required this.enabled,
    required this.volume,
    required this.onQuantidade,
    required this.onCaixa,
    required this.onVolume,
    required this.onPesquisa,
  });
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(8, 4, 8, 2),
      decoration: BoxDecoration(
        color: Colors.blue.shade600,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Expanded(
            child: IconButton(
              onPressed: enabled ? onQuantidade : null,
              icon: Icon(
                Icons.push_pin,
                color: quantidade ? Colors.white : Colors.lightGreenAccent,
              ),
            ),
          ),
          Expanded(
            child: Stack(
              children: [
                IconButton(
                  onPressed: enabled ? onVolume : null,
                  icon: const Icon(
                    Icons.shopping_cart_outlined,
                    color: Colors.white,
                  ),
                ),
                Positioned(
                  right: 2,
                  bottom: 0,
                  child: Text(
                    volume,
                    style: const TextStyle(color: Colors.white, fontSize: 8),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: IconButton(
              onPressed: enabled ? onCaixa : null,
              icon: Icon(
                Icons.inventory_2_outlined,
                color: caixa ? Colors.lightGreenAccent : Colors.white,
              ),
            ),
          ),
          Expanded(
            child: IconButton(
              onPressed: enabled ? onPesquisa : null,
              icon: const Icon(Icons.search, color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}

class _Teclado extends StatelessWidget {
  final bool enabled;
  final ValueChanged<String> numero;
  final VoidCallback apagar, limpar, confirmar;
  const _Teclado({
    required this.enabled,
    required this.numero,
    required this.apagar,
    required this.limpar,
    required this.confirmar,
  });
  @override
  Widget build(BuildContext context) {
    const t = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'C', '0', '⌫'];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: GridView.builder(
        physics: const NeverScrollableScrollPhysics(),
        itemCount: t.length,
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3,
          crossAxisSpacing: 6,
          mainAxisSpacing: 6,
          childAspectRatio: 2.15,
        ),
        itemBuilder: (context, i) {
          final k = t[i];
          return ElevatedButton(
            onPressed: !enabled
                ? null
                : k == 'C'
                ? limpar
                : k == '⌫'
                ? apagar
                : () => numero(k),
            child: Text(
              k,
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
          );
        },
      ),
    );
  }
}

class _NumeroDialog extends StatefulWidget {
  final String titulo, hint, confirmarTexto;
  final TextEditingController controller;
  final VoidCallback cancelar, confirmar;
  const _NumeroDialog({
    required this.titulo,
    required this.hint,
    required this.controller,
    required this.confirmarTexto,
    required this.cancelar,
    required this.confirmar,
  });
  @override
  State<_NumeroDialog> createState() => _NumeroDialogState();
}

class _NumeroDialogState extends State<_NumeroDialog> {
  void n(String x) {
    widget.controller.text += x;
    setState(() {});
  }

  void back() {
    if (widget.controller.text.isNotEmpty) {
      widget.controller.text = widget.controller.text.substring(
        0,
        widget.controller.text.length - 1,
      );
      setState(() {});
    }
  }

  void clear() {
    widget.controller.clear();
    setState(() {});
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(widget.titulo),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        TextField(
          controller: widget.controller,
          readOnly: true,
          keyboardType: TextInputType.none,
          textAlign: TextAlign.center,
          decoration: InputDecoration(
            hintText: widget.hint,
            border: const OutlineInputBorder(),
          ),
          style: const TextStyle(fontSize: 25, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        _DialogKeyboard(
          numero: n,
          apagar: back,
          limpar: clear,
          confirmar: widget.confirmar,
        ),
      ],
    ),
    actions: [
      TextButton(onPressed: widget.cancelar, child: const Text('CANCELAR')),
      ElevatedButton(
        onPressed: widget.confirmar,
        child: Text(widget.confirmarTexto),
      ),
    ],
  );
}

class _QuantidadeDialog extends StatefulWidget {
  final String codigo;
  final bool caixas;
  final TextEditingController controller;
  final VoidCallback cancelar, gravar;
  const _QuantidadeDialog({
    required this.codigo,
    required this.caixas,
    required this.controller,
    required this.cancelar,
    required this.gravar,
  });
  @override
  State<_QuantidadeDialog> createState() => _QuantidadeDialogState();
}

class _QuantidadeDialogState extends State<_QuantidadeDialog> {
  void n(String x) {
    widget.controller.text += x;
    setState(() {});
  }

  void back() {
    if (widget.controller.text.isNotEmpty) {
      widget.controller.text = widget.controller.text.substring(
        0,
        widget.controller.text.length - 1,
      );
      setState(() {});
    }
  }

  void clear() {
    widget.controller.clear();
    setState(() {});
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(widget.caixas ? 'Quantidade de caixas' : 'Quantidade'),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Código: ${widget.codigo}',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: widget.controller,
          readOnly: true,
          keyboardType: TextInputType.none,
          textAlign: TextAlign.center,
          decoration: const InputDecoration(
            hintText: 'Quantidade',
            border: OutlineInputBorder(),
          ),
          style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        _DialogKeyboard(
          numero: n,
          apagar: back,
          limpar: clear,
          confirmar: widget.gravar,
        ),
      ],
    ),
    actions: [
      TextButton(onPressed: widget.cancelar, child: const Text('CANCELAR')),
      ElevatedButton(onPressed: widget.gravar, child: const Text('GRAVAR')),
    ],
  );
}

class _DialogKeyboard extends StatelessWidget {
  final ValueChanged<String> numero;
  final VoidCallback apagar, limpar, confirmar;
  const _DialogKeyboard({
    required this.numero,
    required this.apagar,
    required this.limpar,
    required this.confirmar,
  });
  @override
  Widget build(BuildContext context) {
    const t = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'C', '0', '⌫'];
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: t.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        crossAxisSpacing: 5,
        mainAxisSpacing: 5,
        childAspectRatio: 1.7,
      ),
      itemBuilder: (context, i) {
        final k = t[i];
        return ElevatedButton(
          onPressed: k == 'C'
              ? limpar
              : k == '⌫'
              ? apagar
              : () => numero(k),
          child: Text(
            k,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
        );
      },
    );
  }
}

class ManutencaoContagemPage extends StatefulWidget {
  final Map<String, dynamic> item;
  final int conferenciaId, usuarioId;
  const ManutencaoContagemPage({
    super.key,
    required this.item,
    required this.conferenciaId,
    required this.usuarioId,
  });
  @override
  State<ManutencaoContagemPage> createState() => _ManutencaoContagemPageState();
}

class _ManutencaoContagemPageState extends State<ManutencaoContagemPage> {
  final service = ContagemLocalService();
  int _int(dynamic v) =>
      v is num ? v.toInt() : int.tryParse(v?.toString() ?? '') ?? 0;
  Future<void> _corrigir() async {
    final n = await Navigator.push<int>(
      context,
      MaterialPageRoute(
        builder: (_) => CorrecaoContagemPage(item: widget.item),
      ),
    );
    if (n == null || !mounted) return;
    try {
      await service.corrigirContagem(
        conferenciaId: widget.conferenciaId,
        itemId: _int(widget.item['id']),
        novaQuantidade: n,
        usuarioId: widget.usuarioId,
        motivo: 'Correção manual pelo conferente.',
      );
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
        );
    }
  }

  Future<void> _zerar() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Zerar contagem'),
        content: Text('Deseja zerar ${widget.item['codigo']}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('CANCELAR'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('ZERAR'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await service.corrigirContagem(
        conferenciaId: widget.conferenciaId,
        itemId: _int(widget.item['id']),
        novaQuantidade: 0,
        usuarioId: widget.usuarioId,
        motivo: 'Exclusão da contagem pelo conferente.',
      );
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
        );
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Manutenção'),
      actions: [
        IconButton(onPressed: _corrigir, icon: const Icon(Icons.edit)),
        IconButton(onPressed: _zerar, icon: const Icon(Icons.delete_outline)),
      ],
    ),
    body: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.item['descricao']?.toString() ?? 'Produto',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text('Código: ${widget.item['codigo']}'),
          const SizedBox(height: 20),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            color: Colors.amber.shade100,
            child: Text(
              'Itens registrados: ${_int(widget.item['quantidade_contada'])}',
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    ),
  );
}

class CorrecaoContagemPage extends StatefulWidget {
  final Map<String, dynamic> item;
  const CorrecaoContagemPage({super.key, required this.item});
  @override
  State<CorrecaoContagemPage> createState() => _CorrecaoContagemPageState();
}

class _CorrecaoContagemPageState extends State<CorrecaoContagemPage> {
  final c = TextEditingController();
  @override
  void dispose() {
    c.dispose();
    super.dispose();
  }

  void n(String x) {
    c.text += x;
    setState(() {});
  }

  void back() {
    if (c.text.isNotEmpty) {
      c.text = c.text.substring(0, c.text.length - 1);
      setState(() {});
    }
  }

  void clear() {
    c.clear();
    setState(() {});
  }

  void gravar() {
    final n = int.tryParse(c.text);
    if (n != null && n >= 0) Navigator.pop(context, n);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.red.shade50,
    appBar: AppBar(
      backgroundColor: Colors.red.shade700,
      foregroundColor: Colors.white,
      title: const Text('Correção de contagem'),
    ),
    body: SafeArea(
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                Text(
                  widget.item['descricao']?.toString() ?? 'Produto',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text('Código: ${widget.item['codigo']}'),
                const SizedBox(height: 10),
                Text(
                  'Itens registrados: ${widget.item['quantidade_contada']}',
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: c,
                  readOnly: true,
                  keyboardType: TextInputType.none,
                  textAlign: TextAlign.center,
                  decoration: const InputDecoration(
                    hintText: 'Nova quantidade...',
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(),
                  ),
                  style: const TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: _DialogKeyboard(
              numero: n,
              apagar: back,
              limpar: clear,
              confirmar: gravar,
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(10),
            child: SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: gravar,
                child: const Text('GRAVAR'),
              ),
            ),
          ),
        ],
      ),
    ),
  );
}
