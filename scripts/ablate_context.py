#!/usr/bin/env python3
"""Bağlam vektörü (c1–c7) ablasyonu — Düzlem A (Nav2-bağımsız sim).

Her konfigürasyonda seçilen boyutlar 0'a maskelenir (sinyal yok) ve
3 senaryo × N seed AHE koşulur. Maskeleme dominance güncellemesini,
kosinüs-uyumluluğu VE sert override'ları (c4 deadline, c5 arıza) birlikte
etkiler — yani boyutun uçtan-uca katkısı ölçülür.

Kullanım:
  python3 scripts/ablate_context.py --seeds 60
  python3 scripts/ablate_context.py --seeds 100 --configs full,-c3,-c7
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import simulate_and_tune as st  # noqa: E402

CTX_NAMES = ["c1_yoğunluk", "c2_uygunluk", "c3_batarya", "c4_deadline",
             "c5_arıza", "c6_işyükü", "c7_kararsızlık"]

_orig_build = st.EcosystemSimulator._build_context
MASK: set = set()


def _masked_build(self, s):
    ctx = _orig_build(self, s)
    for i in MASK:
        ctx[i] = 0.0
    return ctx


st.EcosystemSimulator._build_context = _masked_build

ALL_CONFIGS = (
    [("full", [])]
    + [(f"-c{i+1}", [i]) for i in range(7)]
    + [("-c2c3", [1, 2]), ("-c3c7", [2, 6]), ("-c2c3c7", [1, 2, 6])]
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=60)
    ap.add_argument("--configs", type=str, default="",
                    help="virgüllü alt küme (örn. full,-c3); boş = hepsi")
    args = ap.parse_args()

    configs = ALL_CONFIGS
    if args.configs:
        want = set(args.configs.split(","))
        configs = [c for c in ALL_CONFIGS if c[0] in want]

    print(f"=== Bağlam ablasyonu — {args.seeds} seed, 3r15t, AHE v4.2 ===")
    print(f"{'config':10s} | {'rf_fit':6s} {'ms_fit':6s} {'dp_fit':6s} | "
          f"{'rf_ins':6s} {'ms_ins':6s} {'dp_ins':6s} | rf_dvr ms_dvr dp_dvr")
    for name, dims in configs:
        MASK.clear()
        MASK.update(dims)
        fits, inss, dvrs = [], [], []
        for sc in ("robot_failure", "mixed_stress", "deadline_pressure"):
            r = st.benchmark(["ahe_mrta_v3"], sc, args.seeds)["ahe_mrta_v3"]
            fits.append(r["alloc_fitness"])
            inss.append(r["instability"])
            dvrs.append(r["deadline_violation_rate"])
        print(f"{name:10s} | {fits[0]:.3f}  {fits[1]:.3f}  {fits[2]:.3f} | "
              f"{inss[0]:.2f}   {inss[1]:.2f}   {inss[2]:.2f} | "
              f"{dvrs[0]:.3f}  {dvrs[1]:.3f}  {dvrs[2]:.3f}", flush=True)
    print("BITTI")


if __name__ == "__main__":
    main()
