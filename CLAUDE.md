# CLAUDE.md — Sistema de Conferência

## 1. Objetivo

Este arquivo é a referência operacional para desenvolvimento do Sistema de Conferência.

O código existente é a fonte de verdade da implementação atual. Não inventar arquitetura, endpoints, tabelas, telas ou regras. Antes de uma mudança estrutural, inspecionar o código relacionado e avaliar impacto nas outras camadas.

## 2. Visão geral

O repositório contém três aplicações:

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL e JWT.
- **Coletor Mobile:** Flutter/Dart, SQLite local, operação offline e sincronização.
- **Painel Web:** Next.js, React, TypeScript e Tailwind CSS.

O sistema atende operações de conferência de estoque, inventário, auditoria e está evoluindo para separação e transferência entre lojas.

## 3. Estrutura atual

```text
/
├── backend/
├── coletor_mobile/
├── painel-conferencia/
├── postman/
├── .postman/
├── produtos_transferencia.csv
├── requirements.txt
└── w__anotacoes
```

Não tratar automaticamente arquivos de anotação ou dados de teste como parte da arquitetura.

## 4. Backend

### Stack

- Python
- FastAPI
- SQLAlchemy 2
- PostgreSQL via psycopg2-binary
- Pydantic
- Uvicorn
- JWT
- bcrypt/passlib no código de autenticação

Entry point:

```text
backend/app/main.py
```

Áreas:

- `core/` — perfis, permissões, segurança e status.
- `database/` — conexão/base.
- `enums/` — enums de conferência.
- `models/` — modelos SQLAlchemy.
- `routes/` — endpoints HTTP.
- `schemas/` — contratos de entrada/saída.
- `services/` — regras de negócio.
- `utils/` — utilitários, incluindo normalização de códigos.

Não mover lógica de negócio arbitrariamente para routes.

## 5. Modelos principais

Existem modelos para:

- `usuarios`
- `conferencias`
- `conferencia_historico`
- `notas_fiscais`
- `itens_nf`
- `contagens`
- `contagem_historico`
- `divergencias`
- `produtos`
- `volumes`
- `irregularidades`

Antes de alterar um model, localizar services, routes, schemas, painel e coletor que dependam dele.

## 6. Perfis e autorização

Perfis definidos no domínio incluem:

- `CONFERENTE`
- `AUDITOR`

Existe também estrutura de permissões para `admin`, `conferente` e `auditor`.

Usuário possui username, senha/hash, perfil e `estabelecimento_id`.

O conferente deve ser isolado ao estabelecimento ao qual está vinculado. O auditor possui visão mais ampla das conferências.

Autorização deve existir no backend. Esconder botão no frontend é apenas UX.

## 7. Autenticação

O sistema usa JWT Bearer. O token contém usuário, perfil e expiração.

Regras:

- nunca colocar segredo JWT no frontend;
- nunca colocar senha real no código;
- nunca registrar tokens ou senhas em logs;
- nunca commitar segredos;
- não criar autenticação paralela sem necessidade;
- mudanças de autenticação devem considerar backend, web e mobile.

### Dívida técnica conhecida

`backend/app/core/security.py` possui `SECRET_KEY` definida diretamente no código.

Tratar isso como dívida técnica. Migrar para variável de ambiente sem expor o segredo.

Também verificar se todas as dependências importadas pelo backend estão declaradas em `backend/requirements.txt`.

## 8. Estados da conferência

A entidade `Conferencia` possui, entre outros:

- `id`
- `estabelecimento_id`
- `usuario_id`
- `quantidade_reaberturas`
- `versao`
- `status`
- `data_inicio`

Estados importantes incluem:

- `RASCUNHO`
- `REABERTA`
- `FINALIZADA`
- `APROVADA`
- `REPROVADA`

Consultar `backend/app/enums/conferencia_enums.py` antes de alterar transições.

## 9. Fluxo de conferência

Fluxo atual:

1. Criar conferência.
2. Importar XML da NF-e.
3. Consolidar produtos da NF por código.
4. Realizar contagens.
5. Contagens podem ocorrer no coletor offline.
6. Sincronizar com backend.
7. Calcular divergências.
8. Justificar divergências quando necessário.
9. Finalizar.
10. Auditor analisar.
11. Aprovar ou reprovar conforme regras.
12. Reabrir quando permitido, mediante motivo.
13. Reabertura cria nova versão e preserva histórico.

Não alterar esse fluxo sem avaliar auditoria e rastreabilidade.

## 10. NF-e

