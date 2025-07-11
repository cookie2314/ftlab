import streamlit as st
import pandas as pd
import random
from math import pow
from itertools import permutations, combinations

def parse_teams(input_text):
    teams = {}
    lines = input_text.strip().splitlines()
    for line in lines:
        parts = line.split()
        if len(parts) != 3:
            st.error(f"팀 입력 형식 오류: '{line}'")
            return {}
        name, elo, points = parts[0], parts[1], parts[2]
        try:
            elo = float(elo)
            points = int(points)
        except ValueError:
            st.error(f"숫자 변환 오류: '{line}'")
            return {}
        teams[name] = {
            "기본Elo": elo,
            "승점": points,
            "홈Elo보정": 60
        }
    return teams

def parse_matches(input_text, teams):
    matches = []
    lines = input_text.strip().splitlines()
    team_names = set(teams.keys())
    for line in lines:
        parts = line.split()
        if len(parts) != 2:
            st.error(f"경기 입력 형식 오류: '{line}'")
            return []
        team1, team2 = parts[0], parts[1]
        if team1 not in team_names or team2 not in team_names:
            st.error(f"팀 이름 오류: '{team1}' 또는 '{team2}'가 등록된 팀이 아닙니다.")
            return []
        matches.append((team1, team2))
    return matches

def combined_elo(team, teams, is_home=False):
    base = teams[team]["기본Elo"]
    if is_home:
        base += teams[team].get("홈Elo보정", 0)
    return base

def win_prob(elo1, elo2):
    diff = (elo2 - elo1) * 1.2
    return 1 / (1 + 10 ** (diff / 400))

def draw_probability(elo1, elo2):
    diff = abs(elo1 - elo2)
    if diff >= 300:
        return 0.15
    elif diff >= 100:
        return 0.18
    else:
        return 0.26 - (diff / 100) * (0.26 - 0.23)

def match_probabilities(team1, team2, teams, p=1):
    elo1 = combined_elo(team1, teams, is_home=True)
    elo2 = combined_elo(team2, teams, is_home=False)
    base_win_prob = win_prob(elo1, elo2)
    base_lose_prob = 1 - base_win_prob
    draw_prob = draw_probability(elo1, elo2)
    win_prob_adj = pow(base_win_prob, p)
    lose_prob_adj = pow(base_lose_prob, 1/p)
    total = win_prob_adj + lose_prob_adj
    win_prob_final = win_prob_adj / total
    lose_prob_final = lose_prob_adj / total
    win_prob_final *= (1 - draw_prob)
    lose_prob_final *= (1 - draw_prob)
    return win_prob_final, draw_prob, lose_prob_final

def simulate_match(p1, p_draw, p2):
    r = random.random()
    if r < p1:
        return 3, 0
    elif r < p1 + p_draw:
        return 1, 1
    else:
        return 0, 3

def run_regular_league_sim(teams, matches, n_sim=1000):
    n_teams = len(teams)
    results = {team: {"순위별횟수": [0]*n_teams} for team in teams}
    for _ in range(n_sim):
        sim_points = {team: teams[team]["승점"] for team in teams}
        for team1, team2 in matches:
            p1, p_draw, p2 = match_probabilities(team1, team2, teams, p=1)
            s1, s2 = simulate_match(p1, p_draw, p2)
            sim_points[team1] += s1
            sim_points[team2] += s2
        sorted_teams = sorted(sim_points.items(), key=lambda x: x[1], reverse=True)
        for rank, (team, _) in enumerate(sorted_teams, start=1):
            results[team]["순위별횟수"][rank-1] += 1
    summary = {}
    for team in teams:
        rank_probs = [count / n_sim * 100 for count in results[team]["순위별횟수"]]
        summary[team] = rank_probs
    return summary

def generate_playoff_matches(playoff_teams):
    playoff_matches = []
    for home, away in permutations(playoff_teams, 2):
        if home != away and (home, away) not in playoff_matches:
            playoff_matches.append((home, away))
    return playoff_matches

def generate_playout_matches(playout_teams):
    matchups = list(combinations(playout_teams, 2))
    random.shuffle(matchups)
    home_counts = {team: 0 for team in playout_teams}
    away_counts = {team: 0 for team in playout_teams}
    matches = []
    for t1, t2 in matchups:
        if home_counts[t1] < 5 and away_counts[t2] < 5:
            matches.append((t1, t2))
            home_counts[t1] += 1
            away_counts[t2] += 1
        else:
            matches.append((t2, t1))
            home_counts[t2] += 1
            away_counts[t1] += 1
    return matches

