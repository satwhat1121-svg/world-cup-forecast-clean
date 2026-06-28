#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
import urllib.request
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from statistics import NormalDist
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[1]
STATE = BASE / "state"
DATA = BASE / "data"
CONFIG = BASE / "config.json"
ANNEX_C_FULL = DATA / "annex_c_full_mapping.json"
TZ = "America/New_York"

TEAM_NAME_OVERRIDES = {
    "USA": "United States",
    "KOR": "South Korea",
    "CZE": "Czechia",
    "COD": "DR Congo",
    "ENG": "England",
    "IRN": "Iran",
    "CRC": "Costa Rica",
    "SUI": "Switzerland",
    "CIV": "Côte d'Ivoire",
    "UAE": "United Arab Emirates",
    "QAT": "Qatar",
    "CPV": "Cape Verde",
    "CUW": "Curaçao",
    "HAI": "Haiti",
    "RSA": "South Africa",
    "KSA": "Saudi Arabia",
    "NZL": "New Zealand",
}

FIFA_TO_ELO = {
    'ARG': 'AR', 'ESP': 'ES', 'FRA': 'FR', 'ENG': 'EN', 'COL': 'CO', 'BRA': 'BR', 'NED': 'NL', 'POR': 'PT', 'GER': 'DE',
    'NOR': 'NO', 'JPN': 'JP', 'MEX': 'MX', 'SUI': 'CH', 'CRO': 'HR', 'DEN': 'DK', 'ITA': 'IT', 'BEL': 'BE', 'MAR': 'MA',
    'ECU': 'EC', 'URU': 'UY', 'SWE': 'SE', 'AUT': 'AT', 'KOR': 'KR', 'TUR': 'TR', 'CZE': 'CZ', 'PAN': 'PA', 'GHA': 'GH',
    'QAT': 'QA', 'UZB': 'UZ', 'BIH': 'BA', 'CAN': 'CA', 'USA': 'US', 'RSA': 'ZA', 'COD': 'CD', 'IRN': 'IR', 'POL': 'PL',
    'CMR': 'CM', 'AUS': 'AU', 'SEN': 'SN', 'TUN': 'TN', 'JAM': 'JM', 'CIV': 'CI', 'NZL': 'NZ', 'EGY': 'EG', 'ALG': 'DZ',
    'CHI': 'CL', 'PAR': 'PY', 'BOL': 'BO', 'HON': 'HN', 'IRL': 'IE', 'SCO': 'SC', 'GRE': 'GR', 'NGA': 'NG', 'MLI': 'ML',
    'SRB': 'RS', 'SVK': 'SK', 'SVN': 'SI', 'ROU': 'RO', 'HUN': 'HU', 'ISL': 'IS', 'PER': 'PE', 'VEN': 'VE', 'KSA': 'SA',
    'UAE': 'AE', 'ISR': 'IL', 'IRQ': 'IQ', 'JOR': 'JO', 'OMA': 'OM', 'BHR': 'BH', 'CHN': 'CN', 'IND': 'IN', 'IDN': 'ID',
    'THA': 'TH', 'VIE': 'VN', 'ZAM': 'ZM', 'ANG': 'AO', 'CGO': 'CG', 'TAN': 'TZ', 'UGA': 'UG', 'GAB': 'GA', 'BEN': 'BJ'
}

THIRD_PLACE_ADVANCERS = 8
ANNEX_C_COLUMN_ORDER = ['1A', '1B', '1D', '1E', '1G', '1I', '1K', '1L']
WINNER_SLOT_TO_MATCH = {'1E': 74, '1I': 77, '1A': 79, '1L': 80, '1D': 81, '1G': 82, '1B': 85, '1K': 87}
MATCH_TO_WINNER_SLOT = {v: k for k, v in WINNER_SLOT_TO_MATCH.items()}

@dataclass
class ForecastSnapshot:
    generated_at: str
    simulation_count: int
    notes: list[str]
    ratings: list[dict]
    title_odds: list[dict]
    group_tables: dict
    upcoming_matches: list[dict]
    round_of_32: list[dict]
    round_of_32_matchup_probs: list[dict]
    knockout_path_probs: list[dict]
    bracket_slot_probs: dict
    sources: list[dict]


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def ensure_dirs() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def fetch_json(url: str) -> dict | list:
    return json.loads(fetch_text(url))


def save_data_file(name: str, payload) -> Path:
    path = DATA / name
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")
    return path


