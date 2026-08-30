import unittest
import hashlib

from app.entities import MissionProgress
from app.domain.errors import ConflictError
from app.domain.patterns import BasicAttackStrategy, CharacterBuilder, SkillAttackStrategy
from app.infrastructure.security import ScryptPasswordHasher


CHARACTER_CLASS = {
    "id": "class-1",
    "name": "Guerreiro",
    "baseHealth": 60,
    "baseEnergy": 20,
    "attributes": {
        "strength": 8,
        "defense": 6,
        "agility": 4,
        "intelligence": 2,
        "vitality": 5,
        "charisma": 1,
    },
    "skillIds": ["skill-1"],
}
RACE = {
    "id": "race-1",
    "name": "Humano",
    "modifiers": {
        "strength": 1,
        "defense": 1,
        "agility": 1,
        "intelligence": 1,
        "vitality": 1,
        "charisma": 1,
    },
    "skillIds": [],
}


def make_character():
    return (
        CharacterBuilder()
        .owned_by("player-1")
        .named("Ayla")
        .from_class(CHARACTER_CLASS)
        .from_race(RACE)
        .build()
    )


class PatternTests(unittest.TestCase):
    def test_builder_applies_class_race_resources_and_skills(self):
        character = make_character()
        self.assertEqual(character.name, "Ayla")
        self.assertEqual(character.attributes.strength, 9)
        self.assertEqual(character.max_health, 72)
        self.assertEqual(character.max_energy, 23)
        self.assertEqual(character.skill_ids, ["skill-1"])

    def test_strategy_changes_damage_calculation(self):
        character = make_character()
        self.assertEqual(BasicAttackStrategy().execute(character, {"defense": 3})["damage"], 8)
        result = SkillAttackStrategy(
            {"name": "Golpe", "type": "FISICA", "damage": 12, "energyCost": 5, "minLevel": 1}
        ).execute(character, {"defense": 3})
        self.assertEqual(result["damage"], 18)
        self.assertEqual(result["energyCost"], 5)

    def test_skill_rejects_insufficient_energy(self):
        character = make_character()
        character.energy = 1
        strategy = SkillAttackStrategy(
            {"name": "Golpe", "type": "FISICA", "damage": 12, "energyCost": 5, "minLevel": 1}
        )
        with self.assertRaises(ConflictError):
            strategy.execute(character, {"defense": 0})

    def test_level_up_grants_and_distributes_attribute_points(self):
        character = make_character()
        original_strength = character.attributes.strength
        original_health = character.max_health
        original_energy = character.max_energy

        levels = character.gain_experience(100)

        self.assertEqual(levels, [2])
        self.assertEqual(character.attribute_points, 5)
        character.distribute_attribute("strength", 2)
        character.distribute_attribute("vitality", 1)
        character.distribute_attribute("intelligence", 1)
        self.assertEqual(character.attributes.strength, original_strength + 2)
        self.assertEqual(character.attribute_points, 1)
        self.assertEqual(character.max_health, original_health + 10 + 6 + 2)
        self.assertEqual(character.max_energy, original_energy + 5 + 1 + 1)

        with self.assertRaises(ConflictError):
            character.distribute_attribute("defense", 2)

    def test_defeated_character_can_recover(self):
        character = make_character()
        character.energy = 1
        character.receive_damage(character.health)
        self.assertEqual(character.status.value, "DERROTADO")

        character.recover()

        self.assertEqual(character.status.value, "ATIVO")
        self.assertEqual(character.health, character.max_health)
        self.assertEqual(character.energy, character.max_energy)
        with self.assertRaises(ConflictError):
            character.recover()

    def test_mission_requires_all_objectives(self):
        progress = MissionProgress(id="p1", character_id="c1", mission_id="m1", target=2)
        progress.update(1)
        with self.assertRaises(ConflictError):
            progress.complete()
        progress.update(1)
        progress.complete()
        self.assertEqual(progress.status.value, "CONCLUIDA")

    def test_password_hasher_accepts_legacy_node_salt(self):
        salt_hex = "00112233445566778899aabbccddeeff"
        password = "Mestre@123"
        legacy_hash = hashlib.scrypt(
            password.encode(), salt=salt_hex.encode(), n=2**14, r=8, p=1, dklen=64
        ).hex()
        self.assertTrue(ScryptPasswordHasher().verify(password, f"{salt_hex}:{legacy_hash}"))


if __name__ == "__main__":
    unittest.main()
