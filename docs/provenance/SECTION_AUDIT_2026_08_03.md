# Bölüm Bazlı Denetim — 2026-08-03

> **SONUÇ: 19 bulgu, 18'i düzeltildi, 1'i kullanıcı kararıyla kapatıldı.**
> EN 27 sf / TR 28 sf, ikisi de temiz derleniyor, **0 çözümsüz referans/atıf**.
> 24/24 tablo ve 8/8 veri figürü tüm düzenlemelerden sonra hâlâ birebir
> yeniden üretilebiliyor. Figür 1 dıştan-içe yeniden çizildi.
>
> En ağır üçü: **F-09** (makale 50 ms bütçesi konusunda kendisiyle çelişiyordu),
> **F-19** (makalenin manşet deneyi üç yerde "henüz yapılmalı" diye yazılıydı),
> **F-03** (§V'te dört bayat sayı — aynı karşılaştırma makalede iki kez yazılmış,
> biri doğru biri bayattı).

Prosedür: her bölümde üç geçiş — (1) veri–kod uyumu, (2) matematiksel doğruluk,
(3) tutarsızlık. Kanıt kuralı: metin ↔ **kanonik kaynak** karşılaştırılır, araya
türetilmiş katman konmaz.

## Harness

### Bölüm satır haritası

| Bölüm | EN (`main.tex`) | TR (`main_tr.tex`) |
|---|---|---|
| Abstract | 52–80 | 55–86 |
| I Introduction / Giriş | 88 | 94 |
| II Problem Formulation / Problem Tanımı | 205 | 213 |
| III Method / Metot | 352 | 358 |
| — context representation | 388 | 387 |
| — override cascade | 419 | 418 |
| — cost weights + dominance fallback | 455 | 455 |
| — geodesic ETA + bounded repair | 546 | 548 |
| — paradigm library | 610 | 613 |
| — algorithm | 661 | 668 |
| — configuration | 696 | 703 |
| IV Experimental Design / Deney Tasarımı | 717 | 725 |
| — Hardware / Software / Arena / Scales | 720/729/760/791 | 728/737/768/799 |
| — Stress Scenarios / Baselines | 806/846 | 814/855 |
| — Eval settings / Metrics / Statistics | 898/914/952 | 906/923/961 |
| V Allocation-only + proxy | 966 | 976 |
| VI Gazebo | 1102 | 1108 |
| VII Discussion / Tartışma | 1468 | 1484 |
| — Limitations / Sınırlılıklar | 1718 | 1737 |
| VIII Conclusion / Sonuç | 1838 | 1862 |

22 denklem etiketi (`\label{eq:*}`). Tahsis edici: `baselines/ahe_variants.py`
(2524 satır, `AHEMRTAv3Allocator` sınıfı satır 292).

### Kanonik kaynaklar
`processed/all_summary.csv` (480 Gazebo koşusu) · `processed/sim_fitness*.csv`
(500 tohum) · `processed/sim_scalability.csv` (100 tohum) ·
`stats/stat_tests.csv` · `raw/gazebo_ablation/` + `ablation_analysis.txt` ·
`arm5_exploratory.txt` · `prio_ab_result.txt`.

---

## Bulgular

### F-01 · `\rho` iki farklı büyüklük için kullanılıyor — DÜZELTİLDİ
**Bölüm:** II (eq:cost) ve III (override kaskadı + Configuration).

