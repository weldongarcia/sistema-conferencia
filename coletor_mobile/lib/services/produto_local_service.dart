import 'package:sqflite/sqflite.dart';

import '../database/app_database.dart';
import '../models/produto_local.dart';

class ProdutoLocalService {
  final AppDatabase _database = AppDatabase.instance;

  Future<void> salvarProduto(ProdutoLocal produto) async {
    final db = await _database.database;

    await db.insert(
      'produtos',
      produto.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<ProdutoLocal?> buscarPorCodigo(String codigo) async {
    final db = await _database.database;

    final resultado = await db.query(
      'produtos',
      where: 'codigo = ?',
      whereArgs: [codigo],
      limit: 1,
    );

    if (resultado.isEmpty) {
      return null;
    }

    return ProdutoLocal.fromMap(resultado.first);
  }

  Future<List<ProdutoLocal>> listarProdutos() async {
    final db = await _database.database;

    final resultado = await db.query('produtos', orderBy: 'codigo ASC');

    return resultado.map((map) => ProdutoLocal.fromMap(map)).toList();
  }

  Future<void> removerProduto(String codigo) async {
    final db = await _database.database;

    await db.delete('produtos', where: 'codigo = ?', whereArgs: [codigo]);
  }

  Future<void> limparProdutos() async {
    final db = await _database.database;

    await db.delete('produtos');
  }

  Future<int> quantidadeProdutos() async {
    final db = await _database.database;

    final resultado = await db.rawQuery(
      'SELECT COUNT(*) AS total FROM produtos',
    );

    return Sqflite.firstIntValue(resultado) ?? 0;
  }
}
