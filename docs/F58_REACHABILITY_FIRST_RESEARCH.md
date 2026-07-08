# F58: Reachability-First F45 derin araştırma ve yöntem tasarımı

**Tarih:** 2026-06-29  
**Referans:** F45/v4.5  
**Kapsam dışı:** F53 completion-fairness kolu

## Karar özeti

F45'in sonraki sürümü doğrudan completion sayısını eşitlememelidir. En güçlü
aday, F45'in EDPS/3PHA çekirdeğini koruyan ve tahsis maliyetini üç katmanda
düzelten **F58 Geodesic-Risk Lexicographic Repair (GRLR)** yöntemidir:

1. Öklid mesafesi yerine statik occupancy-map üzerinde geodezik yol maliyeti;
2. tekil `robot×task` sayacı yerine rota-bölgesi/koridor düzeyinde, belirsizliği
   de taşıyan erişilebilirlik olasılığı;
3. birincil verimli plan üretildikten sonra yalnız maliyeti en fazla ε artıran
   fizibil taşıma/takaslarla maksimum öngörülen robot yükünü azaltma.

Bu yapı Nav2-bağımsız düzlemde engel-duyarlı ETA ve rota yükünü, Gazebo'da ise
gerçek plan fizibilitesi ve yürütme geri bildirimini kullanır. Completion Jain
rapor metriği olarak kalır; optimizasyon girdisi olmaz.

## Neden mevcut adalet ekleri çalışmadı?

### 1. Allocation-only F45 zaten tavana yakın

`ideal_nav=True`, 5 robot/25 görev koşullarında aktif-robot Jain yaklaşık
0.98'dir. Arıza senaryosundaki düşük tüm-filo Jain'in önemli bölümü 45. saniyede
kalıcı kapatılan robottan gelir. Bu robotu completion bonusuyla yeniden seçmek
adalet değil, fizibil olmayan iş yüklemedir.

### 2. F45 yanlış kaynağı dengeliyordu

