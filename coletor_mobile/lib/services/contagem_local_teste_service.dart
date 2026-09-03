import '../database/app_database.dart';
import 'contagem_local_service.dart';
import 'package:sqflite/sqflite.dart';

class ContagemLocalTesteService {
  final AppDatabase _database = AppDatabase.instance;
  final ContagemLocalService _contagemService = ContagemLocalService();

  Future<void> prepararDados() async {
    final db = await _database.database;

    // Limpa somente os dados da conferência de teste.
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
    // Não cadastramos o código 88888.
    //
  }

  Future<void> executarTeste() async {
    await prepararDados();

    print('========================================');
    print('INICIANDO TESTE DE CONTAGEM LOCAL');
    print('========================================');

    // ------------------------------------------------------
    // TESTE 1
    // Produto da NF - unidade
    // ------------------------------------------------------

    final resultado1 = await _contagemService.registrarBipagem(
      conferenciaId: 999,
      codigo: '75082',
      tipoContagem: TipoContagem.unidade,
    );

    print('TESTE 1 - PRODUTO DA NF');
    print('Código: ${resultado1.codigo}');
    print('Adicionado: ${resultado1.quantidadeAdicionada}');
    print('Contado: ${resultado1.quantidadeContada}');
    print('Esperado: ${resultado1.quantidadeEsperada}');
    print('Diferença: ${resultado1.diferenca}');
    print('');

    // ------------------------------------------------------
    // TESTE 2
    // Mesmo produto - caixa fechada
    // ------------------------------------------------------

    final resultado2 = await _contagemService.registrarBipagem(
      conferenciaId: 999,
      codigo: '75082',
      tipoContagem: TipoContagem.caixaFechada,
    );

    print('TESTE 2 - CAIXA FECHADA');
    print('Código: ${resultado2.codigo}');
    print('Adicionado: ${resultado2.quantidadeAdicionada}');
    print('Contado: ${resultado2.quantidadeContada}');
    print('Esperado: ${resultado2.quantidadeEsperada}');
    print('Diferença: ${resultado2.diferenca}');
    print('');

    // ------------------------------------------------------
    // TESTE 3
    // Produto extra
    // ------------------------------------------------------

    final resultado3 = await _contagemService.registrarBipagem(
      conferenciaId: 999,
      codigo: '99999',
      tipoContagem: TipoContagem.unidade,
    );

    print('TESTE 3 - PRODUTO EXTRA');
    print('Código: ${resultado3.codigo}');
    print('Origem: ${resultado3.tipoResultado}');
    print('Contado: ${resultado3.quantidadeContada}');
    print('Diferença: ${resultado3.diferenca}');
    print('');

    // ------------------------------------------------------
    // TESTE 4
    // Produto desconhecido
    // ------------------------------------------------------

    final resultado4 = await _contagemService.registrarBipagem(
      conferenciaId: 999,
      codigo: '88888',
      tipoContagem: TipoContagem.unidade,
    );

    print('TESTE 4 - PRODUTO DESCONHECIDO');
    print('Código: ${resultado4.codigo}');
    print('Origem: ${resultado4.tipoResultado}');
    print('Contado: ${resultado4.quantidadeContada}');
    print('Diferença: ${resultado4.diferenca}');
    print('');

    // ------------------------------------------------------
    // CONSULTA DOS EVENTOS
    // ------------------------------------------------------

    final eventos = await dbQueryEventos();

    print('========================================');
    print('EVENTOS REGISTRADOS');
    print('========================================');

    for (final evento in eventos) {
      print(evento);
    }

    print('');

    // ------------------------------------------------------
    // CONSULTA DA FILA
    // ------------------------------------------------------

    final fila = await dbQueryFila();

    print('========================================');
    print('FILA DE SINCRONIZAÇÃO');
    print('========================================');

    for (final item in fila) {
      print(item);
    }

    print('');

    // ------------------------------------------------------
    // CONSULTA DOS ITENS
    // ------------------------------------------------------

    final itens = await dbQueryItens();

    print('========================================');
    print('ITENS DA CONFERÊNCIA');
    print('========================================');

    for (final item in itens) {
      print(item);
    }

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
