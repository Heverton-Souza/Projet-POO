import unittest
from dataclasses import is_dataclass

from app.entities import (
    Character,
    CharacterClass,
    Combat,
    Enemy,
    Item,
    Mission,
    MissionProgress,
    Race,
    Skill,
    User,
)


class EntityStructureTests(unittest.TestCase):
    def test_project_entities_are_explicit_dataclasses(self):
        entities = (
            User,
            CharacterClass,
            Race,
            Character,
            Skill,
            Item,
            Mission,
            MissionProgress,
            Enemy,
            Combat,
        )

        self.assertTrue(all(is_dataclass(entity) for entity in entities))


if __name__ == "__main__":
    unittest.main()
