import 'dart:convert';

import 'package:sqflite/sqflite.dart';

import '../database/app_database.dart';

enum TipoContagem { unidade, caixaFechada }

enum ResultadoContagemTipo { itemDaNota, produtoExtra, produtoDesconhecido }

class ResultadoContagem {
  final int itemId;
  final String codigo;
  final String? descricao;
  final int quantidadeAdicionada;
  final int quantidadeContada;
  final int quantidadeEsperada;
  final int diferenca;
  final TipoContagem tipoContagem;
  final ResultadoContagemTipo tipoResultado;
  final bool divergente;

  ResultadoContagem({
    required this.itemId,
    required this.codigo,
    required this.descricao,
    required this.quantidadeAdicionada,
    required this.quantidadeContada,
    required this.quantidadeEsperada,
    required this.diferenca,
    required this.tipoContagem,
    required this.tipoResultado,
    required this.divergente,
  });
}

class ContagemLocalService {
  final AppDatabase _database = AppDatabase.instance;

  int _int(dynamic value) {
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  Future<ResultadoContagem> registrarBipagem({
    required int conferenciaId,
    required String codigo,
    TipoContagem tipoContagem = TipoContagem.unidade,
  }) async {
    return registrarQuantidade(
      conferenciaId: conferenciaId,
      codigo: codigo,
      quantidade: 1,
      tipoContagem: tipoContagem,
      origem: 'BIPAGEM',
    );
  }

  /// Registra uma quantidade informada pelo conferente em UMA transação.
  ///
  /// Unidade:
  ///   quantidade = número de unidades.
  ///
  /// Caixa fechada:
  ///   quantidade = número de caixas.
  ///   quantidade adicionada = caixas * quantidade_caixa.
  ///
  /// Para caixa fechada, cada caixa é preservada como um evento histórico
  /// individual, mas a atualização do item e a fila são feitas em uma única
  /// transação SQLite.
  Future<ResultadoContagem> registrarQuantidade({
    required int conferenciaId,
    required String codigo,
    required int quantidade,
    required TipoContagem tipoContagem,
    String origem = 'QUANTIDADE_INFORMADA',
  }) async {
    final codigoNormalizado = codigo.trim();

    if (codigoNormalizado.isEmpty) {
      throw Exception('Código do produto não informado.');
    }

    if (quantidade <= 0) {
      throw Exception('A quantidade deve ser maior que zero.');
    }

    final db = await _database.database;

    return db.transaction((txn) async {
      final conferencia = await txn.query(
        'conferencias',
        columns: ['id', 'status', 'status_conferencia'],
        where: 'id = ?',
        whereArgs: [conferenciaId],
        limit: 1,
      );

      if (conferencia.isEmpty) {
        throw Exception('Conferência não encontrada.');
      }

      final status =
          conferencia.first['status_conferencia']?.toString().toUpperCase() ??
          '';
      if (status == 'FINALIZADA') {
        throw Exception('A conferência já está finalizada.');
      }

      final itens = await txn.query(
        'itens_conferencia',
        where: 'conferencia_id = ? AND codigo = ?',
        whereArgs: [conferenciaId, codigoNormalizado],
        limit: 1,
      );

      final produto = await _buscarProdutoNaTransacao(txn, codigoNormalizado);

      int quantidadeAdicionada;

      if (tipoContagem == TipoContagem.unidade) {
        quantidadeAdicionada = quantidade;
      } else {
        if (produto == null) {
          throw Exception(
            'Produto desconhecido. Não é possível contar como caixa '
            'fechada sem a quantidade da caixa cadastrada.',
          );
        }

        final quantidadeCaixa = _int(produto['quantidade_caixa']);
        if (quantidadeCaixa <= 0) {
          throw Exception(
            'Quantidade da caixa não cadastrada para o produto '
            '$codigoNormalizado.',
          );
        }

        quantidadeAdicionada = quantidade * quantidadeCaixa;
      }

      final tipoResultado = itens.isNotEmpty
          ? ResultadoContagemTipo.itemDaNota
          : (produto != null
                ? ResultadoContagemTipo.produtoExtra
                : ResultadoContagemTipo.produtoDesconhecido);

      if (itens.isEmpty) {
        return _criarItemNovo(
          txn: txn,
          conferenciaId: conferenciaId,
          codigo: codigoNormalizado,
          produto: produto,
          quantidadeAdicionada: quantidadeAdicionada,
          quantidadeOperacao: quantidade,
          tipoContagem: tipoContagem,
          tipoResultado: tipoResultado,
          origem: origem,
        );
      }

      final item = Map<String, dynamic>.from(itens.first);

      return _atualizarItemExistente(
        txn: txn,
        conferenciaId: conferenciaId,
        item: item,
        codigo: codigoNormalizado,
        quantidadeAdicionada: quantidadeAdicionada,
        quantidadeOperacao: quantidade,
        tipoContagem: tipoContagem,
        tipoResultado: tipoResultado,
        origem: origem,
      );
    });
  }

  Future<ResultadoContagem> _criarItemNovo({
    required DatabaseExecutor txn,
    required int conferenciaId,
    required String codigo,
    required Map<String, dynamic>? produto,
    required int quantidadeAdicionada,
    required int quantidadeOperacao,
    required TipoContagem tipoContagem,
    required ResultadoContagemTipo tipoResultado,
    required String origem,
  }) async {
    final descricao = produto?['descricao']?.toString();

    final itemId = await txn.insert('itens_conferencia', {
      'item_servidor_id': null,
      'conferencia_id': conferenciaId,
      'codigo': codigo,
      'descricao': descricao,
      'quantidade_esperada': 0,
      'quantidade_contada': quantidadeAdicionada,
      'diferenca': quantidadeAdicionada,
      'divergente': 1,
      'divergencia_id': null,
      'tipo_divergencia': tipoResultado == ResultadoContagemTipo.produtoExtra
          ? 'PRODUTO_A_MAIS'
          : 'PRODUTO_DESCONHECIDO',
      'justificado': 0,
      'justificativa_tipo': null,
      'justificativa_descricao': null,
      'status': 'PENDENTE',
      'origem': tipoResultado == ResultadoContagemTipo.produtoExtra
          ? 'PRODUTO_EXTRA'
          : 'PRODUTO_DESCONHECIDO',
    });

    await _registrarEventos(
      txn: txn,
      conferenciaId: conferenciaId,
      itemId: itemId,
      codigo: codigo,
      quantidadeOperacao: quantidadeOperacao,
      tipoContagem: tipoContagem,
    );

    await _registrarFila(
      txn: txn,
      conferenciaId: conferenciaId,
      itemId: itemId,
      codigo: codigo,
      quantidade: quantidadeAdicionada,
      quantidadeOperacao: quantidadeOperacao,
      tipoContagem: tipoContagem,
      origem: origem,
    );

    return ResultadoContagem(
      itemId: itemId,
      codigo: codigo,
      descricao: descricao,
      quantidadeAdicionada: quantidadeAdicionada,
      quantidadeContada: quantidadeAdicionada,
      quantidadeEsperada: 0,
      diferenca: quantidadeAdicionada,
      tipoContagem: tipoContagem,
      tipoResultado: tipoResultado,
      divergente: true,
    );
  }

  Future<ResultadoContagem> _atualizarItemExistente({
    required DatabaseExecutor txn,
    required int conferenciaId,
    required Map<String, dynamic> item,
    required String codigo,
    required int quantidadeAdicionada,
    required int quantidadeOperacao,
    required TipoContagem tipoContagem,
    required ResultadoContagemTipo tipoResultado,
    required String origem,
  }) async {
    final itemId = _int(item['id']);
    final quantidadeAnterior = _int(item['quantidade_contada']);
    final quantidadeEsperada = _int(item['quantidade_esperada']);

    final novaQuantidade = quantidadeAnterior + quantidadeAdicionada;
    final novaDiferenca = novaQuantidade - quantidadeEsperada;
    final divergente = novaDiferenca != 0 ? 1 : 0;

    String? tipoDivergencia;
    if (novaDiferenca > 0) {
      tipoDivergencia = 'QUANTIDADE_MAIOR';
    } else if (novaDiferenca < 0) {
      tipoDivergencia = 'QUANTIDADE_MENOR';
    }

    await txn.update(
      'itens_conferencia',
      {
        'quantidade_contada': novaQuantidade,
        'diferenca': novaDiferenca,
        'divergente': divergente,
        'tipo_divergencia': tipoDivergencia,
      },
      where: 'id = ? AND conferencia_id = ?',
      whereArgs: [itemId, conferenciaId],
    );

    await _registrarEventos(
      txn: txn,
      conferenciaId: conferenciaId,
      itemId: itemId,
      codigo: codigo,
      quantidadeOperacao: quantidadeOperacao,
      tipoContagem: tipoContagem,
    );

    await _registrarFila(
      txn: txn,
      conferenciaId: conferenciaId,
      itemId: itemId,
      codigo: codigo,
      quantidade: quantidadeAdicionada,
      quantidadeOperacao: quantidadeOperacao,
      tipoContagem: tipoContagem,
      origem: origem,
    );

    return ResultadoContagem(
      itemId: itemId,
      codigo: codigo,
      descricao: item['descricao']?.toString(),
      quantidadeAdicionada: quantidadeAdicionada,
      quantidadeContada: novaQuantidade,
      quantidadeEsperada: quantidadeEsperada,
      diferenca: novaDiferenca,
      tipoContagem: tipoContagem,
      tipoResultado: tipoResultado,
      divergente: divergente == 1,
    );
  }

  Future<void> _registrarEventos({
    required DatabaseExecutor txn,
    required int conferenciaId,
    required int itemId,
    required String codigo,
    required int quantidadeOperacao,
    required TipoContagem tipoContagem,
  }) async {
    final agora = DateTime.now().toIso8601String();
    final tipo = tipoContagem == TipoContagem.caixaFechada
        ? 'CAIXA_FECHADA'
        : 'UNIDADE';

    // Uma quantidade informada de caixas representa N caixas físicas.
    // Mantemos um evento por caixa para preservar o histórico.
    if (tipoContagem == TipoContagem.caixaFechada) {
      final produto = await _buscarProdutoNaTransacao(txn, codigo);
      final quantidadeCaixa = _int(produto?['quantidade_caixa']);

      if (quantidadeCaixa <= 0) {
        throw Exception(
          'Quantidade da caixa não cadastrada para o produto $codigo.',
        );
      }

      for (var i = 0; i < quantidadeOperacao; i++) {
        await txn.insert('contagem_eventos', {
          'conferencia_id': conferenciaId,
          'item_id': itemId,
          'codigo': codigo,
          'tipo_contagem': tipo,
          'quantidade': quantidadeCaixa,
          'data_hora': DateTime.now().toIso8601String(),
        });
      }
      return;
    }

    await txn.insert('contagem_eventos', {
      'conferencia_id': conferenciaId,
      'item_id': itemId,
      'codigo': codigo,
      'tipo_contagem': tipo,
      'quantidade': quantidadeOperacao,
      'data_hora': agora,
    });
  }

  Future<void> _registrarFila({
    required DatabaseExecutor txn,
    required int conferenciaId,
    required int itemId,
    required String codigo,
    required int quantidade,
    required int quantidadeOperacao,
    required TipoContagem tipoContagem,
    required String origem,
  }) async {
    await txn.insert('sync_queue', {
      'conferencia_id': conferenciaId,
      'item_id': itemId,
      'tipo_operacao': 'CONTAGEM',
      'dados': jsonEncode({
        'codigo': codigo,
        'quantidade': quantidade,
        'quantidade_operacao': quantidadeOperacao,
        'tipo_contagem': tipoContagem == TipoContagem.caixaFechada
            ? 'CAIXA_FECHADA'
            : 'UNIDADE',
        'origem': origem,
      }),
      'status': 'PENDENTE',
      'tentativas': 0,
      'criado_em': DateTime.now().toIso8601String(),
    });
  }

  Future<Map<String, dynamic>?> _buscarProdutoNaTransacao(
    DatabaseExecutor txn,
    String codigo,
  ) async {
    final resultado = await txn.query(
      'produtos',
      where: 'codigo = ? AND ativo = 1',
      whereArgs: [codigo],
      limit: 1,
    );

    if (resultado.isEmpty) return null;
    return Map<String, dynamic>.from(resultado.first);
  }

  // ==========================================================
  // CORREÇÃO MANUAL
  // ==========================================================

  Future<void> corrigirContagem({
    required int conferenciaId,
    required int itemId,
    required int novaQuantidade,
    required int usuarioId,
    String? motivo,
  }) async {
    if (novaQuantidade < 0) {
      throw Exception('A quantidade não pode ser negativa.');
    }

    final db = await _database.database;

    await db.transaction((txn) async {
      final resultado = await txn.query(
        'itens_conferencia',
        where: 'id = ? AND conferencia_id = ?',
        whereArgs: [itemId, conferenciaId],
        limit: 1,
      );

      if (resultado.isEmpty) {
        throw Exception('Item não encontrado na conferência.');
      }

      final item = Map<String, dynamic>.from(resultado.first);
      final quantidadeAnterior = _int(item['quantidade_contada']);
      final quantidadeEsperada = _int(item['quantidade_esperada']);

      if (quantidadeAnterior == novaQuantidade) {
        throw Exception('A nova quantidade é igual à quantidade atual.');
      }

      final diferenca = novaQuantidade - quantidadeEsperada;
      final divergente = diferenca != 0 ? 1 : 0;

      String? tipoDivergencia;
      if (diferenca > 0) {
        tipoDivergencia = 'QUANTIDADE_MAIOR';
      } else if (diferenca < 0) {
        tipoDivergencia = 'QUANTIDADE_MENOR';
      }

      await txn.update(
        'itens_conferencia',
        {
          'quantidade_contada': novaQuantidade,
          'diferenca': diferenca,
          'divergente': divergente,
          'tipo_divergencia': tipoDivergencia,
        },
        where: 'id = ? AND conferencia_id = ?',
        whereArgs: [itemId, conferenciaId],
      );

      await txn.insert('alteracoes_contagem', {
        'conferencia_id': conferenciaId,
        'item_id': itemId,
        'codigo': item['codigo']?.toString() ?? '',
        'usuario_id': usuarioId,
        'quantidade_anterior': quantidadeAnterior,
        'quantidade_nova': novaQuantidade,
        'tipo_alteracao': 'CORRECAO_MANUAL',
        'motivo': motivo,
        'data_hora': DateTime.now().toIso8601String(),
      });

      await txn.insert('sync_queue', {
        'conferencia_id': conferenciaId,
        'item_id': itemId,
        'tipo_operacao': 'CORRECAO_CONTAGEM',
        'dados': jsonEncode({
          'codigo': item['codigo']?.toString() ?? '',
          'quantidade_anterior': quantidadeAnterior,
          'quantidade_nova': novaQuantidade,
          'usuario_id': usuarioId,
          'tipo_alteracao': 'CORRECAO_MANUAL',
          'motivo': motivo,
        }),
        'status': 'PENDENTE',
        'tentativas': 0,
        'criado_em': DateTime.now().toIso8601String(),
      });
    });
  }
}