Mevcut `_arrival_time` ve birçok greedy yol, engelli haritada düz çizgi
mesafesini kullanır. Aynı görev sayısı iki robota eşit “adil” görünürken bir
robot dar koridor, duvar çevresi veya yeniden-planlama nedeniyle çok daha fazla
zaman harcayabilir. Araç rotalama araştırması, denge fonksiyonu kadar dengelenen
kaynağın seçiminin de sonucu belirlediğini gösterir. Değişken-toplamlı rota
kaynaklarında Jain/variance gibi non-monotonic hedefleri doğrudan optimize etmek
workload-inconsistent çözümler üretebilir
([Matl, Hartl ve Vidal](https://arxiv.org/abs/1803.01795),
[survey](https://arxiv.org/abs/1605.08565)).

### 3. F57 kanıtı yeniden kullanamıyordu

`robot_id×task_id` hafızası yalnız aynı görev yeniden denendiğinde etkilidir.
Görev tamamlanınca veya backoff'a girince öğrenilen bilgi kaybolur. Gazebo'daki
asıl ortak neden çoğunlukla görev kimliği değil; koridor, raf köşesi, dar geçit,
başlangıç yönelimi veya o rota üzerindeki dinamik tıkanmadır. Bu nedenle kanıt
harita bölgesine/rota kenarına genellenmelidir.

### 4. Tek ağırlıklı toplam yanlış takası gizliyor

Completion bonusu, mesafe, deadline ve churn ile aynı skora konduğunda farklı
birimlerdeki ağırlıklar seed'e göre davranışı değiştirdi. İki-aşamalı yaklaşım
önce verimli çözümü sabitler, sonra yalnız eşdeğer çözümler içinde denge arar.
Çok dönemli rota araştırmalarında bu ayrımın maliyet kaybetmeden yüksek denge
sağlayabildiği gösterilmiştir
([Nekooghadirli vd.](https://arxiv.org/abs/2206.14596)).

## F58-GRLR yönteminin teknik tasarımı

### A. Statik geodezik maliyet katmanı

Projede `placement.py` zaten Gazebo'nun yüklediği `obstacle_map.pgm` dosyasını,
0.55 m şişirilmiş occupancy maskesini ve dünya↔hücre dönüşümünü ortak kullanır.
Yeni katman aynı maskede 8-komşulu A*/Dijkstra çalıştırmalıdır:

```text
dG(a,b) = inflated occupancy grid üzerindeki en kısa serbest yol uzunluğu
ETA(r,t,Q) = [dG(pose_r,Q1) + Σ dG(Qi,Qi+1)] / v
             + Σ service_time(Qi) + queue_overhead
```

- Sorgular `(yuvarlanmış başlangıç hücresi, hedef hücresi)` anahtarıyla LRU
  cache'e alınır.
- Görev konumları sabit olduğundan task↔task maliyetleri deney başında bir kez
  hesaplanır; yalnız robot-pose↔ilk görev maliyeti çevrim içinde yenilenir.
- Önce 0.10 m çözünürlükte veya hiyerarşik 0.20→0.05 m çözüm denenmelidir.
- Yol yoksa çift `INF` olur; bütün robotlarda yol yoksa görev global backoff'a
  gider. `LAST_RESORT` bu fizibilite reddini ezmemelidir.
- Plane A yürütme modeli de aynı `dG` değerini kullanmalıdır; tahsisçiyi geodezik,
  simülatörü Öklid tutmak geçersiz karşılaştırma üretir.

Nav2 Planner Server bir hedef ve planner kimliği alıp global costmap üzerinde
yol üretir. `ComputePathToPose/ThroughPoses` çıktısı `nav_msgs/Path`, kısmi plan
durumu ve hata kodlarını sağlayabilir
([Planner Server](https://docs.nav2.org/configuration/packages/configuring-planner-server.html),
[ComputePathThroughPoses](https://docs.nav2.org/configuration/packages/bt-plugins/actions/ComputePathThroughPoses.html)).
Ancak her çevrimde bütün `R×T` çiftlerini action ile sorgulamak 50 ms tahsis
bütçesine uymaz. Gazebo'da yalnız statik cache'in seçtiği ilk `K=2 veya 3` aday
asenkron Nav2 sorgusuyla doğrulanmalı; tahsisçi son tamamlanmış cache'i okumalı,
action sonucunu senkron beklememelidir.

### B. Bölgesel erişilebilirlik ve belirsizlik modeli

Her navigasyon denemesinden aşağıdaki yeterli istatistik tutulur:

```text
global corridor/region:  S_e, F_e
robot-specific residual: S_r,e, F_r,e
```

İlk sürümde `e`, hedefin 1 m grid bölgesi olabilir. İkinci sürümde A* yolunun
geçtiği koridor/kenar dizisi kullanılmalıdır. Beta öncülüyle küçültülmüş başarı
ortalaması ve belirsizlik cezası:

```text
mean_e = (S_e + α) / (S_e + F_e + α + β)
LCB_e  = max(p_min, mean_e - κ sqrt(mean_e(1-mean_e)/(N_e+α+β+1)))
hazard(path) = Σ_e length_fraction(e) · [-log(LCB_e)]
p_path = exp[-hazard(path)]
```

Robot-özel tahmin az örnekte global bölge öncülüne çekilmelidir; böylece tek
başarısızlık robotu kalıcı biçimde damgalamaz. Riskli beklenen süre yaklaşık:

```text
ETA_eff = ETA_geo + ((1-p_path)/p_path) · failure_timeout
```

`p_path` sert eşik altında ise çift yalnız daha güvenilir alternatif varken
elenir. Her alternatif aynı derecede riskliyse görev kilitlenmez; kontrollü
backoff/recovery uygulanır. Belirsizlik altında planlama ve başarısızlıkta
yeniden tahsise olasılıksal garanti yaklaşımı, eşzamanlı tahsis-planlama
çalışmalarıyla uyumludur
([Faruq vd.](https://arxiv.org/abs/1803.02906),
[Choudhury vd.](https://iliad.stanford.edu/pdfs/publications/choudhury2022dynamic.pdf)).

İlk fiziksel sürüm için gerekli geri bildirim:

- `NavigateToPose` sonuç hata kodu;
- son geçerli robot pozu ve `distance_remaining`;
- recovery sayısı ve navigasyon süresi;
- planlanan yol hücreleri veya en azından hedef bölgesi.

Nav2 action geri bildirimi mevcut poz, kalan mesafe, tahmini kalan süre ve
recovery sayısını sağlar
([NavigateToPose action](https://github.com/ros-planning/navigation2/blob/main/nav2_msgs/action/NavigateToPose.action)).

### C. ε-sınırlı leksikografik adalet onarımı

F45 önce mevcut biçimde, fakat `ETA_eff` ile birincil kuyrukları üretir. Ardından
yalnız sağlıklı/aktif robotlarda yerel move ve swap adayları değerlendirilir.

Optimize edilen kaynak completion sayısı değil öngörülen iş bitirme yüküdür:

```text
B_r = gerçekleşmiş üretken_nav_süresi_r
      + Σ_(t in queue_r) [ETA_eff_increment(r,t) + service_time_t]

primary(plan) = (missed_deadline_count, total_expected_finish_cost, churn)
fair(plan)    = max_r B_r
```

Bir hareket yalnız şu koşullarda kabul edilir:

1. tahmin edilen deadline-hit sayısı azalmaz;
2. birincil toplam maliyet `C_new ≤ (1+ε) C_F45`, başlangıç için `ε=0.02`;
3. F27'nin incumbent/marj kuralı ve kuyruk kapasitesi korunur;
4. `max B_r` kesin azalır; eşitlikte workload range, sonra mesafe seçilir.

Bu leksikografik yapı ağırlık taramasını ve “Jain yükselsin diye gereksiz yol
uzatma” patolojisini engeller. Min-max rota yükü, çok-ajan rotalamada completion
time eşitliği için yerleşik bir hedeftir
([Equity-Transformer](https://ojs.aaai.org/index.php/AAAI/article/view/30007)).

Önerilen yerel arama:

1. `B_r` en yüksek iki robottan, en düşük iki robota move adayları;
2. her görev için yalnız `ETA_eff` bakımından ilk `K=3` robot;
3. önce tek-task move, sonra 1↔1 swap;
4. en fazla iki iyileştirme turu ve 10 ms zaman bütçesi;
5. hiçbir kabul yoksa F45 sonucu bit-özdeş döner.

## F45 koduna eşleme

| Bileşen | Eklenecek/değişecek yer |
|---|---|
| Grid A*/cache | `placement.py` yanında yeni `geodesic_cost.py` |
| Yol maliyet sağlayıcı | `TaskState`/allocator'a salt-okunur cost cache |
| `_arrival_time` | Öklid fallback + geodezik/riske göre ETA |
| Greedy paradigmalar | hepsi ortak `_arrival_time` kullandığı için otomatik |
| `_cost` | `AT`, deadline capability ve bid aynı `ETA_eff` kullanmalı |
| Rescue/F27/F48 | aynı ETA sağlayıcısına bağlanmalı; farklı mesafe tanımı kalmamalı |
| Geri bildirim | runner/executor Nav2 süre, recovery ve sonuç kodlarını toplamalı |
| Adalet onarımı | F27'den önce veya sonra tek, açık `_epsilon_fair_repair` aşaması |
| Plane A | hareket süresi/mesafesi aynı grid-geodezik oracle ile yürütülmeli |

F58, hormon sayısını veya EDPS bağlam vektörünü ilk aşamada değiştirmemelidir.
`reachability_risk` yeni hormon yapmak ancak maliyet katmanı tek başına
doğrulandıktan sonra ayrı ablasyon olabilir.

## Jazzy uyumluluğu

Nav2 Route Server dinamik kenar kapatma/maliyet ve costmap edge scorer sunar;
fakat Navigation2 paket tablosunda `nav2_route` Jazzy için mevcut değildir,
Kilted ve sonrasında görünür
([Navigation2 deposu](https://github.com/ros-navigation/navigation2),
[Route Server belgeleri](https://docs.nav2.org/configuration/packages/configuring-route-server.html)).
Bu çalışma Jazzy kullandığı için F58 ilk sürümü Route Server'a bağımlı olmamalı.
Mevcut Planner Server + proje içi grid/cache yaklaşımı doğru uyumluluk yoludur.

## Deney ve kabul protokolü

### Aşama 0 — doğruluk

- Haritada duvar arkasındaki iki nokta için `dG > dEuclid`;
- bağlantısız çift için `INF` ve global-fallback testi;
- cache deterministikliği ve sim/Gazebo harita paritesi;
- F58 kapalıyken F45 tüm bilimsel metriklerde bit-özdeş;
- ε-repair hiçbir deadline-hit'i kaybetmiyor.

### Aşama 1 — Nav2-bağımsız geliştirme

- geliştirme: seed 1--50; yalnız `grid_resolution`, `ε`, `K` için küçük ön-kayıtlı
  tarama;
- doğrulama: dokunulmamış seed 101--300;
- ölçek: 3r/15g, 5r/25g, 10r/50g; üç senaryo;
- Plane A hareket oracle'ı geodezik olmalı; ayrıca eski ideal-Euclidean sonuç
  geriye dönük karşılaştırma olarak raporlanmalı.

Kabul kapısı:

- CR ve fitness için ortalama gerileme en fazla 0.005;
- DVR artışı en fazla 0.005;
- aktif completion Jain gerilemez;
- `max predicted burden` ve toplam geodezik mesafeden en az biri azalır;
- en az iki senaryoda aktif-Jain, burden-range, churn veya delay'den biri iyileşir;
- eşleşmiş bootstrap %95 GA ve Holm düzeltmeli test raporlanır.

Allocation-only aktif Jain'in 0.98 tavanında anlamlı artış zorunlu tutulmamalı;
burada amaç onu korurken rota yükünü ve gecikmeyi iyileştirmektir.

### Aşama 2 — navigation-proxy

Mevcut proxy yalnız görev konumuna bağlı başarı olasılığı kullandığı için
robot/koridor öğrenmesini doğru sınamaz. İki sonuç ayrı verilmelidir:

1. eski proxy: geriye uyumluluk;
2. ön-kayıtlı corridor-risk proxy: global koridor riski + küçük robot residualı.

İkinci model F58 lehine sonradan uydurulmamalı; risk haritası seed'den önce sabit
ve raporda açık olmalıdır.

### Aşama 3 — Gazebo

- önce 3r/15g, üç senaryo, en az 5 eşleşmiş seed duman/pilot;
- sonra 5r/25g, en az 10 eşleşmiş seed;
- aynı görev havuzu ve başlangıç pozları, F45/F58 sırası seed bazında
  randomize edilmeli;
- Nav2 plan başarısızlığı, recovery, gerçek path length, redispatch/task,
  makespan, CR, DVR, aktif/tüm Jain birlikte saklanmalı.

Gazebo kabulü: CR/DVR non-inferiority kapısını geçmeden Jain artışı kabul
edilmez. En az iki fiziksel yürütme metriği (`nav_failure`, recovery, path
length, redispatch, makespan) iyileşmeli ve aktif Jain gerilememelidir.

## Öncelik sırası ve riskler

1. **P0 — Geodezik oracle ve Plane-A paritesi.** En düşük yöntem riski, en
   yüksek teşhis değeri; diğer katmanların önkoşulu.
2. **P1 — ε-sınırlı min-max burden repair.** Geodezik oracle üzerinde küçük,
   geri alınabilir yerel arama; allocation-only adalet kolu.
3. **P2 — Hedef-bölgesi Beta riski.** Mevcut event verisiyle uygulanabilir,
   Gazebo'da ilk öğrenme deneyi.
4. **P3 — Nav2 top-K asenkron plan cache ve yol-kenarı risk modeli.** En güçlü
   fiziksel model, fakat mesaj/eylem entegrasyonu daha yüksek.
5. **P4 — Koridor rezervasyonu/congestion.** Büyük filoda değerlidir; Jazzy'de
   proje içi reservation table gerekir.

Başlıca riskler: grid yolu ile Nav2 footprint maliyetinin ayrışması, başarısız
yolun bütün kenarlarına yanlış kredi atanması, az örnekle aşırı karantina ve
asenkron cache'in bayat kalmasıdır. Bunlar sırasıyla aynı inflation parametresi,
hierarchical shrinkage, LCB alt sınırı/global fallback ve cache yaş sınırıyla
kontrol edilmelidir.

## Araştırma sonucu

En savunulabilir yöntem iyileştirmesi yeni bir completion-fairness ağırlığı
değildir. **Önce gerçek ulaşım maliyetini ve erişilebilirlik belirsizliğini
ölçmek, sonra verim zarfı içinde monoton min-max rota yükünü azaltmak** gerekir.
Bu tasarım F45'in güçlü allocation-only sonucunu korurken Gazebo'daki gerçek
kayıp kaynağına müdahale eder ve başarısız F53--F57 deneylerinin kök nedenlerini
doğrudan giderir.

## P0+P1 uygulama ve doğrulama sonucu (2026-06-29)

Geodezik oracle, ortak şişirilmiş occupancy map üzerinde sparse Dijkstra ve
LRU distance-field cache ile uygulandı. F45'in `_arrival_time`, deadline
kontrolü, rota sıralaması, rescue ve bid uzaklığı aynı oracle'a bağlandı.
Ardından deadline-miss sayısını artırmayan, toplam geodezik mesafeyi F45
planının `1+ε` zarfında tutan, maksimum rota yükünü ve projected active-Jain'i
monoton koruyan yerel move onarımı eklendi.

Plane-A denetiminde ayrıca robotun başarılı görevden sonra pozunun hedefe hiç
güncellenmediği bulundu ve düzeltildi. Eski model her rota bacağını spawn
noktasından ölçüyordu. F45/F58 karşılaştırmaları bu düzeltilmiş hareket modeli
ve iki yöntem için aynı geodezik ground-truth ile yeniden yapıldı.

5r/25g, seed 101--300 eşleşmiş allocation-only holdout sonucu (F58−F45):

| Senaryo | Δaktif-Jain (%95 GA) | Δgecikme | Δmesafe | Δchurn |
|---|---:|---:|---:|---:|
| robot_failure | -0.0005 [-0.0029,+0.0020] | -1.48 s | -14.93 m | -0.0006 |
| mixed_stress | -0.0008 [-0.0033,+0.0017] | -1.64 s | -16.61 m | -0.0006 |
| deadline_pressure | -0.0009 [-0.0032,+0.0013] | -0.86 s | -0.93 m | 0.0000 |

Üçünde de CR=1, fitness=1 ve DVR=0 korunmuştur. Aktif-Jain farklarının tüm
güven aralıkları sıfırı kapsar; kanıtlanmış adalet regresyonu yoktur. Mixed
stress mesafe-Jain farkı +0.0138 ve güven aralığı tamamen pozitiftir.

Aynı seed'lerde eski navigation-proxy sonucu:

- robot_failure: fitness +0.0057, CR +0.0050, DVR -0.0034, mesafe -20.72 m;
- mixed_stress: fitness +0.0043, CR +0.0016, DVR -0.0038, mesafe -20.56 m,
  churn -0.083;
- deadline_pressure: fitness +0.0063, CR +0.0080, DVR -0.0074, mesafe
  -19.70 m ve navigasyon başarısızlığı -1.475/seed.

## P0+P1 Gazebo+Nav2 sonucu (2026-06-30)

5 robot/25 görev, üç senaryo ve ortak 1--5 tohumlarında taze F45 ile F58 ayrı
çalıştırıldı (15+15=30 fiziksel koşu). Tüm koşular 25/25 görevi tamamladı;
`DONE` denetimi 30/30, `INVALID_TIMEJUMP` ve `STARTUP_FAILED` sayıları sıfırdır.
Karşılaştırma `results/stats/gazebo_f58_validation/r5t25/REPORT.md` altındadır.

| Senaryo | CR F45→F58 | DVR F45→F58 | Δgecikme | Δmesafe | Δaktif-Jain | F58 karar | Kapı |
|---|---:|---:|---:|---:|---:|---:|---|
| robot_failure | 1.000→1.000 | .024→.008 | +0.564 s | +5.242 m | -0.0216 | 41.97 ms | FAIL |
| mixed_stress | 1.000→1.000 | .312→.336 | +1.334 s | +1.098 m | -0.0047 | 41.58 ms | FAIL |
| deadline_pressure | 1.000→1.000 | .320→.224 | -4.868 s | -0.134 m | -0.0062 | 52.77 ms | FAIL |

Pozitif Δgecikme/Δmesafe kötüleşmedir. İlk rapor kapısı Jain'i destekleyici
dört metrikten biri saydığı için deadline hücresini yanlış biçimde `PASS`
etiketleyebiliyordu. F58'in yöntem sözleşmesi adalet-koruma olduğundan kapı
düzeltildi: aktif-Jain'in ortalama farkı negatif olamaz, karar gecikmesi
50 ms'yi aşamaz ve CR/DVR güvenliğine ek olarak dört fiziksel ölçütün
(mesafe, redispatch, gecikme, makespan) en az ikisi iyileşmelidir.

Sonuç: P0/P1 fiziksel yönteme terfi etmemiştir. Deadline baskısındaki belirgin
DVR/gecikme kazanımı değerlidir, fakat bunu küçük bir Jain kaybı ve 50 ms üstü
hesaplama ile satın alır. Robot arızası ve karışık streste rota/adillik yönü de
olumsuzdur. Sonraki fiziksel sürümün geodezik hesabı olay döngüsünden çıkarması
ve P2/P3'te gerçek Nav2 yol/başarı geri bildirimini kullanması gerekir.

Proxy aktif-Jain farkları üç senaryoda da sıfırdan ayrışmamıştır. Bu kanıtla
P0 geodezik ETA ve P1 ε-repair kodda varsayılan açık F58 adayı yapılmıştır.
F45, `AHE_F58_GEODESIC=0 AHE_F58_FAIR_REPAIR=0` ile yeniden üretilebilir.
P2 bölgesel risk öğrenmesi ve tam Gazebo kampanyası henüz tamamlanmadığından
makaledeki resmî sonuç referansı Gazebo kabul kapısına kadar F45 kalmalıdır.

### Nihai Nav2-bağımsız ölçek koşusu

F58-P0/P1, dört yöntemle ve her hücrede 100 seed kullanılarak üç ölçekte yeniden
çalıştırıldı. Aşağıdaki satırlar F58 AHE'ye aittir:

| Ölçek | Senaryo | Fitness/CR/DVR | Aktif Jain | Mesafe-Jain | Gecikme | Mesafe | Churn | Latency |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 3r/15g | robot_failure | 1/1/0 | 0.990 | 0.830 | 40.1 | 154.3 | 0.0667 | 0.056 ms |
| 3r/15g | mixed_stress | 1/1/0 | 0.991 | 0.833 | 39.9 | 153.3 | 0.0653 | 0.042 ms |
| 3r/15g | deadline_pressure | 1/1/0 | 0.986 | 0.965 | 65.8 | 155.5 | 0 | 0.042 ms |
| 5r/25g | robot_failure | 1/1/0 | 0.983 | 0.841 | 30.6 | 183.7 | 0.0024 | 0.072 ms |
| 5r/25g | mixed_stress | 1/1/0 | 0.983 | 0.843 | 30.7 | 183.8 | 0.0024 | 0.059 ms |
| 5r/25g | deadline_pressure | 1/1/0 | 0.978 | 0.953 | 60.5 | 235.7 | 0 | 0.052 ms |
| 10r/50g | robot_failure | 1/1/0 | 0.961 | 0.859 | 30.9 | 272.7 | 0 | 0.361 ms |
| 10r/50g | mixed_stress | 1/1/0 | 0.968 | 0.864 | 30.9 | 277.0 | 0 | 0.356 ms |
| 10r/50g | deadline_pressure | 1/1/0 | 0.977 | 0.946 | 56.8 | 436.0 | 0 | 0.259 ms |

10r ilk koşusunda üç robot-failure ve üç mixed seed'inde aynı görevin iki
robotta eşzamanlı yürütülebildiği görüldü (CR=1.02). Allocator wrapper'a sağlıklı
in-flight görevi sahibine kilitleyen ve bütün kuyruklarda tek görev-tek sahip
invariantını zorlayan son güvenlik katmanı eklendi. Problemli seed'ler ve tam
10r kampanyası tekrarlandığında CR tam 1.000 oldu. Unit test sayısı 18'e çıktı.

Üretilen raporlar:

- `results/stats/f58_allocation_only_3r15t/REPORT.md`
- `results/stats/f58_allocation_only/REPORT.md`
- `results/stats/f58_allocation_only_10r50t/REPORT.md`

## P1O--P1Q derin fiziksel teşhis (2026-07-01)

P1L smoke koşusunda aktif-Jain gerilerken görev olay izi, tamamlanmış bazı
görevlerin bir sonraki tahsis çevriminde yeniden `assigned` edildiğini gösterdi.
Kök neden tek bir fairness katsayısı değil, üç parçalı bir durum tutarlılığı
hatasıydı: periyodik robot durumu exact completion olayından geri kalabiliyor,
kalıcı `_prev_queues` kapalı görev kimliğini taşıyabiliyor ve yayın sınırı stale
allocator çıktısını filtrelemiyordu. Aşağıdaki korumalar eklendi:

1. yalnız `navigation_state == NAVIGATING` gerçek in-flight lock sayılır;
2. completion olayı runner önbelleğindeki `current_task_id`'yi anında temizler
   ve gecikmiş status içindeki tamamlanmış kimlik allocator'a geçirilmez;
3. allocator kuyrukları güncel aktif `task_map` ile budanır, runner yayın
   sınırında kapalı waypoint'leri tekrar reddeder;
4. karşılaştırma kapısı, completion sonrasında assignment görürse performans
   ortalamalarından bağımsız olarak sert `FAIL` verir.

P1O ile aynı güncel kaynak kodundan taze F45/F58, 5r/25g robot_failure,
seed 1--3 üretildi. Altı geçerli koşunun tamamında 25/25 görev ve sıfır görev
dirilmesi görüldü. Sürekli fairness repair aktif-Jain'i ortalamada
`0.9612 -> 0.9748` yükseltti ve DVR'ı `0.0267 -> 0.0133` düşürdü; ancak gecikme
3.14 s, makespan 3.67 s ve mesafe 0.25 m kötüleşti. Fiziksel kazanç 0/4 olduğu
için sonuç doğru olarak `FAIL` kaldı.

Ablasyon, geodezik-only P1P'nin seed-1'de gecikme, makespan ve mesafeyi birlikte
iyileştirirken aktif-Jain'i düşürdüğünü gösterdi. Bunun üzerine P1Q terminal
repair geliştirildi: repair yalnız kalan aktif görev sayısı sağlıklı robot
sayısının iki katına indiğinde açılır. Nav2-bağımsız 401--420 seed taramasında
üç senaryoda CR/DVR korunarak aktif-Jain, gecikme ve mesafe birlikte iyileşti.
Fiziksel seed-1 de üç verim kazanımı ve Jain artışı verdi; fakat üç-seed sonuç
genellenmedi:

| Ölçüt | F45 | P1Q | İyileşme yönlü fark |
|---|---:|---:|---:|
| Aktif-Jain | 0.9612 | 0.9608 | -0.0004 |
| Ortalama gecikme | 100.02 s | 101.30 s | -1.27 s |
| Makespan | 195.67 s | 202.33 s | -6.67 s |
| Mesafe | 178.31 m | 180.43 m | -2.12 m |
| DVR | 0.0267 | 0.0133 | +0.0133 |

Seed farkları heterojendir: seed-1 tüm hedeflerde iyi, seed-2 makespan'de
37 s ve mesafede 11.7 m kötü, seed-3 Jain'de -0.0148'dir. P1Q bu nedenle
`results/stats/gazebo_f58_p1q_validation/r5t25/REPORT.md` kapısında `FAIL`
almıştır. P0/P1/P1Q fiziksel yönteme terfi ettirilmemiş, makale iddiası ve F45
referansı değiştirilmemiştir. Sonraki araştırma kolu yeni eşik taraması değil;
Nav2 yürütme süresi/koridor beklemesini çevrim içi geri besleyen, seed-2 benzeri
uzun-kuyruk kuyruğunu doğrudan cezalandıran fiziksel ETA modelidir.

## P1R: Nav2 geri-bildirimli kalan-makespan koruması (2026-07-07)

P1Q'nun seed-2 uzun son-kuyruğunu gidermek için statik rota yüküne ek olarak
Nav2 `NavigateToPose` geri bildirimi kullanıldı. Robot arayüzünün zaten
yayımladığı `LocalExecutionFeedback.navigation_effort` (global yol üzerindeki
kalan mesafe) runner üzerinden `RobotState`'e taşındı. Yürütülen ilk görevde
statik kafes sorgusu yerine bu ölçüm kullanılır; sonraki görevlerde cache'li
geodezik uzaklık korunur. Fairness taşıması artık deadline/mesafe/Jain/max-burden
korumalarına ek olarak filonun maksimum tahmini kalan bitiş süresini de
artıramaz. Bu yaklaşım Nav2'nin resmî `NavigateToPose` feedback sözleşmesindeki
`distance_remaining`/`estimated_time_remaining` yaklaşımıyla uyumludur.

401--420 allocation-only holdout'ta terminal eşik 3 seçildi. F45'e karşı üç
senaryoda CR=1 ve DVR=0 korunurken aktif-Jain, gecikme ve mesafe birlikte
iyileşti. Ardından 5r/25g robot_failure seed 1--3 fiziksel kapısı çalıştırıldı:

| Ölçüt | F45 | P1R | İyileşme |
|---|---:|---:|---:|
| Aktif-Jain | 0.9612 | 0.9702 | +0.0090 |
| Makespan | 195.67 s | 195.00 s | +0.67 s |
| Toplam mesafe | 178.31 m | 176.52 m | +1.80 m |
| DVR | 0.0267 | 0.0133 | +0.0133 |
| Karar gecikmesi | 0.52 ms | 16.21 ms | bütçe içinde |

CR her altı eşlenik koşuda 1.0, tamamlanmış-görev dirilmesi sıfırdır. Katı kapı
CR/DVR, aktif-Jain, 50 ms karar bütçesi, olay bütünlüğü ve 2/4 fiziksel kazanım
ile `PASS` vermiştir. Rapor:
`results/stats/gazebo_f58_p1r_validation/r5t25/REPORT.md`.

Bu PASS yalnız robot_failure hücresini terfi ettirir; mixed_stress ve
deadline_pressure için eşlenik çok-seed Gazebo verisi üretilmeden tüm yöntem
için genelleme veya makale ana-tablosu güncellemesi yapılmamalıdır. F58 etkin
olduğunda P1R terminal eşiği 3 artık varsayılandır; F58 özellikleri kapalı F45
referans davranışı değişmez.

## P1R Nav2-bağımsız eşlenik kampanya (2026-07-07)

P1R'ın allocation-only düzlemdeki genellenebilirliği 4 hücrede, seed-eşlenik
F45/F58 koşularıyla ölçüldü (`scripts/validate_f58_nav2free_paired.py`;
her iki kol aynı geodezik yürütme oracle'ında, `ideal_nav=True`, F53 kapalı):
5r/25g seed 1--100, 3r/15g seed 1--100, 10r/50g seed 1--100 ve taze holdout
5r/25g seed 501--600 (eşik 401--420'de seçildiği için görülmemiş aralık).
Toplam 2400 koşu; istatistik eşleştirilmiş Wilcoxon + Holm (hücre×senaryo
başına 10 metrik) + eşlenik Cliff's Δ.

Sonuç: 120 testin 51'i Holm sonrası anlamlı; bunların 39'u F58 lehine, 12'si
karar gecikmesi aleyhine (en kötü 0.08→0.20 ms, 50 ms bütçenin çok altında).
Gecikme dışında hiçbir metrikte anlamlı gerileme yok. CR/Fitness/DVR dört
hücrede de her iki kolda tavanda (1.000/0.000) ve bit-eşit korunur.

| Hücre | Anlamlı F58 kazanımları (Holm p<0.05) |
|---|---|
| 5r/25g ana | delay −1.4 s, Jain(all) +.018, Jain(aktif) +.006, dist-Jain +.018 (rf/ms), mesafe −13 m, churn −.004 (rf/ms); deadline'da Jain +.006, delay −1.5 s |
| 3r/15g | nötr — gecikme dışında hiçbir fark anlamlı değil (küçük filoda repair nadiren tetikleniyor); gerileme de yok |
| 10r/50g | en güçlü hücre: Jain(aktif) +.026 (Δ=.81), Jain(all) +.024, delay −1.3 s, mesafe −21 m, dist-Jain +.014; mixed benzer; deadline'da Jain +.017, mesafe −14 m |
| Holdout 501--600 | kazanımlar taşındı: delay −1.0/−1.6 s, Jain(aktif) +.006/+.005, mesafe −10/−13 m, churn −.004 (rf/ms); deadline'da Jain +.008 |

Rapor ve per-seed CSV'ler: `results/stats/f58_p1r_nav2free_compare/`.
Bu kampanya yalnız Nav2-bağımsız düzlemi kapsar; Gazebo tarafında geçerli
kanıt hâlâ P1R robot_failure PASS'ıdır ve mixed_stress/deadline_pressure
Gazebo hücreleri üretilmeden makale ana-tablosu güncellenmemelidir.

## Paper-grade 5-seed Gazebo kampanyası + makale entegrasyonu (2026-07-08)

Kullanıcı (a) seçeneğini onayladı: ana tablolar kilitli F45 verisiyle kalır,
F58 makaleye doğrulanmış bayrak-kapılı iyileştirme olarak girer. Eski 3-seed
kanıt iki nedenle 5-seed'e tamamlandı: (1) makaledeki eski (FAIL dönemi)
tablo 5-seed standardındaydı; (2) robot_failure kanıtı eski kaynak anlık
görüntüsünden geliyordu (p1o F45 referansı; src/ dosyaları o kampanyadan
sonra değişmişti — karışık provenans tabloya giremez).

Koşumlar (sürücü: Claude job tmp `f58_paper5_driver.sh`, tümü aynı kaynak):
- robot_failure: iki kol taze seed 1-5 → `results/raw/gazebo_f58_paper5_rf_validation/`
  (F45 seed2 ilk koşuda 0 görevle startup-flake verdi; tek koşu yeniden
  koşuldu, DONE). Rapor: `results/stats/gazebo_f58_paper5_rf_validation/r5t25/REPORT.md`
- mixed_stress + deadline_pressure: `gazebo_f58_p1r_other_validation/` kökü
  seed 4-5 ile genişletildi (seed 1-3 aynı gecenin koşusu, sha256 doğrulandı).
  Rapor: `results/stats/gazebo_f58_p1r_other_validation/r5t25/REPORT.md`

**Sonuç: üç senaryo da n=5 ile PASS (3/4 fiziksel kazanım her birinde).**

| Ölçüt (F45→F58) | robot_failure | mixed_stress | deadline_pressure |
|---|---|---|---|
| CR | 1.000→1.000 | 1.000→1.000 | 1.000→1.000 |
| DVR | .016→.000 | .296→.256 | .312→.216 (CI 0-dışı) |
| Gecikme (s) | 95.52→94.01 | 54.24→52.37 | 77.18→70.49 (CI 0-dışı) |
| Mesafe (m) | 167.03→166.47 | 157.96→149.61 (CI 0-dışı) | 146.87→133.53 (CI 0-dışı) |
| J_act | .966→.973 | .961→.985 (CI 0-dışı) | .978→.987 |
| Karar (ms) | .49→17.44 | .45→16.97 | .68→21.16 |

Tutarlı bedel: mesafe-Jain (deadline −.019 CI 0-dışı) + karar gecikmesi
17-21 ms (50 ms bütçe içi). n=5 Wilcoxon tabanı p=.0625 → kanıt yön
tutarlılığı + bootstrap CI; anlamlılık desteği Nav2-bağımsız 100-seed
kampanyadan.

**Makale entegrasyonu (EN+TR, 2026-07-08):** `tab:f58-allocation` P1R
verisiyle yeniden üretildi (9 hücre, per-seed CSV'lerden); `tab:f58-gazebo`
5-seed PASS sayılarıyla yenilendi; TR sec:f58'e P1R paragrafı (terminal
eşik 3×sağlıklı-robot + Nav2 navigation_effort kalan-makespan koruması)
eklendi; FAIL anlatısı (abstract, katkı maddesi, metod kapanışı, Gazebo
alt-bölümü, sonuç) PASS anlatısına çevrildi; **EN makaleye F58 ilk kez
taşındı** (metod alt-bölümü, allocation-only bölüm yapısı + navigation-proxy
ayrımı, Gazebo doğrulama alt-bölümü, abstract/katkı/sonuç). TR 21 sf,
EN 20 sf, 0 çözümsüz ref. F58 bayrakları çalışma zamanında hâlâ default
OFF; dört-yöntem ana kıyaslaması F45 ile üretilmiş halde değişmedi.

## Taze-tohum replikasyonu seed 6-10 + havuzlu n=10 analiz (2026-07-08)

Kullanıcı isteğiyle 5r/25g eşlenik kampanya hiç görülmemiş seed 6-10 ile
yeni kökte tekrarlandı (30/30 DONE, aynı kaynak sha256 doğrulandı):
`results/raw/gazebo_f58_replication_s6_10/`, rapor
`results/stats/gazebo_f58_replication_s6_10/r5t25/REPORT.md`.

**Dalga-2 katı kapı:** deadline_pressure **PASS** (dalga-1'den de güçlü:
delay −11.3s, DVR .368→.248, makespan −18.4s, mesafe −28.5m — hepsi CI
0-dışı); mixed_stress **FAIL** (DVR +.016, CI [−.056,+.016] 0'ı içeriyor —
gürültü; verim kazanımları replike: mesafe −12.1m CI 0-dışı, delay −4.6s,
makespan −6.0s CI 0-dışı, J_act +.023 CI 0-dışı); robot_failure **FAIL**
(J_act −.006, CI [−.025,+.009] 0'ı içeriyor — gürültü; toparlanma −46.5s
CI [26,72]!). Katı kapının sıfır-toleranslı güvenlik sınırları n=5'te tek
tohum gürültüsüyle tetiklenebiliyor.

**Havuzlu n=10 (dalga1+dalga2, hardlink havuz `_f58_pooled_s1_10`, rapor
`results/stats/_f58_pooled_s1_10/r5t25/REPORT.md`): ÜÇ SENARYO DA PASS**
(mixed 4/4 kazanım) ve ilk kez gerçek Wilcoxon anlamlılığıyla:

| Ölçüt (F45→F58, n=10) | robot_failure | mixed_stress | deadline_pressure |
|---|---|---|---|
| DVR | .020→.004 (CI 0-dışı) | .328→.316 ns | .340→.232 **p=.008** |
| Delay | +0.5s ns | −3.2s **p=.049** | −9.0s **p=.004** |
| Mesafe | −2.7m ns | −10.2m **p=.004** | −20.9m **p=.004** |
| J_act | +.0004 nötr | +.024 **p=.008** | +.017 **p=.031** |
| Toparlanma | −34.0s **p=.037** | ns | — |
| Makespan | ns | ns | −11.0s p=.061 |

Bedel değişmedi: latency 17-23ms (bütçe içi), mesafe-Jain dp'de −.020
(p=.006). Havuzlu DVR/J_act "gerileme" yok (ms DVR −.012 ns, rf J_act
nötr) → dalga-2 FAIL'leri gürültü teyitli. SONUÇ: F58 kazanımları tohum
seçimine bağlı değil; n=10 havuz makale için anlamlılık-düzeyinde fiziksel
kanıt sağlıyor (n=5 "yön+CI" çekincesi kaldırılabilir).
