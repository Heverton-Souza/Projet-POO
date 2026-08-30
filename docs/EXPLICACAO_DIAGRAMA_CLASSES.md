# Explicação do Diagrama de Classes — Use Cases e Entities

Este documento explica o diagrama atualizado do backend do **Crônicas do Reino**. Ele foi construído a partir das classes e assinaturas existentes no código Python atual.

Arquivos do diagrama:

- [PDF vetorial](./DIAGRAMA_CLASSES_USE_CASES_ENTITIES.pdf);
- [PNG em alta resolução](./DIAGRAMA_CLASSES_USE_CASES_ENTITIES.png);
- [HTML editável](./DIAGRAMA_CLASSES_USE_CASES_ENTITIES.html).

## 1. Objetivo do diagrama

O diagrama tem dois focos principais:

1. mostrar as entidades que representam os elementos do RPG;
2. mostrar como os três casos de uso principais coordenam essas entidades.

Também foram incluídos o `CharacterBuilder` e as estratégias de ataque porque esses padrões são usados diretamente pelos casos de uso.

Rotas FastAPI, classes de banco de dados, segurança e implementação SQLite não aparecem como classes completas. Elas foram omitidas para evitar que detalhes externos escondam o núcleo solicitado: **use cases e entities**.

## 2. Como ler a notação

### Cores

| Cor | Significado |
|---|---|
| Azul | Casos de uso de `app/use_case` |
| Amarelo | Padrões de projeto de `app/domain/patterns.py` |
| Verde | Entidades de `app/entities` |

### Visibilidade

| Símbolo | Significado |
|---|---|
| `+` | Atributo ou método público |
| `−` | Atributo interno ou helper privado |

Em Python, os helpers privados são identificados por nomes iniciados com `_`, como `_player_turn()` e `_resolve_turn()`.

### Linhas e setas

| Representação | Significado |
|---|---|
| Linha contínua | Associação entre conceitos |
| Linha tracejada com seta | Dependência: uma classe utiliza outra |
| Losango preenchido | Composição: o objeto faz parte do estado de outro |
| Triângulo vazio | Herança ou realização de uma abstração |

### Multiplicidades

| Multiplicidade | Leitura |
|---|---|
| `1` | Exatamente um |
| `0..1` | Zero ou um; relacionamento opcional |
| `0..*` | Zero ou muitos |

## 3. Organização geral

O diagrama é lido de cima para baixo:

1. **Casos de uso:** representam as ações principais executadas pelo sistema.
2. **Padrões de projeto:** ajudam os casos de uso na criação de personagens e na escolha do ataque.
3. **Entidades:** representam os dados e as regras do mundo do RPG.

Essa organização acompanha a Clean Architecture. Os casos de uso coordenam o negócio, mas não executam SQL e não conhecem a implementação do FastAPI.

## 4. Casos de uso

### 4.1 `CreateCharacterUseCase` — UC01

Arquivo: [`app/use_case/create_character.py`](../app/use_case/create_character.py)

Responsabilidade: criar um personagem e vinculá-lo ao jogador autenticado.

Dependências:

- `CharacterRepository`: salva o personagem;
- `CatalogRepository`: busca classe, raça e suas habilidades;
- `EventPublisher`: publica o evento `CHARACTER_CREATED`.

Métodos:

- `__init__(characters, catalog, events)`: recebe as dependências necessárias;
- `execute(user, name, class_id, race_id)`: executa o caso de uso e devolve o personagem em formato de dicionário.

Fluxo:

1. recebe jogador, nome, classe e raça;
2. busca a classe e a raça no catálogo;
3. rejeita referências inexistentes;
4. chama o `CharacterBuilder`;
5. persiste o `Character` pelo repository port;
6. publica `CHARACTER_CREATED`;
7. devolve o personagem criado.

No diagrama, a linha tracejada entre o caso de uso e `CharacterBuilder` significa **dependência**. O caso de uso utiliza o Builder, mas não é parte dele e não herda dele.

