# Arquitetura e decisões de projeto

## Contexto

A implementação deriva dos requisitos e dos casos de uso **Criar Personagem**, **Aceitar Missão** e **Realizar Combate** do PDF. O backend também cobre contas, habilidades, inventário, evolução, histórico e administração por Mestre/Administrador.

Missões globais são modelos cadastrados pelo Mestre. O progresso fica separado por personagem em `character_missions`, permitindo que vários jogadores aceitem a mesma missão.

## Diagrama de classes atualizado

O novo diagrama com foco nas entidades, nos três casos de uso e em seus métodos está disponível em [PDF](./DIAGRAMA_CLASSES_USE_CASES_ENTITIES.pdf), [PNG](./DIAGRAMA_CLASSES_USE_CASES_ENTITIES.png) e [HTML editável](./DIAGRAMA_CLASSES_USE_CASES_ENTITIES.html). A leitura completa de cada classe, método e relacionamento está em [EXPLICACAO_DIAGRAMA_CLASSES.md](./EXPLICACAO_DIAGRAMA_CLASSES.md).

## Escolha da stack Python

Foi adotado FastAPI para a camada HTTP e `sqlite3` da biblioteca padrão para persistência. Não foi utilizado ORM porque o projeto é acadêmico, pequeno e possui consultas diretas simples. A separação por ports permite substituir SQLite ou introduzir SQLAlchemy futuramente sem alterar o domínio.

Também foram evitadas bibliotecas extras para configuração, segurança e testes:

- `dataclasses` para entidades;
- `abc` para interfaces abstratas;
- `hashlib.scrypt` e `secrets` para autenticação;
- `unittest` para testes;
- leitura simples de `.env` na configuração.

## Clean Architecture

### `app/entities`

Contém as classes que representam os elementos do RPG: `User`, `CharacterClass`, `Race`, `Character`, `Skill`, `Item`, `Mission`, `MissionProgress`, `Enemy` e `Combat`. As entidades com regras próprias, como `Character` e `MissionProgress`, protegem seu estado por meio de métodos.

### `app/domain`

Não importa FastAPI nem SQLite. Contém enums, erros, eventos e os padrões de projeto usados pelas entidades e pelos casos de uso.

### `app/application`

Orquestra a aplicação e depende das interfaces de `ports.py`, nunca da implementação SQLite.

Os três casos de uso detalhados no documento possuem classes explícitas em `app/use_case`:

- `CreateCharacterUseCase.execute` — UC01, Criar Personagem;
- `AcceptMissionUseCase.execute` — UC02, Aceitar Missão;
- `PerformCombatUseCase.execute` — UC03, Realizar Combate.

Os serviços de aplicação agrupam somente as operações auxiliares, como consultar personagens, atualizar progresso, administrar inventário e listar histórico.

### `app/infrastructure`

Implementa banco, repositórios, hash de senha, tokens, eventos e dados iniciais.

### `app/interfaces`

Converte HTTP/JSON em chamadas aos casos de uso. O arquivo `api.py` também expõe OpenAPI/Swagger automaticamente em `/docs`.

### Composition root

`app/container.py` cria as implementações, reúne os casos de uso em `UseCases` e injeta todas as dependências. Nenhum caso de uso instancia infraestrutura diretamente.

O d100 segue a mesma inversão de dependência: `PerformCombatUseCase` depende do port `DiceRoller`, enquanto `D100DiceRoller` fornece a aleatoriedade real na infraestrutura. Testes injetam resultados fixos, mantendo o combate determinístico sem introduzir um quarto padrão da lista escolhida.

## Os três padrões escolhidos

### 1. Builder — criação de personagem

Implementação: `CharacterBuilder` em `app/domain/patterns.py`, utilizado por `CreateCharacterUseCase`.

Criar um personagem exige aplicar classe, raça, atributos, habilidades e recursos iniciais. Builder divide essa construção em etapas e impede a entrega de um personagem incompleto. Corresponde ao UC01 e às RN01–RN03.

### 2. Strategy — cálculo de ataques

Implementações: `AttackStrategy`, `BasicAttackStrategy` e `SkillAttackStrategy`.

Ataques comuns e habilidades possuem fórmulas e validações diferentes. Strategy permite adicionar novos ataques sem alterar o fluxo principal do combate, atendendo RF19, RF20, RN06 e RN07.

### 3. Observer — histórico de ações

Implementações: `EventPublisher`, `InMemoryEventPublisher` e o assinante `SqliteRepository.add_history`.

Casos de uso publicam eventos sem conhecer o banco de histórico. Outros assinantes, como notificações e conquistas, podem ser adicionados sem modificar os produtores. Atende diretamente RF28.

Foram escolhidos exatamente esses três padrões da lista solicitada. Os estados são valores protegidos pelas entidades, sem implementar adicionalmente o padrão State.

## SOLID

- **S:** autenticação, personagem, missão, inventário, combate e administração têm serviços próprios.
- **O:** estratégias e observadores aceitam extensões sem alteração dos fluxos existentes.
- **L:** implementações concretas respeitam as classes abstratas definidas nos ports.
- **I:** persistência é dividida em interfaces como `UserRepository`, `MissionRepository` e `CombatRepository`.
- **D:** serviços dependem das abstrações e recebem implementações pelo container.

## Regras materializadas

- nome, classe e raça são obrigatórios;
- jogador acessa somente seus personagens;
- Mestre/Admin gerencia o conteúdo global;
- somente Admin altera perfis;
- missão verifica nível e só conclui com a meta cumprida;
- habilidades verificam nível e energia;
- habilidades de classe e raça são herdadas dinamicamente, inclusive quando cadastradas após a criação do personagem;
- equipamento verifica classe e nível;
- consumível é removido após o uso;
- combate termina por vitória, derrota ou fuga;
- cada ataque soma o d100 à Agilidade do atacante, subtrai a Agilidade do defensor e acerta quando o resultado é maior que 70;
- personagem derrotado pode descansar para recuperar vida, energia e retornar ao estado ativo;
- derrota não entrega recompensa;
- experiência permite evolução e pontos de atributo;
- cada nível concede 5 pontos distribuíveis; Vitalidade amplia a vida máxima e Inteligência amplia a energia máxima;
- ações importantes alimentam o histórico pelo Observer.

## Diagrama de classes

O diagrama existente não foi alterado nesta migração. Quando o código for considerado estável, ele deverá ser redesenhado a partir das entidades, serviços, ports e implementações Python.
