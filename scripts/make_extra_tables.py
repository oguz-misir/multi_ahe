#!/usr/bin/env python3
"""Ek LaTeX tabloları üretir (Q1 zenginleştirme):
  1. efficiency: workload balance, decision latency, comm msgs/bytes, travel dist
  2. effect_size: Cliff's delta özeti (proposed vs her baseline, her senaryo)
İngilizce + Türkçe başlık varyantları.
"""
import pandas as pd
from pathlib import Path

PROC = Path("results/processed")
STATS = Path("results/stats")
STATS.mkdir(exist_ok=True)

METHOD_ORDER = ["ahe_mrta_v3", "big_mrta", "rostam_ea", "consensus_dbta"]
METHOD_LABEL = {
    "ahe_mrta_v3": r"\textbf{AHE-MRTA*}",
    "big_mrta": "BiG-MRTA",
    "rostam_ea": "RoSTAM-EA",
    "consensus_dbta": "Cons-DBTA",
}
SCEN_ORDER = ["robot_failure", "mixed_stress", "deadline_pressure"]
SCEN_LABEL = {
    "robot_failure": r"\textit{Scenario: robot\_failure}",
    "mixed_stress": r"\textit{Scenario: mixed\_stress}",
    "deadline_pressure": r"\textit{Scenario: deadline\_pressure}",
}
SCEN_LABEL_TR = {
    "robot_failure": r"\textit{Senaryo: robot\_failure}",
    "mixed_stress": r"\textit{Senaryo: mixed\_stress}",
    "deadline_pressure": r"\textit{Senaryo: deadline\_pressure}",
}

df = pd.read_csv(PROC / "all_summary.csv")

# ---- 1. Efficiency table ----
def efficiency_table(scen_label_map, caption, label, fname):
    g = df.groupby(["scenario", "strategy"]).agg(
        wlb=("workload_balance", "mean"),
        lat=("mean_decision_latency_ms", "mean"),
        msg=("communication_messages", "mean"),
        dist=("total_travel_distance", "mean"),
    ).reset_index()
    lines = [
        r"\begin{table}[t]", r"\centering",
        rf"\caption{{{caption}}}", rf"\label{{{label}}}",
        r"\small",
        r"\begin{tabular}{lrrrr}", r"\toprule",
        r"\textbf{Method} & \textbf{WLBal$\uparrow$} & "
        r"\textbf{Lat$\downarrow$(ms)} & \textbf{Msgs$\downarrow$} & "
        r"\textbf{Dist$\downarrow$(m)} \\", r"\midrule",
    ]
    for sc in SCEN_ORDER:
        lines.append(rf"\multicolumn{{5}}{{l}}{{{scen_label_map[sc]}}} \\")
        sub = g[g.scenario == sc].set_index("strategy")
        for m in METHOD_ORDER:
            if m not in sub.index:
                continue
            r = sub.loc[m]
            bold = m == "ahe_mrta_v3"
            fmt = (lambda x: rf"\textbf{{{x}}}") if bold else (lambda x: x)
            lines.append(
                f"{METHOD_LABEL[m]} & {fmt(f'{r.wlb:.3f}')} & "
                f"{fmt(f'{r.lat:.2f}')} & {fmt(f'{r.msg:.0f}')} & "
                f"{fmt(f'{r.dist:.1f}')} \\\\"
            )
        if sc != SCEN_ORDER[-1]:
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    (STATS / fname).write_text("\n".join(lines))
    print(f"[OK] {fname}")

# ---- 2. Effect-size table (Cliff's delta) ----
def effect_size_table(scen_label_map, caption, label, fname, note):
    st = pd.read_csv(STATS / "stat_tests.csv")
    key_metrics = ["task_completion_rate", "deadline_violation_rate",
                   "failure_recovery_time", "allocation_instability"]
    mlabel = {"task_completion_rate": "CR", "deadline_violation_rate": "DVR",
              "failure_recovery_time": "RecT", "allocation_instability": "Instab"}
    lines = [
        r"\begin{table}[t]", r"\centering",
        rf"\caption{{{caption}}}", rf"\label{{{label}}}",
        r"\small",
        r"\begin{tabular}{llrrr}", r"\toprule",
        r"\textbf{Metric} & \textbf{vs} & \textbf{BiG} & "
        r"\textbf{RoSTAM} & \textbf{Cons-DBTA} \\", r"\midrule",
    ]
    for sc in SCEN_ORDER:
        lines.append(rf"\multicolumn{{5}}{{l}}{{{scen_label_map[sc]}}} \\")
        for met in key_metrics:
            row = st[(st.scenario == sc) & (st.metric == met)]
            if row.empty:
                continue
            cells = {}
            for _, r in row.iterrows():
                cells[r.baseline] = f"{r.cliffs_delta:+.2f}{r.stars if isinstance(r.stars,str) else ''}"
            lines.append(
                f"{mlabel[met]} & $\\delta$ & "
                f"{cells.get('big_mrta','--')} & "
                f"{cells.get('rostam_ea','--')} & "
                f"{cells.get('consensus_dbta','--')} \\\\"
            )
        if sc != SCEN_ORDER[-1]:
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}",
              rf"\\[2pt]\footnotesize {note}", r"\end{table}", ""]
    (STATS / fname).write_text("\n".join(lines))
    print(f"[OK] {fname}")

# EN
efficiency_table(
    SCEN_LABEL,
    "Efficiency metrics (Gazebo, 3 robots, 15 tasks, 5 seeds). "
    "WLBal: Jain workload balance; Lat: mean decision latency; "
    "Msgs: allocation messages; Dist: total travel distance.",
    "tab:efficiency", "latex_efficiency_table.tex")
effect_size_table(
    SCEN_LABEL,
    "Effect sizes (Cliff's $\\delta$) of AHE-MRTA* vs each baseline on "
    "primary metrics. $\\delta>0$ favors AHE-MRTA*. "
    "$^{*}p{<}0.05$ (uncorrected Mann-Whitney U).",
    "tab:effectsize", "latex_effectsize_table.tex",
    "Positive $\\delta$ = AHE-MRTA* better; magnitude $|\\delta|{>}0.47$ = large.")

# TR
efficiency_table(
    SCEN_LABEL_TR,
    "Verimlilik metrikleri (Gazebo, 3 robot, 15 g\\\"orev, 5 tohum). "
    "WLBal: Jain i\\c{s} y\\\"uk\\\"u dengesi; Lat: ortalama karar gecikmesi; "
    "Msgs: tahsis mesajlar\\i; Dist: toplam yol mesafesi.",
    "tab:efficiency", "latex_efficiency_table_tr.tex")
effect_size_table(
    SCEN_LABEL_TR,
    "Etki b\\\"uy\\\"ukl\\\"ukleri (Cliff $\\delta$): AHE-MRTA* vs her "
    "temel y\\\"ontem, birincil metrikler. $\\delta>0$ AHE-MRTA* lehine. "
    "$^{*}p{<}0.05$ (d\\\"uzeltilmemi\\c{s} Mann-Whitney U).",
    "tab:effectsize", "latex_effectsize_table_tr.tex",
    "Pozitif $\\delta$ = AHE-MRTA* daha iyi; $|\\delta|{>}0.47$ = b\\\"uy\\\"uk etki.")

print("[DONE]")
