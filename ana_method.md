# AHE-MRTA — Q1/RA-L Proje ve Makale Rehberi

## Adaptive Heuristic Ecosystem for Robust Online Multi-Robot Task Allocation

Bu dosya, AHE-MRTA projesini Q1/RA-L düzeyinde bir makaleye dönüştürmek ve Claude Code
ile aşamalı olarak uygulanabilir bir ROS 2/Gazebo prototipi olarak geliştirmek için
sadeleştirilmiş ana rehberdir. Odak: **karşılaştırmalar ve metrik performansı.**

Karşılaştırma yöntemlerinin ayrıntılı matematiksel uyarlamaları ve kod iskeletleri ayrı
dosyada tutulur: `ahe_mrta_recent_comparison_methods.md`.

---

# 1. Genel Bakış

## 1.1. Başlık ve ana iddia

**Adaptive Heuristic Ecosystem for Robust Online Multi-Robot Task Allocation in Dynamic
Inspection Environments**

> AHE-MRTA, klasik MRTA heuristic'lerini etkileşimli "strateji ajanları" olarak modelleyen,
> bağlama göre çevrim içi evrilen, açıklanabilir, hafif ve düşük veri paylaşımlı bir online
> MRTA çerçevesidir. Yenilik tekil bir heuristic değil; heuristic davranışlarının
> dominance–cooperation–suppression dinamikleriyle bağlama göre yeniden örgütlenmesidir.

## 1.2. Ana katkılar (4)

1. **Adaptive heuristic ecosystem formulation.** Heuristic'ler bağımsız solver veya statik
   ağırlık değil; dominance, cooperation ve suppression etkileşimleriyle evrilen strateji
   ajanları olarak modellenir. Çalışma sürümü **v4 EDPS** her döngüde bu dinamiklerle bir
   **paradigma seçer** (`argmax(D)`).
2. **Context-adaptive allocation.** 7 bileşenli çevrim içi bağlam vektörü maliyet
   fonksiyonu ağırlıklarını dinamik üretir.
3. **Communication-efficient execution.** Robotlara yalnızca kendi optimize görev kuyruğu
   gönderilir; ekosistem durumu, maliyet matrisi ve diğer kuyruklar merkezde kalır.
4. **Navigation-independent allocation-fitness + event-triggered replanning.** Gazebo
   metriklerinin Nav2 fiziksel sonuçlarıyla karıştığı (confounded) gözlemlenir; tüm
   yöntemlere aynı uygulanan navigasyon-bağımsız bir uygunluk (fitness) ölçütü tanımlanır.
   Yeniden planlama sürekli değil, olay tetiklemeli yapılır.

## 1.3. Önerilen yöntem ve mevcut durum

- **Önerilen yöntem:** AHE-MRTA **v4 — Ecosystem-Driven Paradigm Selection (EDPS)**.
  Kod/sınıf adları geriye uyumluluk için korundu: paket `ahe_mrta_v3`, sınıf
  `AHEMRTAv3Allocator`, `name()='ahe_mrta_v3'`.
- **Karşılaştırma seti (G1, 4 yöntem):** `ahe_mrta_v3`, `big_mrta`, `rostam_ea`,
  `consensus_dbta`. Ablasyon paper kapsamı dışındadır.

> **Durum (2026-06-29):** Makale sonuç referansı **F45/v45 klasik EDPS**'dir;
> F53 reddedilmiş tarihsel ablasyondur ve varsayılan kapalıdır. Gerçek Jain ile
> Plane-A/B bağlam-parite düzeltmeleri korunur. Eski Plane-A üretimi olasılıksal
> navigasyon proxy'si içerdiğinden allocation-only sonuç `ideal_nav=True` ile ayrı
> üretilir. Ayrıntı §13 ve `docs/F45_FAIRNESS_DEEP_DIVE.md`.
> Kodda F58-P0/P1 (geodezik ETA + ε-sınırlı yük onarımı) Plane-A holdout'unu
> geçtiği için varsayılan adaydır; resmî yönteme terfisi Gazebo kabulünden sonra
> yapılacaktır. F45 `AHE_F58_GEODESIC=0 AHE_F58_FAIR_REPAIR=0` ile korunur.

| İş | Durum |
|---|---|
| Gazebo GT 3r (4 yöntem × 3 senaryo × 5 seed × 3 yoğunluk = 180) | ✓ `results/raw/gazebo` |
| Gazebo GT 5r/25g (60, birincil) | ✓ `results/raw/gazebo_5r_v45` |
| Gazebo GT 10r/50g (60) | ✓ `results/raw/gazebo_10r_clean` |
| Allocation-only sim (5r/25t, 100 seed, `ideal_nav=True`) | ✓ `results/stats/f45_allocation_only` |
| Eski stochastic navigation proxy | tanısal; `sim_fitness.csv` allocation-only diye kullanılamaz |
| İstatistik + figür + LaTeX tablo + yol-planları + paper | ✓ derlendi (0 çözümsüz ref) |

**Ana sonuç özeti:** AHE = Consensus-DBTA ile **eş-lider fitness** (Düzlem A, nav-bound tavan)
+ **150-340× latency** + Gazebo'da **%100 tamamlama / en düşük robot_failure DVR / en düşük churn**
(Düzlem B). Detay §6/§13.

---

# 2. Problem Tanımı

**Sınıf (Gerkey–Matarić):** ST-SR-TA, time-extended, online dynamic task arrival. Her robot
aynı anda tek görev; her görev tek robot; görev sayısı robottan fazla, görevler zamanla
aktifleşir.

- Robot kümesi: `R = {r_1, …, r_N}`
- Görev kümesi: `T(t) = {τ_1, …, τ_M(t)}`, `τ_j = {p_j, q_j, a_j, d_j, s_j, c_j}`
  (konum, öncelik, aktivasyon, deadline, servis süresi, kritik etiketi)
- Robot durumu: `x_i(t) = {pose, availability, battery, nav_state, reliability, workload}`
- Karar değişkeni: `x_ij(t) ∈ {0,1}`; robot kuyruğu `Q_i(t)` sıralı görev listesi

**Olay-düzeyi sözlüksel amaç:** Uygulanabilirlik ve kilitli yürüyen görevler
uygulandıktan sonra önce atanabilen görev sayısı büyütülür, ardından bu
maksimum-kardinaliteli planlar arasında maliyet küçültülür. Yalnız maliyeti
`Σ_iΣ_j x_ij C_ij` biçiminde küçültmek, `Σ_i x_ij ≤ 1` altında hatalı olarak
``hiç görev atama'' çözümünü üretirdi.

```text
X*(t) = argmax_{x∈X(t)} Σ_i Σ_j x_ij
x*(t) = argmin_{x∈X*(t)} Σ_i Σ_j x_ij·Cost(r_i, τ_j, t)
```

**Normalize çift maliyeti:**

```text
Cost(r_i, τ_j, t) = w_d·D_ij + w_p·P_j + w_b·B_i + w_l·L_i + w_f·F_i + w_t·T_j + w_r·R_ij
W(t) = [w_d, w_p, w_b, w_l, w_f, w_t, w_r]
```

`D`=normalize varış/path cost, `P=(4-priority)/3` öncelik cezası,
`B`=batarya riski, `L`=göreli iş yükü, `F`=arıza riski,
`T`=deadline aciliyeti, `R`=navigasyon/toparlanma riski. Deadline, yetenek,
teklif, sticky ve yeniden-atama düzeltmeleri ayrıca eklenir. **AHE'nin farkı: `W(t)`
sabit değildir, ekosistem tarafından çevrim içi üretilir.**

**Koşu düzeyi hedefler:** completion↑, delay↓, DVR↓,
workload imbalance↓, recovery time↓, decision latency↓.

**Kısıtlar:** `Σ_i x_ij ≤ 1`; uygun olmayan/kritik bataryalı robota atama yok; başarısız
görev `T_replan(t)`'e girer; her robot kendi kuyruğunu sırayla yürütür.

---

# 3. Yöntem: AHE-MRTA (EDPS) — 5 hormon / 4-boyutlu bağlam

**Methodolojik katkı.** Mevcut MRTA yöntemleri tek paradigma altında çalışır (BiG: weighted
bipartite, RoSTAM: evolutionary, CDBTA: consensus bidding). AHE bir **selection hyper-heuristic**
(Burke et al.): allocation'ı kendi çözmez, hangi düşük-seviye tahsis-sezgiselinin (paradigma)
uygulanacağını **çevrim içi** seçer. Baskınlık vektörü `D(t) ∈ ℝ⁵_{≥0}`, cooperation matrisi `A` ve
suppression matrisi `S` ile Lotka–Volterra tipi evrilir. **Seçim iki katmanlıdır:** akut rejimleri
(arıza, deadline) hızlı belirlenimci bağlam-override'ları yakalar; aksi halde `argmax_i D_i`.
Her paradigma AHE'nin kendi kodudur (rakip allocator'a delegasyon yok).

> **v4.6 (5h/4c):** energy/resource hormonları + battery/workload/instab bağlam-boyutları
> kaldırıldı (tüm rejimlerde inaktif; bağlam ablasyonu Δfitness≈0). Kod (`ahe_variants.py`,
> `simulate_and_tune.py`, `ecosystem_manager_node.py`) + makale birebir 5 hormon / 4 boyut.

## 3.1. Beş hormon → beş paradigma

