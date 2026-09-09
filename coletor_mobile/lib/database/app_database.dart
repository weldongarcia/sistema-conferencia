import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

class AppDatabase {
  static final AppDatabase instance = AppDatabase._internal();

  static Database? _database;

  AppDatabase._internal();

  Future<Database> get database async {
    if (_database != null) {
      return _database!;
    }

    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    final databasesPath = await getDatabasesPath();
    final path = join(databasesPath, 'coletor_mobile.db');

    return await openDatabase(
      path,
      version: 5,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  // ==========================================================
  // CRIAÇÃO INICIAL DO BANCO
  // ==========================================================

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE conferencias (
        id INTEGER PRIMARY KEY,
        status TEXT NOT NULL,
        status_conferencia TEXT,
        data_download TEXT NOT NULL,
        versao INTEGER NOT NULL DEFAULT 0
      )
    ''');

    await db.execute('''
      CREATE TABLE itens_conferencia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_servidor_id INTEGER,
        conferencia_id INTEGER NOT NULL,
        codigo TEXT NOT NULL,
        descricao TEXT,
        quantidade_esperada INTEGER NOT NULL DEFAULT 0,
        quantidade_contada INTEGER NOT NULL DEFAULT 0,
        diferenca INTEGER NOT NULL DEFAULT 0,
        divergente INTEGER NOT NULL DEFAULT 0,
        divergencia_id INTEGER,
        tipo_divergencia TEXT,
        justificado INTEGER NOT NULL DEFAULT 0,
        justificativa_tipo TEXT,
        justificativa_descricao TEXT,
        status TEXT NOT NULL DEFAULT 'PENDENTE',
        origem TEXT NOT NULL DEFAULT 'NF'
      )
    ''');

    await db.execute('''
      CREATE TABLE produtos (
        codigo TEXT PRIMARY KEY,
        descricao TEXT,
        quantidade_caixa INTEGER,
        ativo INTEGER NOT NULL DEFAULT 1,
        versao INTEGER NOT NULL DEFAULT 0,
        atualizado_em TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE contagem_eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conferencia_id INTEGER NOT NULL,
        item_id INTEGER,
        codigo TEXT NOT NULL,
        tipo_contagem TEXT NOT NULL,
        quantidade INTEGER NOT NULL,
        data_hora TEXT NOT NULL
      )
    ''');

    await db.execute('''
      CREATE TABLE sync_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conferencia_id INTEGER,
        item_id INTEGER,
        tipo_operacao TEXT NOT NULL,
        dados TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDENTE',
        tentativas INTEGER NOT NULL DEFAULT 0,
        criado_em TEXT NOT NULL
      )
    ''');

    await db.execute('''
      CREATE TABLE configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE alteracoes_contagem (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conferencia_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        codigo TEXT NOT NULL,
        usuario_id INTEGER,
        quantidade_anterior INTEGER NOT NULL,
        quantidade_nova INTEGER NOT NULL,
        tipo_alteracao TEXT NOT NULL,
        motivo TEXT,
        data_hora TEXT NOT NULL
      )
    ''');

    await db.insert('configuracoes', {
      'chave': 'versao_produtos',
      'valor': '0',
    });
  }

  // ==========================================================
  // MIGRAÇÕES
  // ==========================================================

  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    // ========================================================
    // VERSÃO 1 → 2
    // ========================================================

    if (oldVersion < 2) {
      await _adicionarColunaSeNaoExiste(
        db,
        'conferencias',
        'status_conferencia',
        'TEXT',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'conferencias',
        'versao',
        'INTEGER NOT NULL DEFAULT 0',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'itens_conferencia',
        'item_servidor_id',
        'INTEGER',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'itens_conferencia',
        'diferenca',
        'INTEGER NOT NULL DEFAULT 0',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'itens_conferencia',
        'divergente',
        'INTEGER NOT NULL DEFAULT 0',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'itens_conferencia',
        'divergencia_id',
        'INTEGER',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'itens_conferencia',
        'tipo_divergencia',
        'TEXT',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'itens_conferencia',
        'justificado',
        'INTEGER NOT NULL DEFAULT 0',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'itens_conferencia',
        'justificativa_tipo',
        'TEXT',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'itens_conferencia',
        'justificativa_descricao',
        'TEXT',
      );

      await db.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
          codigo TEXT PRIMARY KEY,
          descricao TEXT,
          quantidade_caixa INTEGER,
          ativo INTEGER NOT NULL DEFAULT 1,
          versao INTEGER NOT NULL DEFAULT 0,
          atualizado_em TEXT
        )
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS contagem_eventos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conferencia_id INTEGER NOT NULL,
          item_id INTEGER,
          codigo TEXT NOT NULL,
          tipo_contagem TEXT NOT NULL DEFAULT 'UNIDADE',
          quantidade INTEGER NOT NULL DEFAULT 1,
          data_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS sync_queue (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conferencia_id INTEGER,
          item_id INTEGER,
          tipo_operacao TEXT NOT NULL,
          dados TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'PENDENTE',
          tentativas INTEGER NOT NULL DEFAULT 0,
          criado_em TEXT NOT NULL
        )
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
          chave TEXT PRIMARY KEY,
          valor TEXT
        )
      ''');

      final configuracao = await db.query(
        'configuracoes',
        where: 'chave = ?',
        whereArgs: ['versao_produtos'],
        limit: 1,
      );

      if (configuracao.isEmpty) {
        await db.insert('configuracoes', {
          'chave': 'versao_produtos',
          'valor': '0',
        });
      }
    }

    // ========================================================
    // VERSÃO 2 → 3
    // ========================================================

    if (oldVersion < 3) {
      await _adicionarColunaSeNaoExiste(
        db,
        'itens_conferencia',
        'origem',
        "TEXT NOT NULL DEFAULT 'NF'",
      );
    }

    // ========================================================
    // VERSÃO 3 → 4
    // ========================================================

    if (oldVersion < 4) {
      await db.execute('''
        CREATE TABLE IF NOT EXISTS alteracoes_contagem (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conferencia_id INTEGER NOT NULL,
          item_id INTEGER NOT NULL,
          codigo TEXT NOT NULL,
          usuario_id INTEGER,
          quantidade_anterior INTEGER NOT NULL,
          quantidade_nova INTEGER NOT NULL,
          tipo_alteracao TEXT NOT NULL,
          motivo TEXT,
          data_hora TEXT NOT NULL
        )
      ''');
    }

    // ========================================================
    // VERSÃO 4 → 5
    //
    // Corrige bancos antigos onde contagem_eventos já existe,
    // mas possui estrutura incompleta.
    // ========================================================

    if (oldVersion < 5) {
      await _adicionarColunaSeNaoExiste(
        db,
        'contagem_eventos',
        'tipo_contagem',
        "TEXT NOT NULL DEFAULT 'UNIDADE'",
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'contagem_eventos',
        'quantidade',
        'INTEGER NOT NULL DEFAULT 1',
      );

      await _adicionarColunaSeNaoExiste(
        db,
        'contagem_eventos',
        'data_hora',
        'TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP',
      );

      // Garante que as tabelas necessárias existam.
      await db.execute('''
        CREATE TABLE IF NOT EXISTS alteracoes_contagem (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conferencia_id INTEGER NOT NULL,
          item_id INTEGER NOT NULL,
          codigo TEXT NOT NULL,
          usuario_id INTEGER,
          quantidade_anterior INTEGER NOT NULL,
          quantidade_nova INTEGER NOT NULL,
          tipo_alteracao TEXT NOT NULL,
          motivo TEXT,
          data_hora TEXT NOT NULL
        )
      ''');
    }
  }

  // ==========================================================
  // AUXILIAR — ADICIONAR COLUNA COM SEGURANÇA
  // ==========================================================

  Future<void> _adicionarColunaSeNaoExiste(
    Database db,
    String tabela,
    String coluna,
    String definicao,
  ) async {
    final colunas = await db.rawQuery('PRAGMA table_info($tabela)');

    final existe = colunas.any(
      (colunaExistente) => colunaExistente['name'] == coluna,
    );

    if (!existe) {
      await db.execute('ALTER TABLE $tabela ADD COLUMN $coluna $definicao');
    }
  }
}