### 4.2 `AcceptMissionUseCase` — UC02

Arquivo: [`app/use_case/accept_mission.py`](../app/use_case/accept_mission.py)

Responsabilidade: validar e associar uma missão a um personagem.

Dependências:

- `MissionRepository`: consulta a missão e cria o progresso;
- `CharacterRepository`: carrega e salva o personagem;
- `EventPublisher`: publica `MISSION_ACCEPTED`;
- `AuthorizationPolicy`: participa da verificação de acesso ao personagem.

Métodos:

- `__init__(missions, characters, events, authorization)`: recebe os contratos necessários;
- `execute(user, character_id, mission_id)`: autoriza a ação, valida a missão e cria `MissionProgress`.

Fluxo:

1. carrega o personagem;
2. verifica se o usuário pode acessá-lo;
3. busca a missão;
4. exige que a missão esteja disponível;
5. compara o nível do personagem com o nível mínimo;
6. muda o personagem para `EM_MISSAO`;
7. cria e persiste `MissionProgress`;
8. publica `MISSION_ACCEPTED`.

Por isso, o diagrama mostra dependências desse caso de uso com `Character` e `MissionProgress`.

### 4.3 `PerformCombatUseCase` — UC03

Arquivo: [`app/use_case/perform_combat.py`](../app/use_case/perform_combat.py)

Responsabilidade: iniciar combates, executar turnos e determinar vitória, derrota ou fuga.

Dependências:

- `CombatRepository`: persiste combates e turnos;
- `CharacterRepository`: carrega e salva o personagem;
- `CatalogRepository`: busca inimigos e habilidades;
- `EventPublisher`: publica os acontecimentos do combate;
- `AuthorizationPolicy`: protege o acesso ao personagem;
- `IdGenerator`: gera o identificador do combate;
- `DiceRoller`: fornece o resultado do d100.

Constantes:

- `HIT_THRESHOLD = 70`: valor-base usado na regra de acerto;
- `D100_MAX = 100`: maior valor possível no dado percentual.

Métodos públicos:

- `__init__(...)`: recebe todas as dependências;
- `list(user, character_id)`: lista os combates do personagem;
- `start(user, character_id, enemy_id)`: inicia um combate;
- `execute(user, combat_id, action, skill_id)`: executa uma ação do turno.

Helpers privados:

- `_flee(...)`: encerra o combate como fuga;
- `_player_turn(...)`: calcula a ação do personagem;
- `_resolve_turn(...)`: aplica vitória, contra-ataque ou derrota;
- `_publish_result(...)`: publica o resultado final;
- `_roll_attack(...)`: solicita o d100 e calcula chance e acerto;
- `_attack_hits(...)`: verifica se o ataque acertou;
- `_hit_chance(...)`: calcula a chance percentual de acerto;
- `_character(...)`: carrega e autoriza o personagem.

A regra principal de acerto é:

```text
d100 + agilidade do atacante − agilidade do defensor > 70
```

O caso de uso utiliza a abstração `DiceRoller`. Em produção, o container injeta `D100DiceRoller`. Nos testes, pode ser utilizado um dado com valores fixos. Essa substituição demonstra Dependency Inversion e Liskov Substitution.

## 5. Padrões ligados aos casos de uso

### 5.1 `CharacterBuilder`

Arquivo: [`app/domain/patterns.py`](../app/domain/patterns.py)

O Builder monta um personagem em etapas:

- `owned_by(player_id)`: define o dono;
- `named(name)`: define o nome;
- `from_class(character_class)`: aplica classe, atributos básicos, vida, energia e habilidades;
- `from_race(race)`: aplica modificadores raciais e habilidades;
- `build()`: calcula os valores finais e cria `Character`.

Ele é usado pelo `CreateCharacterUseCase`. A linha `«builds»` aponta para `Character` porque o resultado final do Builder é uma entidade desse tipo.

