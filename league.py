import streamlit as st
import pandas as pd
import random
from math import pow

# --- 유틸 함수들 ---
def parse_teams(input_text):
    teams = {}
    lines = input_text.strip().splitlines()
    for line in lines:
        parts = line.split()
        if len(parts) != 3:
            st.error(f"팀 입력 형식 오류: '{line}' (팀이름 현재Elo 현재승점)")
            return {}
        name, elo, points = parts[0], parts[1], parts[2]
        try:
            elo = float(elo)
            points = int(points)
        except ValueError:
            st.error(f"숫자 변환 오류: '{line}'")
            return {}
        teams[name] = {
            "Elo": elo,
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
    base = teams[team]["Elo"]
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

def run_simulation(teams, matches, n_simulations):
    n_teams = len(teams)
    results = {team: {"순위합": 0, "1위횟수": 0, "총승점": 0, "순위별횟수": [0]*n_teams} for team in teams}
    for _ in range(n_simulations):
        sim_points = {team: teams[team]["승점"] for team in teams}
        for team1, team2 in matches:
            p1, p_draw, p2 = match_probabilities(team1, team2, teams, p=1)
            s1, s2 = simulate_match(p1, p_draw, p2)
            sim_points[team1] += s1
            sim_points[team2] += s2
        sorted_teams = sorted(sim_points.items(), key=lambda x: x[1], reverse=True)
        for rank, (team, pts) in enumerate(sorted_teams, start=1):
            results[team]["순위합"] += rank
            results[team]["총승점"] += pts
            results[team]["순위별횟수"][rank-1] += 1
        max_pts = sorted_teams[0][1]
        for team, pts in sorted_teams:
            if pts == max_pts:
                results[team]["1위횟수"] += 1
            else:
                break
    summary = {}
    for team in teams:
        n = n_simulations
        rank_probs = [count / n * 100 for count in results[team]["순위별횟수"]]
        summary[team] = {
            "우승확률(%)": results[team]["1위횟수"] / n * 100,
            "평균순위": results[team]["순위합"] / n,
            "평균승점": results[team]["총승점"] / n,
            "순위별확률(%)": rank_probs,
        }
    return summary

# --- Streamlit UI ---
st.title("⚽ 축구 리그 시뮬레이터")

team_input = st.text_area("📝 팀 정보 입력 (형식: 팀이름 Elo 승점)", height=150)
match_input = st.text_area("📅 경기 일정 입력 (형식: 팀1 팀2)", height=150)
n_simulations = st.number_input("🔁 시뮬레이션 횟수", min_value=100, step=100, value=1000)
range_input = st.text_input("📊 순위 범위 (예: 3~6)", value="3~6")

if st.button("🚀 시뮬레이션 실행"):
    teams = parse_teams(team_input)
    if not teams:
        st.stop()
    matches = parse_matches(match_input, teams)
    if not matches:
        st.stop()
    summary = run_simulation(teams, matches, n_simulations)
    try:
        n_rank, m_rank = map(int, range_input.split("~"))
    except:
        st.error("⚠️ 범위 입력 오류. 예: 3~6")
        st.stop()

    data = []
    for team, data_dict in sorted(summary.items(), key=lambda x: x[1]["평균승점"], reverse=True):
        rank_probs = data_dict["순위별확률(%)"]
        range_prob = sum(rank_probs[n_rank-1:m_rank])
        row = {
            "팀명": team,
            "평균승점": round(data_dict["평균승점"], 2),
            **{f"{i+1}위 확률(%)": round(prob, 2) for i, prob in enumerate(rank_probs)},
            f"{n_rank}~{m_rank}위 확률(%)": round(range_prob, 2)
        }
        data.append(row)
    df = pd.DataFrame(data)
    st.dataframe(df)

    st.subheader("📈 경기별 승/무/패 확률")
    match_probs = []
    for team1, team2 in matches:
        p1, p_draw, p2 = match_probabilities(team1, team2, teams, p=1)
        match_probs.append({
            "경기": f"{team1} vs {team2}",
            "승리 확률(%)": round(p1 * 100, 2),
            "무승부 확률(%)": round(p_draw * 100, 2),
            "패배 확률(%)": round(p2 * 100, 2)
        })
    st.dataframe(pd.DataFrame(match_probs))
