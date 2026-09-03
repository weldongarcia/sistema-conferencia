import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import '../lib/database/app_database.dart';
import '../lib/models/conferencia_resumo.dart';
import '../lib/services/conferencia_local_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  test('Teste de download da conferência para SQLite', () async {
    final service = ConferenciaLocalService();

    final conferencia = ConferenciaResumo(
      status: 'aberta',
      statusConferencia: 'PENDENTE',
      totalItens: 2,
      divergentes: 0,
      versao: 1,
      itens: [
        ItemConferencia(
          codigo: '75082',
          descricao: 'FLORATTA CREM DES HID CPO BLUE 75g',
          xml: 3,
          contado: 0,
          diferenca: -3,
          divergente: true,
          divergenciaId: null,
          tipoDivergencia: null,
          justificado: false,
          justificativaTipo: null,
          justificativaDescricao: null,
        ),
        ItemConferencia(
          codigo: '57077',
          descricao: 'FLORATTA SHOWER GEL CPO BLUE V2 75g',
          xml: 5,
          contado: 0,
          diferenca: -5,
          divergente: true,
          divergenciaId: null,
          tipoDivergencia: null,
          justificado: false,
          justificativaTipo: null,
          justificativaDescricao: null,
        ),
      ],
    );

    await service.salvarConferencia(
      conferenciaId: 500,
      conferencia: conferencia,
    );

    final conferenciaLocal = await service.buscarConferencia(500);

    final itens = await service.listarItens(500);

    expect(conferenciaLocal, isNotNull);
    expect(itens.length, 2);

    expect(itens[0]['codigo'], '75082');
    expect(itens[0]['quantidade_esperada'], 3);
    expect(itens[0]['quantidade_contada'], 0);
    expect(itens[0]['origem'], 'NF');

    expect(itens[1]['codigo'], '57077');
    expect(itens[1]['quantidade_esperada'], 5);
    expect(itens[1]['quantidade_contada'], 0);

    // Limpa os dados utilizados pelo teste.
    await service.removerConferencia(500);

    final existe = await service.existeConferencia(500);

    expect(existe, false);

    // Garante que o singleton do banco não fique
    // aberto entre testes.
    final db = await AppDatabase.instance.database;
    await db.close();
  });
}
