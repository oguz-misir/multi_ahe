# F45 adalet kök-neden araştırması

Tarih: 2026-06-29

## Karar

Aktif yöntem referansı **F45/v4.5**'tir. F53 ve bu turda taranan F54--F56
adayları yöntemden çıkarılmış/kapalıdır. Gerçek Nav2-bağımsız düzlem
`ideal_nav=True` olmalıdır. Olasılıksal duvar/timeout modeli ayrı bir
`navigation-proxy` dayanıklılık deneyi olarak tutulmalıdır.

## Kök neden

Eski "Nav2-bağımsız" koşu gerçekte her görev denemesinde konuma bağlı
`p_success∈{0.05,0.40,0.88}` ve 30 s timeout kullanıyordu. Bu model açıkken
F45 5r/25g, 200 tohum ortalamasında Jain yaklaşık 0.70--0.76'dır. Aynı tahsis
`ideal_nav=True` ile çalıştırıldığında:

| Senaryo | Fitness | CR | Jain (tüm filo) | Jain (aktif robot) |
|---|---:|---:|---:|---:|
| robot_failure | 1.000 | 1.000 | 0.867 | 0.984 |
| mixed_stress | 1.000 | 1.000 | 0.868 | 0.984 |
| deadline_pressure | 1.000 | 1.000 | 0.975 | 0.975 |

Failure senaryolarındaki tüm-filo Jain düşüşünün önemli bölümü kasıtlı olarak
45. saniyede kalıcı kapatılan robottur. Bu nedenle yöntem adaleti için
`workload_balance_active`, sistem dayanıklılığı için tüm-filo Jain birlikte
verilmelidir; biri diğerinin yerine geçirilmemelidir.

F45'in aktif `JTSC_QUEUE_CAP=2` yolundaki yük terimi, birçok birebir Hungarian
eşleştirmesinde robot-satırı sabitine dönüşür. Sabit bir completion bonusu da
aynı nedenle eşleştirmeyi değiştirmez. Buna karşı sonuç Jain'ini doğrudan
zorlamak, düşük completion'ın Nav2 başarısızlığından kaynaklandığı robotlara
daha fazla iş vererek ters etki yaratır.

## Denenen ve reddedilen mekanizmalar

- F53 fırsat-kısıtlı backfill: bağımsız 201--300 holdout'unda Jain artışı
  anlamlı değildi; bazı churn/DVR hücreleri ters yöndeydi.
- Completion-borcu × yakınlık kredisi ve competency-adjusted sürümü: F45'e
  göre özellikle robot_failure Jain'ini düşürdü.
- Üretken-robot tavanı: failure/mixed aktif yolunda etkisiz, deadline'da CR
  kaybettirdi.
- Dönen round-robin backfill: deadline'da yararlı, failure/mixed Jain'inde
  negatifti.
- Konveks kümülatif-seyahat marjı: 1--50 taramasındaki kazanım 101--300
  holdout'unda tekrarlanmadı.
- Queue cap 1/3 ve yoğunluk-duyarlı cap: bazı bloklarda Jain'i artırdı; yeni
  201--400 holdout'unda robot_failure farkı -0.001, mixed +0.006 ve her iki
  güven aralığı da sıfırı kesti. Mesafe-Jain anlamlı geriledi.

Bu sonuçlar hiperparametre aramayı sürdürmek yerine problem katmanını ayırmayı
gerektirir.

## Literatürden çıkan uygulanabilir çareler