O Builder também consulta dados de `CharacterClass` e `Race`. Na implementação, esses dados chegam ao Builder como dicionários retornados pelo catálogo; no modelo conceitual, eles representam as entidades classe e raça.

### 5.2 `AttackStrategy`

`AttackStrategy` é a abstração comum para os algoritmos de ataque.

Método definido pelo contrato:

- `execute(attacker, defender)`: calcula o resultado do ataque.

Implementações:

- `BasicAttackStrategy`: calcula o ataque comum usando força, parte da agilidade, equipamento e defesa do inimigo;
- `SkillAttackStrategy`: valida habilidade, nível e energia e calcula o dano físico ou mágico.

Os triângulos apontando para `AttackStrategy` indicam que as duas estratégias respeitam a mesma abstração.

A função `select_attack_strategy()` funciona como uma pequena factory:

- ação `ATAQUE` → `BasicAttackStrategy`;
- ação `HABILIDADE` → `SkillAttackStrategy`;
- outra ação → erro de validação.

O `PerformCombatUseCase` depende dessa seleção, representada pela seta tracejada `«selects»`.

## 6. Entidades

### 6.1 `User`

Representa uma conta do sistema.

Principais atributos:

- identificador, nome e e-mail;
- hash da senha;
- perfil de acesso;
- data de criação.

Método:

- `to_dict()`: converte a entidade para o formato usado nas bordas da aplicação.

Relação principal:

- um `User` pode possuir zero ou muitos `Character`;
- cada `Character` pertence a exatamente um usuário.

### 6.2 `Character`

É a entidade central do domínio. Ela concentra estado e regras importantes do personagem.

Grupos de atributos:

- identidade: `id`, `player_id` e `name`;
- origem: `class_id`, `class_name`, `race_id` e `race_name`;
- evolução: `level`, `experience` e `attribute_points`;
- recursos: `health`, `max_health`, `energy` e `max_energy`;
- estado: `status`, `coins` e `created_at`;
- capacidades: `attributes`, habilidades e bônus de equipamentos.

Métodos:

- `__post_init__()`: normaliza o nome, valida nome, classe e raça e converte o status para o enum correto;
- `receive_damage(amount)`: reduz a vida sem permitir valor negativo e marca derrota quando a vida chega a zero;
- `spend_energy(amount)`: impede o uso de energia indisponível;
- `recover()`: recupera vida e energia de um personagem derrotado;
- `experience_for_next_level()`: calcula a experiência necessária para subir de nível;
- `gain_experience(amount)`: adiciona experiência, processa níveis, entrega pontos e recalcula recursos;
- `distribute_attribute(name, points)`: distribui pontos e atualiza vida ou energia quando necessário;
- `to_dict()`: converte o objeto para o contrato externo.

Relações:

- pertence a um `User`;
- possui uma `CharacterClass` e uma `Race`;
- compõe exatamente um `Attributes`;
- pode possuir várias `Skill`;
- pode ter vários `Item` no inventário;
- compõe progressos de missão;
- compõe registros de combate.

### 6.3 `Attributes`

`Attributes` está marcado como **value object**, e não como entidade independente. Ele não possui identificador próprio e existe como parte de outro objeto.

Atributos armazenados:

- força;
- defesa;
- agilidade;
- inteligência;
- vitalidade;
- carisma.

Métodos:

- `from_dict(values)`: cria atributos validados a partir de um dicionário;
- `add(modifiers)`: cria um novo conjunto somando modificadores;
- `increase(name, points)`: aumenta um atributo específico;
- `to_dict()`: converte os valores para dicionário.

O losango representa composição. `Character`, `CharacterClass` e `Race` possuem seus próprios valores de `Attributes`.

### 6.4 `CharacterClass`

Representa uma classe jogável, como Guerreiro ou Mago.

Contém:

- identidade, nome e descrição;
- atributos básicos;
- vida e energia básicas.

