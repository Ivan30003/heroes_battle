"""Герой: шаблон из JSON + состояние в бою."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.effect import Effect


@dataclass(frozen=True)
class HeroTemplate:
    id: str
    name: str
    sprite_path: str
    hp: int
    attack: int
    defense: int
    dodge: float
    crit: float
    ability_ids: tuple[str, ...]
    passive_ids: tuple[str, ...]

    @classmethod
    def from_dict(cls, d: dict) -> "HeroTemplate":
        return cls(
            id=d["id"], name=d["name"], sprite_path=d["sprite_path"],
            hp=d["hp"], attack=d["attack"], defense=d["defense"],
            dodge=d["dodge"], crit=d["crit"],
            ability_ids=tuple(d["ability_ids"]),
            passive_ids=tuple(d["passive_ids"]),
        )


@dataclass
class Hero:
    template: HeroTemplate
    team: int
    slot_in_team: int
    slot: int
    hp: int = -1
    mana: int = 0
    effects: list["Effect"] = field(default_factory=list)
    cooldowns: dict[str, int] = field(default_factory=dict)
    # Произвольные флаги для пассивок и временного состояния.
    # Пример: used_ability_this_round — для discipline у Коммандора.
    flags: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.hp < 0:
            self.hp = self.template.hp
        # Гарантируем, что флаг существует с момента создания,
        # чтобы чтение hero.flags["used_ability_this_round"] было безопасным.
        self.flags.setdefault("used_ability_this_round", False)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def has_passive(self, passive_id: str) -> bool:
        return passive_id in self.template.passive_ids