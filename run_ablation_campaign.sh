#!/usr/bin/env bash
# B4 — eşleşmiş Gazebo ablasyonu (4 kol) + D2 — birincil ölçeği n=20'ye çıkarma.
#
# Tasarım ve hipotezler kampanyadan ÖNCE kilitlendi: paper/PREREGISTRATION.md.
# Bu sürücü o belgeyi uygular; kol/tohum/senaryo listesini değiştirmek ön-kaydı
# geçersiz kılar.
#
# 420 koşu ≈ 34-69 saat (medyan 4.9 dk/koşu, ağır kuyruk).  run_experiments_robust.sh
# SKIP_DONE=1 ile çalışır: donma/çökme/reboot sonrası bu script yeniden
# başlatıldığında DONE olan hücreleri atlar, kaldığı yerden sürer.
set -eo pipefail
cd /home/oguz/multi_ahe
source scripts/exp_lib.sh

# Yayımlanan temel ortam — dört kol da bunu paylaşır.  Kol farkı yalnız
# aşağıdaki run_arm çağrılarında verilen ek bayraktır.
export AHE_F58_GEODESIC=1 AHE_F58_FAIR_REPAIR=1 \
       AHE_F58_FAIR_RESERVATION_GAP=2 AHE_F58_FAIR_EXTRA_QUEUE=1 \
       AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3 \
       AHE_WARMUP=1

OUT=/home/oguz/multi_ahe/results/raw/gazebo_ablation
SEEDS="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20"
AHE_COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure"
BASE_COMBOS="big_mrta robot_failure,big_mrta mixed_stress,big_mrta deadline_pressure,\
rostam_ea robot_failure,rostam_ea mixed_stress,rostam_ea deadline_pressure,\
consensus_dbta robot_failure,consensus_dbta mixed_stress,consensus_dbta deadline_pressure"

# run_arm <etiket> <combos> [ek bayrak ataması...]
# Ek bayraklar yalnız bu alt-kabukta geçerlidir; kollar birbirine sızmaz.
run_arm() {
    local label="$1" combos="$2"; shift 2
    echo "########## KOL $label  (ek bayrak: ${*:-yok}) ##########"
    ( export "$@" 2>/dev/null || true
      bash run_experiments_robust.sh \
          --robots 5 --tasks 25 --seeds "$SEEDS" \
          --combos "$combos" --results-dir "$OUT/$label" )
}

# ── B4: dört ablasyon kolu (240 koşu) ────────────────────────────────────────
run_arm full         "$AHE_COMBOS"
run_arm no-override  "$AHE_COMBOS" AHE_NO_OVERRIDE=1
run_arm fixed-EDF    "$AHE_COMBOS" AHE_FORCE_PARADIGM=2
run_arm fixed-orphan "$AHE_COMBOS" AHE_FORCE_PARADIGM=4

# ── D2: dört-yöntem kıyaslamasını n=20'ye çıkar (180 koşu) ───────────────────
# AHE kolonu yukarıdaki `full` kolundan gelir; burada yalnız üç baseline koşar.
run_arm baselines-n20 "$BASE_COMBOS"

echo "ABLATION CAMPAIGN COMPLETE"