Relações:

- uma classe pode ser utilizada por vários personagens;
- seus atributos são representados por `Attributes`;
- habilidades podem possuir `class_id`, limitando seu uso a uma classe;
- itens podem possuir `required_class_id`.

### 6.5 `Race`

Representa uma raça jogável.

Contém:

- identidade, nome e descrição;
- modificadores raciais em `Attributes`.

Uma raça pode ser usada por vários personagens. Habilidades também podem possuir `race_id`, vinculando-as a uma raça.

### 6.6 `Skill`

Representa uma habilidade de combate.

Contém:

- nome, descrição e tipo;
- custo de energia e dano;
- efeito, recarga e nível mínimo;
- vínculo opcional com classe ou raça.

O método `to_dict()` disponibiliza esses dados para os casos de uso e para a API.

### 6.7 `Item`

Representa um item do jogo.

Contém:

- tipo, descrição, raridade e valor;
- recuperação de vida e energia;
- bônus de ataque e defesa;
- classe exigida e nível mínimo.

Relações:

- personagens podem possuir vários itens pelo inventário;
- missões podem entregar um item opcional;
- inimigos podem entregar um item opcional;
- um item pode exigir uma classe específica.

O inventário é uma associação persistida na tabela `inventory`. Por isso, não aparece como atributo `list[Item]` dentro de `Character`, mas a relação conceitual existe e é mostrada no diagrama.

### 6.8 `Mission`

Representa o modelo global de uma missão.

Contém:

- título, descrição e objetivo;
- nível mínimo, status e meta;
- experiência, moedas e item de recompensa.

Uma mesma missão pode gerar vários `MissionProgress`, um para cada personagem que a aceitou.

### 6.9 `MissionProgress`

Representa a relação individual entre um personagem e uma missão.

Contém:

- identificadores do personagem e da missão;
- estado, progresso e meta;
- datas de aceite e conclusão;
- título e objetivo carregados para apresentação.

Métodos:

- `__post_init__()`: converte o status para `MissionStatus`;
- `update(amount)`: avança o progresso sem ultrapassar a meta;
- `complete()`: exige que a meta tenha sido cumprida;
- `cancel()`: impede cancelamento de uma missão já finalizada;
- `to_dict()`: converte o progresso para o contrato externo.

Relações:

- cada progresso pertence a um personagem;
- cada progresso se refere a uma missão;
- um personagem pode possuir vários progressos;
- uma missão pode aparecer em vários progressos.

### 6.10 `Enemy`

Representa um inimigo disponível no catálogo.

Contém:

- tipo e nível;
- vida, força, defesa e agilidade;
- experiência, moedas e item de recompensa.

Um inimigo pode participar de vários registros de `Combat`, embora cada combate possua um único inimigo.

### 6.11 `Combat`

Representa o estado persistido de um combate.

Contém:

- personagem e inimigo participantes;
- nome e vida atual do inimigo;
- status do combate;
- datas de início e término;
- turnos registrados.

Cada combate pertence a um personagem e se refere a um inimigo. O método `to_dict()` devolve o combate e os turnos no formato utilizado pela API.

## 7. Resumo dos relacionamentos

| Origem | Relação | Destino | Multiplicidade |
|---|---|---|---|
| `User` | possui | `Character` | `1` para `0..*` |
| `CharacterClass` | classifica | `Character` | `1` para `0..*` |
| `Race` | caracteriza | `Character` | `1` para `0..*` |
| `Character` | compõe | `Attributes` | `1` para `1` |
| `CharacterClass` | compõe | `Attributes` | `1` para `1` |
| `Race` | compõe | `Attributes` | `1` para `1` |
| `Character` | possui | `Skill` | `0..*` para `0..*` |
| `Character` | possui no inventário | `Item` | `1` para `0..*` |
| `Character` | compõe | `MissionProgress` | `1` para `0..*` |
| `Mission` | é referenciada por | `MissionProgress` | `1` para `0..*` |
| `Character` | compõe | `Combat` | `1` para `0..*` |
| `Enemy` | participa de | `Combat` | `1` para `0..*` |
| `Mission` | pode recompensar | `Item` | `0..1` |
| `Enemy` | pode recompensar | `Item` | `0..1` |

