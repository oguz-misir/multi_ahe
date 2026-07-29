# `results/` — hangi veri kanonik, hangisi tarihsel

Bu dosyanın amacı tek bir soruyu kesin yanıtlamak: **makaledeki bir sayı nereden
geliyor ve nasıl yeniden üretilir?**

İki kez, aynı kök sebepten hata yapıldı: bir figür ve bir tablo, süperseded
edilmiş bir kampanyanın türetilmiş dosyalarından beslendi ve metinle sessizce
çeliştiler (bkz. `3785ec3`, `d0c0943`). Bu dizinlerin çoğu araştırma tarihidir;
**üretimde yalnızca aşağıda "KANONİK" işaretli olanlar kullanılır.**

---

## KANONİK kaynaklar (makaledeki her sayı buradan gelir)

| Dosya | İçerik |
|---|---|
| `processed/all_summary.csv` | **300 Gazebo koşusunun tamamı** (3r×3 yoğunluk, 5r, 10r × 4 yöntem × 3 senaryo × 5 tohum). Ölçek ayrımı `robot_count` / `target_count` **kolonlarıyla filtrelenir** — ayrı ölçek dizini YOKTUR. |
| `processed/all_{task_events,allocation_events,ecosystem_metrics,communication,robot_workload,runtime}.csv` | Aynı 300 koşunun olay/zaman serisi ayrıntısı |
| `processed/sim_fitness.csv` | Navigasyon vekili, 5r/25g, **500 tohum** → `tab:fitness` |
| `processed/sim_scalability.csv` | Vekil ölçeklenebilirlik, N∈{3,5,10}, 100 tohum → `tab:scalability` |
| `processed/ablation_edps_100_geodesic.txt` | EDPS ablasyonu, 5r/25g, 100 tohum, geodezik → `tab:ablation` |
| `stats/descriptive_stats.csv`, `stats/stat_tests.csv`, `stats/stat_summary.txt` | 5r birincil ölçek betimleyici + Mann–Whitney |
| `stats/f58_allocation_only{,_3r15t,_10r50t}/` | Yalnız-tahsis kampanyası → `tab:allocation` |
| `raw/gazebo_benchmark_f58/` | **Makalenin ham kanıtı**: 300 koşunun per-run CSV + konsol logları |

Ham loglar silinmemelidir: deneyin gerçekte ne yaptığı (ör. arıza enjeksiyon anı)
yalnız oradan doğrulanabilir — makale metnindeki senaryo tanımı bir kez tam da bu
yolla yanlış bulundu.

## TARİHSEL (üretimde kullanılmaz, silme — ama okuma)

| Dizin | Ne |
|---|---|
| `raw/gazebo/` | **F58 öncesi** kampanya ham verisi (~2026-06-28). Makale artık bu veriyi raporlamıyor. |
| `raw/gazebo_f58_*_validation/`, `raw/_f58_pooled_s1_10/` | F58 geliştirme turlarının (p1b…p1r, scale3/scale10) doğrulama koşuları |
| `stats/gazebo_f58_*`, `processed/gazebo_f58_*` | Yukarıdakilerin türetilmiş özetleri |
| `_depo_archive/` | Eski `processed`/`stats` yedekleri ve `old_raw` |
| `figures/`, `paper_figures/`, `demo_videos_mixed/` | Ara/gösterim çıktıları; makale figürleri `paper/figure/` altındadır |

> `processed/gazebo_{3r,5r,10r}/` ve `stats/gazebo_{3r,5r,10r}/` **2026-07-29'da
> silindi** (`d0c0943`): F58 öncesi türetilmiş snapshot'lardı ve Şekil 9'u yanlış
> besliyorlardı. Arkalarındaki 299 koşu `raw/gazebo/` altında duruyor; gerekirse
> `consolidate_results.py` ile yeniden üretilebilir.

---

## Zincir: raw → processed → stats → figür/tablo

Ham veri değiştiyse **zincirin tamamı** yeniden koşulmalıdır; ara adımı atlamak
tam olarak yukarıdaki hataları üretir.

