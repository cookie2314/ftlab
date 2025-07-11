import tkinter as tk
from tkinter import ttk, messagebox
import random
from math import pow

def parse_teams(input_text):
    teams = {}
    lines = input_text.strip().splitlines()
    for line in lines:
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"팀 입력 형식 오류: '{line}' (팀이름 현재Elo 현재승점)")
        name, elo, points = parts[0], parts[1], parts[2]
        try:
            elo = float(elo)
            points = int(points)
        except ValueError:
            raise ValueError(f"숫자 변환 오류: '{line}'")
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
            raise ValueError(f"경기 입력 형식 오류: '{line}'")
        team1, team2 = parts[0], parts[1]
        if team1 not in team_names or team2 not in team_names:
            raise ValueError(f"팀 이름 오류: '{team1}' 또는 '{team2}'가 등록된 팀이 아닙니다.")
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

class SimulationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("축구 경기 시뮬레이션")
        self.root.geometry("1200x800")
        self.root.rowconfigure(4, weight=1)
        self.root.columnconfigure(0, weight=1)

        ttk.Label(root, text="팀 정보 입력 (팀이름 현재Elo 현재승점)").grid(row=0, column=0, padx=5, pady=5)
        self.team_text = tk.Text(root, width=40, height=10)
        self.team_text.grid(row=1, column=0, padx=5, pady=5)

        ttk.Label(root, text="경기 입력 (팀1 팀2)").grid(row=0, column=1, padx=5, pady=5)
        self.match_text = tk.Text(root, width=40, height=10)
        self.match_text.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(root, text="시뮬레이션 횟수").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.sim_entry = ttk.Entry(root)
        self.sim_entry.grid(row=2, column=0, padx=(100, 5), pady=5, sticky="w")
        self.sim_entry.insert(0, "1000")

        ttk.Label(root, text="확률 범위 (예: 3~6)").grid(row=2, column=1, padx=5, pady=5, sticky="e")
        self.range_entry = ttk.Entry(root, width=10)
        self.range_entry.grid(row=2, column=1, padx=(150, 5), pady=5, sticky="e")
        self.range_entry.insert(0, "3~6")

        self.run_btn = ttk.Button(root, text="시뮬레이션 실행", command=self.run_simulation)
        self.run_btn.grid(row=3, column=0, pady=10)

        self.update_btn = ttk.Button(root, text="범위만 적용", command=self.update_tree_with_range)
        self.update_btn.grid(row=3, column=1, pady=10)

        self.tree = None
        self.match_prob_tree = None
        self.summary = None

    def run_simulation(self):
        try:
            team_input = self.team_text.get("1.0", "end")
            self.teams = parse_teams(team_input)
            match_input = self.match_text.get("1.0", "end")
            self.matches = parse_matches(match_input, self.teams)
            n_simulations = int(self.sim_entry.get())
            if n_simulations <= 0:
                messagebox.showerror("오류", "시뮬레이션 횟수는 양의 정수여야 합니다.")
                return
        except Exception as e:
            messagebox.showerror("입력 오류", str(e))
            return
        self.run_btn.config(state="disabled")
        if self.tree:
            self.tree.destroy()
        if self.match_prob_tree:
            self.match_prob_tree.destroy()
        self.summary = run_simulation(self.teams, self.matches, n_simulations)
        self.build_prob_table()
        self.run_btn.config(state="normal")

    def update_tree_with_range(self):
        if not self.summary:
            messagebox.showerror("오류", "먼저 시뮬레이션을 실행하세요.")
            return
        if self.tree:
            self.tree.destroy()
        self.build_prob_table()

    def build_prob_table(self):
        try:
            range_text = self.range_entry.get()
            n_rank, m_rank = map(int, range_text.split("~"))
            if not (1 <= n_rank <= m_rank <= len(self.teams)):
                raise ValueError
        except:
            messagebox.showerror("입력 오류", "입력을 다시 확인하세요. 예: 3~6 형태로 입력해야 합니다.")
            return

        n_teams = len(self.teams)
        columns = ["팀명", "평균승점"] + [f"{i}위 확률(%)" for i in range(1, n_teams + 1)] + [f"{n_rank}~{m_rank}위 확률(%)"]

        frame = ttk.Frame(self.root)
        frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=30)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90 if col != "팀명" else 120, anchor="center")

        for team, data in sorted(self.summary.items(), key=lambda x: x[1]["평균승점"], reverse=True):
            rank_probs = data['순위별확률(%)']
            range_prob = sum(rank_probs[n_rank-1:m_rank])
            row = [team, f"{data['평균승점']:.2f}"]
            row += [f"{prob:.2f}" for prob in rank_probs]
            row += [f"{range_prob:.2f}"]
            self.tree.insert("", "end", values=row)

        prob_columns = ["경기", "승리 확률(%)", "무승부 확률(%)", "패배 확률(%)"]
        self.match_prob_tree = ttk.Treeview(self.root, columns=prob_columns, show="headings", height=10)
        for col in prob_columns:
            self.match_prob_tree.heading(col, text=col)
            self.match_prob_tree.column(col, width=100 if col != "경기" else 200, anchor="center")
        self.match_prob_tree.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

        for team1, team2 in self.matches:
            p1, p_draw, p2 = match_probabilities(team1, team2, self.teams, p=1)
            self.match_prob_tree.insert("", "end", values=[f"{team1} vs {team2}", f"{p1*100:.2f}", f"{p_draw*100:.2f}", f"{p2*100:.2f}"])

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationApp(root)
    root.mainloop()