## 8. Associações conceituais e implementação

Nem toda associação do diagrama aparece no Python como uma referência direta entre objetos.

Por exemplo, `Character` armazena `class_id` e `race_id`, e não objetos completos de `CharacterClass` e `Race`. O repository usa esses identificadores para consultar o SQLite e reconstruir os dados necessários.

Da mesma forma:

- inventário é persistido em uma tabela associativa;
- habilidades são ligadas por classe, raça ou `character_skills`;
- progresso de missão é persistido em `character_missions`;
- combates são consultados por `character_id` e `enemy_id`.

Portanto, o diagrama apresenta o **modelo conceitual do domínio**, enquanto o código utiliza IDs e repository ports para manter baixo acoplamento e simplificar a persistência.

## 9. Por que `to_dict()` aparece em várias entidades?

Internamente, as entidades usam nomes Python em `snake_case`, como `max_health` e `reward_experience`.

A API e o frontend recebem campos em `camelCase`, como `maxHealth` e `rewardExperience`.

O método `to_dict()` cria essa representação externa sem transformar as entidades em classes dependentes de FastAPI ou SQLite.

## 10. Ports citados no diagrama

Os casos de uso mostram dependências com tipos como:

- `CatalogRepository`;
- `CharacterRepository`;
- `MissionRepository`;
- `CombatRepository`;
- `EventPublisher`;
- `IdGenerator`;
- `DiceRoller`.

Esses tipos são contratos definidos em [`app/application/ports.py`](../app/application/ports.py). O diagrama cita seus nomes, mas omite suas implementações para manter o foco.

No código, `SqliteRepository` implementa os repository ports, `UuidGenerator` implementa `IdGenerator`, `D100DiceRoller` implementa `DiceRoller` e `InMemoryEventPublisher` implementa `EventPublisher`.

O [`app/container.py`](../app/container.py) cria essas implementações e as injeta nos casos de uso.

## 11. Como apresentar o diagrama

Uma explicação oral pode seguir esta ordem:

1. **Apresente as três cores.** Azul são ações, amarelo são padrões e verde é o domínio.
2. **Comece pelo `Character`.** Ele é a entidade central e se relaciona com usuário, classe, raça, atributos, habilidades, itens, missões e combates.
3. **Explique UC01.** O caso de uso busca classe e raça, usa o Builder e cria o personagem.
4. **Explique UC02.** O caso de uso valida personagem e missão e cria `MissionProgress`.
5. **Explique UC03.** O caso de uso coordena `Character`, `Enemy`, `Combat`, habilidades e Strategy.
6. **Mostre que use cases dependem de ports.** Eles não executam SQL diretamente.
7. **Finalize com as multiplicidades.** Um usuário possui vários personagens; personagens possuem vários progressos e combates; cada combate tem um inimigo.

Uma frase curta para encerrar:

> O diagrama mostra que as entidades guardam o estado e as regras do RPG, enquanto os casos de uso coordenam essas entidades por meio de contratos, mantendo infraestrutura e interface fora do núcleo do negócio.

## 12. Limite e evolução do diagrama

Este diagrama representa o código atual e seu foco deliberado. Uma versão ainda mais ampla poderia acrescentar:

- serviços auxiliares de `app/application`;
- interfaces completas de `ports.py`;
- `SqliteRepository` e outros adapters;
- modelos Pydantic e rotas FastAPI;
- enums e erros de domínio.

Esses elementos não foram incluídos porque produziriam um diagrama de implementação muito maior e desviariam do foco solicitado em **use cases, entities e seus métodos**.