```bash
# 1) konsolidasyon  (raw/*/exp_*/ → processed/all_*.csv)
#    DİKKAT: consolidate_results.py --raw-dir'ın YALNIZ bir alt seviyesine bakar
#    (iterdir, özyinelemeli değil). Kampanya ölçek dizinlerine (r3t9/, r5t25/, …)
#    bölünmüş olduğundan, kökü doğrudan vermek SESSİZCE BOŞ çıktı üretir.
#    Doğru yol: önce 300 koşuyu tek düzlemde toplayan geçici symlink havuzu kur.
POOL=$(mktemp -d)
for d in results/raw/gazebo_benchmark_f58/*/exp_*/; do
    [ -f "$d/DONE" ] && ln -s "$(realpath "$d")" "$POOL/$(basename "$d")"
done
ls "$POOL" | wc -l          # 300 olmalı; değilse eksik DONE var
python3 scripts/consolidate_results.py --raw-dir "$POOL" \
                                       --processed-dir results/processed
rm -rf "$POOL"

# 2) istatistik + iki ana tablo  (→ paper/table/latex_{main,deadline}_table.tex)
python3 scripts/statistical_analysis.py --processed-dir results/processed \
                                        --output-dir results/stats
#    (--table-dir varsayılanı paper/table; 5r birincil ölçeğe kendi içinde filtreler)

# 3) figürler  (→ paper/figure/, 8 üretilen figür)
python3 scripts/plot_results.py --processed-dir results/processed \
                                --output-dir paper/figure --dpi 300

# 4) verimlilik + etki-boyutu tabloları  (→ paper/table/latex_{efficiency,effectsize}_table{,_tr}.tex)
python3 scripts/make_extra_tables.py
```

### Simülatör düzlemleri (Gazebo gerektirmez)

**Bu env bayrakları olmadan sim Öklid mesafeye düşer ve makaleyle uyuşmayan
sayılar üretir.** Kaynak: `scripts/run_f58_benchmark_until_complete.sh`.

```bash
source install/setup.bash
export AHE_SIM_GEODESIC_EXECUTION=1 AHE_F58_GEODESIC=1 AHE_F58_FAIR_REPAIR=1 \
       AHE_F58_FAIR_RESERVATION_GAP=2 AHE_F58_FAIR_EXTRA_QUEUE=1 \
       AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3

python3 scripts/simulate_and_tune.py --seeds 500 --scenario all                    # sim_fitness.csv
python3 scripts/simulate_and_tune.py --seeds 100 --scenario all --robot-counts 3,5,10  # sim_scalability.csv
python3 scripts/ablation_edps.py 100 > results/processed/ablation_edps_100_geodesic.txt
```

---

## Elle bakımlı LaTeX tabloları — dikkat

`paper/table/` altındaki şu dosyalar **script tarafından yazılmaz**; sayıları
yukarıdaki çıktılardan elle taşınır. Bayatlama riski buradadır:

| Tablo | Beslendiği kaynak |
|---|---|
| `allocation_only{,_tr}.tex` | `stats/f58_allocation_only*/` |
| `fitness{,_tr}.tex` | `processed/sim_fitness.csv` |
| `scalability{,_tr}.tex` | `processed/sim_scalability.csv` |
| `ablation{,_tr}.tex` | `processed/ablation_edps_100_geodesic.txt` |
| `scales`, `proto_vectors`, `as_matrices`, `hormones` | Statik yapılandırma (veri değil) |

Bu dosyalardan birine dokunulduğunda kaynağıyla birebir karşılaştır. `ablation.tex`
tam olarak bu adım atlandığı için aylarca `sim_scalability.csv` ile çelişti.

## Makale sayılarını doğrulama

```bash
python3 - <<'PY'
import pandas as pd
s = pd.read_csv('results/processed/all_summary.csv')
d = s[s.robot_count == 5]                      # ölçeği burada seç
g = d.groupby(['scenario','strategy']).agg(
        CR=('task_completion_rate','mean'), DVR=('deadline_violation_rate','mean'))
g['eff_on_time'] = g.CR * (1 - g.DVR)          # makalenin "effective on-time" metriği
print(g.round(3))
PY
```

LaTeX derleme (latexmk yok): `pdflatex → bibtex → pdflatex ×2`, ayrı ayrı
`paper/main.tex` (EN) ve `paper/main_tr.tex` (TR) için.
