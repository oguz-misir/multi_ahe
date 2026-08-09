# `results/` — hangi veri kanonik, hangisi tarihsel

Bu dosyanın amacı tek bir soruyu kesin yanıtlamak: **makaledeki bir sayı nereden
geliyor ve nasıl yeniden üretilir?**

İki kez, aynı kök sebepten hata yapıldı: bir figür ve bir tablo, süperseded
edilmiş bir kampanyanın türetilmiş dosyalarından beslendi ve metinle sessizce
çeliştiler (bkz. `13c411d`, `ff5709e`). Bu dizinlerin çoğu araştırma tarihidir;
**üretimde yalnızca aşağıda "KANONİK" işaretli olanlar kullanılır.**

---

## KANONİK kaynaklar (makaledeki her sayı buradan gelir)

| Dosya | İçerik |
|---|---|
| `processed/all_summary.csv` | **480 Gazebo koşusunun tamamı**: 3r×3 yoğunluk ve 10r × 4 yöntem × 3 senaryo × **5 tohum**, 5r × 4 yöntem × 3 senaryo × **20 tohum** (D2). Ölçek ayrımı `robot_count` / `target_count` **kolonlarıyla filtrelenir** — ayrı ölçek dizini YOKTUR. |
| `processed/all_{task_events,allocation_events,ecosystem_metrics,communication,robot_workload,runtime}.csv` | Aynı 480 koşunun olay/zaman serisi ayrıntısı |
| `processed/sim_fitness.csv` | Navigasyon vekili, 5r/25g, **500 tohum** → `tab:fitness` |
| `processed/sim_scalability.csv` | Vekil ölçeklenebilirlik, N∈{3,5,10}, 100 tohum → `tab:scalability` |
| `processed/ablation_edps_100_geodesic.txt` | EDPS ablasyonu, 5r/25g, 100 tohum, geodezik → `tab:ablation` |
| `stats/descriptive_stats.csv`, `stats/stat_tests.csv`, `stats/stat_summary.txt` | 5r birincil ölçek betimleyici + Mann–Whitney |
| `stats/f58_allocation_only{,_3r15t,_10r50t}/` | Yalnız-tahsis kampanyası → `tab:allocation`. ✅ **2026-08-02 18:13–18:15'te düzeltilmiş senaryo parametreleriyle YENİDEN KOŞULDU** (`scripts/_campaigns/run_alloc_only_rebuild.sh`, log: `alloc_rebuild.log`). Artık hücreye göre değişiyor (CR 1.000, DVR 0.000–0.353); eski "her hücre fitness 1.000 / DVR 0.000" çıktısı gitti. |
| `raw/gazebo_benchmark_f58/` | **Makalenin ham kanıtı**: 3r/10r koşularının per-run CSV + konsol logları (5r için bkz. `raw/gazebo_ablation/baselines-n20` ve `full`) |
| `raw/gazebo_ablation/` | **Eşleşmiş kapalı-çevrim ablasyonu (B4)**: beş kol × 5r/25g. Ablasyon `full` / `no-override` / `fixed-EDF` / `fixed-orphan` (her biri 3 senaryo × 20 tohum = 60 koşu, toplam 240) → `tab:gazebo-ablation`; ayrıca `baselines-n20` (3 baseline × 3 senaryo × 20 tohum = 180) → dört-yöntem kıyaslamasını n=20'ye çıkarır. |
| `ablation_analysis.txt` | Yukarıdakinin ön-kayıtlı analiz çıktısı (`scripts/analyze_ablation.py`) |
| `processed/ab_geodesic_{on,off}{,_seedwise}.csv` | Geodezik-ETA kâhini eşli A/B, 500 tohum, 5r/25g → §VII-D "What the geodesic ETA contributes" ve Sınırlılık (xiii). Üretici: `scripts/validate_geodesic_eta_ab.py`, log: `geodesic_ab.log`. **Tasarım:** yürütme kâhini iki kolda da geodezik (`AHE_SIM_GEODESIC_EXECUTION=1`), yalnız tahsis edicinin maliyet kâhini değişiyor (`AHE_F58_GEODESIC` 1↔0). Doğrulama: üç temel yöntem kollar arası birebir, ve "on" kolu `sim_fitness.csv`'yi 12 hücrede birebir (fark 0.000000) yeniden üretiyor. |
| `processed/ab_prio_{on,off}{,_seedwise}.csv` | Öncelik çarpanı $\rho$ eşli A/B, 500 tohum → Sınırlılık (xii). ✅ **2026-08-02 19:02'de hizalanmış senaryolarla YENİDEN KOŞULDU** (`scripts/_campaigns/run_prio_ab_when_ready.sh`, sonuç: `prio_ab_result.txt`). En büyük \|delta\| = 0.77 yp → Sınırlılık (xii)'nin "ölçülemez" iddiası ayakta, iki dilde de güncel. |

