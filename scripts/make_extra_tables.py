#!/usr/bin/env python3
"""Ek LaTeX tabloları üretir (Q1 zenginleştirme):
  1. efficiency: workload balance, decision latency, comm msgs/bytes, travel dist
  2. effect_size: Cliff's delta özeti (proposed vs her baseline, her senaryo)
İngilizce + Türkçe başlık varyantları.
"""
import pandas as pd
from pathlib import Path

PROC = Path("results/processed")
STATS = Path("results/stats")          # data artefacts (stat_tests.csv) read from here
STATS.mkdir(exist_ok=True)
TABLE_DIR = Path("paper/table")        # LaTeX tables written next to the paper
TABLE_DIR.mkdir(parents=True, exist_ok=True)

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
    # Efficiency table is reported at the 3-robot scale (densities 9/15/24
    # pooled, n=15 per cell). all_summary.csv pools all scales, so filter here;
    # without it the means would mix 3r/5r/10r and contradict the caption.
    src = df[df["robot_count"] == 3] if "robot_count" in df.columns else df
    g = src.groupby(["scenario", "strategy"]).agg(
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
    # (column key, decimals, higher_is_better) — drives best-cell bolding
    col_spec = [("wlb", 3, True), ("lat", 2, False),
                ("msg", 0, False), ("dist", 1, False)]
    for sc in SCEN_ORDER:
        lines.append(rf"\multicolumn{{5}}{{l}}{{{scen_label_map[sc]}}} \\")
        sub = g[g.scenario == sc].set_index("strategy")
        # bold the best cell per column (direction-aware, on displayed value);
        # the AHE row name stays bold via METHOD_LABEL, but values are only
        # emphasised where they are actually best — even for a baseline.
        best = {}
        for key, dec, higher in col_spec:
            vals = {m: round(float(sub.loc[m, key]), dec)
                    for m in METHOD_ORDER if m in sub.index}
            if len(set(vals.values())) <= 1:
                best[key] = set()
            else:
                tgt = max(vals.values()) if higher else min(vals.values())
                best[key] = {m for m, v in vals.items() if v == tgt}
        for m in METHOD_ORDER:
            if m not in sub.index:
                continue
            r = sub.loc[m]
            cell = lambda key, x, _m=m: rf"\textbf{{{x}}}" if _m in best[key] else x
            lines.append(
                f"{METHOD_LABEL[m]} & {cell('wlb', f'{r.wlb:.3f}')} & "
                f"{cell('lat', f'{r.lat:.2f}')} & {cell('msg', f'{r.msg:.0f}')} & "
                f"{cell('dist', f'{r.dist:.1f}')} \\\\"
            )
        if sc != SCEN_ORDER[-1]:
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    (TABLE_DIR / fname).write_text("\n".join(lines))
    print(f"[OK] {fname}")

# ---- 2. Effect-size table (Cliff's delta) ----
def effect_size_table(scen_label_map, caption, label, fname, note):
    st = pd.read_csv(STATS / "stat_tests.csv")
    key_metrics = ["task_completion_rate", "deadline_violation_rate",
                   "failure_recovery_time", "redispatch_per_task"]
    mlabel = {"task_completion_rate": "CR", "deadline_violation_rate": "DVR",
              "failure_recovery_time": "RecT", "redispatch_per_task": "Churn"}
    # lower-better metrics: flip sign so that delta>0 always favours AHE,
    # matching the caption's stated convention
    flip = {"task_completion_rate": 1, "deadline_violation_rate": -1,
            "failure_recovery_time": -1, "redispatch_per_task": -1}
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
                d = flip[met] * r.cliffs_delta
                cells[r.baseline] = f"{d:+.2f}{r.stars if isinstance(r.stars,str) and r.stars not in ('ns','—') else ''}"
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
    (TABLE_DIR / fname).write_text("\n".join(lines))
    print(f"[OK] {fname}")

# EN
efficiency_table(
    SCEN_LABEL,
    "Efficiency metrics (Gazebo, 3-robot scale; densities 9/15/24 pooled, $n{=}15$ per cell). "
    "WLBal: all-robot Jain workload balance; Lat: mean decision latency; "
    "Msgs: allocation messages; Dist: total travel distance. "
    "Best value per column (within scenario) in \\textbf{bold}.",
    "tab:efficiency", "latex_efficiency_table.tex")
effect_size_table(
    SCEN_LABEL,
    "Effect sizes (Cliff's $\\delta$) of AHE-MRTA* vs each baseline on "
    "primary metrics. $\\delta>0$ favors AHE-MRTA*. "
    "$^{*}p{<}0.05$ (Mann--Whitney U, Bonferroni-corrected within scenario family).",
    "tab:effectsize", "latex_effectsize_table.tex",
    "Positive $\\delta$ = AHE-MRTA* better; magnitude $|\\delta|{>}0.47$ = large.")

# TR
efficiency_table(
    SCEN_LABEL_TR,
    "Verimlilik metrikleri (Gazebo, 3 robot \\\"ol\\c{c}e\\u{g}i; 9/15/24 yo\\u{g}unluk havuzu, h\\\"ucre ba\\c{s}\\i na $n{=}15$). "
    "WLBal: t\\\"um-robot Jain i\\c{s} y\\\"uk\\\"u dengesi; Lat: ortalama karar gecikmesi; "
    "Msgs: tahsis mesajlar\\i; Dist: toplam yol mesafesi. "
    "Her s\\\"utunda en iyi de\\u{g}er \\textbf{kal\\i n}.",
    "tab:efficiency", "latex_efficiency_table_tr.tex")
effect_size_table(
    SCEN_LABEL_TR,
    "Etki b\\\"uy\\\"ukl\\\"ukleri (Cliff $\\delta$): AHE-MRTA* vs her "
    "temel y\\\"ontem, birincil metrikler. $\\delta>0$ AHE-MRTA* lehine. "
    "$^{*}p{<}0.05$ (d\\\"uzeltilmemi\\c{s} Mann-Whitney U).",
    "tab:effectsize", "latex_effectsize_table_tr.tex",
    "Pozitif $\\delta$ = AHE-MRTA* daha iyi; $|\\delta|{>}0.47$ = b\\\"uy\\\"uk etki.")

print("[DONE]")
