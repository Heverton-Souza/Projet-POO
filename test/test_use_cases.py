import unittest

from app.use_case import (
    AcceptMissionUseCase,
    CreateCharacterUseCase,
    PerformCombatUseCase,
)


class UseCaseStructureTests(unittest.TestCase):
    def test_pdf_use_cases_are_explicit_and_executable(self):
        use_cases = {
            "UC01 — Criar Personagem": CreateCharacterUseCase,
            "UC02 — Aceitar Missão": AcceptMissionUseCase,
            "UC03 — Realizar Combate": PerformCombatUseCase,
        }

        for name, use_case in use_cases.items():
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(use_case, "execute", None)))


if __name__ == "__main__":
    unittest.main()