`backend/app/services/nfe_service.py` processa XML de NF-e.

Regras atuais:

- validar conferência e status;
- impedir segunda nota na mesma conferência;
- validar XML e chave de acesso;
- impedir NF duplicada;
- extrair número da NF;
- extrair produtos;
- normalizar códigos;
- consolidar linhas repetidas do mesmo produto;
- salvar itens consolidados.

Não remover a consolidação por código.

## 11. Contagens

Contagem representa quantidade de um código dentro da conferência.

O fluxo de sincronização trabalha com snapshot. Ausência no snapshot equivale a quantidade zero.

No cálculo de divergências, contagem 0 equivale a ausência de contagem.

Existe `ContagemHistorico` para rastreabilidade.

Não criar eventos artificiais `0 -> 0`.

## 12. Divergências

`Divergencia` registra diferenças entre esperado e contado.

Inclui:

- código;
- XML/esperado;
- contado;
- diferença;
- tipo;
- origem;
- versão;
- justificativa.

Tipos existentes incluem:

- quantidade menor;
- quantidade maior;
- produto a mais;
- produto não encontrado.

### Regra crítica

Divergências são associadas à versão da conferência.

Não misturar divergências de versões anteriores com a versão atual.

### Cálculo e manutenção (BACKEND-01.1)

Fonte única da regra: `calcular_comparacao` em `backend/app/services/divergencia_service.py`. Não acessa o banco.

| Situação | Resultado |
|---|---|
| Item da NF sem contagem ou com contagem 0 | `PRODUTO_NAO_ENCONTRADO` |
| Item da NF com contagem > 0 e menor que a NF | `QUANTIDADE_MENOR` |
| Item da NF com contagem igual à NF | sem divergência |
| Item da NF com contagem maior que a NF | `QUANTIDADE_MAIOR` |
| Produto fora da NF com contagem > 0 | `PRODUTO_A_MAIS` |
| Produto fora da NF com contagem 0 | sem divergência (não aparece) |

Linhas repetidas do mesmo código na NF e nas contagens são somadas; códigos passam por `normalizar_codigo`.

As divergências gravadas são mantidas somente por `recalcular_divergencias`, chamado nos fluxos de escrita:

- sincronização (`/conferencias/{id}/sincronizar` e `/contagens/sincronizar/{id}`);
- `POST /contagens/`;
- importação de XML;
- reabertura (gera as divergências da nova versão);
- fechamento (recalcula antes de validar pendências).

`recalcular_divergencias`:

- atua somente na versão atual;
- não grava em `FINALIZADA`, `APROVADA` ou `REPROVADA`;
- não faz commit próprio (o fluxo chamador controla a transação).

`GET /conferencia/{id}` é somente leitura: calcula na hora e exibe as divergências gravadas da versão atual. Não criar, atualizar ou remover divergências em operações de leitura.

## 13. Justificativas

Uma divergência pode possuir:

- `justificativa_tipo`
- `justificativa_descricao`

Quando uma divergência muda materialmente, a justificativa anterior pode precisar ser invalidada.

Não preservar automaticamente uma justificativa para uma situação diferente.

Mudança material é definida por `divergencia_corresponde`: XML, contado, diferença, tipo ou origem diferentes do cálculo. O recálculo invalida a justificativa somente nesse caso. O GET exibe `divergencia_id` e justificativa somente quando a divergência gravada corresponde ao cálculo; caso contrário retorna `divergencia_id = null` e `justificado = false`, sem alterar o banco.

## 14. Auditoria e histórico

Operações relevantes devem preservar:

- quem;
- quando;
- conferência;
- versão;
- estado;
- motivo, quando aplicável.

Reabertura incrementa a versão e a quantidade de reaberturas e registra motivo no histórico.

Não apagar histórico para simplificar interface ou correção.

## 15. Coletor Mobile

Diretório:

```text
coletor_mobile/
```

Stack:

- Flutter/Dart
- `sqflite`
- `sqflite_common_ffi`
- `http`
- SQLite local

Estrutura principal:

```text
coletor_mobile/lib/
├── database/
├── models/
├── pages/
├── screens/
└── services/
```

Páginas atuais:

- `conferencia_list_page.dart`
- `conferencia_resumo_page.dart`
- `conferencia_page.dart`

Serviços importantes:

- `api_service.dart`
- `auth_service.dart`
- `conferencia_local_service.dart`
- `contagem_local_service.dart`
- `contagem_service.dart`
- `conferencia_service.dart`
- `produto_local_service.dart`
- `produto_sync_service.dart`

