import streamlit as st
import pandas as pd
import random

def elo_win_prob(elo_A, elo_B, k=400):
    return 1 / (1 + 10 ** ((elo_B - elo_A) / k))

def simulate_score(elo_A, elo_B, draw_rate=0.24):
    P = elo_win_prob(elo_A, elo_B)
    d = draw_rate
    r = random.random()
    if r < d:
        return random.choice([(0, 0), (1, 1), (2, 2)])
    p_A = max(0.0, P - d / 2)
    if r < d + p_A:
        margin = random.randint(1, 3)
        goals_A = margin
        goals_B = random.randint(0, margin - 1)
        return goals_A, goals_B
    margin = random.randint(1, 3)
    goals_B = margin
    goals_A = random.randint(0, margin - 1)
    return goals_A, goals_B

def parse_teams(txt):
    teams = {}
    for line in txt.strip().splitlines():
        parts = line.split()
        if len(parts) != 4:
            st.error(f"팀 입력 형식 오류: '{line}' (팀, Elo, 현재승점, 골득실)")
            return {}
        name, elo, pts, gd = parts
        teams[name] = {"Elo": float(elo), "승점": int(pts), "골득실": int(gd)}
    return teams

def parse_matches(txt, teams):
    matches = []
    for line in txt.strip().splitlines():
        if not line.strip():
            continue
        a, b = line.split()
        if a not in teams or b not in teams:
            st.error(f"등록되지 않은 팀: {a} 또는 {b}")
            return []
        matches.append((a, b))
    return matches

def run_simulation(teams, matches, sims):
    n = len(teams)
    stats = {t: {"순위합": 0, "1위횟수": 0, "총승점": 0, "총골득실": 0, "순위별횟수": [0] * n} for t in teams}

    for _ in range(sims):
        pts = {t: teams[t]["승점"] for t in teams}
        gd = {t: teams[t]["골득실"] for t in teams}
        head_pts = {t: {o: 0 for o in teams} for t in teams}
        head_gd = {t: {o: 0 for o in teams} for t in teams}

        for a, b in matches:
            g1, g2 = simulate_score(teams[a]["Elo"], teams[b]["Elo"])
            # 승점 배분
            if g1 > g2:
                pts[a] += 3
                head_pts[a][b] += 3
            elif g1 < g2:
                pts[b] += 3
                head_pts[b][a] += 3
            else:
                pts[a] += 1; pts[b] += 1
                head_pts[a][b] += 1; head_pts[b][a] += 1
            # 골득실 갱신
            diff = g1 - g2
            gd[a] += diff; gd[b] -= diff
            head_gd[a][b] += diff; head_gd[b][a] -= diff

        # 동률 그룹화
        grouped = {}
        for t, p in pts.items():
            grouped.setdefault(p, []).append(t)
        ordered_pts = sorted(grouped.keys(), reverse=True)

        rank_order = []
        for p in ordered_pts:
            grp = grouped[p]
            if len(grp) == 1:
                rank_order.extend(grp)
            else:
                tmp = []
                for t in grp:
                    hp = sum(head_pts[t][o] for o in grp if o != t)
                    hg = sum(head_gd[t][o] for o in grp if o != t)
                    tmp.append((t, hp, hg, gd[t]))
                sorted_grp = sorted(tmp, key=lambda x: (x[1], x[2], x[3]), reverse=True)
                rank_order.extend([t for t, *_ in sorted_grp])

        # 통계 집계
        for idx, t in enumerate(rank_order, start=1):
            stats[t]["순위합"] += idx
            stats[t]["총승점"] += pts[t]
            stats[t]["총골득실"] += gd[t]
            stats[t]["순위별횟수"][idx-1] += 1
        stats[rank_order[0]]["1위횟수"] += 1

    summary = {}
    for t in teams:
        summary[t] = {
            "우승확률(%)": stats[t]["1위횟수"] / sims * 100,
            "평균순위": stats[t]["순위합"] / sims,
            "평균승점": stats[t]["총승점"] / sims,
            "평균골득실": stats[t]["총골득실"] / sims,
            "순위별확률(%)": [cnt / sims * 100 for cnt in stats[t]["순위별횟수"]]
        }
    return summary

# --- Streamlit UI ---
st.title("🏆 동아시안컵 시뮬레이션")

team_txt = st.text_area("팀 정보 (팀 Elo 승점 골득실)", height=100)
match_txt = st.text_area("경기 (팀A 팀B)", height=100)
sims = st.number_input("시뮬레이션 횟수", min_value=100, value=1000, step=100)

if st.button("실행"):
    teams = parse_teams(team_txt)
    if not teams:
        st.stop()
    matches = parse_matches(match_txt, teams)
    if not matches:
        st.stop()
    res = run_simulation(teams, matches, int(sims))
    n = len(teams)
    columns = ["팀", "우승%", "평균순위", "평균승점", "평균골득실"] + [f"{i}위%" for i in range(1, n + 1)]
    rows = []
    for t, d in sorted(res.items(), key=lambda item: item[1]["평균순위"]):
        row = [t,
               f"{d['우승확률(%)']:.1f}",
               f"{d['평균순위']:.2f}",
               f"{d['평균승점']:.1f}",
               f"{d['평균골득실']:.1f}"] + [f"{p:.1f}" for p in d["순위별확률(%)"]]
        rows.append(row)
    st.dataframe(pd.DataFrame(rows, columns=columns), use_container_width=True)
