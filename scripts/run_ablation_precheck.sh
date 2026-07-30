#!/usr/bin/env bash
# B3 — ucuz ön-kontrol: dört ablasyon kolunu ÖNCE vekil düzlemde koş (dakikalar),
# sonra 34-69 saatlik Gazebo kampanyasına (B4) gir.
#
# Amacı sonuç üretmek değil, BAYRAKLARI DOĞRULAMAK: kollar birbirinin aynısı
# çıkarsa bayrak bağlanmamıştır ve bu 240 Gazebo koşusu harcanmadan anlaşılır.
# Kollar ayrışıyorsa yön bilgisi de bedava gelir (Gazebo'da doğrulanacak hipotez).
#
# NOT: vekil düzlem Nav2 gecikmesini, çarpışmayı ve sıkışmayı GÖSTERMEZ.  Buradaki
# fark yokluğu Gazebo'da fark yokluğu anlamına gelmez; bu yüzden B4 yine koşar.
set -eo pipefail
cd /home/oguz/multi_ahe
source install/setup.bash

# Vekil düzlem env'i — bunlar olmadan sim Öklid mesafeye düşer ve yayımlanan
# geodezik sayılarla uyuşmaz (results/README.md).
export AHE_SIM_GEODESIC_EXECUTION=1 AHE_F58_GEODESIC=1 AHE_F58_FAIR_REPAIR=1 \
       AHE_F58_FAIR_RESERVATION_GAP=2 AHE_F58_FAIR_EXTRA_QUEUE=1 \
       AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3

SEEDS="${1:-60}"

run_arm() {   # etiket  [ek bayrak ataması...]
    local label="$1"; shift
    echo "── kol: $label  (ek bayrak: ${*:-yok})"
    ( export "$@" 2>/dev/null || true
      python3 scripts/simulate_and_tune.py \
          --seeds "$SEEDS" --robots 5 --tasks 25 --scenario all \
          --method ahe_mrta_v3 --save-fitness-runs \
          --fitness-summary-name "sim_ablation_${label}.csv" >/dev/null )
}

run_arm full
run_arm no-override  AHE_NO_OVERRIDE=1
run_arm fixed-EDF    AHE_FORCE_PARADIGM=2
run_arm fixed-orphan AHE_FORCE_PARADIGM=4

python3 - "$SEEDS" <<'PY'
import csv, sys, itertools
from statistics import mean
try:
    from scipy.stats import wilcoxon
except ImportError:
    wilcoxon = None

ARMS = ['full', 'no-override', 'fixed-EDF', 'fixed-orphan']
P = 'results/processed/sim_ablation_%s_seedwise.csv'

def load(arm):
    d = {}
    for r in csv.DictReader(open(P % arm)):
        d[(r['scenario'], int(r['seed']))] = float(r['alloc_fitness'])
    return d

data = {a: load(a) for a in ARMS}
scenarios = sorted({k[0] for k in data['full']})
print(f"\n{'='*70}\nB3 ÖN-KONTROL — vekil düzlem, {sys.argv[1]} tohum, AHE tek yöntem")
print(f"{'='*70}")

for sc in scenarios:
    print(f"\n{sc}")
    keys = sorted(k for k in data['full'] if k[0] == sc)
    for a in ARMS:
        print(f"  {a:14s} fitness {mean(data[a][k] for k in keys):.6f}")
    base = [data['full'][k] for k in keys]
    for a in ARMS[1:]:
        other = [data[a][k] for k in keys]
        ndiff = sum(1 for x, y in zip(base, other) if x != y)
        line = f"  full vs {a:14s} farklı tohum: {ndiff:3d}/{len(keys)}"
        if wilcoxon and ndiff:
            line += f"   p={wilcoxon(base, other).pvalue:.4f}"
        print(line)

total_diff = sum(
    1 for a in ARMS[1:] for k in data['full'] if data['full'][k] != data[a][k])
print(f"\n{'='*70}")
if total_diff == 0:
    print("SONUÇ: HİÇBİR KOL AYRIŞMADI — bayraklar bağlanmamış. B4'E GİRME.")
    sys.exit(1)
print(f"SONUÇ: kollar ayrışıyor ({total_diff} tohum-hücresi). Bayraklar bağlı; B4 koşulabilir.")
PY