| `i` | Hormon | Paradigma | İç mekanizma | İlişkili klasik aile |
|---|---|---|---|---|
| 0 | H_SPATIAL | `_paradigm_spatial_greedy` | Nearest-feasible + strict reject | Uzamsal açgözlü tahsis |
| 1 | H_CRIT | `_paradigm_priority_first` | Priority-tiered LSA | Auction/CBBA |
| 2 | **H_TEMP** (default) | `_paradigm_edf_strict` | EDF + 3PHA multi-phase bipartite | deadline-aware bipartite |
| 3 | H_STAB | `_paradigm_commit_once` | Hard sticky, no reassign | Commit-once / kararlılık-odaklı tahsis |
| 4 | H_RECOV | `_paradigm_orphan_first` | Orphan-first redistribution | Recovery-first MAPF |

Her paradigma ortak bir ilkel paylaşır — fizibilite-maskeli maliyet matrisi `C^(p)` üzerinde
**doğrusal toplam atama (LSA / Hungarian):**

```text
x^(p) = argmin_{x∈X} Σ_r Σ_τ C^(p)_{r,τ} · x_{r,τ}
X: Σ_τ x_{r,τ} ≤ Q (kuyruk),  Σ_r x_{r,τ} ≤ 1 (tek-atama),  yetenek fizibilitesi
infeasible çift → C^(p)_{r,τ} = ∞
```

Paradigmalar yalnız `C^(p)`'yi ve kuyruk sıralamasını şekillendirir (ayrıntı §3.6).

## 3.2. Bağlam vektörü (4-boyut)

Her olayda `t_k` durum 4-boyutlu vektöre sıkıştırılır, `c(t_k) ∈ [0,1]^4`. `m=|T(t_k)|`,
`n=|R|`, `R^av` = uygun (alive, stuck değil, kapasiteli), `R^f` = arızalı/stuck robotlar;
`Δ_d = 60` s deadline ufku:

```text
c1 = min(1, m/n)                              # görev yoğunluğu (task density)
c2 = |R^av| / n                              # robot uygunluğu (availability)
c3 = |{τ : d_τ − t_k ≤ Δ_d}| / max(1, m)     # deadline baskısı
c4 = |R^f| / n                               # arıza oranı (failure rate)
```

Her boyut, farklı bir tahsis-sezgiseli ailesinin sömürdüğü bir sinyaldir: `c1,c2` arz/talep
dengesi (yük-farkında); `c3` deadline-kısıtlı tahsis; `c4` arıza-dayanıklı tahsis.

### 3.2.1. Boyut ablasyonu (7→4 indirgeme gerekçesi)

`scripts/ablate_context.py` her boyutu 0'a maskeler ve uçtan-uca etkiyi ölçer (100-seed teyit):

| Boyut | Etki (fitness / DVR) | Karar |
|---|---|---|
| failure (`c4`) | ms 0.491→0.403 (−8.8pp) | **Kritik** — H_RECOV override + boost'u taşır → **tut** |
| deadline (`c3`) | dp DVR 0.004→0.072 (18×) | **Kritik** — H_TEMP override'ı taşır → **tut** |
| density, avail (`c1,c2`) | Δ≤0.3pp | yedek ama ucuz, fallback argmax için sinyal → **tut** |
| battery, workload_var, alloc_instab | Δ≤0.3pp (tüm rejimler) | **inaktif → KALDIR** (v4.6) |

Sonuç: bağlam **4 boyuta** indirildi (battery/workload/instab çıkarıldı; Δfitness≈0). Bu, hem
sade hem hakemin "neden bu boyutlar?" sorusuna ablasyonla dayanaklı cevaptır.

## 3.3. Baskınlık dinamiği (Lotka–Volterra) — gerçek uygulama

Her paradigma `i`'nin sabit bağlam-prototipi `V_i ∈ [0,1]^4` var (Tablo aşağıda); **uyumluluk:**

```text
v_i(t_k) = cos(V_i, c(t_k)) = (V_i · c) / (‖V_i‖ ‖c‖)
```

**Performans geri-beslemesi** (tamamlama − arıza, uyumlulukla ölçeklenmiş) ve **arıza-destek vektörü:**

```text
p(t_k) = (CR_k − FR_k) · v(t_k)
b: b[RECOV]=0.6·c4,  b[STAB]=0.4·c4,  b[SPATIAL]=−0.3·c4,  diğer=0
```

**Baskınlık güncellemesi** (winner-reinforce / winner-suppress, Lotka–Volterra tipi):

```text
D(t_{k+1}) = normalize( clip_[0,1][ α·D(t_k) + η·A·D(t_k) − λ·S·D(t_k)
                                    + β·p(t_k) + γ·v(t_k) + δ·b(t_k) ] )
```

`normalize` = olasılık simpleksine projeksiyon (‖D‖₁=1, D≥0). Hiperparametreler (sim+node+makale
birebir): **α=0.65** (momentum), **β=0.40** (performans), **γ=0.20** (uyumluluk), **η=λ=0.12**
(işbirliği/baskılama), **δ=0.20** (arıza desteği), softmax **T=0.3**.

**Prototip `V` (5×4) ve seyrek `A`, `S`:**

```text
              c1(td) c2(ra) c3(dp) c4(fr)
H_SPATIAL(0)   0.7    0.7    0.1    0.1
H_CRIT  (1)    0.3    0.5    0.8    0.2
H_TEMP  (2)    0.5    0.5    0.9    0.1
H_STAB  (3)    0.3    0.3    0.3    0.8
H_RECOV (4)    0.3    0.2    0.2    0.9
A: A[TEMP,CRIT]=0.20, A[RECOV,STAB]=0.20      S: S[SPATIAL,TEMP]=0.30      (diğer=0)
```

### 3.3.1. Paradigma seçimi (override cascade + argmax + dwell)

Seçim iki katmanlı; akut rejimler belirlenimci override ile, kalanı baskınlık argmax'ı ile:

```text
p* = H_RECOV          if c4 > 0.05            # arıza → orphan_first
   = H_TEMP           else if c3 > 0.50       # deadline → edf_strict
   = argmax_i D_i     aksi halde              # klasik EDPS (kararların ~%6.8'i)
```

**Dwell histerezisi** (ρ=4): H_RECOV dışı paradigma değişimi ρ çağrı geciktirilir (ping-pong↓,
reaktiflik korunur). *Mimari nüans: override'lar akut olayları çözdüğünden L-V dinamiği kararların
azınlığını (rf/mixed ~%6.8) belirler; dinamiğin ağırlığı ağırlık-karışımı (W_eco) üzerindedir.*

## 3.4. Maliyet fonksiyonu ve sabitler (tek kaynak)

```text
cost(r_i, τ_j, t) =
   w_d·AT_ij + w_p·P_j + w_b·B_i + w_l·L_rel_i + w_f·F_i + w_t·T_j(escalated) + w_r·R_i
 + deadline_penalty_ij
 − DEADLINE_CAPABILITY_W·capability_ij        (W = 2.20)
 − 0.05·bid_ij                                 (hibrit bid)
 − STICKY·[τ_j ∈ prev_queue(r_i)]              (STICKY = 1.00, incumbent bonus)
 + REASSIGN·[prev_robot(τ_j) ≠ r_i]            (REASSIGN = 1.00, instab ↓)
 + 1.0·[q_i ≥ soft_cap]                        (kapasite)

Hard-deadline gating: yeni görevde arrival > deadline ise çift reddedilir;
                      eski rescue görevinde durum-bağımlı sınırlı pay uygulanır
Urgency escalation:    T_raw ≥ 0.70 ise üstel artış (URGENCY_SCALE)
Kuyruk sıralama:       failure_active → cheapest_insertion;  aksi halde → EDF
Local swap refine:     ≤3 iterasyon, overrun azaltan robot/görev takasları
```

**Ağırlıklar ve sabitler (tek yer):**

```python
W0_V3      = [0.34, 0.10, 0.04, 0.16, 0.10, 0.22, 0.04]   # baz ağırlık
W_RECOVERY = [0.55, 0.04, 0.03, 0.22, 0.09, 0.05, 0.02]   # H_RECOV blend
ECO_BLEND_NORMAL = 0.70    # W_base = 0.30·W0_V3 + 0.70·W_eco(t)
EDPS_ENABLED = True;  STUCK_PREEMPT_ENABLED = True
DVR_SOFT_SLACK = 8.0;  URGENT_HORIZON = 30.0;  RECOVERY_HYSTERESIS = 1
SPEED = 0.22 (m/s);  NAV2_QUEUE_OVERHEAD = 22.0 (s);  AT_NORM = 220.0
DEADLINE_SLACK = 80 (s);  softmax T = 0.3;  α = 0.65;  β = 0.40 (§3.3)
```

failure_rate > 0.05 → `failure_active` (recovery_hold=4); aktifken
`W = (1−blend)·W_base + blend·W_RECOVERY`, `blend = min(0.80, 0.50 + failure_rate·0.60)`.

## 3.4.1. Kararlılık mekanizmaları (v4.1–v4.2)

Minimal-bozulma yeniden planlama ilkesi: yeniden tahsis sıfırdan değil, önceki
plan korunarak yapılır; yürüyen/çapalı atamalar yalnızca gerekçeli nedenlerle
(yetimleşme, rescue, yakın deadline) bozulur.

