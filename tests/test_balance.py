# """Устойчивость AI vs AI на расширенном ростере."""
# import random

# import pytest

# from core.battle import battle_from_data
# from ai.simple_ai import SimpleAI


# BOT_ROSTERS = [
#     ["handswing", "smut", "mage", "healer", "tank"],
#     ["assassin", "archer", "necromancer", "berserker", "paladin"],
#     ["mage", "mage", "mage", "healer", "healer"],
#     ["tank", "tank", "paladin", "paladin", "healer"],
#     ["assassin", "assassin", "berserker", "berserker", "archer"],
# ]


# def _random_roster(rng: random.Random, pool: list[str]) -> list[str]:
#     return [rng.choice(pool) for _ in range(5)]


# @pytest.mark.parametrize("seed", range(5))
# def test_ai_vs_ai_100_battles_no_crash(settings, game_data, seed):
#     """100 полных боёв, рендомные составы. Проверяем: доходят до конца,
#     инварианты (cap/floor/alive) не нарушены, событий battle_end ровно одно."""
#     rng = random.Random(seed * 1000)
#     pool = [h["id"] for h in game_data["heroes"]]
#     ai = SimpleAI()

#     for match_idx in range(100):
#         top = _random_roster(rng, pool)
#         bottom = _random_roster(rng, pool)
#         battle = battle_from_data(game_data, settings,
#                                   top_ids=top, bottom_ids=bottom,
#                                   seed=rng.randint(0, 2**31 - 1))
#         battle.start()
#         safety = 0
#         while not battle.is_over():
#             safety += 1
#             assert safety < 4000, \
#                 f"Бой не завершился (match={match_idx}, top={top}, bot={bottom})"
#             actor = battle.current_actor()
#             if actor is None:
#                 break
#             action = ai.choose_action(battle, actor)
#             battle.apply_action(action)

#             for h in battle.heroes:
#                 assert 0 <= h.mana <= battle.MAX_MANA
#                 assert h.hp <= h.template.hp
#                 # floor защиты не нарушен после любых эффектов
#                 from core.stats import effective_stat
#                 base_def = h.template.defense
#                 assert effective_stat(h, "defense") >= base_def * 0.3 - 1e-6

#         assert battle.is_over()
#         assert battle.winner() in (0, 1, None)


# def test_roster_diversity_all_heroes_playable(settings, game_data):
#     """Каждый герой из data/heroes.json провёл хотя бы один бой без падений."""
#     pool = [h["id"] for h in game_data["heroes"]]
#     ai = SimpleAI()
#     for hid in pool:
#         battle = battle_from_data(game_data, settings,
#                                   top_ids=[hid] * 5,
#                                   bottom_ids=["handswing"] * 5,
#                                   seed=hash(hid) & 0xFFFF)
#         battle.start()
#         safety = 0
#         while not battle.is_over() and safety < 3000:
#             safety += 1
#             actor = battle.current_actor()
#             if actor is None:
#                 break
#             battle.apply_action(ai.choose_action(battle, actor))
#         assert battle.is_over(), f"{hid}: бой не завершился"