import 'package:sqflite/sqflite.dart';

import '../database/app_database.dart';
import 'contagem_local_service.dart';

class ContagemLocalTesteService {
  final AppDatabase _database = AppDatabase.instance;
  final ContagemLocalService _contagemService = ContagemLocalService();

  Future<void> prepararDados() async {
    final db = await _database.database;

    // ------------------------------------------------------
    // LIMPA SOMENTE OS DADOS DA CONFERÊNCIA DE TESTE
    // ------------------------------------------------------

    await db.delete(
      'alteracoes_contagem',
      where: 'conferencia_id = ?',
      whereArgs: [999],
    );

    await db.delete(
      'contagem_eventos',
      where: 'conferencia_id = ?',
      whereArgs: [999],
    );

    await db.delete(
      'sync_queue',
      where: 'conferencia_id = ?',
      whereArgs: [999],
    );

    await db.delete(
      'itens_conferencia',
      where: 'conferencia_id = ?',
      whereArgs: [999],
    );

    await db.delete('conferencias', where: 'id = ?', whereArgs: [999]);

    // ------------------------------------------------------
    // CONFERÊNCIA DE TESTE
    // ------------------------------------------------------

    await db.insert('conferencias', {
      'id': 999,
      'status': 'ABERTA',
      'status_conferencia': 'EM_ANDAMENTO',
      'data_download': DateTime.now().toIso8601String(),
      'versao': 1,
    }, conflictAlgorithm: ConflictAlgorithm.replace);

    // ------------------------------------------------------
    // PRODUTO DA NF
    // ------------------------------------------------------

    await db.insert('itens_conferencia', {
      'item_servidor_id': 1,
      'conferencia_id': 999,
      'codigo': '75082',
      'descricao': 'FLORATTA CREM DES HID CPO BLUE 75g',
      'quantidade_esperada': 3,
      'quantidade_contada': 0,
      'diferenca': -3,
      'divergente': 1,
      'tipo_divergencia': null,
      'status': 'PENDENTE',
      'origem': 'NF',
    });

    // ------------------------------------------------------
    // ITEM PARA TESTE DE CORREÇÃO MANUAL
    // ------------------------------------------------------

    await db.insert('itens_conferencia', {
      'item_servidor_id': 2,
      'conferencia_id': 999,
      'codigo': '22322',
      'descricao': 'PRODUTO TESTE CORREÇÃO',
      'quantidade_esperada': 5,
      'quantidade_contada': 0,
      'diferenca': -5,
      'divergente': 1,
      'tipo_divergencia': null,
      'status': 'PENDENTE',
      'origem': 'NF',
    });

    // ------------------------------------------------------
    // PRODUTO COM QUANTIDADE DE CAIXA
    // ------------------------------------------------------

    await db.insert('produtos', {
      'codigo': '75082',
      'descricao': 'FLORATTA CREM DES HID CPO BLUE 75g',
      'quantidade_caixa': 6,
      'ativo': 1,
      'versao': 1,
      'atualizado_em': DateTime.now().toIso8601String(),
    }, conflictAlgorithm: ConflictAlgorithm.replace);

    // ------------------------------------------------------
    // PRODUTO EXTRA
    // ------------------------------------------------------

    await db.insert('produtos', {
      'codigo': '99999',
      'descricao': 'PRODUTO EXTRA TESTE',
      'quantidade_caixa': 12,
      'ativo': 1,
      'versao': 1,
      'atualizado_em': DateTime.now().toIso8601String(),
    }, conflictAlgorithm: ConflictAlgorithm.replace);

    // ------------------------------------------------------
    // PRODUTO DESCONHECIDO
    // ------------------------------------------------------
    //
    // O código 88888 não é cadastrado.
    //
  }