```python
# v4.1
PARADIGM_DWELL = 4          # F23: paradigma değişimine 4-çağrı histerezis
                            #      (H_RECOV bypass eder; reaktiflik korunur)
# v4.2 — kök neden: reassignment'ların %85'i A→B→A ping-pong'du;
# baskın kaynak stuck-preempt'in kuyruğu toptan boşaltması + arızada
# NOOP/sticky/commit-lock üçünün birden devre dışı kalması.
F26_SCOPED_FAILURE_STICKY = True   # arızada sticky yalnız yetimler için kapanır
F27_REASSIGN_MARGIN = 0.10         # robot değişimi ancak varış ≥%10 iyileşirse
                                   # (kalıcı _assign_history üzerinden; muaf:
                                   #  yetim, rescue, URGENT_HORIZON içi)
F28_DEADLINE_AWARE_PREEMPT = True  # stuck kuyruğu toptan boşaltılmaz; yalnız
F28_STUCK_WAIT_EST = 60.0          # bekleme(60s)+varış > deadline olan görevler
                                   # yetim havuzuna düşer
# (F25_INPROGRESS_LOCK = False — kuyruk yaşam döngüsünde görev tamamlanana
#  dek kuyrukta kaldığından hem sim'de hem Gazebo'da no-op; bayrak duruyor)
```

100-seed doğrulama (2026-06-12): sim kararsızlık 4.0 → **0.2–0.4** (~12×,
baseline bandı; Cons 0.11, BiG 0.11), fitness korunur: rf 0.503★ (1.),
ms 0.500 (Cons 0.506'ya −0.6pp ≈ SE/2), dp 0.447; 5r/10r ortalamada 1.lik
sürer. Regresyon kuralı: F26=False, F27=0, F28=False → v4.1 bit-özdeş.
Sim yeniden-atamayı bedelsiz modellediğinden bu paketin asıl getirisi
Gazebo'da beklenir (her yeniden-atama = Nav2 yol iptali + yeniden katetme).

### 3.4.2. F30 ablasyonu — kuyruk sıralaması (cheapest REDDEDİLDİ)

dp sim fitness'ta AHE'nin BiG'in hafif gerisinde görünmesi araştırıldı.
Sistematik eleme (rescue penceresi, atama ağırlıkları, kuyruk derinliği,
TOPTW prize-insertion, hız-kalibrasyonu) açığı kapatmadı; yalnız **EDF →
cheapest-insertion** sıralaması sim dp'yi ~0.005 artırdı (EDF aşırı yükte
"domino-kaçırma" yapar).

**Ancak cheapest çift-düzlem doğrulamasında REDDEDİLDİ:**
1. **Gazebo regresyonu:** r3t9 dp'de cheapest CR 0.889→0.778, DVR
   0.044→0.190 (4.3×), makespan 429→745 s. Sim temiz-nav'da sıralamayı
   önemsemez; gerçek Nav2 gecikmeleriyle EDF'in aciliyet-önceliği
   deadline-uyumu için gereklidir.
2. **Açık zaten gürültüydü:** 200 eşleştirilmiş tohumda EDF ile de dp
   AHE 0.4559 vs BiG 0.4583 (p=0.49 → istatistiksel parite). 100-tohumdaki
   "0.447 vs 0.461" örnekleme gürültüsüydü; mimari değişikliğe gerek yok.

→ **EDF (M18) korundu.** 200 tohumda AHE 9/9 senaryo×ölçek hücresinde
en iyi baseline ile parite veya önde (5r rf/ms anlamlı önde). Metodolojik
ders: önerilen iyileştirme ideal-sim'e değil **gerçek sisteme (Gazebo)** karşı
doğrulanır; regresyon görülünce reddedilir. (F30 bayrağı `USE_EDF_ORDER`
kodda ablasyon için durur; varsayılan True.)

## 3.5. Karmaşıklık ve maliyet

- **Latency:** bipartit matching `O(n³)` ≈ 1.3 ms (3r/15g); swap-refine ~0.4 ms ek. 5 s
  periyotta ihmal edilebilir CPU.
- **Communication:** ~84 B/kuyruk (yalnızca görev indeksleri).
- **Bellek:** `prev_queues` O(R·Q), `prev_robot_for_task` O(Q) — ihmal edilebilir.

---

# 4. Karşılaştırma Yöntemleri (G1)

Ana dosyada kısa karakterizasyon ve bibliyografya tutulur. Bu çalışmadaki operasyonel
uyarlamaların ayrıntıları `m_ahe_task_allocator/.../baselines/` altındaki uygulamalardadır;
bunlar kaynak sistemlerin bağımsız ve birebir replikasyonları değildir.

| Yöntem | Online? | Adaptive? | Distributed? | Kaynak / DOI |
|---|---|---|---|---|
| **ahe_mrta_v3** (önerilen, v4 EDPS) | Yes | Yes | Centralized adaptation, decentralized execution | bu çalışma |
| big_mrta — Online Weighted Bipartite Graph MRTA | Yes | No/limited | Dağıtık kullanıma uygun | P. Ghassemi and S. Chowdhury, “Multi-robot task allocation in disaster response: Addressing dynamic tasks with deadlines and robots with range and payload constraints,” RAS 147 (2022) 103905, DOI: 10.1016/j.robot.2021.103905 |
| rostam_ea — RoSTAM-inspired Evolutionary MRTA | Yes | Yes | No/centralized | M. U. Arif and S. Haider, “On-line task allocation for multi-robot teams under dynamic scenarios,” IDT 18(2) (2024) 1053–1076, DOI: 10.3233/IDT-230693 |
| consensus_dbta — Consensus-Based DBTA2 | Yes | Partly | Yes | P. Mahato, S. Saha, C. Sarkar, and M. Shaghil, “Consensus-based fast and energy-efficient multi-robot task allocation,” RAS 159 (2023) 104270, DOI: 10.1016/j.robot.2022.104270 |

Buradaki `rostam_ea` ve `consensus_dbta` adları benchmark uyarlamalarını belirtir. Özgün
yayınlardaki yöntem adları sırasıyla **RoSTAM** ve **DBTA/DBTA2**'dir. Consensus-DBTA,
CBBA tipi görev demeti oluşturmaktan ziyade robotların en iyi tekliflerini paylaşıp görev
başına ağ-geneli maksimum teklif üzerinde uzlaşmasına dayanır.

**Adil karşılaştırma:** tüm yöntemler aynı seed seti, aynı görev havuzu, aynı robot
durumları, aynı failure olayları ve aynı Nav2 path-cost cache ile çalışır. Ortak loglanan
yöntem-bağımsız metrikler: `communication_footprint_bytes`, `allocation_message_count`,
`mean_decision_latency_ms`, `solver_runtime_ms`.

---

# 5. Deney Tasarımı

> **Değerlendirme felsefesi (neden iki düzlem?).** Gazebo'da bir yöntemin gecikmesi yüksek
> çıkarsa bunun nedeni *ya kötü atama kararı ya da* Nav2'nin fiziksel takılması olabilir —
> tek başına ayırt edilemez (confounding). Bu yüzden başarıyı **iki ayrı düzlemde** ölçeriz:
> **Düzlem A (navigasyon-bağımsız sim)** "algoritma gerçekten iyi mi?" sorusunu, **Düzlem B
> (Gazebo/Nav2 fiziksel)** "gerçek robot yığınında da çalışıyor mu?" sorusunu yanıtlar. Güçlü
> bir Q1 iddiası için AHE'nin **her iki düzlemde de** öne çıkması hedeflenir: A'da fitness
> manşeti, B'de DVR/recovery/latency üstünlüğü.

## 5.1. Senaryolar (3)

| Senaryo | Stres bileşeni | Rolü |
|---|---|---|
| **robot_failure** | Bir robot deney ortasında arızalanır (`nav_state=FAILED`) | Recovery + event-triggered replanning |
| **deadline_pressure** | Görevlerin **%50'sine** sıkı deadline | Temporal Regulator / deadline-aware allocation |
| **mixed_stress** | failure + dinamik görev + deadline + batarya + congestion birlikte | Tüm bileşenlerin birlikte testi |

## 5.2. Çoklu ölçek (sabit yoğunluk ~5 görev/robot)

Üç ölçek de aynı inspection arenasını paylaşır; yalnızca robot başlangıç sayısı (N) ve
aktifleşen görev sayısı (M) değişir, görev/robot yoğunluğu ~5'te sabit tutulur. Aşağıdaki
senaryo haritaları gerçek `_GRID` aday inspection noktalarından, `compute_spawn_positions`
başlangıç düzeninden ve `obstacle_map.pgm` doluluk haritasından üretilir (seed=1; üretici:
`scripts/generate_scenario_maps.py`).

![Ortam senaryo haritaları — 3r/15g, 5r/25g, 10r/50g](results/figures/scenario_maps_panel.png)

*Şekil — Robot sayısı (N) ve görev sayısına (M) göre senaryo haritaları. Kırmızı üçgenler
robot başlangıç konumları (sol-orta x∈[-4,-2] sütunları), mavi kareler o ölçekte örneklenen
görev noktaları, soluk noktalar 46 elemanlı aday inspection grid'i. Engeller: 16 raf direği +
4 bölme duvarı (orta 3 m geçit) + 4 silindir. 50 görevde grid tükendiğinden birkaç nokta
rastgele doldurulur (`_generate_tasks`).*

