from secrets import randbelow

from app.application.ports import DiceRoller


class D100DiceRoller(DiceRoller):
    """Dado percentual usado para calcular acertos no combate."""

    def roll_d100(self) -> int:
        return randbelow(100) + 1