- `\rho(\pi)=1-0.1(\pi-1)` → öncelik maliyet çarpanı (satır 298, 301, 317, 321;
  Sınırlılık (xii)'de 1818, 1822, 1834).
- `\rho=4` → override **dwell/hold sayacı** (satır 450: "the counter is reset to
  $\rho=4$"; satır 701 Configuration listesi).

Aynı sembol, aynı makalede, iki tamamen farklı nicelik. eq:cost'u okuyup
Configuration'da `$\rho=4$` gören hakem öncelik çarpanını 4 sanır.
→ Dwell sayacı **$K_{\rm dwell}$** olarak yeniden adlandırıldı (EN satır 456,
701; TR 449, 708) ve tanımlandığı yerde neden ayrı sembol kullanıldığı yazıldı.
Kalan tüm `\rho` geçişleri artık yalnız öncelik çarpanı (iki dilde doğrulandı).

### Doğrulanan (kod ↔ makale birebir)
| Makale | Kod | Sonuç |
|---|---|---|
| $A_{\max}=220$~s | `AT_NORM = 220.0` (:324) | ✓ |
| $\rho(\pi)=1-0.1(\pi-1)$ | `cost *= (1 - F59_PRIORITY_COST_SCALE*(π-1))`, `=0.10` (:505,1990) | ✓ |
| $Q{=}2$ AHE, $Q{=}5$ BiG (:852-855) | `JTSC_QUEUE_CAP = 2` (:334) | ✓ |
| "$s_{r\tau}^k$ nominal konfigürasyonda sıfır" | `ADAPTIVE_SLACK_K = 0.0` → `_slack_extra()` 0 döner (:430,873) | ✓ |
| eq:cost'un $\Psi$ listesi (7 kalem) | `_cost` içinde ρ çarpanının İÇİNDE kalan 7 terim (:1915-1983) | ✓ tam |
| eq:cost'ta görünmeyen 2 terim | `_completion_fairness_cost_bonus` (`FAIR_COMPLETION_COST=0.0` → atıl) ve `_pair_failure_cost` (`F57_PAIR_MEMORY_ENABLED=False` → atıl) | ✓ atıl, denklem doğru |
| $P_\tau=(4-\pi_\tau)/3$ | `P = (4 - task.priority) / 3.0` (:1885) | ✓ |

**Not (kod hijyeni, makaleyi etkilemez):** `_cost` içindeki yorum satırları
(:1836-1837) `DVR_SOFT_SLACK (25s)` / `DVR_HARD_SLACK (60s)` diyor; gerçek
sabitler `8.0` ve `20.0` (:396-397). Yorum bayat.

---

## §Abstract (Özet) — 3 geçiş TAMAM

### F-02 · Özette ölçek karışımı — DÜZELTİLDİ
Cümle 5r ve 10r sonuçlarını sayıyor, sonra "deciding in $0.5$--$3.4$~ms" diyor.
Warm-up düzeltilmiş gerçek aralıklar: **3r 0.47–0.72 · 5r 0.81–1.33 · 10r
1.88–3.36 ms**. Yani `0.5` alt sınırı **3 robot** hücresinden geliyor, cümlenin
konusu olan 5r/10r'den değil. Skill kuralı: "Abstract — tek ölçek karışımı YOK".
→ `$0.8$--$3.4$~ms at those two scales` olarak düzeltildi. Gövdedeki
(satır 1249) `0.81--1.33 5r / 1.9--3.4 10r` zaten doğruydu.

### F-03 · §V gövdesinde dört bayat sayı — DÜZELTİLDİ
Satır 993–996 "at the primary scale AHE-MRTA leads every scenario---$0.994$,
$0.727$ ve **$0.835$** against **$0.978$, $0.678$, $0.738$**
(Table~\ref{tab:fitness}, left)" diyordu. Kanonik `sim_fitness_ideal.csv`:

| | AHE | en iyi baseline |
|---|---|---|
| RF | 0.9940 | BiG **0.9798** (metin 0.978 = Cons-DBTA, en iyi değil) |
| MS | 0.7267 | BiG **0.6682** (metin 0.678) |
| DP | **0.8402** (metin 0.835) | BiG **0.7325** (metin 0.738) |

`0.835` aslında `tab:allocation`'ın (100 tohum) 5r/DP hücresi — metin
`tab:fitness`'i (500 tohum) gösterirken öbür tablonun sayısını yazmış.
→ `0.994, 0.727, 0.840` vs `0.980, 0.668, 0.733` olarak düzeltildi ve en iyi
baseline'ın üçünde de **BiG-MRTA** olduğu açıkça yazıldı (denetim kuralı:
"en iyi" iddiası kime göre).

### F-04 · Aleyhte sonuçlar özette görünmüyordu — DÜZELTİLDİ
"20 of 63 ... 15 in its favour" → beş aleyhte sonuç yazılmamıştı.
`stat_tests.csv` ile doğrulandı: 63 test, 20 anlamlı, **15 lehte / 5 aleyhte**.
→ "15 in its favour and five against".

### F-05 · Özet 302 kelime — RAS için uzun, KARAR BEKLİYOR
Skill hedefi ~250; Elsevier/RAS tipik olarak daha da kısa ister. Kısaltma
otomatik yapılmadı: bu 300 kelime dört kez daraltılmış iddia cümlesini taşıyor,
kırpma anlamı değiştirebilir. **Kullanıcı kararı.**

### Özetteki her sayı — kanonik kaynaktan doğrulandı
| İddia | Kaynak | Sonuç |
|---|---|---|
| 480 koşu, birincil ölçekte 20 tohum/hücre | `all_summary.csv` (480 satır, 5r n=20) | ✓ |
| 500 tohum vekil | `sim_fitness*.csv` n_seeds=500 | ✓ |
| dp 5r: 0.650 vs 0.578 | hesaplandı: AHE 0.6500, Cons-DBTA 0.5780 | ✓ |
| dp 10r: 0.764 vs 0.524 | hesaplandı: 0.7644 / 0.5240 | ✓ |
| DVR −%17 / −%49 | 0.350 vs 0.422 → %17.1; 0.220 vs 0.428 → %48.6 | ✓ |
| "üç katmanda da her senaryoyu önde bitiriyor" | 5r etkin zamanında: 0.986 / 0.616 / 0.650, üçünde de birinci | ✓ |
| 20/63, 15 lehte | `stat_tests.csv` | ✓ |
| ablasyon 240 koşu, 4 kol, 20 ortak tohum | `ablation_analysis.txt` (4×60) | ✓ |
| sabit paradigma −9…−11 yp, büyük etki, düzeltilmiş p<0.005 | full 0.650 vs fixed-EDF 0.556 (−9.4 yp, p_bonf 0.0032) ve fixed-orphan 0.540 (−11.0 yp, p_bonf 0.0035), ikisi de "large" | ✓ |
| override kaskadı ölçülebilir fark yaratmıyor | no-override 0.641 vs 0.650, p=0.5872 | ✓ |
| 5. kol 0.638 vs 0.650, p=0.43 | `arm5_exploratory.txt` (0.638 / 0.650 / p=0.4287) | ✓ |

---

## §I Introduction — 3 geçiş TAMAM

### F-06 · "This letter" — DÜZELTİLDİ
RA-L bırakılıp tam-uzunluk dergiye (RAS) geçildi; metin hâlâ "This letter"
diyordu. → "This paper". (EN'de tek geçiş; TR'de karşılığı yok.)

### F-07 · "The allocation-only ablation" — YANLIŞ KATMAN ADI, DÜZELTİLDİ
Girişte "The allocation-only ablation separates the variants too, and the proxy
agrees with..." deniyordu; sanki iki ayrı ablasyon varmış gibi. Oysa tek bir
simülatör-tarafı ablasyon var ve o **stokastik navigasyon vekili** düzleminde
(`tab:ablation` caption'ı ve §VII.D ikisi de böyle diyor). Üstelik
"allocation-only" bu makalede tanımlı ayrı bir katmanın adı → doğrudan kafa
karışıklığı. → "The navigation-proxy ablation ... and it agrees with...".

### F-08 · Katkı 4'te fazla iddia — DÜZELTİLDİ
"all three rank the methods alike" (üç katman da yöntemleri aynı sıralıyor)
veriyle çelişiyor. Doğrulanan:

| Düzlem | Sıralama (mixed_stress) |
|---|---|
| kusursuz-nav | AHE > BiG > RoSTAM > Cons |
| stokastik vekil | AHE > BiG > RoSTAM > Cons |
| Gazebo 5r | AHE > RoSTAM > Cons > **BiG (sonuncu)** |

BiG-MRTA vekilde üç senaryoda da ikinciyken Gazebo'da ikisinde sonuncu — çünkü
görev terk ediyor (5r/dp CR 0.664) ve vekil bunu bu kadar cezalandırmıyor.
→ "all three put AHE-MRTA first in every scenario, but the ordering *among* the
baselines does not carry across planes---commit-once BiG-MRTA is a consistent
runner-up on the proxy and last in two of three Gazebo scenarios---". Bu hâli
hem doğru hem de üç katmanlı tasarımın gerekçesini güçlendiriyor.

### Doğrulanan — mekanizma anlatımı kodla birebir
| Giriş metni | Kod (`_select_paradigm_raw`, :1037-1073) | Sonuç |
|---|---|---|
| "failure rate eşiği aşınca orphan-first" | `if failure_rate > 0.05: return 4  # H_RECOV` | ✓ |
| "deadline pressure eşiği aşınca strict EDF" | `if deadline_p > 0.50: return 2  # H_TEMP` | ✓ |
| "beş yorumlanabilir davranış üzerinde baskınlık dinamiği" | fallback `np.argmax(d[:5])` | ✓ |
| "fallback %99.9'unda spatial-greedy döndürüyor" | `audit_paradigm_selection.py` **yeniden koşuldu** | ✓ |

**Replay birebir yeniden üretildi** (bu oturumda koşuldu): 15.058 ekosistem
durumu / 120 AHE koşusu → override:failure %49.20, override:deadline %25.34,
fallback:dominance %25.47; dominance çalıştığında spatial_greedy %99.9;
sabitle değiştirmek 3/15.058 durumu (%0.020) değiştiriyor; commit_once hiç
seçilmiyor (0), priority_first tek durumda. Makale (satır 1740-1745) bu
sayıların hepsini doğru yazıyor. ⚠️ Hafızadaki eski "9989 durum / %0.03"
kaydı BAYAT — güncel değer 15.058 / %0.02.

### Not
`no-override` kolu makalede "pure $\arg\max_i D_i$" diye anlatılıyor; kodda
fallback'te iki ek koruma var (`context.dominance` boşsa ve baskınlık
neredeyse tekdüzeyse `H_TEMP` döner). Girişte bu sadeleştirme kabul edilebilir;
§III'te açıklanıp açıklanmadığı Görev #9'da denetlenecek.

---

## §II Problem Tanımı — 3 geçiş TAMAM

Denklem–kod eşlemeleri yukarıdaki harness tablosunda (hepsi ✓). eq:fairdvr
(§IV) ile eq:primary-outcomes (§II) birebir aynı biçimde — tutarlı.
İstatistik tasarımı da doğrulandı: "üç baseline × yedi metrik = 21 test/senaryo"
→ 3 senaryo × 21 = **63**, `stat_tests.csv` 63 satır ve `corrected_alpha`
= 0.05/21 = 0.002381 birebir.

### F-09 · Makale kendi kendisiyle çelişiyor: 50 ms bütçesi — DÜZELTİLDİ
Satır 1265: *"**All four** stay far inside the 50~ms budget, so the ordering is
a property of the allocators rather than a constraint on deployment."*
Satır 1274-75 (10 satır sonra): *"49--95~ms for RoSTAM-EA; AHE-MRTA therefore
stays within the 50~ms budget at every scale **while RoSTAM-EA does not**."*

Kanonik veriden 5r/25g ortalama karar gecikmesi:

| | dp | ms | rf | aralık |
|---|---|---|---|---|
| AHE-MRTA* | 1.33 | 0.89 | 0.81 | 0.81–1.33 |
| BiG-MRTA | 0.15 | 0.14 | 0.24 | 0.14–0.24 |
| Cons-DBTA | 2.43 | 0.45 | 1.39 | 0.45–2.43 |
| **RoSTAM-EA** | **94.76** | **49.28** | **66.69** | **49.3–94.8** |

RoSTAM-EA üç senaryonun ikisinde bütçeyi katbekat aşıyor. "Dördü de" ifadesi
karşılaştırmayı olduğundan iyi gösteriyordu. → "Three of the four stay far
inside the 50~ms budget... RoSTAM-EA does not (49--95~ms at this scale), and
for it the ordering is a deployment constraint as well."

### F-10 · 50 ms "sözleşmesi" iddia ediliyordu, ölçülmüyordu — KANIT EKLENDİ
$\ell_k\leq50$~ms **olay başına** bir sözleşme, ama makale yalnızca koşu-başı
**ortalama** rapor ediyordu; kuyruk görünmüyordu. Olay bazlı logdan
(`all_allocation_events.csv`) doğrudan ölçtüm:

- **Birincil ölçek (5r/25g): 60 koşuda 1.628 karar, en yavaş tek karar
  4.35 ms, 50 ms'i aşan SIFIR.** → §II'ye kanıt cümlesi olarak eklendi.
- 3r ve 10r loglarında kuyruk var (ilk-karar dışı 29 olay >50 ms, maks
  160.8 ms) — **ama bu hücreler zaten süperseded**: satır 1276-81'deki dipnot
  3r/10r gecikmesinin 60-koşuluk yeniden ölçümden geldiğini yazıyor, çünkü
  o kampanya geodezik ısınma düzeltmesinden önce koşulmuştu. Isınma imzası
  veride görünüyor: ilk olayların ortalaması 135.9 ms, ikinci olay 2.2 ms.
  **Makale bu konuda tutarlı; ek düzeltme gerekmedi.**

---

## Figür 1 — YENİDEN ÇİZİLDİ (dıştan içe)

### F-11 · Figür 1 iki bayat sayı taşıyordu — DÜZELTİLDİ
Eski çizimde `decides 75.2 % of events` ve `changes 3 of 9 989 selections`
yazıyordu. Replay'in güncel çıktısı **%74.5** (49.20+25.34) ve
**3 of 15 058**. Yani figür, gövdedeki §VII sayılarıyla çelişiyordu — bu
oturumda yakalanan üçüncü figür-metin çelişkisi.

### Yerleşim — iki tur
**1. tur (konsantrik, dıştan içe):** üç iç içe bant, her ok içe bakan.
Kullanıcı denedi ve **eski iki-satırlı akışın daha anlaşılır olduğuna karar
verdi** → geri alındı.

**2. tur (yürürlükte olan) — draw.io ile baştan çizildi.** Eski sekiz-aşamalı
soldan-sağa akış geri geldi ama düzenlenmiş hâlde:
- **Satır A — "Which behaviour decides this event":** (1) bağlam algılama →
  (2) override kaskadı → (3) fallback → (4) dwell + dispatch.
- **Satır B — "How that behaviour turns into queues":** (5) paradigma portföyü
  → (6) maliyet kâhini → (7) atama + onarım → (8) yayımlama.
- $p^\ast$ satır A'dan satır B'ye iniyor; yürütme geri beslemesi kesikli
  çizgiyle (8)'den (1)'e dönüyor.
- Astlık yine **çizimle** anlatılıyor: kaskad kalın vurgu renginde ve ölçülmüş
  payıyla (`decides 74.5 % of events`), fallback kesikli/soluk
  (`changes 3 of 15 058 selections`).

**Kaynak dosya artık `paper/figure/fig1.drawio`** — draw.io'da açılıp
düzenlenebiliyor. `scripts/make_fig1.py` (matplotlib) kaldırıldı; git
geçmişinde duruyor.

**Son hâli kullanıcının draw.io'da düzenlediği sürüm** (2026-08-03). Onun
getirdiği ve dönüştürücüye eklenmesi gereken üç şey:
1. draw.io kaydı `<mxfile><diagram><mxGraphModel>` sarmalayıcısıyla geliyor.
2. Renk artık `style="...;fontColor=#0000FF;"` içinde de olabiliyor (satır
   etiketleri mavi, ek açıklamalar somon `#EA6B66`, geri besleme teli siyah);
   önceki dönüştürücü rengi yalnız HTML etiketinden okuyordu.
3. **Geri besleme teli `x=-30`'a taşınmış** — yani sayfanın sol kenarının
   dışına. Sabit `viewBox="0 0 W H"` bunu kırpıyordu. Dönüştürücü artık
   çizilen her noktanın sınır kutusunu hesaplayıp viewBox'ı ona göre
   büyütüyor (995×627 pt).

Tek komutla üretim: `python3 scripts/drawio_to_svg.py
paper/figure/fig1.drawio <out>.svg --pdf`

### draw.io CLI bu makinede ÇALIŞMIYOR — çözüm yolu
`/usr/bin/drawio` kurulu ama her export'ta segfault veriyor
(`Schema org.gnome.desktop.interface does not have key font-antialiasing`).
Denenip başarısız olanlar: düz çağrı · `xvfb-run` · `--headless` ·
`--no-sandbox` · `--disable-gpu` · `--ozone-platform=headless` ·
`--disable-dev-shm-usage`. Üç farklı format (pdf/svg/png) da düştü.

**Çalışan zincir:** `scripts/drawio_to_svg.py` (bu oturumda yazıldı) →
`.drawio` XML'ini SVG'ye çeviriyor → headless Chrome `--print-to-pdf` ile
vektör PDF. Fontlar gömülü, metin metin kalıyor (`pdffonts` ile doğrulandı).
Dönüştürücünün kapsamı bilinçli olarak dar: yalnız bu figürün kullandığı
stil sözlüğü (yuvarlatılmış dikdörtgen, metin hücresi, ara noktalı ortogonal
kenar, draw.io'nun HTML etiket alt kümesi).

### ⚠️ Ölçek tuzağı (bir kez düşüldü, düzeltildi)
İlk draw.io sürümü 1280×660 px tuvalde 10–13 px yazı kullanıyordu.
`\textwidth`=516 pt'ye ölçeklenince **1 px = 0.403 pt** → gövde metni baskıda
**4.4 pt**'a düştü, okunmaz. (Tam olarak eski drawio figürünün 2016'daki
sorunu.) Düzeltme: tuval 1280×820'ye çıkarıldı ve yazılar 15/17/18/22 px'e
büyütüldü → baskıda 6.0/6.9/7.3/8.9 pt. **Kural: draw.io tuval genişliği
$W$ px ise, baskıdaki punto = px × 516/$W$; gövde için ≥7 pt hedefle.**

Caption iki dilde de yeni akışı tarif edecek şekilde baştan yazıldı ve
figürdeki sayıların kaynağını (15.058 durum) veriyor. Sayfa 7'de baskı
boyutunda okunaklı doğrulandı.

---

## §III Metot — denklem × kod geçişi TAMAM

### Birebir doğrulanan (kod satırlarıyla)
| Makale | Kod | Sonuç |
|---|---|---|
| eq:ctx-start $c_1=\min(1,m_k/n)$ | `min(1.0, active_count/robot_count)` (eco:328) | ✓ |
| $c_3$, $\Delta_d=60$~s, sonsuz deadline sayılmaz | `_deadline_pressure(..., horizon=60.0)`, `t.deadline>0` filtresi (eco:144-151) | ✓ |
| $c_4$ = arızalı/takılı / n | `failure_flag or navigation_state in (2,3)` (eco:345-351) | ✓ |
| eq:dispatch eşikleri 0.05 / 0.50 | `_select_paradigm_raw` (:1062,1066) | ✓ |
| "$D_k$ yoksa veya menzil $<10^{-4}$ ise H_TEMP" | `if d.size<5 or d.max()-d.min()<1e-4: return 2` (:1071) | ✓ §I'deki not KAPANDI |
| eq:dominance tüm terimler | `ALPHA*D+BETA*perf+GAMMA*compat+ETA*A@D−LMBDA*S@D+DELTA*boost`, clip[0,1], ℓ1-normalize + uniform fallback (eco:282-294) | ✓ |
| $\alpha,\beta,\gamma,\eta,\lambda,\delta$ = 0.65/0.40/0.20/0.12/0.12/0.20 | eco:117-122 | ✓ |
| $A$ iki girdi (0.20), $S$ bir girdi (0.30) | eco:77,78,84 | ✓ |
| $\mathbf b_k=c_4[-0.3,0,0,0.4,0.6]$ | eco:396-399 | ✓ |
| $g_k=(N^c-N^f)/\max(1,N^c+N^f)$, $\mathbf p_k=g_k\mathbf v_k$ | `_compute_performance` (eco:368-379) | ✓ |
| eq:weight-map $M$ (7×5), **35 katsayının hepsi** | eco:105-114 | ✓ |
| $T_w=0.3$ | `SOFTMAX_TEMP = 0.3` (eco:127) | ✓ |
| $w_k=0.3w_0+0.7w^{\rm eco}_k$ | `ECO_BLEND_NORMAL = 0.70` (:374,719) | ✓ |
| $w_0$, $w_{\rm rec}$ yedişer katsayı | `W0_V3`, `W_RECOVERY` (:285,289) | ✓ |
| $\theta_k=\min(0.80,0.50+0.60c_4)$ | `min(0.80, 0.50 + failure_rate*0.60)` (:735) | ✓ |
| eq:eta $h=22$~s, $j(h+s_\tau)$ | `NAV2_QUEUE_OVERHEAD=22.0`, `len(q)*(NAV2_QUEUE_OVERHEAD+service_time)` (:72,1813) | ✓ |
| 0.55 m şişirme | `INFLATION_M = 0.55` (placement:45) | ✓ |
| sekiz-komşuluk | `_NEIGHBORS` 4 ortogonal (1.0) + 4 çapraz (√2) (geodesic:25-28) | ✓ |
| eq:repair $\epsilon=0.10$ | `F58_FAIR_EPSILON = 0.10` (:477), `dist_cap = d*(1+ε)` (:1639) | ✓ |
| onarım terminal fazda, kalan görev ≤ 3× sağlıklı robot | `F58_FAIR_TERMINAL_TASKS_PER_ROBOT = 3.0` (:494) | ✓ |
| %10 sahip-değiştirme marjı | `F27_REASSIGN_MARGIN = 0.10` (:530) | ✓ |

### F-12 · $\mathcal R^{\rm av}$ tanımı kodun hesapladığından fazla — DÜZELTİLDİ
§III, $c_{2,k}$'nin payını "alive, non-stuck robots **with queue capacity**"
diye tanımlıyordu. Ama bağlamı hesaplayan ekosistem yöneticisi kuyruk
uzunluğunu **görmüyor**: yayımlanan robot-durum özetinde sağlık ve navigasyon
durumu var, kuyruk yok (`ecosystem_manager_node.py:331-338`). → Ayrı sembol
$\mathcal R^{\rm alive}_k$ tanımlandı ve tahsis-edici tarafındaki
$\mathcal R^{\rm av}_k$'den neden daha zayıf bir küme olduğu yazıldı.

### F-13 · "batarya kanalı sıfır ağırlık taşıyor" — kendi $w_0$'ıyla çelişiyordu
Configuration $w_0=(0.34,0.10,\mathbf{0.04},\dots)$ diyor; ağırlık sıfır
değil. Sıfır olan **öznitelik**: yığında batarya modeli yok, `battery`
sabit 1.0 → $B=0$. → "battery *feature* is identically zero ... even though
its weight $w_b$ is not zero" olarak düzeltildi.

### F-14 · eq:eta'daki $v_r$ makalede hiç tanımlanmamış — TEKRAR ÜRETİLEBİLİRLİK
Makaledeki tek hız $v_{\max}=0.26$~m/s (§IV-A, TurtleBot3 donanım sınırı).
Kod ise `SPEED = GAZEBO_SPEED = 0.22` m/s kullanıyor ve gerekçesi kodda yazılı:
*"Nominal hız 0.26 m/s, avg planning+accel overhead → efektif ~0.22 m/s"*.
Okuyucu 0.26 ile eq:eta'yı yeniden üretirse **%18 sapan** bir ETA elde eder.
→ $v_r=0.22$~m/s efektif hız olarak tanımlandı ve $v_{\max}$'tan farkı yazıldı.

### F-15 · Marj kapısının muafiyet listesi eksikti — DÜZELTİLDİ
Makale iki muafiyet sayıyordu (yetim, rescue); kodda **üç** var — üçüncüsü
`URGENT_HORIZON` içindeki görevler (`_f27_margin_gate` docstring, :1411-1417).
→ Üçü de yazıldı.

---

## §V + §VI Kıyaslama sonuçları — istatistik dürüstlüğü TAMAM

### ✅ Etik açıdan kritik kontroller — HEPSİ GEÇTİ
- **Yıldızlar düzeltilmiş p'den basılıyor.** 63 satırın 63'ünde `stars`
  `p_adj`'den üretiliyor; ham p'den üretilse **10 satır** farklı yıldız alırdı
  (ör. `mixed_stress` recovery vs BiG: ham p=0.0071 → `**`, düzeltilmiş
  p=0.149 → `ns`; tabloda doğru olan `ns` yazıyor).
- **Cliff $\delta$ işareti tek yönlü normalize.** Ham CSV normalize DEĞİL
  (22 "better" satırı δ<0), ama üretici `d = flip[met] * r.cliffs_delta` ile
  çeviriyor; basılan tablo caption'ın "$\delta>0$ favors AHE-MRTA*" iddiasıyla
  tutarlı (doğrulandı: rf/DVR ham −0.8275 → tabloda +0.83).
- **Düzeltme ailesi caption'da:** "Bonferroni-corrected within each scenario
  family (21 tests)"; α = 0.05/21 = 0.002381, CSV ile birebir.
- **Havuzlanmış n dürüst:** 3r "three densities pool to n=15".
- **3r ve 10r sayıları yeniden hesaplandı:** 3r → 63 test, **14 anlamlı,
  8 lehte** (makale birebir); 10r → **0 anlamlı** (makale "none survive").
  n=5'te ulaşılabilir en küçük iki-yönlü MW p'si 2/C(10,5)=0.0079 ≈ 0.008,
  düzeltilmiş eşik 0.0024 — makale bunu da doğru yazıyor.
- **Hayatta-kalma yanlılığı** §IV Metrics'te açıkça ele alınmış (censored delay
  + tüm-görev DVR), BiG'in düşük CR'si sonuçlarda adlandırılmış.