| Ölçek | Birey görsel |
|---|---|
| 3r/15g | `results/figures/scenario_map_3r15t.png` |
| 5r/25g | `results/figures/scenario_map_5r25t.png` |
| 10r/50g | `results/figures/scenario_map_10r50t.png` |

İki kanaldan ölçeklenebilirlik kanıtı:

**(1) Gazebo fiziksel doğrulama** — aynı arena (`ahe_inspection_arena.sdf`), yalnızca robot/görev
sayısı değişir.

| Ölçek | Robot | Hedef | Durum | Not |
|---|---|---|---|---|
| 3r/15g | 3 | 15 | ✓ Tamamlandı | Birincil G1 karşılaştırma |
| 5r/25g | 5 | 25 | 🔄 Devam ediyor | Nav2 TF fix uygulandı (odom_to_tf identity seed + lifecycle stagger) |
| 10r/50g | 10 | 50 | ◻ Planlandı | 5r fix ile aynı yaklaşım; stagger idx×8s, startup 180s, timeout 1800s |

**(2) Nav2-bağımsız fitness simulator sweep** — idealize varış modeli, navigasyon gürültüsü
yok; yüksek istatistiksel güç.

| Ölçek | Robot/Hedef | Seed | Durum |
|---|---|---|---|
| sim-3 | 3/15 | ≥100 (fitness) | ◻ Sıfırdan koşulacak — Gazebo ile çapraz doğrulama |
| sim-3/5/10 | 3/15, 5/25, 10/50 | 100 | ◻ Planlandı — 100 × 4 yöntem × 3 senaryo × 3 ölçek = 3600 koşu (~10 dk) |

10r için Gazebo Nav2 Jazzy lifecycle sistemsel kararsız → ölçeklenebilirlik bu ölçekte
yalnızca simulator'dan gelir.

## 5.3. Deney matrisi

| Kanal | Ölçek | Yöntem | Senaryo | Seed | Koşu | Durum |
|---|---|---:|---:|---:|---:|---|
| Gazebo | 3r/15g | 4 | 3 | 5 | 60 | ✓ Tamamlandı (+ yoğunluk sweep 180) |
| Gazebo | 5r/25g | 4 | 3 | 5 | 60 | 🔄 Devam ediyor |
| Gazebo | 10r/50g | 4 | 3 | 5 | 60 | ◻ Planlandı (5r bittikten sonra) |
| Sim (fitness) | 3/5/10r | 4 | 3 | 100 | 3600 | ✓ Tamamlandı (sim_matrix.csv) |

Video: her (ölçek × yöntem × senaryo) için **seed=01** koşusundan Gazebo + RViz çift kayıt
(3r/15g'de 12 çift; 5r'da +12 çift; 10r'da +12 çift).

## 5.4. Çift-düzlemli değerlendirme (her metrik bu çerçevede ölçülür)

Tüm metrikler iki ayrı düzlemde, **net ayrılarak** raporlanır. Aynı metriğin iki düzlem
değeri asla harmanlanmaz.

- **Düzlem A — İdealize sim (navigasyon-bağımsız):** algoritmik allocation kalitesi +
  ölçeklenebilirlik + yüksek istatistiksel güç. **Manşet metrik fitness buradadır.** Nav2
  gürültüsü yok → üstünlüğün algoritma kaynaklı olduğunu kanıtlar.
- **Düzlem B — Gazebo/Nav2 fiziksel:** gerçek ROS 2/Nav2 yığınında çalışırlığın doğrulaması.
  delay/makespan/travel burada **Nav2-confounded**'dır (caption'da belirtilir); DVR, recovery
  ve latency'de AHE üstünlüğü fiziksel olarak da görülür.

## 5.5. Metrik kataloğu

| Metrik | Tanım | Düzlem | Yön | İddia / Figür |
|---|---|---|---|---|
| **fitness** | `Σ_{zamanında} w(p) / Σ_{tüm} w(p)`, `w=max(1,p)` | **A** | ↑ | **Manşet** — allocation kalitesi (Table 3, Fig. 3); süreç görünümü Fig. 7 |
| **fitness(t)** (kümülatif) | o ana kadarki zamanında-ağırlık / toplam ağırlık | A (+B) | ↑ | Süreç boyunca karşılaştırmalı eğri (Fig. 7) |
| **CR** (benzersiz) | benzersiz_tamamlanan / aktifleşen | A+B | ↑ | Görev başarısı |
| **DVR** | deadline_ihlali / tamamlanan | A+B | ↓ | Deadline-farkındalık |
| **recovery_time** | reassign_success_time − failure_detect_time | A+B | ↓ | Dayanıklılık (Fig. 5) |
| delay | mean(completion − activation) | A+B* | ↓ | Stres altında; *B Nav2-confounded |
| makespan | son tamamlama zamanı | A+B* | ↓ | Destekleyici; *B confounded |
| workload_balance | Jain: `(Σ completed)^2 / (n Σ completed^2)` | A+B | ↑ | Yük dengesi |
| workload_balance_active | Jain, kalıcı arızalı robotlar hariç | A+B | ↑ | Fırsat-normalize tanı |
| travel_distance_balance | robot-başı mesafenin Jain indeksi | A+B | ↑ | Efor-adaleti tanısı |
| **latency** | allocation döngüsü duvar-saati (ms) | A+B | ↓ | Gerçek-zamanlılık; **robot sayısına karşı** Fig. 6d (O(n³) ölçeklenme) |
| comm_bytes / msg_count | iletim hacmi | A+B | ↓ | Düşük iletişim |
| travel_distance | toplam yol | B | ↓ | Sadece destekleyici |
| dominance / paradigma izi | `argmax(D)` zaman serisi | A+B | — | Açıklanabilirlik (Fig. 4) |

**Başarı anlatısı (öncelik):** (1) fitness'ta lider, (2) CR korunur, (3) DVR düşük,
(4) recovery kısa, (5) workload balance iyi, (6) gereksiz replanning az,
(7) latency <1 ms, (8) dominance evolution bağlama duyarlı, (9) communication düşük. Travel
distance ana başarı metriği değildir; gerekirse "robustness–performance trade-off" olur.

## 5.6. Ölçüm kuralları (sıfırdan koşumda BAŞTAN sabitlenecek)

| # | Kural |
|---|---|
| R1 | **CR = benzersiz_tamamlanan / aktifleşen.** Tamamlama olayları `task_id` ile dedup edilir; bir görev en çok 1 sayılır (eski ham olay-CR > 1.0 artefaktını önler). |
| R2 | **İki düzlem ayrı saklanır:** Düzlem A (sim) → `results/processed/sim_*.csv` (`simulate_and_tune.py`: `sim_fitness.csv`, planlı `sim_scalability.csv`); Düzlem B (Gazebo) → `results/processed/all_*.csv` (`consolidate_results.py`). Ayrı prefix → ayrı kolon/blok; harmanlanmaz. |
| R3 | **Kesin tanımlar:** recovery_time arıza tespitinden ilk başarılı yeniden-atama tamamlamasına; latency tek allocation döngüsünün duvar-saati; replanning_frequency = replan_sayısı / süre. |
| R4 | **Adil koşul:** tüm yöntemler aynı seed, görev havuzu, aktivasyon zamanları, failure olayları ve (Gazebo'da) aynı Nav2 path-cost cache ile koşar. |
| R5 | **Tam loglama:** her metrik bir CSV alanından türetilebilmeli (§8); deney yeniden koşulmadan yeni figür üretilebilsin. `ecosystem_metrics.csv` yalnızca ahe_mrta_v3'te paradigma/dominance/context loglar. |
| R6 | **Çapraz doğrulama:** sim-3r ile Gazebo-3r aynı yöntem/senaryoda korelasyon gösterilir (idealize ↔ fiziksel ayrışma şeffaf raporlanır). |

## 5.7. Raporlama düzeni ve istatistik

**Table 3 (ana):** satır = yöntem; bloklar = [Düzlem A: fitness, CR, DVR, recovery] +
[Düzlem B: CR, DVR, recovery, delay, latency]. Her hücre `mean ± std` + en iyi **kalın**.

**İstatistik:**
- Sim (≥100 seed): Mann-Whitney U (Bonferroni) + Cliff's δ; ölçek regresyonu **her ana metrik için** `metrik ~ robot_count` (fitness, CR, recovery, latency) — eğim + p raporlanır.
- Gazebo (≥5 seed): median ± IQR; Mann-Whitney U (Bonferroni); Cliff's δ.
- Ölçeklenebilirlik iddiası birincil olarak sim sweep regresyonundan; Gazebo 3r/(5r) fiziksel onay.
- **Minimum kabul koşulu:** AHE v4, fitness'ta 3 senaryoda lider **ve** {recovery_time,
  DVR, workload_balance, delay}'den en az 2'sinde istatistiksel anlamlı (p<0.05, |Cliff's δ|
  ≥ 0.33) avantaj üretmeli.

---

# 6. Sonuçlar

> **DURUM (2026-06-04): Sonuç değerleri YOK — sıfırdan koşum bekleniyor.** Yöntemde
> iyileştirmeler yapıldığı için **tüm önceki koşum sonuçları geçersiz kılındı ve silindi**.
> Bu bölüm yalnızca §5.4 çift-düzlemli çerçevenin **rapor iskeletini** tutar; sayısal değerler
> yeni koşum (§5.6 R1–R6 kurallarıyla) tamamlandıkça doldurulacaktır. Aynı metriğin iki düzlem
> değeri asla harmanlanmaz (§5.4); tablolarda ayrı blok/kolonda durur (R2, §5.7 Table 3).

