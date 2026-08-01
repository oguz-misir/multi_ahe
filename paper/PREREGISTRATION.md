# Ön-kayıt — Eşleşmiş Gazebo ablasyonu (B4) ve n=20 birincil ölçek (D2)

**Kilitlenme tarihi:** 2026-07-30. Bu belge kampanya **başlamadan önce** commit
edilmiştir; commit hash'i ve tarihi kaydın kendisidir. Kampanya bittikten sonra
bu dosyanın hipotez, kol, uç nokta ve istatistik bölümleri **değiştirilmez**;
yalnız en alttaki "Sapmalar" bölümüne ekleme yapılır.

## Neden ön-kayıt

Yayımlanan 5r/25g hücreleri n=5 ile koşuldu ve Bonferroni sonrası 63 testin
0'ı anlamlıydı. Bu, sonuçların koşum sonrası seçildiği şüphesine açık bir
yüzey bırakıyor. İkinci sorun daha ağır: makale "Ekosistem-Güdümlü Paradigma
Seçimi" öneriyor ama vekil düzlemdeki 8 ablasyon varyantı 0.9 yüzde puanı
içinde kalıyor ve seçicinin dinamik katmanı 9989 kararın yalnız 3'ünü
değiştiriyor. Kapalı çevrimde ölçülmemiş bir mekanizmayı katkı olarak sunmak
savunulabilir değil. Bu kampanya o ölçümü yapar ve sonucu — hangi yöne çıkarsa
çıksın — raporlanır.

## Hipotezler

- **H1 (birincil).** `deadline_pressure` senaryosunda `full` kolu, sabit
  paradigma kollarından (`fixed-EDF`, `fixed-orphan`) zamanında-etkin
  tamamlamada üstündür.
- **H2 (ikincil).** `robot_failure` senaryosunda `full` kolu `no-override`
  kolundan tamamlama oranı ve toparlanma süresinde üstündür.
- **H0.** Kollar arasında fark yoktur. **Bu sonuç yayımlanacaktır.** Vekil
  düzlem ablasyonuna bakılırsa en olası sonuç budur; o durumda bulgu
  "bu rejimde paradigma-değiştirme makinesi gerekli değil" olarak yazılır ve
  makalenin iddiası gösterilebilene indirilir (revizyon planı, A kolu).

## Kollar ve tam bayrak kümeleri

Tüm kollar aşağıdaki yayımlanmış temel ortamı paylaşır:

```
AHE_F58_GEODESIC=1  AHE_F58_FAIR_REPAIR=1  AHE_F58_FAIR_RESERVATION_GAP=2
AHE_F58_FAIR_EXTRA_QUEUE=1  AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3
AHE_WARMUP=1
```

| Kol | Ek bayrak | Ne kapanıyor |
|---|---|---|
| `full` | (yok) | — yayımlanan yapılandırma |
| `no-override` | `AHE_NO_OVERRIDE=1` | bağlam-override kaskadı; geriye yalnız `argmax(dominance)` kalır (klasik EDPS) |
| `fixed-EDF` | `AHE_FORCE_PARADIGM=2` | seçicinin tamamı; her karar H_TEMP (edf_strict / 3PHA) |
| `fixed-orphan` | `AHE_FORCE_PARADIGM=4` | seçicinin tamamı; her karar H_RECOV (orphan_first) |

Bayraklar 2026-07-30'da bu kampanya için yazıldı (B1). **Kabul ölçütü ve
sonucu:** üçü de kapalıyken vekil düzlemde 5r/25g × 3 senaryo × 20 tohumda
AHE'nin tohum-bazlı fitness değerleri B1-öncesi kodla **60/60 hücrede tam
ondalık özdeş** çıktı. Bayraklar kapalıyken karar yolu değişmemiştir.

Çözülmüş bayraklar her koşuda `metadata.yaml: allocator_env` içine yazılır;
bir koşunun hangi kola ait olduğu sonuç dosyasından okunabilir.

## Tasarım

| | |
|---|---|
| Ölçek | 5 robot / 25 görev (birincil) |
| Senaryo | `robot_failure`, `mixed_stress`, `deadline_pressure` |
| Tohum | 1–20, **dört kolda ortak** (eşli test) |
| Harita | tek arena (ikinci arena ertelendi) |
| Ablasyon koşusu | 4 kol × 3 senaryo × 20 tohum = **240** |
| D2 uzantısı | 3 baseline (BiG, RoSTAM, CDBTA) × 3 senaryo × 20 tohum = **180** |
| Toplam | **420 koşu** |

`full` kolunun 60 koşusu aynı zamanda dört-yöntem kıyaslamasının AHE kolonudur;
D2'nin marjinal maliyeti bu yüzden yalnız 180 baseline koşusudur.

Süre tahmini yayımlanan 300 koşunun DONE-metadata zaman farklarından:
medyan 4.9 dk, ortalama 9.8 dk (ağır kuyruk, maks 25 dk) → **34–69 saat**.