## 16. Offline

Modo offline é requisito central.

O coletor possui banco local e serviços de persistência/sincronização.

### Regra crítica

Uma bipagem não deve depender de uma requisição HTTP.

Não transformar a leitura do scanner em chamada de rede síncrona por item.

## 17. Performance do coletor

Existe problema operacional conhecido de velocidade de bipagem: aproximadamente 1 leitura/s em testes anteriores, enquanto o aplicativo de referência chega a aproximadamente 5 leituras/s.

Performance de bipagem é requisito funcional.

Ao alterar leitura:

- evitar queries desnecessárias;
- evitar rebuilds completos;
- evitar HTTP por bip;
- evitar gravações SQLite excessivas;
- preferir processamento em memória durante sequência de leitura;
- agrupar persistências quando seguro;
- usar índices adequados;
- evitar parsing pesado por leitura;
- evitar logs excessivos;
- medir antes/depois quando possível.

**Nunca sacrificar precisão para ganhar velocidade.**

## 18. Produtos e caixas fechadas

`Produto` possui:

- código;
- descrição;
- `quantidade_caixa`;
- ativo;
- versão;
- `atualizado_em`.

Quantidade por caixa é importante para caixas fechadas.

Contagem normal representa unidade. No modo caixa fechada, uma leitura pode representar a quantidade previamente cadastrada.

Exemplo:

```text
Produto: 87541
Quantidade por caixa: 10

1 leitura de caixa fechada = 10 unidades
```

Preservar a distinção entre bipagem normal e caixa fechada.

## 19. Separação e transferência

O sistema está evoluindo para separação e transferência entre lojas.

Requisitos já definidos:

- múltiplos conferentes podem participar da mesma operação;
- produtos podem ser separados em caixas;
- coletor recebe a lista;
- operação deve poder funcionar offline;
- sincronização deve consolidar quantidades;
- dados fiscais devem permitir consolidação por código;
- exemplo: código `87541` com quantidade `10` em uma linha.

Existem dois cenários:

1. caixa fechada contendo um único produto;
2. caixa fracionada contendo vários produtos.

Não modelar caixa fracionada como se fosse sempre um SKU.

Antes de implementar transferência/separação definitivamente, revisar o domínio e evitar acoplamento indevido ao fluxo de conferência.

## 20. Painel Web

Diretório:

```text
painel-conferencia/
```

Stack atual:

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- ESLint
- lucide-react

Scripts:

```bash
npm run dev
npm run build
npm start
npm run lint
```

Principais áreas:

```text
app/dashboard/
app/dashboard/auditor/
app/dashboard/conferencia/[id]/
app/login/
components/layout/
services/api.ts
```

Há fluxo normal e fluxo de auditoria.

## 21. API do painel

`painel-conferencia/services/api.ts` centraliza chamadas à API.

Operações existentes incluem:

- login;
- usuário atual;
- criar conferência;
- importar XML;
- listar/buscar conferência;
- fechar;
- aprovar;
- reprovar;
- reabrir;
- justificar divergência;
- timeline.

Ao adicionar endpoint ao painel, preferir centralizar a chamada em `services/api.ts`.

## 22. Interface

O painel possui identidade visual própria, com:

- cards;
- bordas discretas;
- tipografia objetiva;
- estados visuais claros;
- responsividade;
- componentes compartilhados.

Não substituir o design por template genérico sem solicitação.

Antes de criar componente novo, verificar se existe componente compartilhado reutilizável.

## 23. Banco de dados

PostgreSQL é o banco principal do backend.

A aplicação atualmente usa:

```python
Base.metadata.create_all(bind=engine)
```

Não assumir existência de Alembic/migrations sem verificar.

Ao modificar tabela:

1. localizar model;
2. localizar services;
3. localizar routes;
4. localizar schemas;
5. localizar painel;
6. localizar coletor;
7. avaliar dados existentes.

## 24. Normalização de códigos

Usar:

```text
backend/app/utils/codigo.py
```

como referência.

Não criar segunda função de normalização sem necessidade.

Alterar normalização é alteração de regra de negócio porque afeta XML, contagens, divergências, produtos e sincronização.

## 25. Regras de desenvolvimento

### Antes de editar

1. identificar módulo;
2. ler implementação atual;
3. localizar consumidores;
4. entender regra de negócio;
5. procurar componente/service reutilizável.

### Durante

- fazer a menor alteração segura;
- preservar comportamento existente;
- evitar reescrever arquivos inteiros;
- não remover código funcional sem motivo;
- não alterar API sem verificar clientes;
- não alterar banco sem verificar dependências.