## 6.1. Düzlem A — Navigasyon-bağımsız sim (algoritmik allocation kalitesi)

İdealize varış modeli; Nav2 gürültüsü yok → üstünlüğün **algoritma kaynaklı** olduğunu
ayrıştırır. Yüksek istatistiksel güç (≥100 seed × 3 senaryo × ölçek).

### 6.1.1. Fitness — manşet metrik

Fitness = idealize varış modelinde öncelik-ağırlıklı zamanında-tamamlama oranı; tüm
yöntemlere aynı uygulanır.

```text
F = Σ_{zamanında} w(p_i) / Σ_{tüm} w(p_i),   w(p) = max(1, p)
```

| Senaryo | AHE v4 | Cons-DBTA | BiG | RoSTAM |
|---|---:|---:|---:|---:|
| robot_failure | — | — | — | — |
| mixed_stress | — | — | — | — |
| deadline_pressure | — | — | — | — |

*(yeni koşumdan doldurulacak; `mean ± std`, en iyi kalın)*

### 6.1.2. Düzlem A — CR / DVR / recovery

Benzersiz-CR, DVR ve recovery_time sim sweep'ten (§5.2) ayrı blokta raporlanır (§5.7 Table 3
Düzlem A bloğu). *(yeni koşumdan doldurulacak)*

## 6.2. Düzlem B — Gazebo/Nav2 fiziksel (3r/15g, ≥5 seed)

Gerçek ROS 2/Nav2 yığınında çalışırlığın doğrulaması. delay/makespan/travel burada
**Nav2-confounded**'dır (caption'da belirtilir); DVR, recovery ve latency fiziksel düzlemde
ayrıca raporlanır.

**CR ölçümü hakkında kritik not:** Gazebo runner tamamlama *olaylarını* sayar; agresif
yeniden-navigasyon yapan yöntemler aynı görev için yinelenen `task_completed` üretebildiğinden
ham olay-CR 1.0'ı aşabilir (çift-sayım artefaktı). Tüm CR değerleri **düzeltilmiş
benzersiz-CR** (R1) olarak raporlanır.

### 6.2.1. Benzersiz-CR (canonical)

| Senaryo | AHE v4 | BiG | RoSTAM | Cons-DBTA |
|---|---:|---:|---:|---:|
| robot_failure | — | — | — | — |
| mixed_stress | — | — | — | — |
| deadline_pressure | — | — | — | — |

*(yeni koşumdan doldurulacak)*

### 6.2.2. CR dışı metrikler (DVR / Delay / RecTime / Latency)

| Senaryo | Metrik | AHE v4 | BiG | RoSTAM | CDBTA |
|---|---|---:|---:|---:|---:|
| robot_failure | DVR | — | — | — | — |
| | Delay (s) | — | — | — | — |
| | RecTime (s) | — | — | — | — |
| | Latency (ms) | — | — | — | — |
| mixed_stress | Delay (s) | — | — | — | — |
| | DVR | — | — | — | — |
| | RecTime (s) | — | — | — | — |
| | Latency (ms) | — | — | — | — |
| deadline_pressure | Delay (s) | — | — | — | — |
| | DVR | — | — | — | — |
| | Latency (ms) | — | — | — | — |

*(yeni koşumdan doldurulacak; ★ = o senaryoda 1. sıra)*

## 6.3. Çapraz-düzlem tartışma (A ↔ B ayrışması)

Yeni koşum sonrası AHE'nin Düzlem A üstünlüğünün **algoritma kaynaklı**, Düzlem B'deki olası
metrik kayıplarının ise **navigasyon kaynaklı** olduğu R6 çapraz doğrulama (sim-3r ↔ Gazebo-3r)
ile gösterilecektir. mixed_stress'te beklenen CR↔DVR takası (strict deadline-gating düşük DVR
sağlar) yeni verilerle tartışılacaktır. *(metin yeni koşum sonrası yazılacak)*

---

# 7. ROS 2 / Gazebo Mimarisi

**Yazılım yığını:** Ubuntu 24.04 · ROS 2 Jazzy · Gazebo Harmonic · ros_gz · Nav2 ·
TurtleBot3 Waffle Pi · Python 3.12 · rclpy · rosbag2 · pandas · matplotlib.
Gazebo Classic API varsayma; ros_gz-uyumlu Harmonic entegrasyonu kullan.

## 7.1. Paketler

| Paket (`src/`) | Görev |
|---|---|
| `m_ahe_mrta_bringup` | Launch dosyaları (`phase9_experiments.launch.py` vb.) + `multi_robot_helpers.py` |
| `m_ahe_mrta_msgs` | Custom mesajlar |
| `m_ahe_mrta_gazebo` | World, robot spawn, target marker |
| `m_ahe_task_manager` | Görev havuzu, aktivasyon, durum |
| `m_ahe_robot_interface` | Status summary, queue listener, Nav2 action, STUCK tespiti (`robot_interface_node.py`) |
| `m_ahe_ecosystem_manager` | Context vector, dominance, A/S, weight (`ecosystem_manager_node.py`) |
| `m_ahe_task_allocator` | Maliyet matrisi, atama, kuyruk optimizasyonu (EDPS); `experiment_runner_node.py` + `baselines/` |
| `m_ahe_recovery_manager` | Arıza/erişilemezlik/delay → replan tetikleme |
| `m_ahe_evaluation` | CSV, metrik, grafik, rapor |
| `m_ahe_nav2_config` | Robot-bazlı Nav2 parametreleri + `maps/obstacle_map.pgm` |

**Önerilen yöntem + baseline kodu:** `m_ahe_task_allocator/.../baselines/`. Strateji
registry `experiment_runner_node.py` `_STRATEGIES`: `ahe_mrta_v3` →
`AHEMRTAv3Allocator` (`ahe_variants.py`), `big_mrta`, `rostam_ea`, `consensus_dbta`
(+ `static_weighted` baz). `ahe_mrta_v3` bir **strateji adıdır** (paket değil; geriye
uyumluluk için korunmuştur).

## 7.2. Custom mesajlar (özet)

`TaskWaypoint`, `OptimizedTaskQueue` (robota giden tek mesaj), `RobotStatusSummary`,
`LocalExecutionFeedback`, `TaskInfo`, `TaskPool`, `AllocationEvent`, `EcosystemState` (yalnızca
offline analiz — robotlara gönderilmez). Tam alan tanımları repo `.msg` dosyalarındadır.

Durum kodları: `availability {0 available,1 busy,2 unavailable}`; `battery {0 normal,1 low,
2 critical}`; `navigation {0 idle,1 navigating,2 stuck,3 failed,4 reached}`.

## 7.3. Düşük veri paylaşımı ilkesi

Robotlara **yalnızca kendi optimize görev kuyruğu** gönderilir. Robotlara gönderilmeyenler:
heuristic dominance, cooperation/suppression matrisleri, global context vector, tam
görev-robot maliyet matrisi, diğer robotların kuyrukları, ekolojik hafıza. Doğru ifade:
*"communication-efficient centralized adaptation with decentralized execution."*

## 7.4. Kritik Jazzy/Harmonic düzeltmeleri

- **Nav2 namespace:** `nav2_params.yaml`'daki niteliksiz anahtarlar tam-nitelikli forma
  çevrilir (`controller_server:` → `/robot_1/controller_server:`); `map_server` altına
  `frame_id: robot_1/map` eklenir (yoksa TF zinciri tamamlanmaz).
- **Sensör:** gz-sim 8 `type="lidar"` (CPU) desteklemez → `gpu_lidar` + OGRE1
  (`<render_engine>ogre`). OGRE2 EGL ile llvmpipe'ı yok sayar → segfault. Gazebo headless
  (`-r -s`).
- **Yazılım render (GPU sürücüsü yok):** `LIBGL_ALWAYS_SOFTWARE=1`, `GALLIUM_DRIVER=llvmpipe`,
  `MESA_LOADER_DRIVER_OVERRIDE=llvmpipe`, `DISPLAY=:1`; snap GTK değişkenleri unset.
- **DDS:** FastDDS UDP-only (`fastdds_udp_only.xml`) — SHM hataları sıfırlanır.
- **Tipler:** `startup_delay` her zaman DOUBLE (`45.0`, `75.0`), INT değil.
- **5r/25g — TF fix uygulandı:** `odom_to_tf.py` identity TF startup seed (clock-now) + 20 Hz;
  `multi_robot_nav2.launch.py` lifecycle_manager stagger idx×6s; `nav2_params.yaml`
  `transform_tolerance=5.0`. Smoke test PASS; full batch devam ediyor.
- **10r/50g — planlandı (F6 fazı):** aynı fix + stagger idx×8s (son robot: 72s gecikmeli);
  `run_experiments_robust.sh` STARTUP_DELAY=180s, TIMEOUT_SEC=1800s; smoke test sonra full batch.

**Arena:** 20×20 m; 16 raf direği, 4 bölme duvarı (orta 3 m boşluk), 4 silindir;
`inflation_radius=0.30 m`; min güvenli mesafe 0.72 m. 46 noktalı engelsiz inspection grid
(`_GRID`; 3r/15g'de 15, 5r/25g'de 25 örneklenir; 10r/50g'de grid tükenir, kalan görevler
rastgele doldurulur).