**Bu kampanyanın kapatmadığı şey.** Makalenin Limitasyon (x) maddesi kesin
takip deneyi için üç şey istiyor: ön-belirtilmiş birincil ölçüt, koşul başına
en az 20–30 tohum ve **birden fazla harita**. Bu kampanya ilk ikisini
karşılıyor, üçüncüsünü karşılamıyor: `placement.py` içinde ORIGIN/ARENA_LIM/GRID
ve harita yolu sabit kodlu olduğu için ikinci arena parametrizasyon gerektiriyor
(revizyon planı, C kolu; ~60 koşu, 5–10 sa). Dolayısıyla B4 sonrası (x)
**kısmen** kapanır ve kalan kısmı — tek arena — Limitasyon (iv) ile birleştirilip
açıkça korunur. Sonuç ne çıkarsa çıksın tek haritaya bağlıdır.

## Uç noktalar

- **Birincil:** zamanında-etkin tamamlama,
  `effective_on_time = task_completion_rate × (1 − deadline_violation_rate)`,
  `deadline_pressure` senaryosunda. (Tanım `scripts/plot_results.py` içinde
  zaten kullanılıyor; yeni bir ölçüt uydurulmuyor.)
- **İkincil:** `robot_failure`'da `task_completion_rate` ve
  `failure_recovery_time` (sansürlü kolon).
- **Betimleyici (test edilmez):** `average_task_delay`, `redispatch_per_task`,
  `exec_preemptions`, `mean_decision_latency_ms`, iş yükü dengesi.

## İstatistik planı

- Eşli Wilcoxon işaretli-sıra testi (tohumlar kollar arasında ortak).
- Etki büyüklüğü: Cliff δ, %95 GA ile.
- Çoklu karşılaştırma: **senaryo ailesi içinde Bonferroni**. Birincil aile =
  `deadline_pressure`'da `full` vs diğer 3 kol (3 test, α=0.05/3).
  İkincil aile = `robot_failure`'da 2 ölçüt × 3 kol (6 test, α=0.05/6).
- Betimleyici ölçütler için p değeri raporlanır ama düzeltmeye girmez ve
  hiçbir iddiayı desteklemek için kullanılmaz.
- Eksik koşu (timeout/çökme) olursa o tohum **dört kolda birden** düşürülür;
  eşleştirme korunur. Düşürülen tohumlar sapma bölümüne yazılır.

## Durdurma kuralı ve ara bakma

Kampanya 420 koşunun tamamı bitene kadar sürer. Ara sonuçlara bakmak
serbesttir (ilerleme takibi), ancak **ara sonuca dayanarak kol eklenmez,
çıkarılmaz, tohum sayısı değiştirilmez ve uç nokta yeniden tanımlanmaz.**

## Üç olası sonuç ve her birinde ne yazılacağı

| Sonuç | Makalede ne olur |
|---|---|
| `full` anlamlı önde | Asıl iddia kapalı çevrimde kanıtlanır; A kolunun geri çekilmesi iptal edilir. |
| Fark yok | Negatif sonuç dürüstçe raporlanır; Limitasyon (x) kaldırılıp yerine ölçüm konur; iddia override kaskadı + geodezik ETA + terminal onarıma indirilir. |
| Sabit paradigma önde | Yöntem sadeleştirilir; seçici katmanı çıkarılır, makale "iki override yeter" iddiasına döner. |

## Sapmalar

*(Kampanya sırasında plandan her sapma, gerekçesiyle birlikte buraya tarihli
olarak eklenir. Boşsa sapma olmamıştır.)*

- **2026-08-01 — düşen tohum yok.** Dört kolun tamamı 60/60 tamamlandı,
  hiçbir koşu `STARTUP FAILED` vermedi, dolayısıyla üç senaryonun her birinde
  20 tohumun tamamı eşleşti. Eşleştirme kuralı hiç devreye girmedi.

- **2026-08-01 — ikincil uç nokta ayırt edemedi (plan değiştirilmedi).**
  `robot_failure` için kaydettiğimiz iki ikincil ölçütten tamamlama oranı dört
  kolda da tavanda çıktı (full 1.000, no-override 1.000, fixed-EDF 0.998,
  fixed-orphan 1.000) ve hiçbir şeyi ayırt edemedi; toparlanma süresi
  düzeltmeden sonra anlamlı çıkmadı (p_bonf 0.064–0.158). O senaryoda gerçekte
  ayıran ölçüt zamanında-etkin tamamlamaydı (0.986 / 0.998 / 0.846 / 0.850)
  ama onu yalnız birincil senaryo için kaydetmiştik.
  **Uç noktayı sonradan değiştirmedik.** Zamanında-etkin tamamlama
  `robot_failure`'da betimleyici olarak raporlanıyor, test olarak değil.
  Ders: tavan etkisi olası olan bir ölçütü ikincil uç nokta seçmemeli.

- **2026-08-01 — sonuç, öngörülen üç senaryonun ikisinin bileşimi çıktı.**
  Plan "seçici önde / fark yok / sabit paradigma önde" diye üç dal yazmıştı.
  Gerçekleşen: sabit paradigma kollarına karşı **full anlamlı önde**
  (birinci dal), `no-override` koluna karşı **fark yok** (ikinci dal).
  Bu post-hoc bir okuma değil — kollar tam olarak bu iki soruyu ayırmak için
  tasarlanmıştı; plan yalnız ikisinin aynı anda çıkabileceğini yazmamıştı.
  Yazıya giren iddia buna göre daraltıldı: portföy + çevrim içi değiştirme
  savunuluyor, belirli seçici mekanizması savunulmuyor.