### Depois

- executar verificações relevantes;
- revisar segurança;
- revisar performance;
- revisar compatibilidade;
- revisar regressões.

## 26. Validação

Backend, quando aplicável:

```bash
python -m pytest
```

Executar em `backend/`, com as dependências de `backend/requirements-dev.txt` (pytest e httpx; não instalar em produção). Os testes ficam em `backend/tests/` e usam SQLite em memória, sem PostgreSQL; o `conftest.py` monta apenas os routers necessários porque `app/main.py` executa `create_all` no PostgreSQL ao ser importado.

Mobile, quando aplicável:

```bash
flutter analyze
flutter test
```

Web:

```bash
npm run lint
npm run build
```

Se uma verificação não puder ser executada, informar explicitamente.

## 27. Segurança

Nunca:

- expor JWT;
- expor senha;
- adicionar segredo ao frontend;
- registrar token em console/log;
- commitar `.env` com credenciais;
- colocar credenciais no README;
- confiar somente em autorização do frontend.

Ao encontrar segredo hardcoded, tratar como dívida técnica e corrigir com variável de ambiente e compatibilidade.

## 28. Compatibilidade

Arquitetura:

```text
             ┌── Painel Web
Backend API ─┤
             └── Coletor Mobile
```

Uma alteração no backend pode quebrar dois clientes.

Antes de alterar request, response, campo, status, autenticação ou endpoint, verificar todos os consumidores.

Preferir evolução compatível da API quando possível.

## 29. Git

Branch principal:

```text
main
```

O histórico recente utiliza mensagens como:

- `feat:`
- `fix:`
- `refactor:`
- `checkpoint`

Preferir commits pequenos e descritivos.

Exemplos:

```text
feat(mobile): otimizar leitura offline
fix(api): corrigir validação de divergência
refactor(web): extrair componente compartilhado
```

Não fazer force push sem solicitação explícita.

## 30. Estado atual conhecido

Commit analisado:

```text
458c248803dc9d2a65f438537cd89fd1f3fcc634
fix(web): remover exposicao de token no login
```

Alterações recentes relevantes:

- correções no fluxo de reprovação;
- correções de autorização;
- correção da coluna esperada;
- remoção de exposição de token no login web;
- checkpoints antes de melhorias;
- preparação e implementação do modo offline;
- armazenamento local da conferência;
- evolução do fluxo de auditoria;
- melhorias de feedback do coletor.

### BACKEND-01.1 — concluído

Integridade das divergências e GET somente leitura:

- recálculo centralizado (`calcular_comparacao` e `recalcular_divergencias`);
- recálculo nos fluxos de escrita (sync, contagens, XML, reabrir, fechar);
- sync corrigido: não altera, move ou apaga divergências de versões anteriores; considera contagens criadas no próprio snapshot; soma linhas repetidas da NF;
- `GET /conferencia/{id}` somente leitura, com contrato HTTP inalterado;
- script de saneamento de divergências legadas (`backend/scripts/recalcular_divergencias.py`);
- testes automatizados em `backend/tests/` cobrindo esses comportamentos.

Script de recálculo legado (executar em `backend/`):

```bash
python -m scripts.recalcular_divergencias                       # dry-run (padrão)
python -m scripts.recalcular_divergencias --apply               # grava
python -m scripts.recalcular_divergencias --conferencia-id 12   # limita (pode repetir)
```

- atua somente em `RASCUNHO` e `REABERTA`; demais status são ignorados;
- dry-run é o padrão e não grava nada; `--apply` é explícito;
- `--apply` grava em uma única transação; erro desfaz tudo;
- idempotente.

O sistema continua em desenvolvimento.

## 31. Dívidas técnicas conhecidas

1. `SECRET_KEY` do JWT está definida diretamente no código.
2. Dependências do backend: `backend/requirements.txt` não declara `python-jose`, `passlib` e `bcrypt`, usados pelo código de autenticação. Revisar o arquivo e garantir que todas as dependências de produção estejam declaradas.
3. O backend usa `create_all`; avaliar futuramente migrations formais.
4. Performance da bipagem offline precisa de medição e otimização.
5. Transferência/separação ainda está em evolução.
6. Caixas fracionadas precisam de modelagem adequada.
7. Estruturas antigas podem coexistir com a atual; não remover sem confirmar uso.

Registradas após o BACKEND-01.1 (não corrigidas):