## 7.5. Congestion-aware Nav2 + recovery yürütme (Düzlem B açığını kapatma)

**Sorun.** Önceki koşumda robot_failure'da Gazebo Delay/RecTime baseline'ların gerisindeydi
(eski sayısal değerler §6 ile birlikte temizlendi). Bu bir allocation kusuru değil — aynı
senaryoda navigasyon-bağımsız fitness'ta (Düzlem A) AHE öndeydi. Kök neden navigasyon
tarafında, üç maddede:
(i) **STUCK durumu hiç set edilmiyordu** — `robot_interface_node` yalnızca REACHED/FAILED
raporluyordu; allocator'ın `navigation_state∈{2,3}` ve `STUCK_PREEMPT` mantığı ile ecosystem
`failure_rate` sayımı (STUCK+FAILED) **boşta** kalıyordu;
(ii) navigasyon congestion'dan habersizdi (`use_cost_regulated_linear_velocity_scaling=false`);
(iii) recovery yalnızca allocation düzeyinde — orphan'lar öklid mesafesiyle dağıtılıyordu.

**Çözüm — iki bölüm.** Tüm Nav2 değişiklikleri **tüm yöntemlere eşit** uygulanır (adil
karşılaştırma R4); aksi halde AHE'ye haksız avantaj olur.

### Bölüm A — Congestion-aware Nav2 (navigasyon tarafı)

