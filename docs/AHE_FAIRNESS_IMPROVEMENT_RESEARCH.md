# AHE-MRTA adalet ve çift-düzlem iyileştirme araştırması

> **Yerine geçen karar (2026-06-29):** F53 aktif yöntemden çıkarıldı; referans
> F45/v4.5'tir. Güncel kök-neden ve kabul/reddetme kayıtları
> `docs/F45_FAIRNESS_DEEP_DIVE.md` içindedir. Bu belge F53 deney geçmişi olarak
> korunmaktadır.
>
> **Yeni yöntem araştırması (2026-06-29/30):** F45 sonrası önerilen geodezik yol
> maliyeti, bölgesel erişilebilirlik öğrenmesi ve ε-sınırlı min-max yük onarımı
> `docs/F58_REACHABILITY_FIRST_RESEARCH.md` içinde tasarlanmış ve P0/P1
> uygulanmıştır. Allocation-only holdout'u geçmesine karşın 30-koşuluk
> Gazebo+Nav2 doğrulamasında üç fiziksel kabul kapısını da geçemediği için F58
> etkin fiziksel yöntem değildir; referans F45 olarak kalır.

Tarih: 2026-06-28

## Sonuç

Bu turda önerilen işletim noktası **F53 — fırsat-kısıtlı adil backfill**'dir.
F53, aktif AHE paradigmasının atamadığı işi sabit robot-listesi sırasıyla ilk
robota vermek yerine görev-öncelikli dağıtır. En yakın robotun 2 m çevresindeki
eşdeğer adaylar arasında sırasıyla (i) daha az tamamlanmış görev, (ii) daha az
kümülatif seyahat ve (iii) deterministik robot kimliği kullanılır. Önceki sahip
aynı 2 m penceresinde hâlâ uygunsa atama korunur; böylece adalet Nav2 hedefini
iptal ederek churn üretmez.

Doğrudan maliyet fonksiyonuna completion bonusu ekleyen alternatif varsayılan
dışı bırakılmıştır. Düşük completion bazen yetersiz erişilebilirlik veya arıza
belirtisidir; robotu her LSA'da ödüllendirmek eşitliği de throughput'u da
bozabilmektedir. Adalet yalnız **yakın-verimli aday kümesinde** tie-break olarak
kullanılmalıdır.

## Literatürden çıkarılan tasarım ilkeleri