### F-16 · "Aleyhte beş sonuç" yanlış tarif edilmişti — DÜZELTİLDİ
Satır 1237: *"decision latency against **the two commit-once baselines**"*.
Ama commit-once baseline **tek** (BiG-MRTA; makale 8 yerde böyle adlandırıyor),
ve gecikmede aleyhte çıkan ikinci yöntem Consensus-DBTA. Gerçek beşli
(`stat_tests.csv`, direction=worse & Bonferroni):

| senaryo | metrik | karşı | p_adj |
|---|---|---|---|
| robot_failure | karar gecikmesi | BiG-MRTA | 0.00031 |
| robot_failure | ort. görev gecikmesi | Cons-DBTA | 0.00218 |
| mixed_stress | karar gecikmesi | BiG-MRTA | 0.000001 |
| mixed_stress | karar gecikmesi | **Cons-DBTA** | 0.000001 |
| deadline_pressure | karar gecikmesi | BiG-MRTA | 0.000001 |

Makalenin satır 1345'i bunu **zaten doğru** yazıyor → satır 1237 kendi
makalesiyle çelişiyordu. 1237 doğru hâle getirildi.

### F-17 · "CR = 1.000" fazla geniş — DÜZELTİLDİ
"AHE-MRTA completes every task in the reported runs (CR = 1.000)". 5r'de doğru
(üç senaryoda da 1.000) ama **10r'de 0.976–0.988**. → "At this scale ...
(CR = 1.000); at 10 robots it does not, reaching 0.976--0.988."