| # | Değişiklik | Dosya | Durum |
|---|---|---|---|
| A1 | `use_cost_regulated_linear_velocity_scaling: false→true` (engele yaklaşınca yavaşla) | `nav2_params.yaml` | ✓ Uygulandı |
| A3 | Hızlı stuck tespiti: `movement_time_allowance 10→5`, `required_movement_radius 0.5→0.3` | `nav2_params.yaml` | ✓ Uygulandı |
| A2 | Robotlar-arası costmap katmanı (her robotun `amcl_pose`'u diğerlerine dinamik engel) | yeni node | ◻ Aşamalı (TF/timing testi gerekir) |
| A4 | Stuck'ta önce `clear_costmap`+replan, sonra spin/backup (BT) | behavior tree | ◻ Aşamalı |
| A5 | `inflation_radius`/`cost_scaling_factor` grid-search (koridoru tıkamadan güvenli mesafe) | `nav2_params.yaml` | ◻ Aşamalı (sim'de daralt, Gazebo'da 2–3 aday) |

### Bölüm B — Recovery ↔ fiziksel yürütme uyumu

| # | Değişiklik | Dosya | Durum |
|---|---|---|---|
| B1 | **STUCK tespiti + feedback:** NAVIGATING'de pose-deltası `STUCK_NO_PROGRESS_SEC` boyunca `STUCK_MIN_MOVE_M` altındaysa → `nav_state=STUCK(2)`, hedefi gerçekten iptal et, görevi `task_failed(trigger_replan)` ile erken yeniden-atamaya sok, robotu AVAILABLE'a döndür. | `robot_interface_node.py` | ✓ Uygulandı |
| B3 | Kademeli recovery tetikleyici — **B1 sayesinde otomatik:** STUCK robot `failure_rate`'i yükseltir → H_RECOV (orphan_first) congestion'da da açılır (mevcut altyapı). | — | ✓ B1 ile sağlandı |
| B2 | Congestion-aware orphan maliyeti: `_phase2_recovery_bipartite`'te öklid yerine Nav2 path-cost cache + yoğunluk cezası | `ahe_variants.py` | ◻ Aşamalı |
| B4 | Recovery'de reassign edilen göreve preemptive Nav2 izni | `robot_interface_node.py` | ◻ Aşamalı |
| B5 | Ulaşılamaz orphan'ı düşür (`expired`) — kısmen mevcut (`experiment_runner` task-fail backoff, 3 retry→120 s) | `experiment_runner_node.py` | ~ Kısmen mevcut |

### Doğrulama
- Gazebo robot_failure: AHE RecTime ≤ BiG (hedef), Delay BiG'e yaklaşsın.
- Regresyon: Düzlem A fitness + DVR/CR bozulmamalı (B5 + strict gating DVR'ı korur).
- Ablasyon: {A1+A3+B1} / {+A2} / {+B2} → her katkıyı izole et.
- R6 çapraz doğrulama: A+B sonrası sim-3r ↔ Gazebo-3r korelasyonu artmalı (açık daralmalı).
- Önce smoke test (1 seed × ahe_mrta_v3 × robot_failure), sonra 5 seed batch.

---

# 8. CSV-First Çıktı Sistemi

Grafikler rosbag'den değil CSV'den üretilir. İlke: ham olay verisi yeniden kullanılabilir CSV
olarak arşivlenir; yeni grafik/metrik istendiğinde Gazebo yeniden koşulmaz.

```text
Gazebo run → raw CSV (per experiment, runner doğrudan yazar) → consolidate (processed/all_*.csv)
           → statistical_analysis (stats/*.csv + LaTeX) + plot_results (PNG)
Sim (Düzlem A) → simulate_and_tune → processed/sim_*.csv → aynı stats/plot adımları
```

**Ana CSV'ler (her deney dizininde — `experiment_runner_node.py` koşu sırasında doğrudan
yazar; ayrı parse adımı yok):** `metadata.yaml`, `task_events.csv` (görev zamanlama/durum/
reassignment), `task_positions.csv` (görev konumları), `summary.csv` (tek satır özet — sabit
robot_N sütunu YOK), `robot_workload.csv` (robot-başına yük), `allocation_events.csv` (reassign/
failure/queue), `method_runtime.csv` (latency), `communication_metrics.csv`,
`ecosystem_metrics.csv` (yalnızca ahe_mrta_v3), `robot_state_timeseries.csv` (trajectory/state
— supplementary). Koşu bitince `DONE` dosyası yazılır.

**Pipeline scriptleri (gerçek):**
- `consolidate_results.py` → Gazebo raw CSV'leri birleştirir: `processed/all_*.csv`
  (`all_summary.csv`, `all_task_events.csv`, `all_runtime.csv`, `all_communication.csv`,
  `all_ecosystem_metrics.csv`, `all_robot_workload.csv`, `all_allocation_events.csv`).
- `simulate_and_tune.py` → Düzlem A sim çıktısı: `processed/sim_fitness.csv` (planlı:
  `sim_scalability.csv`).
- `statistical_analysis.py` → `all_summary.csv` okur, `stats/descriptive_stats.csv` +
  `stats/stat_tests.csv` + LaTeX tablolar üretir (Mann-Whitney U + Bonferroni).
- `make_extra_tables.py` → `all_summary.csv` + `stats/stat_tests.csv` → ek LaTeX tablolar.
- `plot_results.py` → PNG figürler.
- `generate_scenario_maps.py` → senaryo haritaları (`scenario_map_*.png`).

**CSV → PNG haritası (paper figür seti — plot_results.py bunların tamamını ve
yalnızca bunları üretir; main.tex referanslarıyla birebir):**

| Kaynak | PNG | Tip |
|---|---|---|
| statik diyagram | `system_overview.png` | mimari |
| statik diyagram | `adaptive_ecosystem_mechanism.png` | EDPS akışı |
| `processed/sim_fitness.csv` | `fitness_comparison.png` | gruplu bar (3 senaryo × 4 yöntem) |
| `processed/sim_scalability.csv` | `scalability_panel.png` | 2×2 line (fitness/CR/recovery/latency vs N) |
| `all_summary.csv` (3r) | `baseline_comparison_multi_metric.png` | 6-panel bar+err |
| `gazebo_10r/all_summary.csv` | `baseline_comparison_10r.png` | 6-panel bar+err |
| `all_summary.csv` | `failure_recovery.png` | 3-panel bar (robot_failure) |
| `all_ecosystem_metrics.csv` + `all_task_events.csv` + `all_summary.csv` | `dominance_recovery_panel.png` | dominance + kümülatif CR + 3 bar |
| `all_communication.csv` | `communication_footprint.png` | 2-panel bar (log+linear) |
| `all_task_events.csv` | `task_completion_timeline.png` | kümülatif line (rf+ms) |
| `generate_scenario_maps.py` | `scenario_maps_panel.png` | 1×3 harita paneli |
| ekran görüntüsü montajı | `gazebo_rviz_combined.png` | Gazebo+RViz görsel |

**Figür stili (tek yer):** 300 dpi; taban font 10, tick 9; tek sütun ~3.5", çift ~7.0";
Okabe–Ito renk körü dostu palet (AHE=vermilyon `#D55E00`, BiG=mavi `#0072B2`,
RoSTAM=yeşil `#009E73`, Cons=mor `#CC79A7`); error bar = std; yöntem sırası sabit,
önerilen yöntem son ve kalın kenarlı; figür numarası görüntü içinde DEĞİL caption'da.
**Radar chart kullanılmaz** (ters normalizasyon hakem kafası karıştırır).

---

# 9. Makale Planı

## 9.1. RA-L iskeleti (6 sayfa hedefi)

1. Introduction (0.75) — problem, gap, idea, **4 katkı**
2. Related Work (0.75) — konumlandırma (solver/auction/RL-MARL-GNN/warehouse/fault-tolerant
   hatlarından ayrım)
3. Problem Formulation (0.75)
4. Adaptive Heuristic Ecosystem (1.5) — strateji ajanları, context, dominance, A/S, weight,
   EDPS paradigma seçimi, event-triggered replanning
5. ROS 2/Gazebo Implementation & Setup (1.0) — mimari, senaryolar, G1 baselines, metrikler
6. Results & Discussion (1.5) — G1 karşılaştırma, fitness, failure/recovery, dominance
   evolution, ölçeklenebilirlik
7. Conclusion (0.25) — bulgular, sınırlılıklar, gelecek

## 9.2. Ana figürler (7; RA-L bütçesi 6) ve tablolar (4)

| # | İçerik | Kaynak |
|---|---|---|
| Fig. 1 | Sistem mimarisi | şema |
| Fig. 2 | Adaptive heuristic ecosystem mekanizması (context→dominance→weight→EDPS) | şema |
| Fig. 3 | G1 çok-metrik karşılaştırma (3 senaryo × 4 yöntem × 5 seed) | `summary.csv` |
| Fig. 4 | Dominance evolution + failure recovery paneli | `ecosystem_metrics` + `allocation_events` + `summary` |
| Fig. 5 | Failure recovery karşılaştırması (4 yöntem) | `summary` + `allocation_events` |
| Fig. 6 | **Çoklu-ölçek panel** — robot sayısına karşı: (a) fitness (b) CR (c) recovery_time (d) **latency** | `sim_scalability.csv` (+ Gazebo 3r/5r/10r noktaları overlay) |
| Fig. 7 | **Kümülatif fitness(t)** — süreç boyunca karşılaştırmalı (4 yöntem × 3 senaryo, event marker'lı) | `task_events.csv` |

> *Yerleşim:* RA-L 6-figür bütçesi sıkıysa Fig. 7 supplementary'ye alınabilir veya Fig. 3
> ile birleştirilebilir (manşet metriğin hem son-değer hem süreç görünümü tek figürde). Sayfa
> izin verirse Fig. 7 ana metinde kalması önerilir — manşet metriği görsel olarak en güçlü
> anlatan figür budur.
>
> *Ölçek etiketi (vurgu):* **Fig. 3, 4, 5 ve Table 1–3 → 3r/15g** (birincil ölçek);
> **Fig. 6 ve Table 4 → çoklu ölçek 3/5/10r** (sim sweep + Gazebo 3r/5r fiziksel onay noktaları).
> Fig. 7 birincil 3r; 5r/10r varyantları supplementary'de. Robot-sayısı bağımlılığı ana
> metinde **Fig. 6 + Table 4** ile birlikte açıkça vurgulanır; her ana figür/tablo caption'ında
> ölçek belirtilir.

| Tablo | İçerik |
|---|---|
| Table 1 | Yöntem karakterizasyonu (Online/Adaptive/Distributed) |
| Table 2 | Deney senaryoları × yöntem eşleştirmesi |
| Table 3 | Ana nicel sonuçlar (mean ± std + Mann-Whitney p) |
| Table 4 | **Ölçeklenebilirlik** — {3r, 5r, 10r} × {fitness, CR, DVR, recovery, latency} + her metrik için regresyon eğimi/p |

**Supplementary:** Table S1–S4 (descriptive / normality / pairwise p / effect size);
video çiftleri (seed=01); arena overview PNG'leri; ek figürler (communication,
latency, completion timeline, workload, arena map).

## 9.3. Anlatı stratejisi

```text
Problem: Online MRTA değişen yoğunluk, deadline, congestion ve arızada kararsızlaşır.
Gap:     Mevcut yöntemler sabit maliyet, bidding, ağır solver veya veri-yoğun öğrenmeye dayanır.
Idea:    Klasik heuristic davranışları ekosistem ajanlarına dönüştürülür.
Mechanism: Dominance + cooperation + suppression + context → çevrim içi ağırlık/paradigma.
Evidence: G1 4-yöntem (Gazebo 3r/15g + 5r/25g + 10r/50g + fitness sim) çift-düzlemli değerlendirme
          (sonuçlar yeni koşumdan — §6).
```

---

# 10. Claude Code Faz Planı

Tek prompt ile başlama. İlke: **bir faz → bir build hedefi → bir runtime doğrulama → sonraki
faz.** Her faz sonunda "stop and report."

| Faz | Çıktı | Doğrulama kapısı | Başarısızlıkta |
|---|---|---|---|
| 0 | README, research_spec, paket planı | Yapı anlaşılır, kod yok | — |
| 1 | Workspace + custom mesajlar | `colcon build` + `ros2 interface show` | dependency/msg import düzelt |
| 2 | Test pub/sub node'ları | `ros2 topic echo` alışverişi | msg type, setup.py |
| 3 | Tek robot Gazebo | `/robot_1/odom`, `/scan` yayınlanır | ros_gz, model path |
| 4 | 3 robot namespace + TF | her robot ayrı topic/TF | frame prefix, remap |
| 5 | Nav2 (robot başına) | manuel NavigateToPose çalışır | map, lifecycle, action |
| 6 | Task Manager + Robot Interface | 3 robot 15 görevi yürütür, `task_events.csv` | state machine, allocator |
| 7 | Minimum baseline allocator (sabit W0) | CSV üretir, Faz 6 ile kıyaslanır | maliyet fn, sıralama, log |
| 8 | Full AHE (context/dominance/A/S/weight/EDPS) | dominance + weight loglanır, `ecosystem_metrics.csv` | normalize, clip, softmax |
| 9 | G1 deneyleri (4 yöntem) | tüm CSV'ler dolu, aynı seed/görev/failure | `ahe_mrta_recent_comparison_methods.md` oku |
| 10 | Figür + tablo + istatistik | `results/figures/*.png`, `results/stats/*.csv` + LaTeX `.tex` | plot/stats script düzelt |

**Başlangıç prompt'u (özet):**

```text
You are building a ROS 2 Jazzy + Gazebo Harmonic prototype for a Q1/RA-L multi-robot task
allocation paper: AHE-MRTA (Adaptive Heuristic Ecosystem). Develop in validated phases; each
phase must pass colcon build + a minimal runtime check before the next. Use ros_gz-compatible
Harmonic (no Gazebo Classic APIs). Do NOT reduce AHE to adaptive weighting — log dominance,
cooperation/suppression, context compatibility, and weights separately. Robots receive ONLY
their own optimized task queue; ecosystem state stays centralized (logged for eval only).
Prioritize navigation-independent fitness, workload balance, recovery time, delay-under-stress,
dominance evolution, communication footprint — not travel distance. Use a CSV-first reusable
pipeline (raw per-experiment CSV → processed merged CSV → plots/stats). Implement comparison
baselines only after reading ahe_mrta_recent_comparison_methods.md. No deep RL / heavy VRP
solvers. Phase 1: workspace + custom messages only; success = colcon build + ros2 interface
show. Then stop and report.
```

---

# 11. Hakem Soru-Cevap

1. **Sadece adaptive weighting değil mi?** Ağırlıklar elle değil; dominance, A/S, context
   compatibility ve EDPS paradigma seçimi üzerinden üretilir. Dominance evolution figürü ve
   bağlama-koşullu ağırlık değişimi bunu deneysel gösterir.
2. **Neden RL değil?** Amaç açıklanabilir, düşük-hesap, gerçek-zamanlı ROS 2 uygulanabilir bir
   heuristic framework. RL ileride karşılaştırma olarak eklenebilir.
3. **Auction'dan farkı?** Auction'da robotlar teklif verir; AHE heuristic davranışların
   bağlama göre baskınlığını yöneten üst katmandır. Auction baseline olabilir.
4. **Simülasyon yeterli mi?** 4 baseline, 3 stres senaryosu, karar gecikmesi ve gerçek
   ROS 2/Nav2 yığını ile desteklenir; mimari gerçek robota taşınabilir.
5. **Ölçeklenebilirlik?** İki kanal: Gazebo fiziksel (3r, 5r planlandı) + Nav2-bağımsız
   fitness sweep (3/5/10r, ≥100 seed) + regresyon. (Sonuçlar yeni koşumdan; §6.)
6. **Ne zaman başarısız olur?** Çok hızlı görev akışı / aşırı dar geçitlerde replanning
   yükselir; bu yüzden replanning_frequency ve latency açıkça raporlanır.
7. **Batarya gerçek mi?** Fiziksel enerji modeli yoksa "simulated battery state variable"
   olarak açıkça belirtilir; donanım ömrü iddiası yapılmaz.
8. **Merkezi mi dağıtık mı?** Merkezi adaptasyon + dağıtık yürütme; düşük-boyutlu kuyruk
   gönderir, düşük-veri özet alır. Tam dağıtık iddia edilmez.

---

# 12. Sınırlılıklar (dürüst raporlama)

- Doğrulama Gazebo/ROS 2 simülasyonuyla yapılır; gerçek robot filosu gelecek çalışma.
- Battery-aware bileşen simüle edilmiş durum değişkenidir.
- AHE merkezi karar katmanı kullanır; tam dağıtık MRTA iddiası yoktur.
- Gazebo 10r, 5r TF fix (odom_to_tf identity seed + lifecycle stagger idx×8s) uygulanarak
  koşulacaktır; Nav2 lifecycle kararsızlığı giderildi. Başarısız olursa §12 limitation olarak
  yeniden belgelenir ve ölçeklenebilirlik yalnızca sim sweep'ten raporlanır.
- AHE her metrikte 1. olmak zorunda değildir; temel iddia stres altında dayanıklılık, yük
  dengesi, toparlanma ve açıklanabilir adaptasyondur.

---

# 13. Mevcut Durum ve Kalan İşler (2026-06-23)

## 13.1. Tamamlanan durum

**Makale anlık görüntüsü: AHE = v45 (klasik EDPS).** F50 (hafif statik seçici), F51
(max-on-time route) ve F52 (öncelik-baskın sıralama) sim'de doğrulandı ve **REDDEDİLDİ**
(marjinal/zararlı; ablasyon bayrakları ve kodları kaldırıldı). Derin iyileştirme analizi
(7 bağımsız test): sim
fitness **pozisyon-tabanlı nav-failure-bound** (~14/25 tamamlama tavanı tüm yöntemlerde),
**AHE ≈ Consensus-DBTA Pareto-frontier eşit**; realize edilebilir allocation iyileştirmesi yok
(p-hacking reddi, projenin tutarlı kalıbı).

**Reddedilen F53 deneyi (2026-06-28):** sabit robot-sırası yanlılığını kaldıran,
2 m yakın-verimli aday kümesinde exact-completion + travel tie-break kullanan adil backfill.
100-tohum 5r/25g'de ortalama Jain 0.727→0.733; deadline_pressure Jain 0.779→0.794,
CR 0.573→0.585, mesafe 869.7→775.3, churn 0.995→0.668; fitness/DVR değişimi ≤0.002.
3r/15g deadline Gazebo dumanı 15/15 görev, Jain=0.974, latency=0.43 ms tamamlandı.
Bağımsız 101--200 tohum holdout'unda üç senaryoda da Jain/CR/delay/DVR/mesafe/churn
yönlerinden hiçbiri gerilemedi; deadline Jain +0.025, CR +0.013, mesafe -91.0, churn -0.256.
İkinci bağımsız 201--300 holdout'unda Jain farkları +0.001/+0.001/+0.013, mesafe
farkları -14.33/-14.32/-87.18'dir. Holm düzeltmesi sonrası tüm mesafe farkları ile
deadline CR/churn anlamlı; Jain farkları pozitif fakat bu blokta tek başına anlamlı
değildir. Deadline fitness (-0.003) ve DVR (+0.003) küçük ters farkları Holm sonrası
anlamlı değildir; bu takas sonuç anlatımında korunacaktır.
Ek ölçek denetiminde 10r/50g Jain farkları robot_failure/mixed/deadline için
+0.001/+0.010/+0.038'dir. 3r/15g deadline Jain +0.015 iken failure/mixed Jain
-0.003/-0.005'tir; bu küçük-filo takası fiziksel çok-tohum kampanya öncesinde
olumlu sonuç gibi sunulmayacaktır.
Ek düzeltmeler: gerçek Jain ortak tanımı; `deadline-now≤60`; enjekte arızanın c4'e iletimi;
Plane-A yoğunluk paydasının robot sayısına hizalanması. Tam kanıt ve komutlar ayrı araştırma
notundadır. 2026-06-29 kararıyla bu aday aktif yöntemden çıkarılmıştır.

**F45 kök-neden sonucu (2026-06-29):** eski Plane-A varsayılanı konuma bağlı
`p_success` ve 30 s timeout içerdiği halde Nav2-bağımsız diye etiketlenmişti.
`ideal_nav=True` allocation-only koşusunda F45 5r/25g için üç senaryoda CR/fitness
1.000; aktif Jain robot_failure/mixed/deadline için 0.984/0.986/0.973'tür. F54--F56
adalet adayları bağımsız holdout'ta doğrulanmadı ve temizlendi. Bundan sonraki
iyileştirme completion bonusu değil, gerçek yol/reachability maliyeti ve robot-görev
çiftine özgü başarısızlık hafızasıdır. Tam kayıt `docs/F45_FAIRNESS_DEEP_DIVE.md`.

**Lokalizasyon: ground-truth** (statik `map→odom`, başlangıç pozu). AMCL terk edildi (5r'de
temelden sapıyor; katkı = allocation, lokalizasyon değil → ground-truth bilimsel savunulabilir,
kasıtlı deneysel kontrol; §12 limitation).

**Veri TAM (hepsi ground-truth):**
| Düzlem | Veri | Durum |
|---|---|---|
| A — Nav2-bağımsız sim | `sim_fitness.csv` (5r/25t 100 tohum), `sim_scalability.csv` (3/5/10) | ✓ taze v45 |
| B — Gazebo GT 3r | `results/raw/gazebo` (180 deney, yoğunluk sweep 9/15/24) | ✓ |
| B — Gazebo GT 5r | `results/raw/gazebo_5r_v45` (60 deney, birincil) | ✓ kanonik |
| B — Gazebo GT 10r | `results/raw/gazebo_10r_clean` (60 deney) | ✓ |

**Pipeline + makale TAM:** consolidate/stats/plots/extra_tables v45'e bağlı; **yol-planları**
(`results/figures/path_grids/`, 4 yöntem hizalı, 3 ölçek × 3 senaryo); `main.tex` + `main_tr.tex`
iki-düzlem (Düzlem A sim eş-liderlik + Düzlem B Gazebo GT üstünlük), 0 çözümsüz ref, derlendi
(EN 16sf + TR 17sf).

**Manşet (dürüst):** AHE = en güçlü baseline (Consensus-DBTA) ile **eş-lider fitness** (A deadline
1.=0.482, rf eşit=0.540, mixed −0.001) + **150-340× latency üstünlüğü** + Gazebo'da **%100
tamamlama / en düşük deadline-ihlali (robot_failure) / en düşük gerçek churn**.

## 13.2. Kalan işler (opsiyonel)
- Gazebo prose'undaki bireysel CR/DVR/latency sayılarının her birini stats CSV'leriyle tek tek
  çapraz-doğrulama (LaTeX tablolar otomatik `\input`, güncel).
- 3r/10r yol-planı grid'lerini ek figür olarak ekleme (şu an yalnız 5r setup figüründe).
- Related work 2023-sonrası güncelleme (MRTA SLR, SMT-based, RL/MARL/GNN, fault-tolerant).
- Yedek/dead-end veriler `results/_depo_archive/`'a alındı (silme yerine arşiv politikası).

## 13.3. Temel kaynaklar

Taksonomi: Gerkey & Matarić (2004), Korsah et al. (2013). Fault-tolerant: Parker (ALLIANCE,
1998). Market/auction: Zlot et al. (2002), Kalra et al. (2005). Deadline: Liu & Layland (1973).
Energy-aware: Mei et al. (2005), Dasgupta & Woosley (2013). Nihai related work, 2023 sonrası
güncel hatlarla (yukarıda) genişletilmeli.

---

> **Revizyon notu (2026-06-04 sadeleştirme):** Belge ~4460 → ~600 satıra indirildi. Tek
> kaynağa hizalananlar: **CR = §22.3 benzersiz-CR** (ham olay-CR tablosu çıkarıldı);
> **yöntem = EDPS, 5 paradigma / 4-boyut bağlam** (v4.6; energy/resource + battery/workload/instab
> kaldırıldı — §3); **dominance = gerçek `ecosystem_manager_node.py` Lotka–Volterra denklemi**
> (α=0.65, β=0.40 — §3.3); **deadline_pressure = %50**. Çoklu ölçek planı "DONE/planlandı" etiketleriyle
> korundu. Karşılaştırma yöntemi ayrıntıları `ahe_mrta_recent_comparison_methods.md`'dedir.
>
> **Sonraki eklemeler:** çift-düzlemli değerlendirme (§5.4, Düzlem A/B) + ölçüm kuralları
> R1–R6 (§5.6); **instability** raporlanan metriklerden çıkarıldı (yalnızca context girdisi);
> **Fig. 7** kümülatif fitness(t); **Fig. 6 çoklu-ölçek panel** (fitness/CR/recovery/latency
> vs robot) + Table 4 genişletildi; **§7.5 congestion-aware Nav2 + recovery** (kod: A1/A3
> `nav2_params.yaml`, B1 `robot_interface_node.py` uygulandı; A2/B2 aşamalı). Güncel: **7 ana
> figür (bütçe 6) + 4 ana tablo**.
>
> **Revizyon (2026-06-23):** Yöntem **v45 (klasik EDPS) kilitlendi**; F50/F51/F52 sim'de
> doğrulanıp reddedildi (kod+bayraklar kaldırıldı). **AMCL terk → ground-truth** (katkı=allocation).
> Sonuç çerçevesi **eş-liderlik** (AHE≈Consensus-DBTA, fitness nav-bound) + Gazebo GT üstünlük
> (latency/tamamlama/churn). Tüm veri TAM, paper EN+TR derlendi. **Yol-planları** eklendi
> (`path_grids/`). §1.3 ve §13 güncel duruma çekildi. Dead-end/yedek veriler `results/_depo_archive/`.
>
> **Revizyon (2026-06-29):** F53 ve devam fairness yamaları bağımsız holdout'ta
> reddedildi; aktif yöntem F45'e döndü. Plane-A allocation-only (`ideal_nav=True`) ile
> stochastic navigation-proxy ayrıldı. Gerçek Jain ve Plane-A/B context-parite
> düzeltmeleri yöntemden bağımsız doğruluk düzeltmeleri olarak korunur.
