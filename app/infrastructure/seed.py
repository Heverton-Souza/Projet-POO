from datetime import UTC, datetime
from typing import Any

from app.application.ports import IdGenerator, PasswordHasher
from app.domain.enums import UserRole

from .repositories import SqliteRepository


def seed_database(
    repository: SqliteRepository,
    password_hasher: PasswordHasher,
    id_generator: IdGenerator,
    config: Any,
) -> dict[str, Any]:
    """Adiciona um mundo de demonstração sem apagar nem duplicar dados existentes."""
    master = repository.find_user_by_email(config.master_email)
    if not master:
        master = repository.create_user(
            {
                "id": id_generator.generate(),
                "name": config.master_name,
                "email": config.master_email,
                "passwordHash": password_hasher.hash(config.master_password),
                "role": UserRole.ADMIN.value,
                "createdAt": datetime.now(UTC).isoformat(),
            }
        )

    cache: dict[str, dict[str, dict[str, Any]]] = {}

    def ensure(resource: str, data: dict[str, Any]) -> dict[str, Any]:
        key = "title" if resource == "missions" else "name"
        if resource not in cache:
            cache[resource] = {
                str(item[key]).casefold(): item for item in repository.list_catalog(resource)
            }
        normalized_key = str(data[key]).casefold()
        if normalized_key not in cache[resource]:
            cache[resource][normalized_key] = repository.create_catalog(
                resource, data, master["id"]
            )
        return cache[resource][normalized_key]

    classes = {
        data["name"]: ensure("classes", data)
        for data in [
            {
                "name": "Guerreiro",
                "description": "Combatente resistente que protege o grupo e domina armas de curto alcance.",
                "attributes": {"strength": 8, "defense": 7, "agility": 3, "intelligence": 1, "vitality": 7, "charisma": 2},
                "baseHealth": 70,
                "baseEnergy": 20,
            },
            {
                "name": "Mago",
                "description": "Estudioso das artes arcanas, capaz de causar grande dano usando magia.",
                "attributes": {"strength": 2, "defense": 2, "agility": 4, "intelligence": 9, "vitality": 3, "charisma": 5},
                "baseHealth": 45,
                "baseEnergy": 50,
            },
            {
                "name": "Ladino",
                "description": "Especialista em furtividade, velocidade, armadilhas e ataques precisos.",
                "attributes": {"strength": 4, "defense": 3, "agility": 9, "intelligence": 5, "vitality": 3, "charisma": 5},
                "baseHealth": 52,
                "baseEnergy": 35,
            },
            {
                "name": "Clérigo",
                "description": "Guerreiro sagrado que combina proteção, fé e magia divina contra seus inimigos.",
                "attributes": {"strength": 4, "defense": 6, "agility": 2, "intelligence": 7, "vitality": 6, "charisma": 7},
                "baseHealth": 62,
                "baseEnergy": 40,
            },
            {
                "name": "Arqueiro",
                "description": "Atirador disciplinado que vence combates mantendo distância e explorando pontos fracos.",
                "attributes": {"strength": 5, "defense": 3, "agility": 8, "intelligence": 4, "vitality": 4, "charisma": 3},
                "baseHealth": 55,
                "baseEnergy": 34,
            },
            {
                "name": "Bárbaro",
                "description": "Combatente feroz que transforma resistência e fúria em golpes devastadores.",
                "attributes": {"strength": 10, "defense": 4, "agility": 3, "intelligence": 1, "vitality": 9, "charisma": 2},
                "baseHealth": 82,
                "baseEnergy": 24,
            },
        ]
    }

    races = {
        data["name"]: ensure("races", data)
        for data in [
            {
                "name": "Humano",
                "description": "Povo versátil e determinado, presente em todos os reinos e ofícios.",
                "modifiers": {"strength": 1, "defense": 1, "agility": 1, "intelligence": 1, "vitality": 1, "charisma": 2},
            },
            {
                "name": "Elfo",
                "description": "Ser longevo, ágil e naturalmente ligado à magia e às florestas antigas.",
                "modifiers": {"strength": -1, "defense": 0, "agility": 3, "intelligence": 2, "vitality": 0, "charisma": 1},
            },
            {
                "name": "Anão",
                "description": "Povo das montanhas conhecido pela resistência, honra e domínio da forja.",
                "modifiers": {"strength": 2, "defense": 3, "agility": -1, "intelligence": 0, "vitality": 3, "charisma": -1},
            },
            {
                "name": "Orc",
                "description": "Guerreiro de grande força física, criado em clãs que valorizam coragem e lealdade.",
                "modifiers": {"strength": 4, "defense": 1, "agility": 0, "intelligence": -1, "vitality": 2, "charisma": -2},
            },
            {
                "name": "Halfling",
                "description": "Pequeno aventureiro de reflexos rápidos, sorte incomum e espírito comunitário.",
                "modifiers": {"strength": -2, "defense": 1, "agility": 4, "intelligence": 1, "vitality": 1, "charisma": 2},
            },
            {
                "name": "Draconato",
                "description": "Descendente de dragões que carrega escamas resistentes e poder elemental no sangue.",
                "modifiers": {"strength": 3, "defense": 2, "agility": 0, "intelligence": 1, "vitality": 2, "charisma": 0},
            },
        ]
    }

    class_skills = [
        ("Guerreiro", "Golpe Poderoso", "Concentra a força em um único ataque capaz de romper a guarda inimiga.", "FISICA", 5, 12, "Dano físico concentrado.", 1, 1),
        ("Guerreiro", "Investida Implacável", "Avança com o escudo e a arma, atingindo o alvo antes que ele possa reagir.", "FISICA", 9, 20, "Ataque pesado de abertura.", 2, 3),
        ("Mago", "Bola de Fogo", "Lança um projétil flamejante que explode ao alcançar o inimigo.", "MAGICA", 8, 16, "Dano mágico de fogo.", 2, 1),
        ("Mago", "Nevasca Arcana", "Invoca ventos congelantes e fragmentos de gelo sobre o campo de batalha.", "MAGICA", 14, 28, "Dano mágico de gelo.", 3, 4),
        ("Ladino", "Ataque Furtivo", "Explora uma abertura na defesa para realizar um golpe rápido e preciso.", "FISICA", 6, 15, "Dano aumentado por precisão.", 1, 1),
        ("Ladino", "Lâmina Envenenada", "Cobre a arma com um veneno preparado para enfraquecer o adversário.", "FISICA", 10, 22, "Aplica veneno narrativo ao alvo.", 2, 3),
        ("Clérigo", "Luz Sagrada", "Canaliza energia divina em um clarão que fere criaturas hostis.", "MAGICA", 7, 13, "Dano sagrado.", 1, 1),
        ("Clérigo", "Julgamento Divino", "Convoca uma coluna de luz para punir um inimigo considerado indigno.", "MAGICA", 13, 25, "Dano sagrado intenso.", 3, 4),
        ("Arqueiro", "Tiro Preciso", "Respira fundo e dispara contra um ponto vulnerável da armadura inimiga.", "FISICA", 5, 14, "Ignora parte da defesa na narrativa.", 1, 1),
        ("Arqueiro", "Chuva de Flechas", "Dispara várias flechas em arco para cobrir uma grande área do combate.", "FISICA", 11, 23, "Ataque de múltiplos projéteis.", 2, 3),
        ("Bárbaro", "Fúria Selvagem", "Libera a fúria acumulada em um golpe brutal executado sem hesitação.", "FISICA", 6, 17, "Dano movido pela fúria.", 1, 1),
        ("Bárbaro", "Golpe Sísmico", "Esmaga o chão com tanta força que a onda de impacto alcança o inimigo.", "FISICA", 12, 27, "Onda de impacto física.", 3, 4),
    ]
    for class_name, name, description, skill_type, cost, damage, effect, cooldown, level in class_skills:
        ensure(
            "skills",
            {
                "name": name,
                "description": description,
                "type": skill_type,
                "energyCost": cost,
                "damage": damage,
                "effect": effect,
                "cooldown": cooldown,
                "minLevel": level,
                "classId": classes[class_name]["id"],
                "raceId": None,
            },
        )

    racial_skills = [
        ("Humano", "Determinação Humana", "A determinação dos humanos transforma um momento de perigo em um ataque decisivo.", "FISICA", 5, 11),
        ("Elfo", "Rajada Élfica", "Conduz a magia natural em uma rajada veloz de energia esmeralda.", "MAGICA", 6, 13),
        ("Anão", "Martelo Ancestral", "Invoca a memória dos antigos ferreiros para fortalecer um golpe pesado.", "FISICA", 6, 14),
        ("Orc", "Ímpeto Orc", "Ataca com a força explosiva e a coragem cultivadas pelos clãs orcs.", "FISICA", 5, 15),
        ("Halfling", "Pedra Certeira", "Arremessa um pequeno projétil com uma precisão surpreendente.", "FISICA", 4, 10),
        ("Draconato", "Sopro Dracônico", "Expele uma rajada elemental herdada de uma antiga linhagem de dragões.", "MAGICA", 8, 17),
    ]
    for race_name, name, description, skill_type, cost, damage in racial_skills:
        ensure(
            "skills",
            {
                "name": name,
                "description": description,
                "type": skill_type,
                "energyCost": cost,
                "damage": damage,
                "effect": "Habilidade característica da raça.",
                "cooldown": 2,
                "minLevel": 1,
                "classId": None,
                "raceId": races[race_name]["id"],
            },
        )

    item_data = [
        {"name": "Poção de Vida", "type": "POCAO", "description": "Frasco rubro que recupera 25 pontos de vida quando consumido.", "rarity": "COMUM", "value": 15, "effectHealth": 25, "minLevel": 1},
        {"name": "Poção de Mana", "type": "POCAO", "description": "Essência azul que recupera 30 pontos de energia mágica quando consumida.", "rarity": "COMUM", "value": 20, "effectEnergy": 30, "minLevel": 1},
        {"name": "Poção Superior de Vida", "type": "POCAO", "description": "Mistura alquímica concentrada que recupera 60 pontos de vida.", "rarity": "RARO", "value": 55, "effectHealth": 60, "minLevel": 4},
        {"name": "Poção Superior de Mana", "type": "POCAO", "description": "Essência arcana concentrada que recupera 65 pontos de energia.", "rarity": "RARO", "value": 60, "effectEnergy": 65, "minLevel": 4},
        {"name": "Espada de Ferro", "type": "ARMA", "description": "Espada equilibrada e confiável, forjada para os primeiros combates de um guerreiro.", "rarity": "COMUM", "value": 50, "attackBonus": 4, "requiredClassId": classes["Guerreiro"]["id"], "minLevel": 1},
        {"name": "Cajado de Carvalho", "type": "ARMA", "description": "Cajado entalhado com runas simples que ajudam o mago a canalizar seus feitiços.", "rarity": "COMUM", "value": 55, "attackBonus": 5, "requiredClassId": classes["Mago"]["id"], "minLevel": 1},
        {"name": "Adagas Sombrias", "type": "ARMA", "description": "Par de lâminas leves, escurecidas para não refletir luz durante uma emboscada.", "rarity": "INCOMUM", "value": 75, "attackBonus": 6, "requiredClassId": classes["Ladino"]["id"], "minLevel": 2},
        {"name": "Maça Sagrada", "type": "ARMA", "description": "Arma cerimonial abençoada, usada por clérigos para defender peregrinos.", "rarity": "INCOMUM", "value": 80, "attackBonus": 6, "requiredClassId": classes["Clérigo"]["id"], "minLevel": 2},
        {"name": "Arco Élfico", "type": "ARMA", "description": "Arco flexível de madeira branca, preciso mesmo em disparos de longa distância.", "rarity": "RARO", "value": 110, "attackBonus": 8, "requiredClassId": classes["Arqueiro"]["id"], "minLevel": 3},
        {"name": "Machado do Berserker", "type": "ARMA", "description": "Machado pesado marcado por batalhas, poderoso nas mãos de um bárbaro experiente.", "rarity": "RARO", "value": 120, "attackBonus": 10, "requiredClassId": classes["Bárbaro"]["id"], "minLevel": 3},
        {"name": "Lâmina Prateada", "type": "ARMA", "description": "Espada de prata capaz de ferir criaturas corrompidas e mortos-vivos.", "rarity": "EPICO", "value": 180, "attackBonus": 12, "minLevel": 5},
        {"name": "Escudo de Aço", "type": "ARMADURA", "description": "Escudo reforçado que absorve impactos e aumenta a defesa do portador.", "rarity": "INCOMUM", "value": 70, "defenseBonus": 6, "requiredClassId": classes["Guerreiro"]["id"], "minLevel": 2},
        {"name": "Manto Arcano", "type": "ARMADURA", "description": "Manto tecido com fios encantados que forma uma barreira ao redor do mago.", "rarity": "RARO", "value": 105, "defenseBonus": 7, "requiredClassId": classes["Mago"]["id"], "minLevel": 3},
        {"name": "Couro Reforçado", "type": "ARMADURA", "description": "Armadura leve que protege sem prejudicar movimentos rápidos e silenciosos.", "rarity": "INCOMUM", "value": 85, "defenseBonus": 5, "requiredClassId": classes["Ladino"]["id"], "minLevel": 2},
        {"name": "Anel do Vigor", "type": "ACESSORIO", "description": "Anel gravado com símbolos de resistência que fortalece a defesa de qualquer aventureiro.", "rarity": "RARO", "value": 130, "defenseBonus": 4, "minLevel": 3},
        {"name": "Amuleto do Caçador", "type": "ACESSORIO", "description": "Amuleto feito com presas antigas que aguça o instinto ofensivo do usuário.", "rarity": "RARO", "value": 135, "attackBonus": 5, "minLevel": 3},
    ]
    items = {data["name"]: ensure("items", data) for data in item_data}

    mission_data = [
        {"title": "A ameaça dos goblins", "description": "Mercadores estão sendo atacados por goblins na estrada ao norte da vila.", "objective": "Derrotar 2 goblins batedores", "minLevel": 1, "target": 2, "rewardExperience": 80, "rewardCoins": 30, "rewardItem": "Poção de Vida", "rewardItemQuantity": 1},
        {"title": "Ervas sob o luar", "description": "A curandeira precisa de folhas luminosas que crescem na mata durante a noite.", "objective": "Coletar 3 ervas lunares", "minLevel": 1, "target": 3, "rewardExperience": 60, "rewardCoins": 25, "rewardItem": "Poção de Mana", "rewardItemQuantity": 1},
        {"title": "A caravana desaparecida", "description": "Uma caravana não chegou ao reino e deixou rastros próximos ao território dos bandidos.", "objective": "Encontrar 4 pistas da caravana", "minLevel": 2, "target": 4, "rewardExperience": 120, "rewardCoins": 55, "rewardItem": "Couro Reforçado", "rewardItemQuantity": 1},
        {"title": "A cripta esquecida", "description": "Sons e luzes estranhas surgiram na cripta onde antigos cavaleiros foram sepultados.", "objective": "Purificar 3 altares corrompidos", "minLevel": 3, "target": 3, "rewardExperience": 180, "rewardCoins": 75, "rewardItem": "Maça Sagrada", "rewardItemQuantity": 1},
        {"title": "Caçada ao ogro da ponte", "description": "Um ogro tomou a única ponte comercial e exige moedas de todos os viajantes.", "objective": "Enfraquecer as defesas do ogro em 5 etapas", "minLevel": 3, "target": 5, "rewardExperience": 220, "rewardCoins": 100, "rewardItem": "Poção Superior de Vida", "rewardItemQuantity": 1},
        {"title": "Ecos da torre arcana", "description": "Uma torre abandonada voltou a emitir pulsos de magia que perturbam os habitantes próximos.", "objective": "Estabilizar 4 focos de energia", "minLevel": 4, "target": 4, "rewardExperience": 280, "rewardCoins": 130, "rewardItem": "Manto Arcano", "rewardItemQuantity": 1},
        {"title": "O culto das cinzas", "description": "Seguidores de um necromante estão reunindo relíquias para realizar um ritual proibido.", "objective": "Destruir 6 componentes do ritual", "minLevel": 5, "target": 6, "rewardExperience": 360, "rewardCoins": 180, "rewardItem": "Lâmina Prateada", "rewardItemQuantity": 1},
        {"title": "Cerco ao forte orc", "description": "Um clã hostil ocupou um forte de fronteira e ameaça as aldeias do vale.", "objective": "Superar 7 posições defensivas", "minLevel": 6, "target": 7, "rewardExperience": 450, "rewardCoins": 240, "rewardItem": "Machado do Berserker", "rewardItemQuantity": 1},
        {"title": "O despertar do dragão", "description": "Um jovem dragão acordou sob a montanha e seu fogo já alcança as fazendas do reino.", "objective": "Quebrar 8 selos dracônicos", "minLevel": 8, "target": 8, "rewardExperience": 700, "rewardCoins": 400, "rewardItem": "Amuleto do Caçador", "rewardItemQuantity": 1},
    ]
    for data in mission_data:
        reward_name = data.pop("rewardItem")
        ensure("missions", {**data, "rewardItemId": items[reward_name]["id"]})

    enemy_data = [
        {"name": "Goblin Batedor", "type": "GOBLIN", "level": 1, "health": 28, "strength": 5, "defense": 2, "agility": 5, "rewardExperience": 45, "rewardCoins": 10, "rewardItem": "Poção de Vida"},
        {"name": "Lobo Cinzento", "type": "FERA", "level": 1, "health": 32, "strength": 6, "defense": 2, "agility": 7, "rewardExperience": 50, "rewardCoins": 8, "rewardItem": "Poção de Mana"},
        {"name": "Bandido da Estrada", "type": "HUMANOIDE", "level": 2, "health": 45, "strength": 8, "defense": 4, "agility": 6, "rewardExperience": 85, "rewardCoins": 25},
        {"name": "Esqueleto Guardião", "type": "MORTO_VIVO", "level": 3, "health": 58, "strength": 9, "defense": 7, "agility": 3, "rewardExperience": 120, "rewardCoins": 30},
        {"name": "Ogro da Ponte", "type": "OGRO", "level": 3, "health": 75, "strength": 12, "defense": 5, "agility": 1, "rewardExperience": 140, "rewardCoins": 45, "rewardItem": "Poção Superior de Vida"},
        {"name": "Aranha Sombria", "type": "FERA", "level": 4, "health": 68, "strength": 10, "defense": 5, "agility": 10, "rewardExperience": 165, "rewardCoins": 50, "rewardItem": "Adagas Sombrias"},
        {"name": "Necromante das Cinzas", "type": "CHEFE", "level": 5, "health": 110, "strength": 14, "defense": 8, "agility": 5, "rewardExperience": 260, "rewardCoins": 110, "rewardItem": "Lâmina Prateada"},
        {"name": "Golem Rúnico", "type": "CONSTRUTO", "level": 6, "health": 150, "strength": 17, "defense": 14, "agility": 2, "rewardExperience": 330, "rewardCoins": 145, "rewardItem": "Anel do Vigor"},
        {"name": "Capitão Orc", "type": "HUMANOIDE", "level": 7, "health": 165, "strength": 20, "defense": 11, "agility": 7, "rewardExperience": 410, "rewardCoins": 190, "rewardItem": "Machado do Berserker"},
        {"name": "Dragão Jovem", "type": "CHEFE", "level": 9, "health": 260, "strength": 26, "defense": 17, "agility": 11, "rewardExperience": 750, "rewardCoins": 420, "rewardItem": "Amuleto do Caçador"},
    ]
    for data in enemy_data:
        reward_name = data.pop("rewardItem", None)
        ensure(
            "enemies",
            {**data, "rewardItemId": items[reward_name]["id"] if reward_name else None},
        )

    return master