### §V doğrulandı
Vekil düzlem sayıları (`sim_fitness.csv` / `sim_fitness_ideal.csv`) satır
1050-1054'te birebir doğru: kusursuz-nav 0.994/0.727/0.840 vs 0.980/0.668/0.733;
stokastik 0.384/0.263/0.349 vs 0.380/0.229/0.284; rf'de AHE−BiG farkı +0.0038
→ "+0.004, p=0.14". **F-03'ün neden kaçtığı böylece netleşti:** aynı
karşılaştırma makalede iki kez yazılmış, biri doğru (1050) biri bayat (993).

---

## §VIII Sonuç — TAMAM

### F-18 · "All three evaluation layers now rank the methods alike" — DÜZELTİLDİ
F-08'in Sonuç'taki eşi. → "put AHE-MRTA first in every scenario, though they
disagree on the order below it: commit-once BiG-MRTA is the consistent
runner-up on both simulator planes and finishes last in two of the three
closed-loop scenarios."

Ayrıca override kolunun p'si `$p{=}1.000$` diye yalın yazılıyordu; ham
p=0.5872 olduğu için "raw $p{=}0.59$, $p{=}1.000$ after correction" yapıldı.

Doğrulanan: %12 (5r) ve %46 (10r) marjlar → hesaplandı **12.5%** ve **45.9%** ✓;
"full completion under robot failure at 3 and 5 robots" → 3r ve 5r CR 1.000 ✓;
DVR −%17/−%49 ✓; ablasyon 9–11 yp / p<0.005 / büyük etki ✓; 5. kol 0.638/p=0.43 ✓.