def parse_tsv(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        line = line.strip("\n\r")
        if not line:
            continue
        rows.append(line.split("\t"))
    return rows


def get_team_dictionary() -> dict[str, str]:
    rows = parse_tsv(fetch_text("https://eloratings.net/en.teams.tsv"))
    mapping = {}
    for row in rows:
        if len(row) >= 2:
            mapping[row[0]] = row[1]
    return mapping


def load_world_elo(team_names: dict[str, str]) -> dict[str, dict]:
    rows = parse_tsv(fetch_text("https://eloratings.net/World.tsv"))
    ratings = {}
    for row in rows:
        if len(row) < 4:
            continue
        code = row[2].upper()
        name = team_names.get(code, code)
        try:
            elo = float(row[3])
        except ValueError:
            continue
        ratings[code] = {"code": code, "team": name, "elo": elo}
    return ratings


def load_fifa_matches() -> list[dict]:
    data = fetch_json("https://api.fifa.com/api/v3/calendar/matches?count=500&idSeason=285023")
    return data.get("Results", [])


def fifa_to_elo_code(code: str) -> str:
    return FIFA_TO_ELO.get(code, code)


def normalize_team_name(abbr: str, team_names: dict[str, str]) -> str:
    if abbr in TEAM_NAME_OVERRIDES:
        return TEAM_NAME_OVERRIDES[abbr]
    rec = team_names.get(fifa_to_elo_code(abbr)) or team_names.get(abbr)
    if rec:
        return rec
    return TEAM_NAME_OVERRIDES.get(abbr, abbr)


def match_team_display(team_obj: dict, team_names: dict[str, str]) -> str:
    abbr = team_obj.get('Abbreviation')
    if abbr:
        normalized = normalize_team_name(abbr, team_names)
        if normalized != abbr:
            return normalized
    names = team_obj.get('TeamName') or []
    if names and names[0].get('Description'):
        name = names[0]['Description']
        if name == 'USA':
            return 'United States'
        if name == 'Korea Republic':
            return 'South Korea'
        if name == 'Czech Republic':
            return 'Czechia'
        if name == 'Ivory Coast':
            return "Côte d'Ivoire"
        if name == 'Congo DR':
            return 'DR Congo'
        return name
    if abbr:
        return normalize_team_name(abbr, team_names)
    return 'TBD'


def expected_goals(home_elo: float, away_elo: float, host_boost: float = 0.0) -> tuple[float, float]:
    diff = (home_elo + host_boost) - away_elo
    total_goals = 2.55
    home_share = 0.5 + diff / 800.0
    home_share = min(0.82, max(0.18, home_share))
    home = max(0.2, total_goals * home_share)
    away = max(0.2, total_goals * (1 - home_share))
    return home, away


def poisson_pmf(lam: float, k: int) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def match_probs(home_xg: float, away_xg: float, max_goals: int = 10) -> tuple[float, float, float, str]:
    home = draw = away = 0.0
    best_score = None
    best_p = -1.0
    for i in range(max_goals + 1):
        pi = poisson_pmf(home_xg, i)
        for j in range(max_goals + 1):
            p = pi * poisson_pmf(away_xg, j)
            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p
            if p > best_p:
                best_p = p
                best_score = f"{i}-{j}"
    tail = max(0.0, 1.0 - (home + draw + away))
    home += tail * 0.45
    draw += tail * 0.10
    away += tail * 0.45
    return home, draw, away, best_score or "1-0"


def norm_cdf(x: float, mean: float, sd: float) -> float:
    return NormalDist(mu=mean, sigma=sd).cdf(x)


def group_advancement_probs(points: dict[str, int], remaining: dict[str, list[dict]], ratings: dict[str, dict], team_names: dict[str, str]) -> dict[str, dict[str, float]]:
    teams = list(points.keys())
    means = {t: float(points[t]) for t in teams}
    vars_ = {t: 0.0 for t in teams}
    for t, matches in remaining.items():
        for m in matches:
            if m['home'] != t:
                continue
            home_elo = ratings.get(fifa_to_elo_code(m['home']), {}).get('elo', 1700.0)
            away_elo = ratings.get(fifa_to_elo_code(m['away']), {}).get('elo', 1700.0)
            host = 55.0 if m.get('host_team') == 'home' else 0.0
            pwin, pdraw, ploss, _ = match_probs(*expected_goals(home_elo, away_elo, host))
            means[m['home']] += 3*pwin + pdraw
            vars_[m['home']] += max(0.2, (9*pwin + pdraw) - (3*pwin + pdraw)**2)
            means[m['away']] += 3*ploss + pdraw
            vars_[m['away']] += max(0.2, (9*ploss + pdraw) - (3*ploss + pdraw)**2)
    rank_score = {t: means[t] + 0.15 * ratings.get(fifa_to_elo_code(t), {}).get('elo', 1700.0) / 100.0 for t in teams}
    first_probs = {}
    top2_probs = {}
    for team in teams:
        pairwise = []
        for other in teams:
            if other == team:
                continue
            sd = max(1.25, math.sqrt(vars_[team] + vars_[other] + 1.5))
            p_ahead = 1 - norm_cdf(rank_score[other], rank_score[team], sd)
            pairwise.append(max(0.02, min(0.98, p_ahead)))
        pairwise.sort(reverse=True)
        first_probs[team] = pairwise[0] * pairwise[1] * pairwise[2]
        top2_probs[team] = sum(pairwise) / len(pairwise)
    results = {}
    for team in teams:
        results[team] = {
            "mean_points": means[team],
            "win_group": max(0.0, min(1.0, first_probs[team])),
            "top2": max(first_probs[team], min(1.0, top2_probs[team]))
        }
    return results


def rank_group_rows(table: dict, simulated_points: dict | None = None) -> list[tuple[str, dict]]:
    rows = []
    for abbr, stats in table.items():
        row = dict(stats)
        if simulated_points and abbr in simulated_points:
            row['points'] = simulated_points[abbr]
        row['sort_team'] = abbr
        rows.append((abbr, row))
    rows.sort(key=lambda item: (item[1]['points'], item[1]['gd'], item[1]['gf'], item[0]), reverse=True)
    return rows


def load_annex_c_full() -> dict[str, list[str]]:
    if ANNEX_C_FULL.exists():
        return json.loads(ANNEX_C_FULL.read_text(encoding='utf-8'))
    return {}


def resolve_third_place_slot_from_annex_c(third_place_groups: list[str], match_number: int, annex_c: dict[str, list[str]]) -> str | None:
    combo = ''.join(sorted(third_place_groups))
    row = annex_c.get(combo)
    if not row:
        return None
    slot = MATCH_TO_WINNER_SLOT.get(match_number)
    if not slot:
        return None
    try:
        idx = ANNEX_C_COLUMN_ORDER.index(slot)
    except ValueError:
        return None
    if idx >= len(row):
        return None
    val = row[idx]
    if not val or not val.startswith('3') or len(val) != 2:
        return None
    return val[1]


def get_qualified_fifa_codes(matches: list[dict]) -> set[str]:
    codes = set()
    for m in matches:
        home_obj = (m.get('Home') or {})
        away_obj = (m.get('Away') or {})
        if home_obj.get('Abbreviation'):
            codes.add(home_obj['Abbreviation'])
        if away_obj.get('Abbreviation'):
            codes.add(away_obj['Abbreviation'])
    return codes


def build_group_tables(matches: list[dict], team_names: dict[str, str]) -> tuple[dict, dict]:
    groups = defaultdict(lambda: defaultdict(lambda: {
        "team": "", "played": 0, "wins": 0, "draws": 0, "losses": 0,
        "gf": 0, "ga": 0, "gd": 0, "points": 0
    }))
    remaining = defaultdict(list)
    for m in matches:
        group = (m.get('GroupName') or [{"Description": "Knockout"}])[0]['Description']
        home_obj = (m.get('Home') or {})
        away_obj = (m.get('Away') or {})
        home_team_obj = (m.get('HomeTeam') or {})
        away_team_obj = (m.get('AwayTeam') or {})
        home = home_obj.get('IdTeam') or home_team_obj.get('IdTeam')
        away = away_obj.get('IdTeam') or away_team_obj.get('IdTeam')
        home_abbr = home_obj.get('Abbreviation') or home_team_obj.get('Abbreviation')
        away_abbr = away_obj.get('Abbreviation') or away_team_obj.get('Abbreviation')
        if not home_abbr or not away_abbr or not group.startswith('Group'):
            continue
        for abbr in (home_abbr, away_abbr):
            groups[group][abbr]['team'] = normalize_team_name(abbr, team_names)
        status = m.get('MatchStatus')
        if status == 0:
            hs = int(m.get('HomeTeamScore') or 0)
            aw = int(m.get('AwayTeamScore') or 0)
            gh, ga = groups[group][home_abbr], groups[group][away_abbr]
            gh['played'] += 1; ga['played'] += 1
            gh['gf'] += hs; gh['ga'] += aw; ga['gf'] += aw; ga['ga'] += hs
            gh['gd'] = gh['gf'] - gh['ga']; ga['gd'] = ga['gf'] - ga['ga']
            if hs > aw:
                gh['wins'] += 1; ga['losses'] += 1; gh['points'] += 3
            elif hs < aw:
                ga['wins'] += 1; gh['losses'] += 1; ga['points'] += 3
            else:
                gh['draws'] += 1; ga['draws'] += 1; gh['points'] += 1; ga['points'] += 1
        else:
            info = {
                'home': home_abbr,
                'away': away_abbr,
                'host_team': 'home' if home_abbr in {'USA','MEX','CAN'} else ('away' if away_abbr in {'USA','MEX','CAN'} else None)
            }
            remaining[group].append(info)
    group_tables = {}
    points_only = {}
    for group, table in groups.items():
        ranked = rank_group_rows(table)
        group_tables[group] = [row for _, row in ranked]
        points_only[group] = {abbr: stats['points'] for abbr, stats in table.items()}
    return group_tables, remaining, points_only


def build_round_of_32(matches: list[dict], group_tables: dict) -> list[dict]:
    r32 = [m for m in matches if m.get('IdStage') == '289287']
    r32.sort(key=lambda m: int(m['MatchNumber']))
    group_letters = {name: name.split()[-1] for name in group_tables.keys()}
    third_rows = []
    for group_name, rows in group_tables.items():
        if len(rows) >= 3:
            row = dict(rows[2])
            row['group'] = group_letters[group_name]
            third_rows.append(row)
    third_rows.sort(key=lambda r: (r['points'], r['gd'], r['gf'], r['team']), reverse=True)
    selected_third_groups = sorted(r['group'] for r in third_rows[:THIRD_PLACE_ADVANCERS])
    third_lookup = {r['group']: r for r in third_rows[:THIRD_PLACE_ADVANCERS]}
    annex_c = load_annex_c_full()

    slots = []
    for m in r32:
        a = m.get('PlaceHolderA')
        b = m.get('PlaceHolderB')
        resolved = {'match_number': int(m['MatchNumber']), 'home_slot': a, 'away_slot': b, 'home_team': None, 'away_team': None}
        if a and len(a) == 2 and a[0] in {'1', '2'}:
            group_name = f"Group {a[1]}"
            idx = 0 if a[0] == '1' else 1
            rows = group_tables.get(group_name, [])
            if len(rows) > idx:
                resolved['home_team'] = rows[idx]['team']
        if b and len(b) == 2 and b[0] in {'1', '2'}:
            group_name = f"Group {b[1]}"
            idx = 0 if b[0] == '1' else 1
            rows = group_tables.get(group_name, [])
            if len(rows) > idx:
                resolved['away_team'] = rows[idx]['team']
        elif b and b.startswith('3'):
            grp = resolve_third_place_slot_from_annex_c(selected_third_groups, int(m['MatchNumber']), annex_c)
            if grp and grp in third_lookup:
                resolved['away_team'] = third_lookup[grp]['team']
                resolved['resolved_third_place_group'] = grp
            else:
                resolved['resolved_third_place_group'] = None
        slots.append(resolved)
    return slots


def simulate_group_stage(group_name: str, rows: list[dict], remaining_matches: list[dict], elo: dict[str, dict]) -> list[dict]:
    state = {}
    for row in rows:
        code = row.get('sort_team') or None
        if not code:
            continue
        state[code] = {
            'team': row['team'], 'played': row['played'], 'wins': row['wins'], 'draws': row['draws'], 'losses': row['losses'],
            'gf': row['gf'], 'ga': row['ga'], 'gd': row['gd'], 'points': row['points']
        }
    if not state:
        # fallback from rows without sort_team persisted in snapshot structure
        for row in rows:
            state[row['team']] = dict(row)
    for m in remaining_matches:
        h = m['home']; a = m['away']
        if h not in state or a not in state:
            continue
        host_boost = 55.0 if m.get('host_team') == 'home' else 0.0
        hxg, axg = expected_goals(elo.get(fifa_to_elo_code(h), {'elo':1700})['elo'], elo.get(fifa_to_elo_code(a), {'elo':1700})['elo'], host_boost)
        hg = max(0, min(10, random.poisson(hxg) if hasattr(random, 'poisson') else int(round(hxg + random.random()*1.6 - 0.8))))
        ag = max(0, min(10, random.poisson(axg) if hasattr(random, 'poisson') else int(round(axg + random.random()*1.6 - 0.8))))
        sh, sa = state[h], state[a]
        sh['played'] += 1; sa['played'] += 1
        sh['gf'] += hg; sh['ga'] += ag; sa['gf'] += ag; sa['ga'] += hg
        sh['gd'] = sh['gf'] - sh['ga']; sa['gd'] = sa['gf'] - sa['ga']
        if hg > ag:
            sh['wins'] += 1; sa['losses'] += 1; sh['points'] += 3
        elif ag > hg:
            sa['wins'] += 1; sh['losses'] += 1; sa['points'] += 3
        else:
            sh['draws'] += 1; sa['draws'] += 1; sh['points'] += 1; sa['points'] += 1
    ranked = sorted(state.items(), key=lambda item: (item[1]['points'], item[1]['gd'], item[1]['gf'], item[0]), reverse=True)
    return [{'code': code, **vals} for code, vals in ranked]


def sample_score_from_xg(hxg: float, axg: float) -> tuple[int, int]:
    def sample_one(lam: float) -> int:
        l = math.exp(-lam)
        k = 0
        p = 1.0
        while p > l and k < 10:
            k += 1
            p *= random.random()
        return max(0, k - 1)
    return sample_one(hxg), sample_one(axg)


def simulate_knockout_team(home_code: str, away_code: str, elo: dict[str, dict], host_boost: float = 0.0) -> str:
    hxg, axg = expected_goals(elo.get(fifa_to_elo_code(home_code), {'elo':1700})['elo'], elo.get(fifa_to_elo_code(away_code), {'elo':1700})['elo'], host_boost)
    hg, ag = sample_score_from_xg(hxg, axg)
    if hg > ag:
        return home_code
    if ag > hg:
        return away_code
    ehg, eag = sample_score_from_xg(hxg * 0.33, axg * 0.33)
    if hg + ehg > ag + eag:
        return home_code
    if ag + eag > hg + ehg:
        return away_code
    return home_code if random.random() < 0.5 else away_code


def build_group_code_rows(group_name: str, rows: list[dict], remaining: dict, elo: dict[str, dict]) -> list[dict]:
    code_rows = []
    current_codes = {}
    for m in remaining.get(group_name, []):
        current_codes[m['home']] = True
        current_codes[m['away']] = True
    for row in rows:
        matched = None
        for code in current_codes:
            if normalize_team_name(code, {}) == row['team'] or row['team'] == code:
                matched = code
                break
        if not matched:
            for code in elo.keys():
                if normalize_team_name(code, {}) == row['team']:
                    matched = code
                    break
        code_rows.append({'sort_team': matched or row['team'], **row})
    return code_rows


def simulate_group_outcomes(group_tables: dict, remaining: dict, elo: dict[str, dict]):
    simulated_groups = {}
    third_rows = []
    advances = Counter()
    for g, rows in group_tables.items():
        code_rows = build_group_code_rows(g, rows, remaining, elo)
        sim_rows = simulate_group_stage(g, code_rows, remaining.get(g, []), elo)
        simulated_groups[g] = sim_rows
        if len(sim_rows) >= 3:
            third = dict(sim_rows[2])
            third['group'] = g.split()[-1]
            third_rows.append(third)
        for row in sim_rows[:2]:
            advances[row['code']] += 1
    third_rows.sort(key=lambda r: (r['points'], r['gd'], r['gf'], r['code']), reverse=True)
    top_third = third_rows[:THIRD_PLACE_ADVANCERS]
    for row in top_third:
        advances[row['code']] += 1
    return simulated_groups, top_third, advances


def resolve_simulated_r32_pairings(simulated_groups: dict, top_third: list[dict], matches: list[dict]):
    annex = load_annex_c_full()
    third_lookup = {r['group']: r['code'] for r in top_third}
    combo = ''.join(sorted(third_lookup.keys()))
    row = annex.get(combo)
    if not row:
        return None, None
    slot_to_group = {ANNEX_C_COLUMN_ORDER[i]: row[i][1] for i in range(8)}
    slot_to_team = {}
    for g, sim_rows in simulated_groups.items():
        letter = g.split()[-1]
        slot_to_team[f'1{letter}'] = sim_rows[0]['code']
        slot_to_team[f'2{letter}'] = sim_rows[1]['code']
    r32_template = [m for m in matches if m.get('IdStage') == '289287']
    pairings = []
    for m in r32_template:
        match_no = int(m['MatchNumber'])
        home_slot, away_slot = m['PlaceHolderA'], m['PlaceHolderB']
        home = slot_to_team.get(home_slot)
        away = slot_to_team.get(away_slot)
        if not away and away_slot and away_slot.startswith('3'):
            third_group = slot_to_group.get(home_slot)
            away = third_lookup.get(third_group)
        if home and away:
            pairings.append({'match_number': match_no, 'home_code': home, 'away_code': away, 'home_slot': home_slot, 'away_slot': away_slot})
    return pairings, slot_to_team


def simulate_tournament(group_tables: dict, remaining: dict, matches: list[dict], elo: dict[str, dict], iterations: int = 5000) -> tuple[dict[str, dict[str, float]], dict[str, Counter], dict[str, dict[str, Counter]], dict[int, Counter], Counter]:
    counts = Counter()
    finals = Counter(); semis = Counter(); quarters = Counter(); advances_total = Counter()
    matchup_counter = defaultdict(Counter)
    path_counter = defaultdict(lambda: {'quarterfinal_opponents': Counter(), 'semifinal_opponents': Counter(), 'final_opponents': Counter()})
    bracket_slot_counter = defaultdict(Counter)
    champion_counter = Counter()
    for _ in range(iterations):
        simulated_groups, top_third, advances = simulate_group_outcomes(group_tables, remaining, elo)
        for team_code, n in advances.items():
            advances_total[team_code] += n
        pairings, _ = resolve_simulated_r32_pairings(simulated_groups, top_third, matches)
        if not pairings:
            continue
        r32_winners = {}
        for pairing in pairings:
            home = pairing['home_code']
            away = pairing['away_code']
            matchup_counter[home][away] += 1
            matchup_counter[away][home] += 1
            winner = simulate_knockout_team(home, away, elo, 55.0 if home in {'USA','MEX','CAN'} else 0.0)
            r32_winners[pairing['match_number']] = winner
            bracket_slot_counter[pairing['match_number']][winner] += 1
        r16_pairs = [(89,73,74),(90,75,76),(91,77,78),(92,79,80),(93,81,82),(94,83,84),(95,85,86),(96,87,88)]
        r16_winners = {}
        for match_no, a, b in r16_pairs:
            if a in r32_winners and b in r32_winners:
                left = r32_winners[a]
                right = r32_winners[b]
                winner = simulate_knockout_team(left, right, elo)
                loser = right if winner == left else left
                r16_winners[match_no] = winner
                bracket_slot_counter[match_no][winner] += 1
                quarters[winner] += 1
                path_counter[winner]['quarterfinal_opponents'][loser] += 1
        qf_pairs = [(97,89,90),(98,93,94),(99,91,92),(100,95,96)]
        qf_winners = {}
        for match_no, a, b in qf_pairs:
            if a in r16_winners and b in r16_winners:
                left = r16_winners[a]
                right = r16_winners[b]
                winner = simulate_knockout_team(left, right, elo)
                loser = right if winner == left else left
                qf_winners[match_no] = winner
                bracket_slot_counter[match_no][winner] += 1
                semis[winner] += 1
                path_counter[winner]['semifinal_opponents'][loser] += 1
        sf_pairs = [(101,97,98),(102,99,100)]
        sf_winners = {}
        for match_no, a, b in sf_pairs:
            if a in qf_winners and b in qf_winners:
                left = qf_winners[a]
                right = qf_winners[b]
                w = simulate_knockout_team(left, right, elo)
                l = right if w == left else left
                sf_winners[match_no] = w
                bracket_slot_counter[match_no][w] += 1
                finals[w] += 1
                path_counter[w]['final_opponents'][l] += 1
        if 101 in sf_winners and 102 in sf_winners:
            final_left = sf_winners[101]
            final_right = sf_winners[102]
            bracket_slot_counter[103][final_left] += 1
            bracket_slot_counter[103][final_right] += 1
            champion = simulate_knockout_team(final_left, final_right, elo)
            counts[champion] += 1
            champion_counter[champion] += 1
            finals[final_left] += 1
            finals[final_right] += 1
    probs = {}
    teams = set(list(counts.keys()) + list(finals.keys()) + list(semis.keys()) + list(quarters.keys()) + list(advances_total.keys()))
    for team in teams:
        probs[team] = {
            'win_world_cup': 100 * counts[team] / iterations,
            'reach_final': 100 * finals[team] / iterations,
            'reach_semifinal': 100 * semis[team] / iterations,
            'reach_quarterfinal': 100 * quarters[team] / iterations,
            'advance_from_group_or_r32': 100 * advances_total[team] / iterations,
        }
    return probs, matchup_counter, path_counter, bracket_slot_counter, champion_counter


def compute_forecast() -> ForecastSnapshot:
    cfg = load_config()
    now = datetime.now(ZoneInfo(cfg.get('timezone', TZ))).isoformat()
    team_names = get_team_dictionary()
    elo = load_world_elo(team_names)
    matches = load_fifa_matches()
    save_data_file('eloratings_world.tsv', fetch_text('https://eloratings.net/World.tsv'))
    save_data_file('fifa_matches_285023.json', matches)

    qualified_fifa_codes = get_qualified_fifa_codes(matches)
    qualified_elo_codes = {fifa_to_elo_code(code) for code in qualified_fifa_codes}
    ratings = []
    for code, rec in sorted(elo.items(), key=lambda kv: kv[1]['elo'], reverse=True):
        if code in qualified_elo_codes:
            ratings.append({'team': rec['team'], 'code': code, 'elo': round(rec['elo'], 1)})

    group_tables, remaining, points_only = build_group_tables(matches, team_names)

    advancement = {}
    for group, pts in points_only.items():
        # map remaining by home team for convenience
        rem_map = defaultdict(list)
        for item in remaining.get(group, []):
            rem_map[item['home']].append(item)
        advancement[group] = group_advancement_probs(pts, rem_map, elo, team_names)

    round_of_32 = build_round_of_32(matches, group_tables)

    sim_probs, matchup_counter, path_counter, bracket_slot_counter, champion_counter = simulate_tournament(group_tables, remaining, matches, elo, iterations=min(cfg['simulation_count'], 6000))
    title_odds = []
    for t in ratings:
        code = t['code']
        fifa_code = None
        for k, v in FIFA_TO_ELO.items():
            if v == code:
                fifa_code = k
                break
        p = sim_probs.get(fifa_code or code, sim_probs.get(code, {
            'win_world_cup': 0.0,
            'reach_final': 0.0,
            'reach_semifinal': 0.0,
            'reach_quarterfinal': 0.0,
            'advance_from_group_or_r32': 0.0,
        }))
        title_odds.append({
            'team': t['team'],
            'code': code,
            'win_world_cup': round(p['win_world_cup'], 1),
            'reach_final': round(p['reach_final'], 1),
            'reach_semifinal': round(p['reach_semifinal'], 1),
            'reach_quarterfinal': round(p['reach_quarterfinal'], 1),
            'advance_from_group_or_r32': round(p['advance_from_group_or_r32'], 1),
            'change_vs_yesterday': None,
        })
    title_odds.sort(key=lambda x: x['win_world_cup'], reverse=True)

    upcoming = []
    future = []
    for m in matches:
        if m.get('MatchStatus') != 0:
            future.append(m)
    future.sort(key=lambda m: m.get('Date'))
    for m in future[:8]:
        home_obj = (m.get('Home') or {})
        away_obj = (m.get('Away') or {})
        home_team_obj = (m.get('HomeTeam') or {})
        away_team_obj = (m.get('AwayTeam') or {})
        home = home_obj.get('Abbreviation') or home_team_obj.get('Abbreviation')
        away = away_obj.get('Abbreviation') or away_team_obj.get('Abbreviation')
        if not home or not away:
            continue
        host_boost = 55.0 if home in {'USA','MEX','CAN'} else 0.0
        hxg, axg = expected_goals(elo.get(fifa_to_elo_code(home), {'elo':1700})['elo'], elo.get(fifa_to_elo_code(away), {'elo':1700})['elo'], host_boost)
        hw, dr, aw, score = match_probs(hxg, axg)
        upcoming.append({
            'match': f"{match_team_display(home_obj or home_team_obj, team_names)} vs {match_team_display(away_obj or away_team_obj, team_names)}",
            'home_win': round(hw * 100, 1),
            'draw': round(dr * 100, 1),
            'away_win': round(aw * 100, 1),
            'most_likely_score': score,
            'why': 'Driven by public Elo baseline, host effect where relevant, and Poisson scoreline model.'
        })

    matchup_probs = []
    for team_code, opponents in matchup_counter.items():
        total = sum(opponents.values())
        if not total:
            continue
        team_name = normalize_team_name(team_code, team_names)
        opps = []
        for opp_code, count in opponents.most_common():
            opps.append({
                'opponent_code': fifa_to_elo_code(opp_code) if len(opp_code) == 3 else opp_code,
                'opponent_team': normalize_team_name(opp_code, team_names),
                'probability': round(100 * count / total, 1),
            })
        matchup_probs.append({
            'team_code': fifa_to_elo_code(team_code) if len(team_code) == 3 else team_code,
            'team': team_name,
            'possible_opponents': opps,
        })
    matchup_probs.sort(key=lambda x: x['team'])

    knockout_path_probs = []
    for team_code, stage_maps in path_counter.items():
        team_name = normalize_team_name(team_code, team_names)
        row = {'team_code': fifa_to_elo_code(team_code) if len(team_code) == 3 else team_code, 'team': team_name}
        for stage_key, label in [('quarterfinal_opponents', 'quarterfinal_opponents'), ('semifinal_opponents', 'semifinal_opponents'), ('final_opponents', 'final_opponents')]:
            counter = stage_maps[stage_key]
            total = sum(counter.values())
            vals = []
            if total:
                for opp_code, count in counter.most_common():
                    vals.append({
                        'opponent_code': fifa_to_elo_code(opp_code) if len(opp_code) == 3 else opp_code,
                        'opponent_team': normalize_team_name(opp_code, team_names),
                        'probability': round(100 * count / total, 1),
                    })
            row[label] = vals
        knockout_path_probs.append(row)
    knockout_path_probs.sort(key=lambda x: x['team'])

    bracket_slot_probs = {}
    for match_no, counter in bracket_slot_counter.items():
        total = sum(counter.values())
        if not total:
            continue
        bracket_slot_probs[str(match_no)] = [
            {
                'team_code': fifa_to_elo_code(team_code) if len(team_code) == 3 else team_code,
                'team': normalize_team_name(team_code, team_names),
                'probability': round(100 * count / total, 1),
            }
            for team_code, count in counter.most_common()
        ]
    if champion_counter:
        total = sum(champion_counter.values())
        bracket_slot_probs['champion'] = [
            {
                'team_code': fifa_to_elo_code(team_code) if len(team_code) == 3 else team_code,
                'team': normalize_team_name(team_code, team_names),
                'probability': round(100 * count / total, 1),
            }
            for team_code, count in champion_counter.most_common()
        ]

    notes = [
        'Initial working public-data forecast built from FIFA public match feed and World Football Elo baseline.',
        'Current title odds now come from a first tournament simulation pass, but the engine still needs calibration, cleanup, and expansion to the full configured simulation count.',
        'Round-of-32 third-place resolution is now driven by the full Annex C lookup recovered from FIFA public regulations plus the official feed placeholders, but full tournament title odds still need true simulation rather than heuristics.',
        'Round-of-32 matchup probabilities are estimated by simulating the remaining group-stage paths and counting how often each opponent pairing appears.',
        'Knockout path probabilities estimate the most likely quarterfinal, semifinal, and final opponents conditional on reaching each stage.'
    ]
    sources = [
        {'name': 'FIFA public match feed', 'url': 'https://api.fifa.com/api/v3/calendar/matches?count=500&idSeason=285023'},
        {'name': 'FIFA public tournament page API', 'url': 'https://cxm-api.fifa.com/fifaplusweb/api/pages/en/tournaments/mens/worldcup/canadamexicousa2026'},
        {'name': 'World Football Elo Ratings', 'url': 'https://eloratings.net/'},
        {'name': 'FIFA 2026 regulations PDF', 'url': 'https://digitalhub.fifa.com/m/636f5c9c6f29771f/original/FWC2026_regulations_EN.pdf'},
    ]
    return ForecastSnapshot(
        generated_at=now,
        simulation_count=cfg['simulation_count'],
        notes=notes,
        ratings=ratings,
        title_odds=title_odds,
        group_tables=group_tables,
        upcoming_matches=upcoming,
        round_of_32=round_of_32,
        round_of_32_matchup_probs=matchup_probs,
        knockout_path_probs=knockout_path_probs,
        bracket_slot_probs=bracket_slot_probs,
        sources=sources,
    )


def save_snapshot(snapshot: ForecastSnapshot) -> Path:
    ts = snapshot.generated_at.replace(':', '').replace('-', '')[:15]
    path = STATE / f'snapshot_{ts}.json'
    payload = asdict(snapshot)
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    (STATE / 'latest.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return path


def main() -> None:
    ensure_dirs()
    snapshot = compute_forecast()
    path = save_snapshot(snapshot)
    print(path)


if __name__ == '__main__':
    main()