1. **Doğru yük kaynağını seç.** Denge sonucunu eşitsizlik fonksiyonundan çok
   dengelenen kaynak (durak, süre, mesafe, talep) belirler. Completion Jain
   sonuç metriği kalmalı; karar girdisi olarak gerçek rota süresi/başarı
   olasılığı kullanılmalıdır. [Matl, Hartl ve Vidal](https://arxiv.org/abs/1803.01795).
2. **Verim ve adaleti ayrı aşamalarda çöz.** Önce verimli/fizibil planı üretip
   yalnız küçük maliyetli eşdeğer çözümler arasında denge onarımı yapmak,
   doğrusal ağırlıklı tek hedefin patolojisini azaltır.
   [Nekooghadirli vd.](https://arxiv.org/abs/2206.14596),
   [2FairGA](https://arxiv.org/abs/2405.19184).
3. **Completion borcunu competency'den ayır.** Düşük çıktı düşük fırsat kadar
   düşük yeterlilikten de doğabilir; subsidy ancak kalite/maliyet tahminiyle
   birlikte kullanılmalıdır.
   [Lee vd.](https://doi.org/10.1177/1729881418812960).
4. **Min-max rota yükünü kullan.** Adalet hedefi görev sayısından çok maksimum
   tur/bitirme süresi üzerinden kurulabilir.
   [Equity-Transformer, AAAI 2024](https://doi.org/10.1609/aaai.v38i18.30007).
5. **Belirsizliği planlama katmanında temsil et.** Görev başarı olasılığı ve
   zaman penceresini birlikte ele alan hiyerarşik planlama, başarısız görevi
   salt fairness bonusuyla başka robota itmekten daha doğrudur.
   [Choudhury vd.](https://arxiv.org/abs/2005.13109).

## Sonraki yöntem kolu: reachability-first F45

Gazebo için yüksek değerli iyileştirme, completion cezası değil şu iki aşamadır:

1. Öklid uzaklığını statik occupancy-map jeodezik maliyetiyle değiştir; yalnız
   kısa listedeki robot-görev çiftlerini Nav2 `ComputePathToPose` ile doğrula ve
   sonucu önbelleğe al.
2. Robot-görev çiftine özgü başarısızlık hafızası tut. Aynı çift tekrarlı
   başarısızsa geçici karantinaya al; görevin kendisi tüm robotlarda
   başarısızsa backoff uygula. Robotun toplam completion sayısını ceza/ödül
   olarak kullanma.
3. Birincil fizibil çözümden sonra yalnız toplam yol/gecikme artışı ε sınırı
   içindeki takaslarda aktif-robot Jain veya maksimum rota süresini iyileştir.

Bu kol gerçek Nav2 yol bilgisini gerektirir; Plane-A'daki yapay başarı zarını
optimize ederek makale metriği yükseltmeye çalışmak yöntem iyileştirmesi değildir.

## F57 ilk uygulama ve kabul kararı (2026-06-29)

Reachability-first kolunun ilk parçası çalışır biçimde eklendi. Runner ve Plane-A
simülatörü her `robot_id × task_id` başarısızlığını ayrı sayıyor; `TaskState`
bu kanıtı tahsisçiye taşıyor. F57 açıkken aynı çift tekrarlı başarısız olursa,
yalnız daha az başarısız olmuş sağlıklı bir alternatif varken çift karantinaya
alınıyor. Bütün robotlarda kanıt eşitse görev kalıcı olarak kilitlenmiyor.

F57 varsayılan olarak **kapalıdır** (`AHE_F57_PAIR_MEMORY=0`); F45 referansı
değişmemiştir. `ideal_nav=True`, 5r/25g, üç senaryo ve ilk 20 tohumda özellik
açık/kapalı iken latency dışındaki bütün ham bilimsel çıktılar birebir aynıdır.

Navigation-proxy geliştirme taramasında ceza `{0.10,0.25,0.50}` ve karantina
eşiği `{1,2,3}` denendi. En umut verici geliştirme noktası
`penalty=0.25, threshold=3` ayrı 101--300 holdout'unda F45'e göre:

| Senaryo | ΔFitness | ΔCR | ΔDVR | Δaktif-Jain | Δchurn | Δmesafe |
|---|---:|---:|---:|---:|---:|---:|
| robot_failure | -0.0007 | +0.0002 | +0.0020 | -0.0010 | -0.0378 | +1.10 |
| mixed_stress | +0.0033 | -0.0010 | -0.0002 | -0.0082 | -0.0498 | +5.73 |
| deadline_pressure | -0.0048 | -0.0010 | +0.0060 | -0.0009 | +0.1190 | +5.03 |

Başarısız navigasyon sayısı her üç senaryoda yaklaşık 0.5--0.7 azalsa da Jain,
DVR ve mesafe kabul kapısını geçmedi. Yalnız karantina (sıfır yumuşak ceza)
eşik 1--4 taraması da kararlı Pareto kazanımı üretmedi. Dolayısıyla F57'nin
geri-bildirim altyapısı ve deneysel uygulaması korunmuş, fakat yöntem iyileştirmesi
olarak etkinleştirilmemiştir. Proxy'deki başarı olasılığının robot-görev çiftine
değil yalnız görev konumuna bağlı olması da bu testin gerçek Gazebo reachability
kanıtının yerini alamayacağını gösterir.

## Yeniden üretim

```bash
python3 scripts/validate_f45_allocation.py \
  --mode allocation-only --robots 5 --tasks 25 --seeds 100 \
  --output-dir results/stats/f45_allocation_only

python3 scripts/validate_f45_allocation.py \
  --mode navigation-proxy --robots 5 --tasks 25 --seeds 100 \
  --output-dir results/stats/f45_navigation_proxy
```