---

## §IV Deney Tasarımı (9 alt başlık) — TAMAM

### Stres Senaryoları: 12 parametrenin hepsi `scenarios.py` ile birebir
`HORIZON_S=900` ✓ · deadline tabanı U[90,300] ✓ · ms çarpanı 0.5 → U[45,150] ✓ ·
dp çarpanı 0.4 → U[36,120] ✓ · servis U[2,8] ✓ · öncelik U{1,2,3} ✓ ·
dalgalar (0,30,60) ✓ · `b=n//3`, son dalga kalan ✓ · arıza 45±5 s ✓ ·
sabit hedef `robot_2` ✓ · deadline'lar koşu başlangıcına çapalı ✓.

### Baseline Methods: skill'in zorunlu kontrolleri KARŞILANIYOR
Her baseline için mantık, aile gerekçesi, AHE'den farkı ve adil-karşılaştırma
koşulları (ortak olay döngüsü, ROS 2 arayüzü, maliyet girdileri, Nav2 istemcisi;
yalnız tahsis politikası farklı) yazılı. Kuyruk kapasiteleri doğrulandı:
BiG `MAX_QUEUE=5` ✓, Cons-DBTA `MAX_QUEUE=5` ve `top_k=2` ("iki en yüksek
teklif") ✓, RoSTAM sınırsız ✓, AHE `JTSC_QUEUE_CAP=2` ✓. Kapsam uyarısı
("operational re-implementations, not independent replications") dürüst.

### F-19 · Üç yerde, ARTIK YAPILMIŞ olan deney "gerekli" diye yazıyordu — DÜZELTİLDİ
Makalenin manşet katkısı ön-kayıtlı kapalı-çevrim ablasyonu (§VII-E, 240 koşu).
Ama üç yer hâlâ B4 kampanyası öncesinden kalma:
1. §IV-F: *"The separate fixed-paradigm proxy ablation ... addresses **only**
   the selector question in the proxy setting."*
2. §IV-F Comparison scope: *"A controlled Gazebo selector ablation ... **is
   required** before any closed-loop difference can be attributed..."*
3. §VI: *"a fixed-paradigm/no-override Gazebo ablation **is needed** before
   assigning the pattern to paradigm switching."*

Hakem bunu okuyunca makalenin kendi ana deneyini yapmadığını sanır.
→ Üçü de tamamlanmış ablasyona işaret edecek şekilde yeniden yazıldı.

---

## TR senkronu — TAMAM

16 düzeltmenin tamamı `main_tr.tex`'e taşındı. Diller-arası sayı sayımı
(EN/TR eşitliği) doğrulandı:

| Değer | EN | TR | | Bayat değer | EN | TR |
|---|---|---|---|---|---|---|
| 0.650 | 11 | 11 | | 0.835 | 0 | 0 |
| 0.578 / 0.764 / 0.524 | 3/3/2 | 3/3/2 | | 0.978 | 0 | 0 |
| 0.840 / 0.980 / 0.668 / 0.733 | 2/3/2/2 | 2/3/2/2 | | 0.678 / 0.738 | 0 | 0 |
| 0.638 | 4 | 4 | | 9 989 | 0 | 0 |
| 15{,}058 | 5 | 5 | | 75.2 | 0 | 0 |
| 74.5 | 2 | 2 | | rho=4 | 0 | 0 |
| `K_{\rm dwell}` | 2 | 2 | | This letter | 0 | — |
| `R^{\rm alive}` | 3 | 3 | | | | |
| `v_r=0.22` | 1 | 1 | | | | |

TR'de `sec:hardware` etiketi de eklendi (EN'deki $v_{\max}$ çapraz-referansının
karşılığı).

