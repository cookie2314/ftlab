import streamlit as st
import pandas as pd
import random
from math import pow

# --- 데이터 파싱 함수 ---
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

# --- 시뮬레이션 함수들 ---
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

def run_split_league_sim(teams, matches, n_simulations):
    n_teams = len(teams)
    results = {team: {"순위별횟수": [0]*n_teams} for team in teams}
    for _ in range(n_simulations):
        sim_points = {team: teams[team]["승점"] for team in teams}
        for team1, team2 in matches:
            p1, p_draw, p2 = match_probabilities(team1, team2, teams, p=1)
            s1, s2 = simulate_match(p1, p_draw, p2)
            sim_points[team1] += s1
            sim_points[team2] += s2
        sorted_teams = sorted(sim_points.items(), key=lambda x: x[1], reverse=True)
        teams_order = [team for team, _ in sorted_teams]
        splitA_teams = teams_order[:6]
        splitB_teams = teams_order[6:]
        split_points = {team: sim_points[team] for team in teams}
        split_matches = []
        for i in range(6):
            for j in range(i+1, 6):
                t1, t2 = splitA_teams[i], splitA_teams[j]
                home_team, away_team = (t1, t2) if (i % 2 == 0) else (t2, t1)
                split_matches.append((home_team, away_team))
        for i in range(6):
            for j in range(i+1, 6):
                t1, t2 = splitB_teams[i], splitB_teams[j]
                home_team, away_team = (t1, t2) if (i % 2 == 0) else (t2, t1)
                split_matches.append((home_team, away_team))
        for team1, team2 in split_matches:
            p1, p_draw, p2 = match_probabilities(team1, team2, teams, p=1)
            s1, s2 = simulate_match(p1, p_draw, p2)
            split_points[team1] += s1
            split_points[team2] += s2
        final_sorted = sorted(split_points.items(), key=lambda x: x[1], reverse=True)
        for rank, (team, _) in enumerate(final_sorted, start=1):
            if team in splitA_teams and rank <= 6:
                results[team]["순위별횟수"][rank-1] += 1
            elif team in splitB_teams and rank >= 7:
                results[team]["순위별횟수"][rank-1] += 1
    summary = {}
    for team in teams:
        rank_probs = [count / n_simulations * 100 for count in results[team]["순위별횟수"]]
        summary[team] = rank_probs
    return summary

# --- Streamlit UI ---
st.title("🏆 K리그1 리그 + 스플릿 시뮬레이션")

team_input = st.text_area("팀 정보 입력 (팀이름 Elo 승점)", height=100)
match_input = st.text_area("남은 정규리그 경기 입력 (팀1 팀2)", height=100)
n_simulations = st.number_input("스플릿 시뮬레이션 횟수", min_value=500, value=1000, step=100)

if st.button("시뮬레이션 실행"):
    teams = parse_teams(team_input)
    if not teams:
        st.stop()
    matches = parse_matches(match_input, teams)
    if not matches:
        st.stop()
    regular_probs = run_regular_league_sim(teams, matches, n_sim=1000)
    split_probs = run_split_league_sim(teams, matches, n_simulations)
    n_teams = len(teams)
    team_order = sorted(teams.keys(), key=lambda t: regular_probs[t][0], reverse=True)

    # 정규리그 종료 확률
    st.markdown("### 정규리그 종료 순위 확률 (%)")
    df_regular = pd.DataFrame([
        {"팀명": team, **{f"{i+1}위": f"{prob:.2f}" for i, prob in enumerate(regular_probs[team])}}
        for team in team_order
    ])
    st.dataframe(df_regular, use_container_width=True)

    # 스플릿 종료 확률
    st.markdown("### 스플릿 종료 순위 확률 (%)")
    df_split = pd.DataFrame([
        {"팀명": team, **{f"{i+1}위": f"{prob:.2f}" for i, prob in enumerate(split_probs[team])}}
        for team in team_order
    ])
    st.dataframe(df_split, use_container_width=True)

    # 스플릿 A/B 진출 확률
    st.markdown("### 스플릿 A/B 진출 확률 (%)")
    ab_probs = []
    for team in team_order:
        prob_A = sum(regular_probs[team][0:6])
        prob_B = sum(regular_probs[team][6:]) if n_teams > 6 else 0.0
        ab_probs.append({"팀명": team, "스플릿A 진출 확률(%)": f"{prob_A:.2f}", "스플릿B 진출 확률(%)": f"{prob_B:.2f}"})
    st.dataframe(pd.DataFrame(ab_probs), use_container_width=True)