def run_romania_split_sim(teams, matches, n_simulations):
    n_teams = len(teams)
    results = {team: {"순위별횟수": [0]*n_teams} for team in teams}
    for _ in range(n_simulations):
        sim_points = {team: teams[team]["승점"] for team in teams}
        for team1, team2 in matches:
            p1, p_draw, p2 = match_probabilities(team1, team2, teams, p=1)
            s1, s2 = simulate_match(p1, p_draw, p2)
            sim_points[team1] += s1
            sim_points[team2] += s2
        # 플레이오프/아웃 직전, 승점 반토막
        for team in sim_points:
            sim_points[team] = round(sim_points[team] / 2)
        sorted_teams = sorted(sim_points.items(), key=lambda x: x[1], reverse=True)
        playoff_teams = [team for team, _ in sorted_teams[:6]]
        playout_teams = [team for team, _ in sorted_teams[6:]]
        split_points = {team: sim_points[team] for team in teams}
        playoff_matches = generate_playoff_matches(playoff_teams)
        playout_matches = generate_playout_matches(playout_teams)
        for team1, team2 in playoff_matches:
            p1, p_draw, p2 = match_probabilities(team1, team2, teams, p=1)
            s1, s2 = simulate_match(p1, p_draw, p2)
            split_points[team1] += s1
            split_points[team2] += s2
        for team1, team2 in playout_matches:
            p1, p_draw, p2 = match_probabilities(team1, team2, teams, p=1)
            s1, s2 = simulate_match(p1, p_draw, p2)
            split_points[team1] += s1
            split_points[team2] += s2
        playoff_sorted = sorted([(team, split_points[team]) for team in playoff_teams], key=lambda x: x[1], reverse=True)
        playout_sorted = sorted([(team, split_points[team]) for team in playout_teams], key=lambda x: x[1], reverse=True)
        for rank, (team, _) in enumerate(playoff_sorted):
            results[team]["순위별횟수"][rank] += 1
        for idx, (team, _) in enumerate(playout_sorted):
            results[team]["순위별횟수"][idx+6] += 1  # 7~16위
    summary = {}
    for team in teams:
        rank_probs = [count / n_simulations * 100 for count in results[team]["순위별횟수"]]
        summary[team] = rank_probs
    return summary

def parse_range(s, n_teams):
    try:
        s = s.replace(" ", "").replace("~", "-")
        a, b = map(int, s.split("-"))
        a = max(1, min(a, n_teams))
        b = max(1, min(b, n_teams))
        if a > b:
            a, b = b, a
        return a-1, b-1  # 인덱스 변환
    except:
        return None

# --- Streamlit UI ---
st.title("🇷🇴 루마니아 리그 방식 시뮬레이션")

team_input = st.text_area("팀 정보 입력 (팀이름 Elo 승점)", height=120)
match_input = st.text_area("남은 정규리그 경기 입력 (팀1 팀2)", height=120)
n_simulations = st.number_input("플레이오프/아웃 시뮬레이션 횟수", min_value=100, value=1000, step=100)
range_input = st.text_input("확률 범위(예: 15~16)", value="15~16")

if st.button("시뮬레이션 실행"):
    teams = parse_teams(team_input)
    if not teams:
        st.stop()
    matches = parse_matches(match_input, teams)
    if not matches:
        st.stop()
    n_teams = len(teams)
    idx_range = parse_range(range_input, n_teams)
    if idx_range is None:
        st.error("순위 범위 입력이 올바르지 않습니다. 예: 15~16")
        st.stop()
    idx_start, idx_end = idx_range
    split_probs = run_romania_split_sim(teams, matches, int(n_simulations))
    team_order = sorted(teams.keys(), key=lambda t: split_probs[t][0], reverse=True)
    # 표 만들기
    columns = ["팀명"] + [f"{i+1}위 확률(%)" for i in range(n_teams)] + [f"{idx_start+1}~{idx_end+1}위 합계(%)"]
    table = []
    for team in team_order:
        range_prob = sum(split_probs[team][idx_start:idx_end+1])
        row = [team] + [f"{p:.2f}" for p in split_probs[team]] + [f"{range_prob:.2f}"]
        table.append(row)
    st.dataframe(pd.DataFrame(table, columns=columns), use_container_width=True)