---

## Tekrar üretilebilirlik — son kontrol

Tüm metin düzenlemelerinden **sonra** beş tablo üreticisi ve figür üreticisi
yeniden koşuldu:

```
git diff --stat paper/table/     → boş  (24/24 tablo bayt-bayt aynı)
plot_results.py → geçici dizin, cmp → 8/8 figür bayt-bayt aynı
```

Yani makaledeki hiçbir veri nesnesi elle düzenlenmiş değil; hepsi kanonik
CSV'lerden deterministik olarak üretiliyor.

---

## Gönderim öncesi kontrol listesi (RAS / Elsevier)

| Madde | Durum |
|---|---|
| Özgünlük — desteklenmeyen yenilik vurgusu | ✅ iddia dört kez daraltılmış, F-08/F-18 ile fazla iddialar da kaldırıldı |
| Yöntem–kod tutarlılığı | ✅ 22 denklem + 35 katsayılık $M$ matrisi + tüm hiperparametreler birebir doğrulandı |
| Baseline adaleti | ✅ ortak olay döngüsü/arayüz/maliyet girdileri; kuyruk kapasitesi farkları açıkça yazılı |
| İstatistik dürüstlüğü | ✅ yıldızlar düzeltilmiş p'den; δ işareti normalize; aile boyutu caption'da; lehte **ve** aleyhte raporlanıyor |
| Tekrar üretilebilirlik | ✅ tablo/figür zinciri deterministik; `results/README.md` veri haritası güncel |
| Figür okunabilirliği | ✅ Figür 1 yeniden çizildi (7.6 pt gövde, vektör); 8 veri figürü 300 dpi |
| Caption kalitesi | ✅ Şekil 5 caption'ı düzeltildi, Figür 1 caption'ı baştan yazıldı |
| Matematik tutarlılığı | ✅ $\rho$ çakışması giderildi; $v_r$ tanımlandı; $\mathcal R^{\rm alive}$ ayrıldı |
| Sınırlılık şeffaflığı | ✅ 12 maddelik blok; tek-arena sınırı (vi) yazılı |
| **Dergi formatı** | ⚠️ **AÇIK** — hâlâ IEEEtran. RAS `elsarticle` istiyor; `elsarticle.cls` sistemde yok. Ayrıca Highlights, CRediT, Declaration of Competing Interest, Data Availability eksik. |
| Özet uzunluğu | ⚠️ 302 kelime — kullanıcı kararıyla **olduğu gibi bırakıldı** |
