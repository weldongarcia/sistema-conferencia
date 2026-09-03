import 'dart:convert';

import 'package:sqflite/sqflite.dart';

import '../database/app_database.dart';

import 'package:coletor_mobile/services/conferencia_local_service.dart';

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

  Future<ResultadoContagem> registrarBipagem({
    required int conferenciaId,
    required String codigo,
    TipoContagem tipoContagem = TipoContagem.unidade,
  }) async {
    final codigoNormalizado = codigo.trim();

    if (codigoNormalizado.isEmpty) {
      throw Exception('Código do produto não informado.');
    }

    final db = await _database.database;

    return await db.transaction((txn) async {
      // ======================================================
      // 1. PROCURA O ITEM NA CONFERÊNCIA
      // ======================================================

      final itens = await txn.query(
        'itens_conferencia',
        where: 'conferencia_id = ? AND codigo = ?',
        whereArgs: [conferenciaId, codigoNormalizado],
        limit: 1,
      );

      Map<String, dynamic>? item;

      if (itens.isNotEmpty) {
        item = Map<String, dynamic>.from(itens.first);
      }

      // ======================================================
      // 2. PROCURA O PRODUTO NO CATÁLOGO LOCAL
      // ======================================================

      final produto = await _buscarProdutoNaTransacao(txn, codigoNormalizado);

      // ======================================================
      // 3. DETERMINA A QUANTIDADE
      // ======================================================

      int quantidadeAdicionada;

      if (tipoContagem == TipoContagem.unidade) {
        quantidadeAdicionada = 1;
      } else {
        if (produto == null) {
          throw Exception(
            'Produto desconhecido. '
            'Não é possível contar como caixa fechada '
            'sem a quantidade da caixa cadastrada.',
          );
        }

        final quantidadeCaixa = produto['quantidade_caixa'];

        if (quantidadeCaixa == null ||
            quantidadeCaixa is! int ||
            quantidadeCaixa <= 0) {
          throw Exception(
            'Quantidade da caixa não cadastrada para o produto '
            '$codigoNormalizado.',
          );
        }

        quantidadeAdicionada = quantidadeCaixa;
      }

      // ======================================================
      // 4. ITEM JÁ EXISTE NA CONFERÊNCIA
      // ======================================================

      if (item != null) {
        return await _atualizarItemExistente(
          txn: txn,
          conferenciaId: conferenciaId,
          item: item,
          codigo: codigoNormalizado,
          quantidadeAdicionada: quantidadeAdicionada,
          tipoContagem: tipoContagem,
          tipoResultado: ResultadoContagemTipo.itemDaNota,
        );
      }

      // ======================================================
      // 5. PRODUTO NÃO ESTÁ NA NOTA
      // ======================================================

      final origem = produto != null ? 'PRODUTO_EXTRA' : 'PRODUTO_DESCONHECIDO';

      final tipoResultado = produto != null
          ? ResultadoContagemTipo.produtoExtra
          : ResultadoContagemTipo.produtoDesconhecido;

      final descricao = produto?['descricao']?.toString();

      // Produto que apareceu durante a conferência.
      final itemId = await txn.insert('itens_conferencia', {
        'item_servidor_id': null,
        'conferencia_id': conferenciaId,
        'codigo': codigoNormalizado,
        'descricao': descricao,
        'quantidade_esperada': 0,
        'quantidade_contada': quantidadeAdicionada,
        'diferenca': quantidadeAdicionada,
        'divergente': 1,
        'divergencia_id': null,
        'tipo_divergencia': produto != null
            ? 'PRODUTO_A_MAIS'
            : 'PRODUTO_DESCONHECIDO',
        'justificado': 0,
        'justificativa_tipo': null,
        'justificativa_descricao': null,
        'status': 'PENDENTE',
        'origem': origem,
      });

      // ======================================================
      // 6. REGISTRA EVENTO
      // ======================================================

      await txn.insert('contagem_eventos', {
        'conferencia_id': conferenciaId,
        'item_id': itemId,
        'codigo': codigoNormalizado,
        'tipo_contagem': tipoContagem.name == 'caixaFechada'
            ? 'CAIXA_FECHADA'
            : 'UNIDADE',
        'quantidade': quantidadeAdicionada,
        'data_hora': DateTime.now().toIso8601String(),
      });

      // ======================================================
      // 7. COLOCA NA FILA DE SINCRONIZAÇÃO
      // ======================================================

      await txn.insert('sync_queue', {
        'conferencia_id': conferenciaId,
        'item_id': itemId,
        'tipo_operacao': 'CONTAGEM',
        'dados': jsonEncode({
          'codigo': codigoNormalizado,
          'quantidade': quantidadeAdicionada,
          'tipo_contagem': tipoContagem.name == 'caixaFechada'
              ? 'CAIXA_FECHADA'
              : 'UNIDADE',
          'origem': origem,
        }),
        'status': 'PENDENTE',
        'tentativas': 0,
        'criado_em': DateTime.now().toIso8601String(),
      });

      return ResultadoContagem(
        itemId: itemId,
        codigo: codigoNormalizado,
        descricao: descricao,
        quantidadeAdicionada: quantidadeAdicionada,
        quantidadeContada: quantidadeAdicionada,
        quantidadeEsperada: 0,
        diferenca: quantidadeAdicionada,
        tipoContagem: tipoContagem,
        tipoResultado: tipoResultado,
        divergente: true,
      );
    });
  }

  Future<ResultadoContagem> _atualizarItemExistente({
    required DatabaseExecutor txn,
    required int conferenciaId,
    required Map<String, dynamic> item,
    required String codigo,
    required int quantidadeAdicionada,
    required TipoContagem tipoContagem,
    required ResultadoContagemTipo tipoResultado,
  }) async {
    final itemId = item['id'] as int;

    final quantidadeAnterior = (item['quantidade_contada'] as int?) ?? 0;

    final quantidadeEsperada = (item['quantidade_esperada'] as int?) ?? 0;

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
      where: 'id = ?',
      whereArgs: [itemId],
    );

    await txn.insert('contagem_eventos', {
      'conferencia_id': conferenciaId,
      'item_id': itemId,
      'codigo': codigo,
      'tipo_contagem': tipoContagem.name == 'caixaFechada'
          ? 'CAIXA_FECHADA'
          : 'UNIDADE',
      'quantidade': quantidadeAdicionada,
      'data_hora': DateTime.now().toIso8601String(),
    });

    await txn.insert('sync_queue', {
      'conferencia_id': conferenciaId,
      'item_id': itemId,
      'tipo_operacao': 'CONTAGEM',
      'dados': jsonEncode({
        'codigo': codigo,
        'quantidade': quantidadeAdicionada,
        'tipo_contagem': tipoContagem.name == 'caixaFechada'
            ? 'CAIXA_FECHADA'
            : 'UNIDADE',
      }),
      'status': 'PENDENTE',
      'tentativas': 0,
      'criado_em': DateTime.now().toIso8601String(),
    });

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

    if (resultado.isEmpty) {
      return null;
    }

    return Map<String, dynamic>.from(resultado.first);
  }
}