Ham loglar silinmemelidir: deneyin gerçekte ne yaptığı (ör. arıza enjeksiyon anı)
yalnız oradan doğrulanabilir — makale metnindeki senaryo tanımı bir kez tam da bu
yolla yanlış bulundu.

## TARİHSEL (üretimde kullanılmaz, silme — ama okuma)

| Dizin | Ne |
|---|---|
| `raw/gazebo/` | **F58 öncesi** kampanya ham verisi (~2026-06-28). Makale artık bu veriyi raporlamıyor. Şekil 7(b) 2026-08-03'e kadar buradan besleniyordu; artık `scripts/make_path_grid.py` ile kanonik ablasyon koşularından üretiliyor. |
| `raw/gazebo_f58_*_validation/`, `raw/_f58_pooled_s1_10/` | F58 geliştirme turlarının (p1b…p1r, scale3/scale10) doğrulama koşuları |
| `stats/gazebo_f58_*`, `processed/gazebo_f58_*` | Yukarıdakilerin türetilmiş özetleri |
| `_depo_archive/` | Eski `processed`/`stats` yedekleri ve `old_raw` |
| `figures/`, `paper_figures/`, `demo_videos_mixed/` | Ara/gösterim çıktıları; makale figürleri `paper/figure/` altındadır |

> `processed/gazebo_{3r,5r,10r}/` ve `stats/gazebo_{3r,5r,10r}/` **2026-07-29'da
> silindi** (`ff5709e`): F58 öncesi türetilmiş snapshot'lardı ve Şekil 9'u yanlış
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

### Eşleşmiş kapalı-çevrim ablasyonu (B4 → `tab:gazebo-ablation`)

Kolu belirleyen şey **env bayrağıdır**, kod değil; çözülmüş bayraklar her koşunun
`metadata.yaml: allocator_env` alanına yazılır, yani bir koşunun hangi kola ait
olduğu sonuç dosyasından okunur. Kampanya ve analiz:

```bash
nohup bash run_ablation_campaign.sh > results/ablation_campaign.log 2>&1 &
python3 scripts/analyze_ablation.py > results/ablation_analysis.txt
```

Analiz `paper/PREREGISTRATION.md`'yi uygular (birincil uç nokta, eşli Wilcoxon,
Cliff δ, senaryo ailesi içinde Bonferroni) ve **iki dildeki tabloyu tek veri
geçişinden üretir** → `paper/table/gazebo_ablation{,_tr}.tex`. Bu tablolar
**elle düzenlenmez**; aşağıdaki elle-bakım listesine dâhil değildirler.

Kollar tamamlanmadan koşulursa analiz ara-sonuç uyarısı basar ve boş kol üzerinden
eşleştirme yapmayı reddeder. `DONE` dosyası olmayan koşu hiç okunmaz — düşmüş bir
bring-up kısmi satır katkısı yapamaz.

> **Kampanya başlatma kuralı:** `MAX_LOAD=5` (sürücü export ediyor) ve koşarken
> ağır iş yapma. Varsayılan eşik 10, 5 robotluk bring-up için fazla gevşek —
> 2026-07-31'de iki koşu bu yüzden `STARTUP FAILED: 0/5 Nav2 hazır` verdi.
> Ayrıntı: `CLAUDE.md`.

### Simülatör düzlemleri (Gazebo gerektirmez)