  Future<void> executarTeste() async {
    await prepararDados();

    final db = await _database.database;

    print('');
    print('========================================');
    print('INICIANDO TESTE DE CONTAGEM LOCAL');
    print('========================================');

    // ------------------------------------------------------
    // TESTE 1
    // PRODUTO DA NF - UNIDADE
    // ------------------------------------------------------

    final resultado1 = await _contagemService.registrarBipagem(
      conferenciaId: 999,
      codigo: '75082',
      tipoContagem: TipoContagem.unidade,
    );

    print('');
    print('TESTE 1 - PRODUTO DA NF');
    print('Código: ${resultado1.codigo}');
    print('Adicionado: ${resultado1.quantidadeAdicionada}');
    print('Contado: ${resultado1.quantidadeContada}');
    print('Esperado: ${resultado1.quantidadeEsperada}');
    print('Diferença: ${resultado1.diferenca}');

    // ------------------------------------------------------
    // TESTE 2
    // MESMO PRODUTO - CAIXA FECHADA
    // ------------------------------------------------------

    final resultado2 = await _contagemService.registrarBipagem(
      conferenciaId: 999,
      codigo: '75082',
      tipoContagem: TipoContagem.caixaFechada,
    );

    print('');
    print('TESTE 2 - CAIXA FECHADA');
    print('Código: ${resultado2.codigo}');
    print('Adicionado: ${resultado2.quantidadeAdicionada}');
    print('Contado: ${resultado2.quantidadeContada}');
    print('Esperado: ${resultado2.quantidadeEsperada}');
    print('Diferença: ${resultado2.diferenca}');

    // ------------------------------------------------------
    // TESTE 3
    // PRODUTO EXTRA
    // ------------------------------------------------------

    final resultado3 = await _contagemService.registrarBipagem(
      conferenciaId: 999,
      codigo: '99999',
      tipoContagem: TipoContagem.unidade,
    );

    print('');
    print('TESTE 3 - PRODUTO EXTRA');
    print('Código: ${resultado3.codigo}');
    print('Origem: ${resultado3.tipoResultado}');
    print('Contado: ${resultado3.quantidadeContada}');
    print('Diferença: ${resultado3.diferenca}');

    // ------------------------------------------------------
    // TESTE 4
    // PRODUTO DESCONHECIDO
    // ------------------------------------------------------

    final resultado4 = await _contagemService.registrarBipagem(
      conferenciaId: 999,
      codigo: '88888',
      tipoContagem: TipoContagem.unidade,
    );

    print('');
    print('TESTE 4 - PRODUTO DESCONHECIDO');
    print('Código: ${resultado4.codigo}');
    print('Origem: ${resultado4.tipoResultado}');
    print('Contado: ${resultado4.quantidadeContada}');
    print('Diferença: ${resultado4.diferenca}');

    // ------------------------------------------------------
    // TESTE 5
    // CORREÇÃO MANUAL
    //
    // Cenário:
    // Esperado = 5
    // Contado = 6
    // Correção = 6 → 5
    // ------------------------------------------------------

    print('');
    print('========================================');
    print('TESTE 5 - CORREÇÃO MANUAL');
    print('========================================');

    // Localiza o item pelo código.
    // Não usamos ID fixo porque o ID é autoincrementável.

    final itemParaCorrecao = await db.query(
      'itens_conferencia',
      where: 'conferencia_id = ? AND codigo = ?',
      whereArgs: [999, '22322'],
      limit: 1,
    );

    if (itemParaCorrecao.isEmpty) {
      throw Exception('Item 22322 não encontrado para teste de correção.');
    }

    final itemIdCorrecao = itemParaCorrecao.first['id'] as int;

    // ------------------------------------------------------
    // SIMULA 6 BIPAGENS
    // ------------------------------------------------------

    for (int i = 0; i < 6; i++) {
      await _contagemService.registrarBipagem(
        conferenciaId: 999,
        codigo: '22322',
        tipoContagem: TipoContagem.unidade,
      );
    }

    final itemAntesCorrecao = await db.query(
      'itens_conferencia',
      where: 'id = ?',
      whereArgs: [itemIdCorrecao],
      limit: 1,
    );

    print('');
    print('ANTES DA CORREÇÃO');
    print('Código: ${itemAntesCorrecao.first['codigo']}');
    print('Esperado: ${itemAntesCorrecao.first['quantidade_esperada']}');
    print('Contado: ${itemAntesCorrecao.first['quantidade_contada']}');
    print('Diferença: ${itemAntesCorrecao.first['diferenca']}');
    print('Divergente: ${itemAntesCorrecao.first['divergente']}');

    // ------------------------------------------------------
    // CORREÇÃO 6 → 5
    // ------------------------------------------------------

    await _contagemService.corrigirContagem(
      conferenciaId: 999,
      itemId: itemIdCorrecao,
      novaQuantidade: 5,
      usuarioId: 123,
      motivo: 'Correção após conferência física',
    );

    // ------------------------------------------------------
    // CONSULTA APÓS A CORREÇÃO
    // ------------------------------------------------------

    final itemDepoisCorrecao = await db.query(
      'itens_conferencia',
      where: 'id = ?',
      whereArgs: [itemIdCorrecao],
      limit: 1,
    );

    print('');
    print('DEPOIS DA CORREÇÃO');
    print('Código: ${itemDepoisCorrecao.first['codigo']}');
    print('Esperado: ${itemDepoisCorrecao.first['quantidade_esperada']}');
    print('Contado: ${itemDepoisCorrecao.first['quantidade_contada']}');
    print('Diferença: ${itemDepoisCorrecao.first['diferenca']}');
    print('Divergente: ${itemDepoisCorrecao.first['divergente']}');
    print(
      'Tipo divergência: '
      '${itemDepoisCorrecao.first['tipo_divergencia']}',
    );

    // ------------------------------------------------------
    // HISTÓRICO DE ALTERAÇÕES
    // ------------------------------------------------------

    final alteracoes = await db.query(
      'alteracoes_contagem',
      where: 'conferencia_id = ? AND item_id = ?',
      whereArgs: [999, itemIdCorrecao],
      orderBy: 'id ASC',
    );

    print('');
    print('========================================');
    print('HISTÓRICO DE ALTERAÇÕES');
    print('========================================');

    for (final alteracao in alteracoes) {
      print(alteracao);
    }

    // ------------------------------------------------------
    // FILA DE CORREÇÃO
    // ------------------------------------------------------

    final filaCorrecao = await db.query(
      'sync_queue',
      where:
          'conferencia_id = ? '
          'AND item_id = ? '
          'AND tipo_operacao = ?',
      whereArgs: [999, itemIdCorrecao, 'CORRECAO_CONTAGEM'],
      orderBy: 'id ASC',
    );

    print('');
    print('========================================');
    print('FILA DE CORREÇÃO');
    print('========================================');

    for (final item in filaCorrecao) {
      print(item);
    }

    // ------------------------------------------------------
    // EVENTOS DO ITEM CORRIGIDO
    // ------------------------------------------------------

    final eventosCorrecao = await db.query(
      'contagem_eventos',
      where: 'conferencia_id = ? AND item_id = ?',
      whereArgs: [999, itemIdCorrecao],
      orderBy: 'id ASC',
    );

    print('');
    print('========================================');
    print('EVENTOS DO ITEM CORRIGIDO');
    print('========================================');

    for (final evento in eventosCorrecao) {
      print(evento);
    }

    // ------------------------------------------------------
    // RESULTADO ESPERADO
    // ------------------------------------------------------

    print('');
    print('========================================');
    print('RESULTADO DO TESTE 5');
    print('========================================');

    print('Esperado: 5');
    print('Contado antes: 6');
    print('Contado depois: 5');
    print('Diferença depois: 0');
    print('Divergente depois: 0');
    print('Alterações registradas: ${alteracoes.length}');
    print('Eventos preservados: ${eventosCorrecao.length}');
    print('Correções na fila: ${filaCorrecao.length}');

    print('');
    print('========================================');
    print('TESTE FINALIZADO');
    print('========================================');
  }

  Future<List<Map<String, dynamic>>> dbQueryEventos() async {
    final db = await _database.database;

    return db.query(
      'contagem_eventos',
      where: 'conferencia_id = ?',
      whereArgs: [999],
      orderBy: 'id ASC',
    );
  }

  Future<List<Map<String, dynamic>>> dbQueryFila() async {
    final db = await _database.database;

    return db.query(
      'sync_queue',
      where: 'conferencia_id = ?',
      whereArgs: [999],
      orderBy: 'id ASC',
    );
  }

  Future<List<Map<String, dynamic>>> dbQueryItens() async {
    final db = await _database.database;

    return db.query(
      'itens_conferencia',
      where: 'conferencia_id = ?',
      whereArgs: [999],
      orderBy: 'id ASC',
    );
  }
}
