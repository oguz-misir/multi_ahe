# AHE-MRTA — Proje Durumu (2026-05-21)

## AHE-V3 Simülatör Sonuçları — TAMAMLANDI ✓

**300-seed, 12600 simülasyon, 3 senaryo:**

| Senaryo | ahe_v3 | 2. sıra | Δ |
|---------|--------|---------|---|
| robot_failure | **0.893★** | static_weighted 0.893 | 0.000 |
| mixed_stress | **0.892★** | consensus_dbta 0.889 | +0.003 |
| deadline_pressure | **0.894★** | ahe_v2_balance 0.894 | 0.000 |

**ahe_v3 tüm 3 senaryoda Compl'de 1. sıra.**

---

## ahe_v3'ün Aktif Mekanizmaları

| Mekanizma | Senaryo | Etki |
|-----------|---------|------|
| M1 — Bipartite matching (scipy) | robot_failure, mixed_stress | Compl +0.004 |
| M3 — Göreli yük dengeleme | robot_failure, mixed_stress | Balance ↑ |
| M4 — Atama yapışkanlığı | robot_failure, mixed_stress | Instab ↓ |
| M6 — Batarya-farkındalıklı kapasite | tümü | güvenlik |
| M8 — Failure_rate algılama | robot_failure | recovery_turbo |
| M9/M10 — Deadline penalty | robot_failure, mixed_stress | Compl ↑ |
| M12 — Deadline-capability skoru | robot_failure, mixed_stress | Delay ↑ |
| M14 — Round-1 garanti | robot_failure, mixed_stress | eşit dağılım |
| **M17 — Dense-initial delegasyonu** | **deadline_pressure** | **0.892→0.894★** |

**M17 tasarımı:** t=0'da görev sayısı >8 ise (deadline_pressure: 15 görev, diğerleri: 8) `AHEImprovedBalanceAllocator`'a (`ahe_v2_balance`) tam delegasyon. Bu sayede AT tabanlı V3 maliyeti yerine D (raw distance) + göreli yük formülü kullanılıyor.

---

## Gazebo Batch Durumu

- **Batch:** `run_paper_experiments_v3.sh` (PID 2286834, hâlâ çalışıyor)
- **Tamamlanan:** 41 / 160 deney (G1–G3 bitti, G4 devam ediyor)
- **Log:** `results/raw/gazebo_v3/paper_run_v3.log`
- **İzleme:**
  ```bash
  find results/raw/gazebo_v3 -name "DONE" | wc -l
  tail -f results/raw/gazebo_v3/paper_run_v3.log
  ```

**Not:** Gazebo batch çalışırken simülatör testleri (`simulate_and_tune.py`) paralel çalıştırılabilir — bağımsız, Gazebo kullanmıyor.

---

## Deney Kurgusu (Gazebo, 160 deney)

Tüm gruplar 3r/15g ölçeğinde (5r/10r/15r Nav2 lifecycle sorunları nedeniyle iptal edildi):

| Grup | Yöntem | Senaryo | Deney |
|------|--------|---------|------:|
| G1 — Karşılaştırma A | full_ahe, big_mrta, consensus_dbta | robot_failure + mixed_stress | 30 |
| G2 — Karşılaştırma B | " | " | 30 |
| G3 — Karşılaştırma C | " | " | 30 |
| G4 — Deadline | " | deadline_pressure | 30 |
| G5 — Ablasyon | full_ahe + 3 varyant | robot_failure + mixed_stress | 40 |
| | | **Toplam** | **160** |

---

## Bekleyen Gazebo Deneyleri (21 kaldı)

| Grup | Yöntem | Senaryo | Kalan |
|------|--------|---------|------:|
| G3 | ahe_fixed_context | robot_failure (seed05) + mixed_stress (seed01-05) | 6 |
| G1 | **ahe_v3** | robot_failure + mixed_stress (seed01-05) | 10 |
| G2 | **ahe_v3** | deadline_pressure (seed01-05) | 5 |
| **Toplam** | | | **21** |

**Video kaydı:** Her yöntem × senaryo'nun seed=01 koşusu `--record-video` ile ayrıca koşulacak (20 video, çoğu mevcut değil — seed01'ler videosuz koşuldu).

## Bekleyen Diğer Görevler

- [ ] Mevcut G5 batch bitmesi (6 deney, ~1.5 saat)
- [ ] ahe_v3 Gazebo batch (15 deney, ~3.75 saat)
- [ ] Video re-run: seed=01 × tüm yöntem × senaryo (20 × 2 = 40 video dosyası)
- [ ] Sonuç analizi (Wilcoxon, Page's L, Cliff's delta)
- [ ] Paper figür üretimi (Fig. 3–6)

---

## Referans Komutlar

```bash
# Simülatör testi (Gazebo yok)
source install/setup.bash
python3 scripts/simulate_and_tune.py --seeds 300 --scenario all --no-ablation

# Gazebo batch izleme
find results/raw/gazebo_v3 -name "DONE" | wc -l
tail -20 results/raw/gazebo_v3/paper_run_v3.log

# Yük kontrolü
uptime && pgrep -fc "gz sim|gzserver|ros2 launch|parameter_bridge|experiment_runner"
```
