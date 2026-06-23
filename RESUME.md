# AHE-MRTA — Durum (v4.5 ADİL-PAYDA PİVOTU)

**Son güncelleme:** 2026-06-20 | **Durum:** Sim metodoloji TAMAM; Gazebo yeniden-koşum bekliyor

## ⟹ CHECKPOINT (2026-06-20) — v4.5 ADİL-PAYDA + ALGO RAFİNE (sim tamam, Gazebo bekliyor)
**Kullanıcı direktifi (remote-control):** tüm metrikleri iyileştir + bütün deneyleri sıfırdan
yeniden koş (tekrar=10; 5 başlat→netse 10; önce 5r-primary). Karar: **adil-payda + gerçek algo**.

**Kök tanı (sim 5r/25t):** AHE delay/DVR "kaybı" = (1) **survivorship** (BiG %30-51 tamamlıyor,
düşürdüğü zor görevler completed-only paydaya girmiyordu) + (2) **yapısal mesafe** (AHE ~800 vs
RoSTAM ~500; ATAMA meselesi, kuyruk-sıralaması değil — 3× doğrulandı).

**Uygulanan (develop-install, rebuild yok):**
- **Adil-payda (BÜYÜK):** delay = tamamlanmayan görev makespan-censored; DVR = bitmemiş deadline'lı
  görev=ihlal, payda=deadline'lı sayı. `simulate_and_tune.py` (~681/687) + `experiment_runner_node.py`
  (~880). Tüm yöntemlere tekdüze. Birincil sütun ADLARI korundu → pipeline kırılmaz; `_completed`
  şeffaflık sütunları eklendi. **Kanonik processed/stats yedeği:** `results/_processed_canonical_baseline/`,
  `results/_stats_canonical_baseline/`.
- **F46** incumbent-stable urgency, **F48** slack-graded capability, **F49** deadline-aware route
  (cheapest yalnız EDF kadar deadline koruyorsa → DVR regresyonu yapısal yok). Hepsi `ahe_variants.py`.
- **REDDEDİLEN:** F47 (A→B→A ping-pong, instab 0.90→1.86); cap=3 (rf fitness 0.552→0.532);
  FAIR_LAMBDA_S=12 (recovery 33.6→47.1 = F45 sorunu). Kodda bayraklar False/ablasyon.

**100-tohum sim sonuç (adil-payda):** rf fit 0.540 eşit-1./delay 444.6(2.)/DVR 0.461(2.);
ms fit 0.538 eşit-1./delay 443.6(1.)/DVR 0.460(1.); dp fit 0.482(1.)/delay 484.2(2.)/DVR 0.521(1.).
→ AHE delay/DVR'da EN KÖTÜ'den her senaryoda 1.-2. **Kalan: WLBal 3.-4. (yapısal) + recovery (Gazebo-özgü).**

**SONRAKİ (Gazebo):** eski raw yedekle, 5r/25t × 5 tohum × 3 senaryo × 4 yöntem çökme-güvenli;
netse 10'a, sonra 3r+10r. WLBal+recovery orada gerçek ölçülür. → consolidate/stats/plots/extra_tables
→ makale (EN+TR): adil-payda metodolojisi + "completeness over punctuality" güçlenir.

---

## (ÖNCEKİ) FİNAL: 4-vektör + 5r-primary + dayanıklılık
**Önceki durum:** Yöntem/veri kararları kilitlendi (4-vektör, 5 paradigma, robot_failure=dayanıklılık)

## KİLİTLENEN KARARLAR
1. **4-vektör kalıcı.** Bağlam = c1 yoğunluk, c2 uygunluk, c4 deadline, c5 arıza.
   c3(batarya)/c6(iş-yük-var)/c7(kararsızlık) = 0.0 (ablasyon Δfit=0). 5 aktif paradigma
   (battery_gated H_ENERGY + load_balance H_RES erişilemez). Makale "4 sinyal → 5 paradigma".
   - **Gerekçe (Gazebo 10r):** 4-vec mixed_stress makespan 342→**165** (3.→1.), deadline 1.,
     robot_failure tamamlamada 1. Kesim, c6/c7'nin yarattığı paradigma çalkantısını durdurdu.
2. **robot_failure = DAYANIKLILIK çerçevesi** (kullanıcı kararı 06-19). AHE manşeti
   tamamlama+dayanıklılık: comp **49.8/50, CR 0.996**, hiç çökmez. CDBTA makespan medyan 171
   ama **zor tohumlarda 44/50'ye çöker** (6 görev düşürür). Makespan ikincil + dürüst takas.
   Seed-hizalı kanıt: seed01/04 AHE hem mk hem comp ezer; seed02/05 comp eşit CDBTA hızlı.
