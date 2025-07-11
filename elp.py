import streamlit as st
import pandas as pd
import re
from collections import defaultdict

# --------------------- 상단 설정값 (ClubElo 방식) ---------------------
K_VALUE = 16
HFA = 50.0

# --------------------- 내부 데이터 구조 (Streamlit 세션에 저장) ---------------------
if 'elos' not in st.session_state:
    st.session_state['elos'] = defaultdict(lambda: 1500.0)
if 'tilts' not in st.session_state:
    st.session_state['tilts'] = defaultdict(lambda: 1.0)
if 'points' not in st.session_state:
    st.session_state['points'] = defaultdict(int)

elos = st.session_state['elos']
tilts = st.session_state['tilts']
points = st.session_state['points']

# --------------------- 승리 확률, G-factor ---------------------
def expected_score(dr: float) -> float:
    return 1 / (10 ** (-dr / 400) + 1)

def g_factor(goal_diff: int) -> float:
    if goal_diff <= 1:
        return 1.0
    if goal_diff == 2:
        return 1.5
    return (11 + goal_diff) / 8.0

# --------------------- Elo/승점 업데이트 ---------------------
def update_elo(home: str, away: str, home_goals: int, away_goals: int) -> None:
    home_adj_elo = elos[home] + HFA
    away_elo = elos[away]
    dr = home_adj_elo - away_elo
    expected_home = expected_score(dr)

    if home_goals > away_goals:
        result_home = 1.0
    elif home_goals == away_goals:
        result_home = 0.5
    else:
        result_home = 0.0

    diff = abs(home_goals - away_goals)
    g_fac = g_factor(diff)
    change = K_VALUE * g_fac * (result_home - expected_home)
    elos[home] += change
    elos[away] -= change

    # 승점 업데이트
    if home_goals > away_goals:
        points[home] += 3
    elif home_goals < away_goals:
        points[away] += 3
    else:
        points[home] += 1
        points[away] += 1

    # Tilt (원본 알고리즘)
    total_goals = home_goals + away_goals
    EXPECTED_GOALS = 2.5
    tilts[home] = 0.98 * tilts[home] + 0.02 * (total_goals / tilts[away] / EXPECTED_GOALS)
    tilts[away] = 0.98 * tilts[away] + 0.02 * (total_goals / tilts[home] / EXPECTED_GOALS)

# --------------------- 초기 입력 처리 ---------------------
def process_initial_elo(input_text):
    lines = input_text.strip().splitlines()
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 3:
            st.error(f"형식: 팀이름 Elo 승점 → {line}")
            continue
        team = " ".join(parts[:-2])
        try:
            elo_val = float(parts[-2])
            pts_val = int(parts[-1])
        except ValueError:
            st.error(f"Elo/승점 숫자 오류: {line}")
            continue
        elos[team] = elo_val
        points[team] = pts_val

# --------------------- 경기 결과 처리 ---------------------
def process_result(result_text):
    lines = result_text.strip().splitlines()
    for line in lines:
        match = re.match(r"(.+?) (\d+)-(\d+) (.+)", line)
        if not match:
            st.error(f"형식: 홈팀 2-1 원정팀 → {line}")
            continue
        home, hg, ag, away = match.groups()
        update_elo(home.strip(), away.strip(), int(hg), int(ag))

# --------------------- 출력 (DataFrame) ---------------------
def get_table():
    rows = []
    sorted_teams = sorted(elos.keys(), key=lambda t: (-points[t], -elos[t]))
    for team in sorted_teams:
        rows.append({
            "팀명": team,
            "Elo": round(elos[team], 1),
            "승점": points[team]
        })
    return pd.DataFrame(rows)

# --------------------- Streamlit UI ---------------------
st.title("⚽ ClubElo 스타일 Elo 계산기 (Streamlit 버전)")

st.markdown("#### 1. 초기 Elo 입력 (예시: Liverpool 1850 12)")
init_text = st.text_area(
    "팀이름 Elo 승점, 한 줄에 한 팀씩 입력 (예: Liverpool 1850 12)", height=120, key="elo_init_area"
)
if st.button("초기 Elo 설정"):
    process_initial_elo(init_text)
    st.success("초기 Elo와 승점이 반영되었습니다.")

st.markdown("#### 2. 경기 결과 입력 (예시: Liverpool 2-1 Chelsea)")
result_text = st.text_area(
    "경기 결과를 한 줄에 하나씩 입력 (예: Liverpool 2-1 Chelsea)", height=120, key="elo_match_area"
)
if st.button("경기 결과 반영"):
    process_result(result_text)
    st.success("경기 결과가 반영되었습니다.")

st.markdown("#### 3. 현재 Elo/승점 현황")
st.write(f"**홈 어드밴티지(HFA):** {HFA:.1f}, **K값:** {K_VALUE}")
st.dataframe(get_table(), use_container_width=True)

if st.button("초기화 (모든 Elo/승점 리셋)"):
    st.session_state['elos'] = defaultdict(lambda: 1500.0)
    st.session_state['tilts'] = defaultdict(lambda: 1.0)
    st.session_state['points'] = defaultdict(int)
    st.success("모든 데이터가 초기화되었습니다.")
