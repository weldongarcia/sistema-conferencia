import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import '../lib/services/contagem_local_teste_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  sqfliteFfiInit();

  databaseFactory = databaseFactoryFfi;

  test('Teste do motor de contagem local', () async {
    final teste = ContagemLocalTesteService();

    await teste.executarTeste();
  });
}
