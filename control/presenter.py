"""Перевод Event (из core) в PresentationCommand (для view).

Правила:
- Один Event → 0..N команд.
- Batches всегда завершаются REFRESH_SNAPSHOT, чтобы view подтянул состояние.
- Координаты слотов, тайминги — ответственность view; здесь только семантика.
"""
from __future__ import annotations

from core.contracts import PresentationCommand, PresentationCommandType
from core.events import Event, EventType


def event_to_commands(event: Event) -> list[PresentationCommand]:
    t = event.type
    p = event.payload

    if t in (EventType.BATTLE_START, EventType.ROUND_START,
             EventType.ROUND_END, EventType.TURN_END,
             EventType.DODGE, EventType.MEDITATE):
        return []

    if t == EventType.TURN_START:
        return [PresentationCommand(PresentationCommandType.PLAY_TURN_HIGHLIGHT,
                                    {"slot": p["slot"]})]

    if t == EventType.ATTACK:
        return [PresentationCommand(PresentationCommandType.PLAY_ATTACK, {
            "attacker": p["attacker"],
            "target": p["target"],
            "percent": p["percent"],
        })]

    if t == EventType.DAMAGE:
        kind = "crit" if p.get("crit") else (
            "reflected" if p.get("reflected") else "damage")
        return [PresentationCommand(PresentationCommandType.PLAY_FLOAT_NUMBER, {
            "slot": p["target"], "value": p["amount"], "kind": kind,
        })]

    if t == EventType.MISS:
        return [PresentationCommand(PresentationCommandType.PLAY_FLOAT_NUMBER, {
            "slot": p["target"], "value": 0, "kind": "miss",
        })]

    if t == EventType.HEAL:
        return [
            PresentationCommand(PresentationCommandType.PLAY_HEAL,
                                {"slot": p["target"]}),
            PresentationCommand(PresentationCommandType.PLAY_FLOAT_NUMBER, {
                "slot": p["target"], "value": p["amount"], "kind": "heal",
            }),
        ]

    if t == EventType.MANA_GAIN:
        return [PresentationCommand(PresentationCommandType.PLAY_MANA_CHANGE, {
            "slot": p["slot"], "amount": p["amount"], "kind": "gain",
        })]

    if t == EventType.MANA_SPENT:
        return [PresentationCommand(PresentationCommandType.PLAY_MANA_CHANGE, {
            "slot": p["slot"], "amount": -p["amount"], "kind": "spend",
        })]

    if t == EventType.EFFECT_APPLIED:
        return [PresentationCommand(PresentationCommandType.PLAY_APPLY_EFFECT, {
            "slot": p["slot"], "family": p["family"],
            "effect_id": p["effect_id"],
        })]

    if t in (EventType.EFFECT_EXPIRED, EventType.EFFECT_CLEANSED,
             EventType.EFFECT_REPLACED):
        reason = {
            EventType.EFFECT_EXPIRED: "expired",
            EventType.EFFECT_CLEANSED: "cleansed",
            EventType.EFFECT_REPLACED: "replaced",
        }[t]
        return [PresentationCommand(PresentationCommandType.PLAY_REMOVE_EFFECT, {
            "slot": p["slot"], "family": p["family"],
            "effect_id": p["effect_id"], "reason": reason,
        })]

    if t == EventType.EFFECT_TICK:
        return [PresentationCommand(PresentationCommandType.PLAY_FLOAT_NUMBER, {
            "slot": p["slot"], "value": p["damage"], "kind": "dot",
        })]

    if t == EventType.DEATH:
        return [PresentationCommand(PresentationCommandType.PLAY_DEATH,
                                    {"slot": p["slot"]})]

    if t == EventType.MADNESS_ACTION:
        return [PresentationCommand(PresentationCommandType.PLAY_TURN_HIGHLIGHT,
                                    {"slot": p["slot"], "madness": True})]

    if t == EventType.BATTLE_END:
        return [PresentationCommand(PresentationCommandType.SHOW_BATTLE_END,
                                    {"winner": p["winner"]})]

    return []


def events_to_commands(events: list[Event]) -> list[PresentationCommand]:
    commands: list[PresentationCommand] = []
    for ev in events:
        commands.extend(event_to_commands(ev))
    commands.append(PresentationCommand(PresentationCommandType.REFRESH_SNAPSHOT))
    return commands


# ---------------------------------------------------------- лог боя (для view)

def event_to_log_line(event: Event) -> str | None:
    t = event.type
    p = event.payload
    if t == EventType.ATTACK:
        return f"Атака: [{p['attacker']}] → [{p['target']}] ({p['percent']:.0f}%)"
    if t == EventType.DAMAGE:
        crit = " КРИТ!" if p.get("crit") else ""
        ref = " (отражено)" if p.get("reflected") else ""
        return f"Урон [{p['target']}]: -{p['amount']}{crit}{ref}"
    if t == EventType.MISS:
        return f"Промах: [{p['attacker']}] по [{p['target']}]"
    if t == EventType.HEAL:
        return f"Лечение [{p['target']}]: +{p['amount']}"
    if t == EventType.MANA_GAIN:
        return f"Мана [{p['slot']}]: +{p['amount']} ({p.get('reason','')})"
    if t == EventType.MANA_SPENT:
        return f"Мана [{p['slot']}]: -{p['amount']}"
    if t == EventType.EFFECT_APPLIED:
        return f"Эффект [{p['slot']}]: {p['family']} ({p['duration']} р.)"
    if t == EventType.EFFECT_EXPIRED:
        return f"Эффект истёк [{p['slot']}]: {p['family']}"
    if t == EventType.EFFECT_TICK:
        return f"Периодический урон [{p['slot']}]: -{p['damage']} ({p['family']})"
    if t == EventType.DEATH:
        return f"Смерть: [{p['slot']}]"
    if t == EventType.MADNESS_ACTION:
        return f"Безумие [{p['slot']}]: {p['action']} → {p['targets']}"
    if t == EventType.ROUND_START:
        return f"—— Раунд {p['round']} ——"
    if t == EventType.BATTLE_END:
        w = p["winner"]
        return f"=== Бой окончен: {'ничья' if w is None else ('верх' if w==0 else 'низ')} ==="
    return None