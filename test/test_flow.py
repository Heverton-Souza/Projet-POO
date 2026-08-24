import unittest

from app.config import load_config
from app.container import create_container
from app.domain.errors import AuthorizationError
from app.infrastructure.security import ScryptPasswordHasher, UuidGenerator
from app.infrastructure.seed import seed_database


class FixedDiceRoller:
    def __init__(self, values: list[int] | None = None) -> None:
        self.values = list(values or [])

    def roll_d100(self) -> int:
        return self.values.pop(0) if self.values else 100


class IntegratedFlowTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(
            database_path=":memory:",
            master_email="mestre@teste.local",
            master_password="Mestre@123",
            seed=True,
        )
        self.container = create_container(self.config, dice_roller=FixedDiceRoller())

    def tearDown(self):
        self.container.close()

    def test_account_character_mission_combat_and_history(self):
        services = self.container.services
        services.auth.register("Lina", "lina@teste.local", "Senha@123")
        login = services.auth.login("lina@teste.local", "Senha@123")
        player = services.auth.authenticate(login["token"])
        warrior = next(item for item in services.admin.list_catalog("classes") if item["name"] == "Guerreiro")
        human = next(item for item in services.admin.list_catalog("races") if item["name"] == "Humano")
        character = services.characters.create(player, "Lina Escarlate", warrior["id"], human["id"])

        mission = services.missions.list_available(player, character["id"])[0]
        accepted = services.missions.accept(player, character["id"], mission["id"])
        services.missions.update(player, accepted["id"], mission["target"])
        completed = services.missions.complete(player, accepted["id"])
        self.assertEqual(completed["progress"]["status"], "CONCLUIDA")
        self.assertGreaterEqual(completed["character"]["coins"], mission["rewardCoins"])

        enemy = next(item for item in services.admin.list_catalog("enemies") if item["name"] == "Goblin Batedor")
        combat = services.combats.start(player, character["id"], enemy["id"])
        while combat["status"] == "EM_ANDAMENTO":
            combat = services.combats.act(player, combat["id"], "ATAQUE")["combat"]
        self.assertEqual(combat["status"], "VITORIA")

        leveled_character = services.characters.get(player, character["id"])
        self.assertEqual(leveled_character["level"], 2)
        self.assertEqual(leveled_character["attributePoints"], 5)
        original_strength = leveled_character["attributes"]["strength"]
        distributed = services.characters.distribute_attribute(player, character["id"], "strength", 2)
        self.assertEqual(distributed["attributes"]["strength"], original_strength + 2)
        self.assertEqual(distributed["attributePoints"], 3)

        events = services.history.list(player, character["id"])
        event_types = {event["type"] for event in events}
        self.assertTrue(
            {"CHARACTER_CREATED", "MISSION_COMPLETED", "COMBAT_WON", "LEVEL_UP", "ATTRIBUTE_DISTRIBUTED"}.issubset(event_types)
        )

    def test_player_cannot_use_admin_operations(self):
        services = self.container.services
        services.auth.register("Ivo", "ivo@teste.local", "Senha@123")
        player = services.auth.authenticate(services.auth.login("ivo@teste.local", "Senha@123")["token"])
        with self.assertRaises(AuthorizationError):
            services.admin.list_users(player)

    def test_existing_character_inherits_new_class_and_general_skills(self):
        services = self.container.services
        services.auth.register("Nilo", "nilo@teste.local", "Senha@123")
        player = services.auth.authenticate(
            services.auth.login("nilo@teste.local", "Senha@123")["token"]
        )
        warrior = next(
            item for item in services.admin.list_catalog("classes") if item["name"] == "Guerreiro"
        )
        human = next(
            item for item in services.admin.list_catalog("races") if item["name"] == "Humano"
        )
        character = services.characters.create(player, "Nilo", warrior["id"], human["id"])

        master = services.auth.authenticate(
            services.auth.login("mestre@teste.local", "Mestre@123")["token"]
        )
        skill = services.admin.create(
            master,
            "skills",
            {
                "name": "Técnica recém-descoberta",
                "description": "Habilidade criada depois do personagem para testar a herança dinâmica.",
                "type": "FISICA",
                "energyCost": 7,
                "damage": 18,
                "cooldown": 2,
                "minLevel": 2,
                "classId": warrior["id"],
                "raceId": None,
            },
        )
        general_skill = services.admin.create(
            master,
            "skills",
            {
                "name": "Técnica geral recém-descoberta",
                "description": "Habilidade sem vínculo disponível para todos os personagens.",
                "type": "FISICA",
                "energyCost": 3,
                "damage": 8,
                "cooldown": 1,
                "minLevel": 1,
                "classId": None,
                "raceId": None,
            },
        )

        updated = services.characters.get(player, character["id"])
        inherited = next(item for item in updated["skills"] if item["id"] == skill["id"])
        self.assertEqual(inherited["minLevel"], 2)
        self.assertIn(skill["id"], updated["skillIds"])
        self.assertIn(general_skill["id"], updated["skillIds"])

        entity = services.characters.get_entity(player, character["id"])
        entity.receive_damage(entity.health)
        self.container.repository.save_character(entity)
        recovered = services.characters.recover(player, character["id"])
        self.assertEqual(recovered["status"], "ATIVO")
        self.assertEqual(recovered["health"], recovered["maxHealth"])
        self.assertEqual(recovered["energy"], recovered["maxEnergy"])

    def test_d100_with_opposed_agility_controls_player_and_enemy_hits(self):
        services = self.container.services
        services.auth.register("Dara", "dara@teste.local", "Senha@123")
        player = services.auth.authenticate(
            services.auth.login("dara@teste.local", "Senha@123")["token"]
        )
        warrior = next(
            item for item in services.admin.list_catalog("classes") if item["name"] == "Guerreiro"
        )
        human = next(
            item for item in services.admin.list_catalog("races") if item["name"] == "Humano"
        )
        enemy = next(
            item for item in services.admin.list_catalog("enemies") if item["name"] == "Goblin Batedor"
        )
        character = services.characters.create(player, "Dara", warrior["id"], human["id"])
        combat = services.combats.start(player, character["id"], enemy["id"])
        player_agility = character["attributes"]["agility"]
        enemy_agility = enemy["agility"]
        minimum_player_hit = 71 - player_agility + enemy_agility

        services.combats.dice_roller = FixedDiceRoller([minimum_player_hit - 1, 1])
        missed = services.combats.act(player, combat["id"], "ATAQUE")
        self.assertFalse(missed["turn"]["playerHit"])
        self.assertFalse(missed["turn"]["enemyHit"])
        self.assertEqual(missed["turn"]["damage"], 0)
        self.assertEqual(missed["turn"]["enemyDamage"], 0)
        self.assertEqual(
            missed["turn"]["playerHitChance"],
            30 + player_agility - enemy_agility,
        )
        self.assertEqual(
            missed["turn"]["enemyHitChance"],
            30 + enemy_agility - player_agility,
        )

        services.combats.dice_roller = FixedDiceRoller([minimum_player_hit, 100])
        hit = services.combats.act(player, combat["id"], "ATAQUE")
        self.assertTrue(hit["turn"]["playerHit"])
        self.assertTrue(hit["turn"]["enemyHit"])
        self.assertGreater(hit["turn"]["damage"], 0)
        self.assertEqual(
            hit["turn"]["playerRoll"] + player_agility - enemy_agility,
            71,
        )
        self.assertGreaterEqual(hit["turn"]["playerHitChance"], 0)
        self.assertLessEqual(hit["turn"]["playerHitChance"], 100)

        persisted = services.combats.list(player, character["id"])[0]["turns"]
        self.assertEqual(len(persisted), 2)
        self.assertEqual(persisted[0]["playerRoll"], minimum_player_hit - 1)
        self.assertEqual(persisted[1]["enemyRoll"], 100)

        master = services.auth.authenticate(
            services.auth.login("mestre@teste.local", "Mestre@123")["token"]
        )
        potion = next(
            item for item in services.admin.list_catalog("items") if item["name"] == "Poção de Vida"
        )
        services.inventory.grant(master, character["id"], potion["id"], 1)
        before_use = services.characters.get(player, character["id"])
        self.assertLess(before_use["health"], before_use["maxHealth"])
        recovered = services.inventory.use(player, character["id"], potion["id"])
        self.assertEqual(recovered["health"], recovered["maxHealth"])
        self.assertEqual(recovered["status"], "EM_COMBATE")

    def test_seed_has_varied_descriptive_content_and_is_idempotent(self):
        services = self.container.services
        minimum_counts = {
            "classes": 6,
            "races": 6,
            "skills": 18,
            "items": 16,
            "missions": 9,
            "enemies": 10,
        }
        before = {}
        for resource, minimum in minimum_counts.items():
            entries = services.admin.list_catalog(resource)
            before[resource] = len(entries)
            self.assertGreaterEqual(len(entries), minimum)

        for resource in ("classes", "races", "skills", "items", "missions"):
            self.assertTrue(
                all(entry["description"].strip() for entry in services.admin.list_catalog(resource))
            )

        weapons = [item for item in services.admin.list_catalog("items") if item["type"] == "ARMA"]
        self.assertGreaterEqual(len(weapons), 7)
        mana_potion = next(
            item for item in services.admin.list_catalog("items") if item["name"] == "Poção de Mana"
        )
        self.assertEqual(mana_potion["effectEnergy"], 30)

        seed_database(
            self.container.repository,
            ScryptPasswordHasher(),
            UuidGenerator(),
            self.config,
        )
        after = {
            resource: len(services.admin.list_catalog(resource)) for resource in minimum_counts
        }
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
