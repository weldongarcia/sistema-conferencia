import 'package:sqflite/sqflite.dart';
import '../database/app_database.dart';
import '../models/produto_model.dart';
import 'api_service.dart';
import 'auth_service.dart';

class ProdutoSyncResult {
  final int versaoAnterior, versaoAtual, recebidos, total, ativos, inativos;
  const ProdutoSyncResult({required this.versaoAnterior, required this.versaoAtual,
    required this.recebidos, required this.total, required this.ativos, required this.inativos});
}

class ProdutoSyncService {
  final AppDatabase _database = AppDatabase.instance;
  final ApiService _apiService = ApiService();
  final AuthService _authService = AuthService();
  static const int _limite = 500;

  Future<int> versaoLocal() async {
    final db = await _database.database;
    final rows = await db.query('configuracoes', columns: ['valor'],
      where: 'chave = ?', whereArgs: ['versao_produtos'], limit: 1);
    if (rows.isEmpty) return 0;
    final v = rows.first['valor'];
    return v is num ? v.toInt() : int.tryParse(v?.toString() ?? '') ?? 0;
  }

  Future<ProdutoSyncResult> sincronizar() async {
    final token = _authService.token;
    if (token == null || token.isEmpty) throw Exception('Usuário não autenticado.');

    final anterior = await versaoLocal();
    var offset = 0;
    var versao = anterior;
    var recebidos = 0, total = 0, ativos = 0, inativos = 0;

    while (true) {
      final r = await _apiService.buscarProdutosParaSincronizar(
        token: token, versaoLocal: anterior, offset: offset, limite: _limite);
      total = r.total;
      final db = await _database.database;

      await db.transaction((txn) async {
        for (final p in r.produtos) {
          await txn.insert('produtos', {
            'codigo': p.codigo, 'descricao': p.descricao,
            'quantidade_caixa': p.quantidadeCaixa, 'ativo': p.ativo ? 1 : 0,
            'versao': p.versao, 'atualizado_em': p.atualizadoEm.toIso8601String(),
          }, conflictAlgorithm: ConflictAlgorithm.replace);
        }
      });

      recebidos += r.produtos.length;
      ativos += r.produtos.where((p) => p.ativo).length;
      inativos += r.produtos.where((p) => !p.ativo).length;
      if (r.versao > versao) versao = r.versao;
      if (!r.temMais || r.produtos.isEmpty) break;
      offset += r.produtos.length;
    }

    final db = await _database.database;
    await db.insert('configuracoes', {'chave': 'versao_produtos', 'valor': versao.toString()},
      conflictAlgorithm: ConflictAlgorithm.replace);

    return ProdutoSyncResult(versaoAnterior: anterior, versaoAtual: versao,
      recebidos: recebidos, total: total, ativos: ativos, inativos: inativos);
  }
}