> **✅ ÇÖZÜLDÜ (2026-08-02).** `d5f9525` senaryo tanımlarını tek bir
> paylaşılan modüle (`m_ahe_task_allocator/scenarios.py`) taşıdı ve **vekil
> düzlemi makaledeki tanımlarla hizaladı**. Öncesinde vekilin `mixed_stress`'ini
> `robot_failure`'dan ayıran tek şey bataryaydı — dalga programı ve yarılanmış
> deadline bütçesi yoktu; `deadline_pressure` da U[200,400] kullanıyordu, makalenin
> yazdığı U[36,120] değil. Üç çıktı da (`sim_fitness` 10:17, `sim_scalability`
> 10:40, `ablation_edps_*` 10:43) hizalanmış senaryolarla yeniden üretildi ve
> `tab:fitness` / `tab:scalability` / `tab:ablation` 11:14'te onlardan yeniden
> kuruldu. Sürüklenmenin tekrarını `tests/test_scenario_parity.py` engelliyor.
>
> **🔴 BUNUN BIRAKTIĞI TUZAK (2026-08-03'te yakalandı).** Yeniden üretim
> tabloları güncelledi ama **figürleri güncellemedi**: `plot_results.py` o gün
> 09:59–10:00'da, yani yeni CSV'ler yazılmadan ÖNCE koşmuştu.
> `fitness_comparison.png` ve `scalability_panel.png` hizalama öncesi sayıları
> çizmeye devam etti — üstelik geri çekilmiş anlatıyı (deadline'da AHE geride,
> ölçeklenebilirlikte AHE≈Cons-DBTA eş-lider) — ve kendi tablolarıyla
> çeliştiler. **Kural: `processed/sim_*.csv` her değiştiğinde `plot_results.py`
> SONRASINDA koşmalı; doğrulaması `--output-dir` ile geçici dizine üretip
> `cmp` ile `paper/figure/` altındakiyle karşılaştırmaktır.**

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
| `fitness{,_tr}.tex` | `processed/sim_fitness.csv` |
| `scalability{,_tr}.tex` | `processed/sim_scalability.csv` |
| `ablation{,_tr}.tex` | `processed/ablation_edps_100_geodesic.txt` |
| `scales`, `proto_vectors`, `hormones` | Statik yapılandırma (veri değil) |

**Script üretimi olanlar — elle DÜZENLEME:** `gazebo_ablation{,_tr}.tex`
(`analyze_ablation.py`), `allocation_only{,_tr}.tex` (`make_allocation_table.py`),
`latex_{main,deadline}_table.tex` (`statistical_analysis.py`),
`latex_{efficiency,effectsize}_table{,_tr}.tex` (`make_extra_tables.py`).
(`as_matrices{,_tr}.tex` **silindi** — üç sıfır-dışı giriş için float harcıyordu,
artık metinde bir cümle.)

Bu dosyalardan birine dokunulduğunda kaynağıyla birebir karşılaştır. `ablation.tex`
tam olarak bu adım atlandığı için aylarca `sim_scalability.csv` ile çelişti.

> `allocation_only{,_tr}.tex` **2026-07-30'da elle-bakımdan çıkarıldı** →
> `python3 scripts/make_allocation_table.py`. Sebep: elle doldurulmuş hâli
> kaynağından sapmıştı (10r/50t robot_failure hücresi tabloda 0.982 Jain /
> 284.1 m / 0.200 ms, kaynakta 0.961 / 272.7 m / **0.361 ms**) ve bayat
> 0.200 ms değeri metne *"latency is at most 0.201 ms"* olarak sızmıştı.

### Warm-up sonrası latency (2026-07-30)
`processed/ahe_latency_warmup.csv`, geodezik kâhin başlangıçta kurulduğunda
yeniden ölçülen **AHE latency**'sini taşır. `scripts/latency_override.py`
bunu `all_summary.csv` üzerine uygular; **hem** `make_extra_tables.py` **hem**
`plot_results.py` bu yardımcıyı çağırır — biri atlanırsa figürler metinle
çelişir. Kararlar bit-özdeş olduğu için yalnız bu kolon süperseded'dir.

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
