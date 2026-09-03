import 'package:sqflite/sqflite.dart';

import '../database/app_database.dart';
import '../models/conferencia_resumo.dart';

class ConferenciaLocalService {
  final AppDatabase _database = AppDatabase.instance;

  // ==========================================================
  // SALVAR CONFERÊNCIA COMPLETA NO SQLITE
  // ==========================================================

  Future<void> salvarConferencia({
    required int conferenciaId,
    required ConferenciaResumo conferencia,
  }) async {
    final db = await _database.database;

    await db.transaction((txn) async {
      // ------------------------------------------------------
      // CONFERÊNCIA
      // ------------------------------------------------------

      await txn.insert('conferencias', {
        'id': conferenciaId,
        'status': conferencia.status,
        'status_conferencia': conferencia.statusConferencia,
        'data_download': DateTime.now().toIso8601String(),
        'versao': conferencia.versao,
      }, conflictAlgorithm: ConflictAlgorithm.replace);

      // ------------------------------------------------------
      // ITENS
      // ------------------------------------------------------

      // Antes de inserir novamente, remove os itens locais
      // dessa conferência.
      //
      // Isso evita duplicação caso a conferência seja baixada
      // novamente antes de começar a contagem.
      await txn.delete(
        'itens_conferencia',
        where: 'conferencia_id = ?',
        whereArgs: [conferenciaId],
      );

      for (final item in conferencia.itens) {
        await txn.insert('itens_conferencia', {
          'item_servidor_id': null,
          'conferencia_id': conferenciaId,
          'codigo': item.codigo,
          'descricao': item.descricao,
          'quantidade_esperada': item.xml,

          // A conferência acabou de ser baixada.
          'quantidade_contada': 0,
          'diferenca': -item.xml,

          'divergente': item.divergente ? 1 : 0,
          'divergencia_id': item.divergenciaId,
          'tipo_divergencia': item.tipoDivergencia,

          'justificado': item.justificado ? 1 : 0,
          'justificativa_tipo': item.justificativaTipo,
          'justificativa_descricao': item.justificativaDescricao,

          'status': 'PENDENTE',
          'origem': 'NF',
        });
      }
    });
  }

  // ==========================================================
  // BUSCAR CONFERÊNCIA LOCAL
  // ==========================================================

  Future<Map<String, dynamic>?> buscarConferencia(int conferenciaId) async {
    final db = await _database.database;

    final resultado = await db.query(
      'conferencias',
      where: 'id = ?',
      whereArgs: [conferenciaId],
      limit: 1,
    );

    if (resultado.isEmpty) {
      return null;
    }

    return resultado.first;
  }

  // ==========================================================
  // LISTAR ITENS DA CONFERÊNCIA
  // ==========================================================

  Future<List<Map<String, dynamic>>> listarItens(int conferenciaId) async {
    final db = await _database.database;

    return db.query(
      'itens_conferencia',
      where: 'conferencia_id = ?',
      whereArgs: [conferenciaId],
      orderBy: 'id ASC',
    );
  }

  // ==========================================================
  // BUSCAR ITEM PELO CÓDIGO
  // ==========================================================

  Future<Map<String, dynamic>?> buscarItemPorCodigo({
    required int conferenciaId,
    required String codigo,
  }) async {
    final db = await _database.database;

    final resultado = await db.query(
      'itens_conferencia',
      where: 'conferencia_id = ? AND codigo = ?',
      whereArgs: [conferenciaId, codigo],
      limit: 1,
    );

    if (resultado.isEmpty) {
      return null;
    }

    return resultado.first;
  }

  // ==========================================================
  // VERIFICAR SE A CONFERÊNCIA EXISTE LOCALMENTE
  // ==========================================================

  Future<bool> existeConferencia(int conferenciaId) async {
    final conferencia = await buscarConferencia(conferenciaId);

    return conferencia != null;
  }

  // ==========================================================
  // LIMPAR CONFERÊNCIA LOCAL
  // ==========================================================

  Future<void> removerConferencia(int conferenciaId) async {
    final db = await _database.database;

    await db.transaction((txn) async {
      await txn.delete(
        'contagem_eventos',
        where: 'conferencia_id = ?',
        whereArgs: [conferenciaId],
      );

      await txn.delete(
        'sync_queue',
        where: 'conferencia_id = ?',
        whereArgs: [conferenciaId],
      );

      await txn.delete(
        'itens_conferencia',
        where: 'conferencia_id = ?',
        whereArgs: [conferenciaId],
      );

      await txn.delete(
        'conferencias',
        where: 'id = ?',
        whereArgs: [conferenciaId],
      );
    });
  }
}
