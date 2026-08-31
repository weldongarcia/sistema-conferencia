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
      version: 2,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  // ==========================================================
  // CRIAÇÃO DO BANCO
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
        status TEXT NOT NULL DEFAULT 'PENDENTE'
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

    await db.insert('configuracoes', {
      'chave': 'versao_produtos',
      'valor': '0',
    });
  }

  // ==========================================================
  // MIGRAÇÃO DA VERSÃO 1 → 2
  // ==========================================================

  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    if (oldVersion < 2) {
      // ------------------------------------------------------
      // CONFERENCIAS
      // ------------------------------------------------------

      await db.execute('''
        ALTER TABLE conferencias
        ADD COLUMN status_conferencia TEXT
      ''');

      await db.execute('''
        ALTER TABLE conferencias
        ADD COLUMN versao INTEGER NOT NULL DEFAULT 0
      ''');

      // ------------------------------------------------------
      // ITENS DA CONFERÊNCIA
      // ------------------------------------------------------

      await db.execute('''
        ALTER TABLE itens_conferencia
        ADD COLUMN item_servidor_id INTEGER
      ''');

      await db.execute('''
        ALTER TABLE itens_conferencia
        ADD COLUMN diferenca INTEGER NOT NULL DEFAULT 0
      ''');

      await db.execute('''
        ALTER TABLE itens_conferencia
        ADD COLUMN divergente INTEGER NOT NULL DEFAULT 0
      ''');

      await db.execute('''
        ALTER TABLE itens_conferencia
        ADD COLUMN divergencia_id INTEGER
      ''');

      await db.execute('''
        ALTER TABLE itens_conferencia
        ADD COLUMN tipo_divergencia TEXT
      ''');

      await db.execute('''
        ALTER TABLE itens_conferencia
        ADD COLUMN justificado INTEGER NOT NULL DEFAULT 0
      ''');

      await db.execute('''
        ALTER TABLE itens_conferencia
        ADD COLUMN justificativa_tipo TEXT
      ''');

      await db.execute('''
        ALTER TABLE itens_conferencia
        ADD COLUMN justificativa_descricao TEXT
      ''');

      // ------------------------------------------------------
      // PRODUTOS
      // ------------------------------------------------------

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

      // ------------------------------------------------------
      // EVENTOS DE CONTAGEM
      // ------------------------------------------------------

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

      // ------------------------------------------------------
      // FILA DE SINCRONIZAÇÃO
      // ------------------------------------------------------

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

      // ------------------------------------------------------
      // CONFIGURAÇÕES
      // ------------------------------------------------------

      await db.execute('''
        CREATE TABLE configuracoes (
          chave TEXT PRIMARY KEY,
          valor TEXT
        )
      ''');

      await db.insert('configuracoes', {
        'chave': 'versao_produtos',
        'valor': '0',
      });
    }
  }
}