8. **Regras de estado / auditoria.** `POST /contagens/` e a sincronização aceitam escritas em `APROVADA` e `REPROVADA` (só bloqueiam `FINALIZADA`), permitindo alterar contagens após uma auditoria. O recálculo não grava divergências nesses status, então o GET pode exibir a divergência como não justificada enquanto o banco mantém a justificativa auditada. A solução futura deve bloquear essas escritas conforme as regras de estado. No mesmo tema: `fechar` só bloqueia `FINALIZADA` e a justificativa de divergência só bloqueia `FINALIZADA`.
9. **Fluxo de aprovação.** `aprovar` valida pelas divergências persistidas e não recalcula. Revisar junto com as regras de estado (item 8).
10. **Quantidade fracionada.** `ItemNF.quantidade` é texto e `Contagem`/`Divergencia` usam Integer. A regra de cálculo está centralizada e todos os fluxos usam a mesma comparação (`quantidade_persistida` arredonda meio para par ao gravar e comparar), mas o domínio ainda não representa quantidade fracionada adequadamente.
11. **`DATABASE_URL` / configuração.** `backend/app/database/connection.py` tem a URL do banco com credenciais no código. Externalizar a configuração (ex.: variável de ambiente) sem credenciais acopladas ao código.
12. **Importação de XML / segurança.** `POST /notas/importar-xml` não exige autenticação nem verifica perfil e estabelecimento. Revisar autenticação e isolamento.
13. **Script de recálculo legado.** A primeira execução real deve ser validada no PostgreSQL com dry-run. Recomenda-se janela sem operação para `--apply` (o script não bloqueia conferências contra escritas concorrentes).
14. **Histórico de invalidação de justificativa.** Quando o recálculo invalida ou remove uma justificativa, não é registrado evento em `conferencia_historico` (o texto original permanece no evento `DIVERGENCIA_JUSTIFICADA`). Avaliar evento próprio, considerando o impacto na timeline do painel.
15. **Unicidade de divergência.** Não há restrição única em `(conferencia_id, versao, codigo)` na tabela `divergencias`; o recálculo remove duplicatas da versão atual, mas o banco não as impede.
16. **Envio de contagens pelo coletor.** O coletor ainda não envia contagens ao backend (nem `POST /contagens/` nem sincronização); somente lê a conferência e chama o fechamento.

## 32. O que não fazer

Não:

- reescrever arquitetura inteira sem necessidade;
- trocar FastAPI, Flutter ou Next.js por preferência;
- introduzir novas arquiteturas de estado sem necessidade;
- criar endpoints duplicados;
- criar tabelas duplicadas para resolver problema local;
- remover histórico;
- eliminar modo offline;
- transformar toda bipagem em HTTP;
- alterar regra de divergência sem verificar auditoria;
- alterar status sem verificar transições;
- modificar autenticação sem verificar web e mobile;
- fazer alterações cosméticas em arquivos não relacionados.

## 33. Como trabalhar em uma nova tarefa

1. **Entender:** identificar módulo, regra e clientes afetados.
2. **Investigar:** pesquisar models, services, routes, componentes, API, telas mobile e banco local.
3. **Planejar:** listar arquivos e riscos.
4. **Implementar:** menor mudança segura.
5. **Validar:** executar checks relevantes.
6. **Revisar:** segurança, performance, compatibilidade e regressões.
7. **Git:** revisar diff e criar commit quando solicitado ou apropriado.

## 34. Regra especial do coletor

Prioridade da tela operacional:

1. leitura rápida;
2. feedback imediato;
3. precisão;
4. persistência local confiável;
5. sincronização posterior.

Não transformar tela de bipagem em tela pesada de consulta.

## 35. Regra especial de auditoria

Qualquer ação relevante deve responder:

- quem;
- quando;
- qual conferência;
- qual versão;
- estado;
- motivo, quando aplicável.

## 36. Regra especial de domínio

Se a tarefa envolver transferência, separação, caixas, múltiplos conferentes, inventário, auditoria ou sincronização, mapear o fluxo completo antes de implementar.

Se o modelo atual não suportar a nova regra sem gambiarra, propor extensão de domínio antes de acoplar comportamento incorreto.

## 37. Princípio final

O sistema deve evoluir incrementalmente.

Prioridades gerais:

**correção > rastreabilidade > segurança > performance > simplicidade > estética**

Para o coletor, performance e precisão são simultaneamente críticas.

Para o backend, consistência e autorização são críticas.

Para o painel, clareza e coerência com o backend são críticas.

Quando uma solução rápida conflitar com a preservação correta do domínio, preservar o domínio e explicar o custo.