3. **F45 (recovery yük-dengeleme) REDDEDİLDİ** → ablasyon bulgusu. W=0.25 Gazebo'da makespan
   tail'i BOZDU (343 vs no-F45 224): yetimi yaymak=uzak robotu yürütmek=travel↑. Kod'da
   `F45_RECOVERY_LOADBAL_W=0.0` (kapalı), env override durur. no-F45 veri kanonik (geri yüklendi).
4. **Ölçek 3/5/10, birincil 5r.** 15r INFEASIBLE (16 çekirdek/15GB; 2/15 Nav2 kalktı —
   readiness-gating yakaladı). Donanım limiti, algoritma değil; limitations'da dürüst yazılır.

## KANONİK VERİ
- `results/raw/gazebo/` — 3r (AHE 4-vec yeniden, baseline korundu)
- `results/raw/gazebo_5r_low/` — 5r/15g (4 yöntem 15/15 TAM; AHE 4-vec)
- `results/raw/gazebo_5r/` — 5r/25g birincil (AHE 4-vec yeniden, baseline korundu)
- `results/raw/gazebo_10r_clean/` — 10r/50g (AHE 4-vec, robot_failure=no-F45 kanonik; 60 done)
- `results/raw/_ahe_7vec_backup/` — eski 7-vec AHE (regresyon yedeği)
- `results/raw/_ahe_4vec_noF45_rf10r/` — robot_failure no-F45 referansı
- `sim_fitness.csv` tuning'de EZİLDİ → final config'le YENİDEN üret (--scenario all, 5r primary)

## KOD DURUMU (hepsi develop-install, rebuild YOK)
- `ahe_variants.py`: F45=0.0 (kapalı/ablasyon), fleet-gate yok (F44=999, tek config)
- `ecosystem_manager_node.py`: c3/c6/c7 → 0.0 (4-vektör)
- Method matematiği (main.tex + main_tr.tex) GÜÇLENDİRİLDİ: her vektör formal denklem +
  her paradigma LSA-formülasyonu + klasik köken atıfı; dominance=Lotka-Volterra (peng2023) +
  hiper-sezgisel (burke2013). Kod 6-param dominance ile birebir doğrulandı. 14 atıf, 0 çözümsüz.

## ⟹ CHECKPOINT (2026-06-20 ~08:00) — 4-VEKTÖR TAM İNDİRGEME (makale)
**Kullanıcı kararı: makale yalnız 4-vektör. EN+TR baştan sona 7→4-sinyal/5-paradigma'ya indirgendi
ve derlendi (0 çözümsüz ref).** Önemli: kod K=7 ama c3/c6/c7=0 → Gazebo verisi ZATEN 4-vektör
(dormant kısımlar inert), sonuçlar değişmedi; bu SUNUM değişikliği.
- **Bağlam vektörü 7→4:** c1 yoğunluk, c2 uygunluk, c3 deadline, c4 arıza (eski c4/c5 yeniden numaralandı;
  c3-batarya/c6-işyükü/c7-kararsızlık çıkarıldı). Denklem, V tablosu (5×4), dominance D∈ℝ⁵.
- **5 paradigma:** spatial/criticality/temporal(EDF)/stability(commit)/recovery(orphan). load_balance(H_RES)
  + battery_gated(H_ENERGY) ve bunların A/S girdileri + 3. dispatch override (battery>0.85) ÇIKARILDI.
- **Matris doğrulaması:** paper V/A/S = kodun (simulate_and_tune V/A/S) aktif 5×4 alt-kümesiyle BİREBİR.
- **Figürler:** plot_results.py mimari diyagram metinleri (∈[0,1]^4, A_{5×5}, 5 paradigma) + HEURISTIC_LABELS
  (5: d_0,d_1,d_2,d_5,d_6) + CONTEXT_LABELS (4) indirgendi; figürler yeniden üretildi.
- Abstract/intro/contrib/positioning/algorithm/no-ablation/metrics/mixed_stress(batarya çıktı) hepsi 4/5.
- Çıkarılan atıflar (liu2019energy,zhou2020energy) artık kullanılmıyorsa zararsız (bibtex hata vermez).