1. Jain indeksi, kaynak paylaşımı için ölçekten bağımsız ve [0,1] aralığında bir
   adalet ölçüsüdür. Bu nedenle `workload_balance` her iki düzlemde de
   \(J(x)=(\sum_i x_i)^2/(n\sum_i x_i^2)\) olmalıdır. Kaynak:
   [Jain, Chiu ve Hawe (1984)](https://www.cse.wustl.edu/~jain/papers/fairness.htm).
2. Rota adaletinde **neyin dengelendiği** (durak sayısı, mesafe, süre, talep),
   eşitsizlik fonksiyonunun seçiminden çoğu zaman daha belirleyicidir. Bu nedenle
   görev-completion Jain ana makale metriği olarak kalırken aktif-robot Jain ve
   seyahat-mesafesi Jain tanısal metrik olarak ayrıca kaydedilir. Kaynaklar:
   [Matl, Hartl ve Vidal (2019)](https://doi.org/10.1016/j.cor.2019.05.016),
   [Matl, Hartl ve Vidal (2018)](https://doi.org/10.1287/trsc.2017.0744).
3. Min-max/equitable routing, en uzun bireysel rotayı sınırlayarak dengeyi
   makespan ile ilişkilendirir; fakat çevrim içi AHE'de tam min-max çözüm olay
   başına gecikmeyi artırır. F53 bunun hafif, sınırlı tie-break karşılığıdır.
   Kaynak: [Son vd., AAAI 2024](https://doi.org/10.1609/aaai.v38i18.30007).
4. İki-aşamalı yaklaşımlar önce verimli/coğrafi çözümü kurup sonra yalnız denge
   için küçük bir düzeltme yapar. F53 de AHE paradigmasının birincil çözümünü
   koruyup yalnız sahipsiz kalan işte düzeltme yapar. Kaynak:
   [Li vd. (2023)](https://doi.org/10.3390/electronics12183842).
5. Dinamik isteklerde bir miktar kaynak dengesi, gelecekteki işi kabul etme
   esnekliğini yükseltebilir. Ancak bu denge başlangıç rota verimliliğini sınırsız
   feda etmemelidir; 2 m penceresi bu takası açıkça sınırlar. Kaynak:
   [Soeffker, Ulmer ve Mattfeld (2024)](https://doi.org/10.1007/s00291-024-00747-1).

## Kod denetiminde bulunan kök sorunlar

### 1. “Jain” etiketi taşıyan Gazebo metriği Jain değildi

Plane A gerçek Jain kullanırken Plane B `1/(1+variance)` hesaplıyordu. İki
değer aynı ölçeğe ve aynı aksiyomlara sahip değildir. Düzeltme:

- `workload_balance`: gerçek Jain;
- `workload_balance_active`: kalıcı olarak arızalı robotlar hariç Jain;
- `travel_distance_balance`: robot-başı mesafenin Jain indeksi;
- `workload_balance_legacy_variance`: eski değeri denetim için korur.

`consolidate_results.py`, eski ham kampanyaları `robot_workload.csv` üzerinden
yeniden hesaplayabilir; eski değer kaybolmaz.

### 2. Completion geri bildirimi güvenilir değildi

Bir görevin açık havuzdan kaybolması completion anlamına gelmez; retry backoff
da aynı görünümü üretir. `RobotState` artık çalıştırıcının tuttuğu gerçek
`completed_tasks` ve `travel_distance` sayaçlarını taşır. F53 yalnız bu kesin
geri bildirimi kullanır.

### 3. Plane B deadline baskısı hiç tetiklenmiyordu

Ekosistem yöneticisi mutlak ROS zamanındaki `deadline` değerini doğrudan 60 ile
karşılaştırıyordu. Doğru ifade `deadline - now <= 60`'tır. Bu hata H_TEMP
override'ını Gazebo'da fiilen kapatıyordu. Kod Plane A ve makaledeki denklemle
hizalandı.

### 4. Enjekte edilen robot arızası ekosisteme ulaşmıyordu

ExperimentRunner robotu kendi tahsis görünümünde arızalı işaretliyor, fakat
robot süreci normal status yayınlamaya devam ediyordu. EcosystemManager artık
`robot_failure` AllocationEvent'ini kalıcı dış arıza olarak kaydeder; `c4`,
availability ve recovery boost aynı kaynağı kullanır. Böylece H_RECOV fiziksel
deneyde tarif edildiği şekilde tetiklenir.

### 5. Plane A görev yoğunluğu formülden sapmıştı

Makale ve Plane B \(c_1=\min(1,m/n_{robot})\) kullanırken Plane A
`m/n_tasks` kullanıyordu. Plane A, makale formülüne çekildi.

## 100-tohum Plane-A doğrulaması

5 robot / 25 görev, 100 tohum. Parantez içi yeni eksi eski değerdir.

| Senaryo | Fitness | Jain | Aktif Jain | CR | Gecikme (s) | DVR | Mesafe | Churn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| robot_failure | 0.538 (-0.001) | 0.705 (+0.005) | 0.819 (+0.006) | 0.562 (+0.002) | 444.5 (-0.6) | 0.463 (+0.001) | 791.7 (-15.8) | 0.254 (-0.004) |
| mixed_stress | 0.539 (-0.001) | 0.700 (-0.002) | 0.814 (-0.002) | 0.564 (+0.004) | 443.4 (-0.2) | 0.461 (+0.001) | 791.3 (-15.2) | 0.272 (+0.016) |
| deadline_pressure | 0.480 (-0.001) | 0.794 (+0.015) | 0.794 (+0.015) | 0.585 (+0.012) | 481.4 (-4.1) | 0.522 (+0.000) | 775.3 (-94.4) | 0.668 (-0.327) |

Üç senaryo ortalama Jain 0.727'den 0.733'e çıkar. En belirgin kazanım, eski
sabit robot-sırası yanlılığının en çok etkilediği deadline_pressure'dadır. Aynı
senaryoda 100-tohum temel yöntemlerin en iyi Jain'i 0.789 iken F53 AHE 0.794'tür.
Ortalama karar gecikmesi 0.046--0.061 ms bandında değişmemiştir.

### Bağımsız holdout (tohum 101--200)

2 m eşiğinin seçildiği 1--100 aralığından bağımsız 100 tohumda kazanım tekrarlandı:

| Senaryo | Fitness Δ | Jain Δ | CR Δ | Gecikme Δ (s) | DVR Δ | Mesafe Δ | Churn Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| robot_failure | +0.000 | +0.004 | +0.001 | -0.1 | -0.001 | -13.8 | -0.009 |
| mixed_stress | +0.000 | +0.005 | +0.001 | -0.2 | +0.000 | -13.5 | -0.019 |
| deadline_pressure | +0.001 | +0.025 | +0.013 | -3.7 | -0.001 | -91.0 | -0.256 |

Holdout'ta hiçbir raporlanan metrik yön olarak gerilemedi; bu, ilk 100 tohumdaki
sonucun yalnız eşik ayarına özgü olmadığını gösterir.

### İkinci bağımsız holdout (tohum 201--300)

Yeni, daha önce hiçbir eşik seçiminde kullanılmamış 100 tohum paired biçimde
çalıştırıldı. Aşağıdaki farklar F53 eksi v4.5'tir:

| Senaryo | Fitness Δ | Jain Δ | CR Δ | Gecikme Δ (s) | DVR Δ | Mesafe Δ | Churn Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| robot_failure | -0.0009 | +0.0012 | +0.0000 | +0.0004 | +0.0008 | -14.33 | +0.0252 |
| mixed_stress | -0.0003 | +0.0010 | +0.0016 | -0.1264 | +0.0008 | -14.32 | +0.0088 |
| deadline_pressure | -0.0031 | +0.0128 | +0.0064 | -1.9453 | +0.0032 | -87.18 | -0.2948 |

Tohum-eşleşmiş bootstrap + Wilcoxon/Holm denetiminde üç senaryodaki mesafe
azalışı, deadline CR artışı ve deadline churn azalışı aile-düzeyi anlamlıdır
(`Holm p<0.05`). Jain farkları üç senaryoda da pozitif olmakla birlikte bu
holdout tek başına sıfırı dışlayan güven aralığı üretmemiştir. Deadline fitness
ve DVR'daki küçük ters farklar nominal testte görünür, fakat Holm düzeltmesi
sonrasında anlamlı değildir. Sonuç dolayısıyla "her metrik kesin iyileşti"
olarak değil; güçlü mesafe/kararlılık kazancı ve küçük, belirsiz adalet artışı
olarak raporlanmalıdır.

Tam yeniden üretim:

```bash
python3 scripts/validate_f53_sim.py \
  --robots 5 --tasks 25 --seeds 100 --seed-start 201 \
  --output-dir results/stats/f53_sim_holdout_201_300
```

Betik her tohumu F53 kapalı/açık aynı girdilerle çalıştırır ve
`paired_runs.csv`, `metric_summary.csv`, `REPORT.md` üretir.

### Ölçek duyarlılığı denetimi

F53 ayrıca ilk ayar aralığından bağımsız tohumlarla 3r/15g ve 10r/50g üzerinde
denetlendi. 10r/50g, 101--150 tohumlarında üç senaryoda da Jain'i artırdı:
robot_failure +0.001, mixed_stress +0.010 ve deadline_pressure +0.038. Aynı
sırayla toplam mesafe 43.8, 44.5 ve 253.9 birim; deadline churn'u 0.621 azaldı.

3r/15g için 1--200 tohum denetimi daha nüanslıdır. Deadline_pressure'da Jain
+0.015, CR +0.005, gecikme -1.11 s, mesafe -12.15 ve churn -0.087 ile ortak
iyileşme vardır. Robot_failure ve mixed_stress'te Jain sırasıyla -0.003 ve
-0.005 değişirken CR/DVR farkları mutlak 0.001'in, gecikme farkı 0.02 s'nin
altındadır; mesafe
yaklaşık 0.9--1.1 azalır. 0--2 m pencere ve robot-first fırsat varyantları bu
küçük-filo takasını kaldırmadığı için reddedildi. Bu bulgu gizlenmemeli: F53'ün
adalet kazanımı 5 ve 10 robotta, ayrıca 3 robot deadline rejiminde güçlüdür;
3-robot failure/mixed hücreleri için fiziksel çok-tohum kanıtı gereklidir.

## Plane B için doğrulama durumu

- Değişen Python paketleri `colcon build --symlink-install` ile başarıyla
  derlendi.
- Unit testler Jain formülünü, remaining-deadline bağlamını, enjekte arıza
  iletimini, 2 m verim sınırını ve deterministik tie-break'i kapsar.
- Ağ/IPC izinli 3 robot / 15 görev / deadline_pressure / seed 1 duman koşusu
  başarıyla tamamlandı (237 s sürücü süresi; fiziksel makespan 196 s): 15/15
  görev, CR=1.000, Jain=0.974, aktif-Jain=0.974, mesafe-Jain=0.996, toplam
  mesafe=113.66 m ve karar gecikmesi=0.43 ms.
- Kök `ecosystem_metrics.csv` içinde `context_deadline` 1.0'a çıktı ve baskın
  hormon `SpatialOpportunist`'ten `TemporalRegulator`'a geçti. Böylece Plane-B
  remaining-deadline düzeltmesi uçtan uca doğrulandı.
- Duman denetimi, deney klasöründeki ikincil ekosistem loglayıcısının eski
  7-hormon başlığını kullandığını da gösterdi. Başlık/context satırı 5 hormon /
  4 context olarak düzeltildi; sonraki koşular kendi klasörlerinde tam denetim
  izi taşıyacak.

Robot-failure bağlam düzeltmesi için önerilen ek kısa fiziksel doğrulama:

```bash
ROS_LOG_DIR=/tmp/ahe_ros_logs \
bash run_experiments_robust.sh \
  --robots 3 --tasks 15 --seeds "1 2 3" \
  --combos "ahe_mrta_v3 robot_failure" \
  --results-dir results/raw/gazebo_f53_smoke
```

Tekrarlanabilir ve eski sonuçları ezmeyen kampanya sürücüsü eklendi:

```bash
# 3r/15g, üç senaryo, tohum 1--3
bash scripts/run_f53_gazebo_validation.sh pilot

# Makaledeki birincil 5r/25g ölçek, üç senaryo, tohum 1--5
bash scripts/run_f53_gazebo_validation.sh paper
```

Çıktılar `results/raw/gazebo_f53_validation/<ölçek>` altına, birleştirilmiş
tablolar ve eşleşmiş v4.5 karşılaştırmaları ayrı `processed`/`stats`
dizinlerine yazılır. `compare_f53_gazebo.py` eski ve yeni Jain'i doğrudan
`robot_workload.csv` üzerinden hesaplar; churn için çağrı-sıklığı sayacı yerine
fiziksel `redispatch_per_task` kullanır. Kabul kapısı en az üç eşleşmiş tohum,
CR/DVR için 0.01 toleranslı gerilememe ve Jain/mesafe/redispatch/gecikmeden en
az ikisinde iyileşme ister. Tek mevcut deadline smoke bu nedenle doğru olarak
`INSUFFICIENT` etiketlidir; makale tablosuna terfi ettirilmemiştir.

Kontrol edilecek kabul koşulları:

- robot_failure sonrasında `context_failure_rate > 0` ve
  `RecoveryCoordinator` görülmeli;
- `summary.csv`: gerçek-Jain sütunları mevcut olmalı;
- F53, eski v4.5'e karşı CR/DVR'ı bozmayıp mesafe/churn/Jain'den en az ikisini
  iyileştirmeli.

## Sonraki yüksek-değerli araştırma kolu

Mevcut tahsis maliyeti statik engel haritasına rağmen Öklid mesafesi kullanır.
Nav2 Jazzy `ComputePathToPose` sonucu bir `nav_msgs/Path` döndürür; yol uzunluğu
ölçülerek Öklid yerine gerçek global-plan maliyeti kullanılabilir:
[resmî action tanımı](https://docs.ros.org/en/ros2_packages/jazzy/api/nav2_msgs/action/ComputePathToPose.html).
Ancak her robot-görev çifti için çevrim içi action çağrısı 50 ms bütçesini
aşabilir. Güvenli sonraki adım, statik occupancy map üzerinde önceden
hesaplanmış/kafes-cached jeodezik maliyet ve yalnız seçilen birkaç aday için
Nav2 plan doğrulamasıdır. Nav2 Route Server'ın dinamik kenar maliyetleri ve
kilitlenebilir koridorları da daha büyük filolarda congestion-aware genişleme
sağlar: [Nav2 Route Server](https://docs.nav2.org/configuration/packages/configuring-route-server.html).