## ⟹ CHECKPOINT (2026-06-19 ~22:45) — q1 TAM DENETİM TAMAM
**EN+TR güncel sonuçlarla denetlendi+derlendi (0 çözümsüz ref). PDF gönderildi.** Bu turda ek:
- **Fitness derin araştırma:** kayıp kaynağı = incomplete (kapasite, ~2100 pri-ağırlık) + dp'ye özgü
  GEÇ-tamamlama (490). İlkesel kaldıraç = deadline-fizibilite-duyarlı sıralama: dp +0.0064 (BiG'i geçer)
  AMA ms'yi −0.009 bozar (kuplaj, Pareto). Deploy EDİLMEDİ; **§4 Discussion'a takas-içgörüsü eklendi**
  (sec:deadline-tie, EN+TR): "bütünlük-over-dakiklik" — hakem gözünde "neden eşit?" sorusunu güce çevirir.
- **q1 denetim düzeltmeleri (EN+TR):** (a) 3r sonuç prose'u 5r-primary'ye reframe (AHE 3r dp/ms CR
  0.891/0.779 BAYAT → 4-vec'te 1.000; tüm "where AHE wins/costs/efficiency" 5r sayılarıyla yenilendi);
  (b) artefakt "instability 4.5-14.5" TÜM yerlerde kaldırıldı → corrected churn (AHE en iyi bantta);
  (c) effect-size paragrafı 5r tablodan (CR vs BiG +1.00, RecT −0.48, Churn AHE-lehine); (d) significance
  31/11/20 BAYAT → 12/7/5 @5r (3r=15, 10r=0); (e) scalability sim REGEN (fitness ~aynı, sim-latency
  makine-bağlı 14.5→6.6ms güncellendi; "RoSTAM lowest at all" yanlıştı→düzeltildi); (f) figür caption'ları
  (failure_recovery, multi_metric) 3r→5r + exec_preemptions; (g) 10r dp DVR 0.200→0.248 her yerde.
- **Stat yıldızları:** p_adj=p×n_tests'ten (Bonferroni) ✓ caption ile tutarlı.

## ⟹ CHECKPOINT (2026-06-19 ~21:15) — PIPELINE+MAKALE TAMAM
**Tüm post-proc + EN/TR makale güncellendi ve derlendi (0 çözümsüz ref).** Bitenler:
1. **Stabilite artefakt düzeltmesi ENTEGRE:** `consolidate_results.py` → all_summary'ye
   `exec_preemptions`/`task_redispatch`/`redispatch_per_task` enjekte eder
   (`recompute_stability_metrics.compute_for_exp`). stats/plot/extra_tables artık fiziksel
   metrik kullanır (Preempt/Churn); eski `allocation_instability`/`replanning_frequency` artefaktı
   tablo/figürden çıktı. AHE düzeltilmiş churn'de en iyi bantta (rf 0.048/ms 0.049).
2. **sim_fitness.csv YENİDEN ÜRETİLDİ** (5r/25t, 100 seed, capw=2.2 kanonik): AHE ms 0.546 (1.),
   rf 0.539 (eşit-1. CDBTA 0.540), dp 0.480 (eşit-1. BiG 0.480). Paper fitness tablo+metin+caption
   3r/15t→5r/25t güncellendi.
3. **Tablo caption'ları** 3-robot/n=15 → 5-robot/n=10 (statistical_analysis.py:219,269).
4. **Makale sayı doğrulama (EN+TR):** 10r rf CR 1.000→0.996, DVR 0.004→0.012; 5r rf DVR→0.000;
   10r dp DVR 0.200→0.248, effective 0.80→0.75; makespan "194 fastest" → CDBTA 171 daha hızlı
   (dayanıklılık takası çerçevesi); latency 0.22-0.25/0.37-0.47ms; oranlar 1.9×. Katkı listesi
   "recovery-time'a yardım" iddiası KALDIRILDI (AHE recovery'de en kötü) → "tamamlama/deadline-
   dayanıklılık/kararlılık'a yardım; gecikme/recovery/makespan'a maliyet".
5. **KARAR (kullanıcı onayı):** rf+dp fitness = istatistiksel beraberlik (gürültü tabanı ~0.007);
   capw=5.0 dp'yi nominal çevirir AMA dar gürültü tepesi (p-hacking) → KULLANILMADI. Dürüst
   "ms'de 1., rf+dp'de eşit-1." çerçevesi. Kaynak kod capw=2.20 değişmedi.
6. **KRİTİK BULGU (gelecek fitness ayarı için):** `simulate_and_tune.py:246 _patch_ahe_cost`
   ÇAĞRILMIYOR → `_assign_v3` ÖLÜ KOD; sim gerçek `allocator.allocate()` kullanır. Sim fitness
   kaldıracı = AHE sınıf nitelikleri (DEADLINE_CAPABILITY_W etkili; slack/urgency/hyst dp'ye etkisiz)
   + ekosistem ağırlıkları (W=softmax(M@D)).
7. EN+TR `pdflatex+bibtex×2` → main.pdf / main_tr.pdf TAMAM.

## ⟹ ESKİ CHECKPOINT (2026-06-19 ~09:15)
**Tüm Gazebo verisi TAM** (3r 180, 5r-low 60, 5r-mid 60, 10r 60). Gazebo YOK; post-proc+makale.

### YENİ DÜZEN (uygulandı) — root = 5r BİRİNCİL
- `results/processed/` + `results/stats/` = **5r havuzlanmış (low+mid, n=10/hücre, 120 satır)** ← BİRİNCİL
- `results/processed/gazebo_3r/` + `stats/gazebo_3r/` = 3r (180 satır, scalability alt-uç)
- `results/processed/gazebo_10r/` + `stats/gazebo_10r/` = 10r (60 satır, scalability üst-uç)
- 5r-havuz raw symlink dizini: `results/raw/_gazebo_5r_pooled/` (120 symlink; silinebilir, yeniden kurulur)
- YEDEK (geri dönüş): `results/_processed_bak_091141/`, `results/_stats_bak_091141/`

### ✅ BİTEN
1. consolidate ×3 (yukarıdaki düzen). 2. statistical_analysis ×3 → stats/ + LaTeX tablolar
   (latex_main_table, _deadline, _effectsize{,_tr}, _efficiency{,_tr}, descriptive_stats, stat_tests).

### ◻ KALAN (sırayla)
3. **sim YENİDEN ÜRET** (sim_fitness.csv F45-tuning'de EZİLDİ → şu an çöp, 4 satır rf-10r!):
   `python3 scripts/simulate_and_tune.py --seeds 100 --scenario all --robots 5 --tasks 25`
   → processed/sim_fitness.csv (5r birincil). sim_scalability: `--robot-counts 3,5,10` (arg satır 911;
   üretim biçimini doğrula). ENV: AHE_RECOVERY_LOADBAL_W boş bırak (F45=0 zaten).
4. **figür+tablo:** `python3 scripts/plot_results.py --processed-dir results/processed --output-dir results/figures`
   (10r figürü için ayrıca --processed-dir gazebo_10r gerekebilir; plot_results 10r'yi gazebo_10r/'dan okur,
   kontrol et). `python3 scripts/make_extra_tables.py` (PROC/STATS hardcoded=root=5r → birincil 5r).
5. **Makale (main.tex + main_tr.tex):** Method matematiği ZATEN güçlendirildi (4-vec formülleri,
   paradigma-LSA, atıflar). Kalan METİN: (a) "7 hormon→7 paradigma" → **4-sinyal/5-paradigma**
   anlatısı + c3/c6/c7 ablasyon tablosu (Δfit=0, sim); (b) birincil ölçek **3r→5r** (tablolar/caption/
   metin "3-robot"→"5-robot"; 3r=scalability noktası kalsın); (c) **robot_failure DAYANIKLILIK
   çerçevesi** (manşet comp 49.8/50 CR 0.996, hiç çökmez; CDBTA zor tohumda 44/50; makespan ikincil+
   takas); (d) 10r 4-vec sayıları (mixed 1., deadline 1.); (e) 15r donanım limiti (limitations);
   (f) F45 ablasyon notu opsiyonel (recovery yük-dengeleme makespan'i bozar). TÜM sayıları taze
   CSV'den DOĞRULA (Q1 skill). 6. `pdflatex+bibtex×2` EN+TR, 0 çözümsüz ref, PDF gönder.

### SAYI KAYNAKLARI (doğrulama için)
- 5r birincil: `results/stats/descriptive_stats.csv` + `stat_tests.csv` + `processed/all_summary.csv`
- 10r: `results/stats/gazebo_10r/` ; 3r: `results/stats/gazebo_3r/`
- 10r 4-vec makespan medyan: mixed **165**(1.), deadline **152**(1.), rf 224 (CDBTA 171 ama AHE comp
  49.8 vs 48.4, CR 0.996 vs 0.968, CDBTA seed01/04'te 48/44 çöker). Kaynak: gazebo_10r_clean raw.
