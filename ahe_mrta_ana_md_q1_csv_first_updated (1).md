# AHE-MRTA RA-L/Q1 Revize Proje ve Makale Çerçevesi

## Adaptive Heuristic Ecosystem for Robust Online Multi-Robot Task Allocation

Bu dosya, AHE-MRTA projesini RA-L/Q1 SCI düzeyinde bir makale hedefiyle geliştirmek ve Claude Code ile aşamalı olarak uygulanabilir bir ROS 2/Gazebo prototipine dönüştürmek için revize edilmiş ana rehberdir.

Revizyonun temel amacı üç noktadır:

- AHE-MRTA'nın yenilik iddiasını yalnızca “adaptif ağırlıklı görev atama” düzeyinde bırakmadan, heuristic ajanları arasında dominance, cooperation, suppression ve çevrim içi ekolojik evrim mekanizmalarıyla formalize etmek
- ROS 2 Jazzy, Gazebo Harmonic, Nav2 ve TurtleBot3 Waffle Pi üzerinde uygulanabilirliği korumak
- RA-L/Q1 makale için karşılaştırma, ablation, metrik, ölçeklenebilirlik ve tekrar üretilebilirlik planını güçlendirmek

## Bu sürümde işlenen ek düzeltmeler

Bu dosya, önceki değerlendirme sonucunda önerilen tüm kritik düzeltmeleri içerecek şekilde güncellenmiştir. Özellikle aşağıdaki noktalar güçlendirilmiştir:

- RA-L/SCI-E için çalışmanın nihai karar düzeyi ve makale olgunluğu açıkça ayrılmıştır.
- AHE-MRTA'nın yalnızca adaptive weighted assignment gibi görünmemesi için yenilik iddiası daha keskinleştirilmiştir.
- 2023 sonrası dinamik MRTA, solver tabanlı MRTA, learning-based MRTA ve graph/attention tabanlı task allocation çizgilerine göre literatür konumlandırması eklenmiştir.
- Karşılaştırma yöntemlerinin ayrıntılı tanımları ana dosyadan çıkarılmış ve ayrı ek dosyada toplanmıştır: `ahe_mrta_recent_comparison_methods.md`. Ana dosya yalnızca deney tasarımı, çıktı sistemi, AHE mekanizması ve Claude Code faz planını içerir.
- Deney planı RA-L sayfa sınırına uygun olacak şekilde ana senaryolar, opsiyonel senaryolar ve ablation deneyleri olarak yeniden düzenlenmiştir.
- Robot ölçeği bu sürümde kompakt tutulmuştur; ana makale deneyleri 5 robot / 25 hedef ölçeğine, opsiyonel kısa ölçek kontrolü ise 3/15 → 5/25 karşılaştırmasına odaklanır.
- Claude Code ile geliştirme için her faza geçmeden önce doğrulama kapıları eklenmiştir.
- Muhtemel hakem itirazları, sınırlılıklar, başarısızlık riskleri ve makale anlatı stratejisi ayrıntılandırılmıştır.
- Q1/RA-L gücünü artırmak için dominance + cooperation + suppression üçlüsü ana yenilik ekseni olarak sabitlendi.
- Başarı anlatısı travel distance yerine robustness, workload balance, failure recovery, allocation instability ve dominance evolution üzerine yeniden vurgulandı.
- Ana makale çıktı planı 6 figür, 3 ana tablo ve 4 supplementary istatistik tablosu olarak netleştirildi.
- Claude Code fazları, adaptive weighting eleştirisini önleyecek ablation ve istatistiksel kanıtları zorunlu üretecek şekilde güncellendi.

---

# 1. RA-L/Q1 Odaklı Nihai Konumlandırma

## 1.1. Çalışmanın önerilen İngilizce başlığı

**Adaptive Heuristic Ecosystem for Robust Online Multi-Robot Task Allocation in Dynamic Inspection Environments**

Alternatif daha kısa başlık:

**AHE-MRTA: An Adaptive Heuristic Ecosystem for Online Multi-Robot Task Allocation**

Türkçe karşılığı:

**Dinamik Denetim Ortamlarında Dayanıklı Çevrim İçi Çoklu Robot Görev Atama için Adaptif Heuristic Ekosistemi**

## 1.2. RA-L için önerilen temel iddia

Bu çalışma, çevrim içi çoklu robot görev atamada sabit heuristic seçimi, statik ağırlıklı görev dağıtımı veya tekil auction tabanlı karar mekanizmaları yerine, birden fazla klasik görev atama heuristic'ini adaptif bir ekosistem içinde etkileşimli strateji ajanları olarak modelleyen açıklanabilir bir MRTA çerçevesi sunar.

AHE-MRTA'nın yeniliği tamamen yeni bir tekil heuristic önermek değildir. Asıl yenilik, literatürdeki bilinen heuristic ailelerinin çevrim içi bağlam vektörü, dominance evolution, cooperation, suppression, failure penalty ve event-triggered replanning üzerinden birlikte evrilen bir karar ekosistemi içinde yeniden örgütlenmesidir.

## 1.3. Makalenin önerilen ana katkıları

Makale katkıları doğrudan ve ölçülebilir şekilde şöyle yazılmalıdır:

1. **Adaptive heuristic ecosystem formulation:** Çevrim içi MRTA için heuristic'leri bağımsız solver'lar veya statik ağırlık bileşenleri olarak değil, dominance, cooperation ve suppression etkileşimleriyle evrilen strateji ajanları olarak modelleyen yeni bir AHE-MRTA formülasyonu önerilir.

2. **Context-adaptive allocation mechanism:** Görev yoğunluğu, robot uygunluğu, batarya riski, deadline baskısı, workload variance, failure rate ve allocation instability bileşenlerinden oluşan çevrim içi bağlam vektörü ile görev dağıtım maliyet fonksiyonunun ağırlıkları dinamik olarak güncellenir.

3. **Communication-efficient execution architecture:** Robotlara yalnızca kendi optimize edilmiş görev kuyruğu gönderilir. Heuristic dominance değerleri, cooperation/suppression matrisleri, global görev-robot maliyet matrisi ve ekosistem hafızası robotlara yayınlanmaz. Böylece düşük veri paylaşımlı ve ölçeklenebilir bir mimari korunur.

4. **Event-triggered replanning under failures and congestion:** Sürekli yeniden planlama yerine arıza, hedefe ulaşamama, deadline riski, batarya kritikliği ve dar koridor gecikmesi gibi olaylara bağlı yeniden atama mekanizması kullanılır.

5. **Reproducible ROS 2/Gazebo evaluation:** ROS 2 Jazzy, Gazebo Harmonic, Nav2 ve TurtleBot3 Waffle Pi tabanlı çok robotlu simülasyon ortamında baseline, ablation ve ölçeklenebilirlik deneyleriyle görev tamamlama, gecikme, yük dengesi, toparlanma süresi, karar gecikmesi, yeniden planlama sıklığı ve heuristic dominance evrimi değerlendirilir.

## 1.4. Hakeme karşı en önemli savunma cümlesi

AHE-MRTA, yalnızca ağırlıkların dinamik ayarlandığı bir görev dağıtım yöntemi değildir. Yöntem, heuristic stratejiler arasındaki işbirliği ve baskılama ilişkilerini çevrim içi performans geri bildirimiyle güncelleyerek hangi görev dağıtım davranışının hangi bağlamda baskın hâle geleceğini açıkça modelleyen ekolojik bir karar çerçevesidir.

## 1.5. RA-L/SCI-E için mevcut olgunluk kararı

Bu çalışma mevcut kurgu düzeyinde doğrudan makale değil, güçlü bir RA-L/SCI-E araştırma planıdır. Makaleye dönüşebilmesi için algoritmik formülasyonun kodda çalıştırılması, baseline ve ablation deneylerinin aynı seed setiyle yürütülmesi ve sonuçların istatistiksel olarak raporlanması gerekir.

Değerlendirme:

| Boyut                   | Durum        | Not                                                         |
| ----------------------- | ------------ | ----------------------------------------------------------- |
| Fikir özgünlüğü         | Güçlü        | Ekolojik heuristic etkileşimi iyi savunulursa özgün görünür |
| RA-L uyumu              | Orta-yüksek  | Kısa ve odaklı algoritma + deney makalesi olarak yazılmalı  |
| Teknik uygulanabilirlik | Yüksek       | MVP 3 robot/15 hedef ile başlanmalı                         |
| Makale deney gücü       | Sonuca bağlı | Fixed-weight kontrol ve ablation farkı belirleyici olur     |
| En büyük risk           | Orta         | “Sadece adaptive weighting” eleştirisi                      |
| Nihai potansiyel        | Yüksek       | Güçlü sonuçlarla RA-L/Q1 SCI-E adayı olabilir               |

## 1.6. RA-L kısa format stratejisi

RA-L kısa ve odaklı bir yayın formatı olduğu için çalışma geniş bir proje raporu gibi sunulmamalıdır. Makale, tek bir ana iddia etrafında kurulmalıdır:

```text
Adaptive heuristic ecosystem = online MRTA için açıklanabilir, hafif, düşük veri paylaşımlı ve event-triggered adaptasyon katmanı.
```

Makale içinde ROS 2 paket yapısı ayrıntılı biçimde anlatılmamalıdır. Paket yapısı ve kod mimarisi repository veya supplementary materyal düzeyinde kalmalıdır. Ana makalede yalnızca şu üç teknik unsur görünür olmalıdır:

```text
1. AHE algoritmik mekanizması
2. Düşük veri paylaşımlı ROS 2 yürütme mimarisi
3. Baseline ve ablation sonuçları
```

RA-L için önerilen katkı sayısı 3 veya en fazla 4 olmalıdır. Çok fazla katkı maddesi makaleyi proje raporu gibi gösterir. Nihai makalede katkılar şu şekilde sadeleştirilebilir:

1. Heuristic dominance, cooperation ve suppression üzerinden çevrim içi evrilen AHE-MRTA formülasyonu
2. Robotlara yalnızca optimize görev kuyruğu gönderen communication-efficient execution architecture
3. Failure, congestion, deadline pressure ve dynamic task arrival altında event-triggered replanning mekanizması
4. ROS 2/Gazebo üzerinde baseline ve ablation destekli deneysel doğrulama

## 1.7. Q1/RA-L güçlendirme kararları

Bu bölüm, nihai makale yazımında ve Claude Code uygulamasında korunması gereken çekirdek kararları özetler. Amaç, çalışmanın “kalabalık proje planı” gibi değil, net hipotezi olan deneysel bir RA-L/Q1 makalesi gibi görünmesidir.

| Güçlendirme kararı                                  | Ana dosyada uygulanacak karşılığı                                                                              | Q1 açısından gerekçe                                            |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| AHE yalnızca adaptive weighting olarak sunulmayacak | Dominance + cooperation + suppression birlikte formüle edilecek                                                | En güçlü hakem eleştirisini önler                               |
| Katkılar 3–4 maddeyle sınırlandırılacak             | AHE formülasyonu, communication-efficient mimari, event-triggered replanning, deneysel doğrulama               | Makaleyi proje raporu olmaktan çıkarır                          |
| Travel distance ana başarı metriği yapılmayacak     | Robustness, workload balance, failure recovery, allocation instability ve dominance evolution öne çıkarılacak  | AHE'nin gerçek avantajını doğru metriklerle gösterir            |
| Ablation zorunlu olacak                             | `ahe_no_dominance`, `ahe_no_cooperation_suppression`, `ahe_no_event_replanning`, opsiyonel `ahe_fixed_context` | Bileşen katkılarını izole eder                                  |
| Fixed-weight kontrol mutlaka çalıştırılacak         | Full AHE ile aynı seed, görev ve failure setinde karşılaştırılacak                                             | “Sadece ağırlık değiştirme” eleştirisini test eder              |
| Dominance evolution ana figür olacak                | Failure, critical task arrival ve deadline pressure event marker'larıyla çizilecek                             | Açıklanabilir adaptasyon iddiasını görünür kılar                |
| Deney ölçeği kontrollü kalacak                      | 3/15 debug, 5/25 ana deney, 3/15→5/25 kısa ölçek kontrolü                                                      | Fazla robot sayısı yerine temiz deney ve istatistik gücü sağlar |
| Ana çıktı formatı sabitlenecek                      | 6 ana figür, 3 ana tablo, 4 supplementary istatistik tablosu                                                   | RA-L/Q1 formatında okunabilirlik sağlar                         |

Nihai makalenin ana cümlesi şu doğrultuda kurulmalıdır:

```text
AHE-MRTA is an explainable, lightweight, communication-efficient adaptive heuristic ecosystem for robust online MRTA under dynamic tasks, failures, deadlines and congestion.
```

Çalışma şu şekilde sunulmamalıdır:

```text
Büyük ölçekli swarm benchmark çalışması
Yeni bir tekil heuristic algoritması
RL/MARL alternatifi
Tam dağıtık auction/CBBA sistemi
Genel amaçlı optimizasyon paketi
```

---

# 2. Problem Tanımı ve RA-L Uyumlu Formülasyon

## 2.1. Problem sınıfı

Bu çalışma, çevrim içi ve dinamik görev oluşumuna sahip çoklu robot görev atama problemini ele alır.

Problem, Gerkey ve Matarić taksonomisi açısından temel olarak şu karaktere sahiptir:

```text
Single-task robots
Single-robot tasks
Time-extended assignment
Online dynamic task arrival
```

Kısaca problem sınıfı:

```text
ST-SR-TA Online MRTA
```

Bu çalışmada her robot aynı anda yalnızca bir görevi yürütür. Her görev tek robot tarafından tamamlanabilir. Ancak görev sayısı robot sayısından fazladır ve görevler zaman içinde aktifleşebilir.

## 2.2. Küme ve değişken tanımları

Robot kümesi:

```text
R = {r_1, r_2, ..., r_N}
```

Görev kümesi:

```text
T(t) = {τ_1, τ_2, ..., τ_M(t)}
```

Her görev şu bileşenlerle tanımlanır:

```text
τ_j = {p_j, q_j, a_j, d_j, s_j, c_j}
```

Burada:

```text
p_j = görevin konumu
q_j = görev öncelik seviyesi
a_j = görevin aktifleşme zamanı
 d_j = deadline
 s_j = servis süresi
 c_j = kritik görev etiketi
```

Her robot şu durum vektörü ile temsil edilir:

```text
x_i(t) = {pose_i(t), availability_i(t), battery_i(t), nav_i(t), reliability_i(t), workload_i(t)}
```

## 2.3. Karar değişkeni

Görev atama değişkeni:

```text
x_ij(t) = 1, eğer τ_j görevi r_i robotuna atanırsa
x_ij(t) = 0, aksi halde
```

Her robot için görev sırası:

```text
Q_i(t) = [τ_a, τ_b, τ_c, ...]
```

## 2.4. Çok amaçlı maliyet fonksiyonu

Robot-görev çifti için temel maliyet:

```text
Cost(r_i, τ_j, t) =
 w_d(t) · D_ij(t)
+ w_p(t) · P_j(t)
+ w_b(t) · B_i(t)
+ w_l(t) · L_i(t)
+ w_f(t) · F_i(t)
+ w_t(t) · T_j(t)
+ w_r(t) · R_ij(t)
```

Burada:

```text
D_ij(t) = robot ile görev arasındaki tahmini mesafe veya Nav2 path cost
P_j(t) = görev öncelik cezası
B_i(t) = robotun batarya risk skoru
L_i(t) = robotun mevcut iş yükü cezası
F_i(t) = robotun hata veya güvenilirlik riski
T_j(t) = deadline gecikme riski
R_ij(t) = yeniden atama veya recovery maliyeti
```

Ağırlık vektörü:

```text
W(t) = [w_d, w_p, w_b, w_l, w_f, w_t, w_r]
```

AHE-MRTA'nın temel farkı, `W(t)` vektörünün sabit olmamasıdır. Bu vektör ekosistem mekanizması tarafından çevrim içi güncellenir.

## 2.5. Optimizasyon hedefi

Amaç, aktif görevlerin robotlara atanması ve her robot için yürütülebilir görev kuyruğunun üretilmesidir.

```text
minimize Σ_i Σ_j x_ij(t) · Cost(r_i, τ_j, t)
```

Ek olarak sistem düzeyinde şu hedefler izlenir:

```text
maximize task_completion_rate
minimize average_task_delay
minimize deadline_violation_rate
minimize total_travel_distance
minimize workload_imbalance
minimize failure_recovery_time
minimize allocation_instability
minimize mean_decision_latency
```

## 2.6. Temel kısıtlar

Her aktif görev en fazla bir robota atanmalıdır:

```text
Σ_i x_ij(t) ≤ 1
```

Uygun olmayan robotlara görev atanmaz:

```text
x_ij(t) = 0 if availability_i(t) = unavailable
```

Kritik batarya durumundaki robotlara yeni görev atanmaz:

```text
x_ij(t) = 0 if battery_i(t) = critical
```

Başarısız veya erişilemez görevlere yeniden atama yapılabilir:

```text
if failed(τ_j) = true then τ_j ∈ T_replan(t)
```

Her robot kendisine gönderilen görev kuyruğunu sırayla yürütür:

```text
Q_i(t) = ordered_tasks_assigned_to_robot_i
```

---

# 3. AHE-MRTA'nın Yenilik Analizi

## 3.1. Mevcut literatürdeki yakın yaklaşımlar

AHE-MRTA aşağıdaki literatür aileleriyle ilişkilidir:

- greedy ve nearest-task assignment
- priority-aware task allocation
- deadline-aware scheduling
- load-balancing MRTA
- energy-aware MRTA
- reliability-aware MRTA
- auction-based MRTA
- CBBA ve market-based allocation
- adaptive veya self-adaptive online allocation
- failure-aware dynamic reallocation
- learning-assisted MRTA

## 3.2. AHE-MRTA'nın bunlardan farkı

| Literatür ailesi           | Tipik yaklaşım                                | AHE-MRTA'nın farkı                                                                                                   |
| -------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Greedy assignment          | En yakın veya en düşük maliyetli görevi seçer | Greedy davranış yalnızca bir strategy agent olarak kullanılır ve baskınlığı bağlama göre değişir                     |
| Fixed-weight assignment    | Sabit ağırlıklı maliyet fonksiyonu kullanır   | Ağırlıklar dominance, cooperation, suppression ve bağlam uyumu üzerinden çevrim içi evrilir                          |
| Auction-based MRTA         | Robotlar görevler için teklif verir           | AHE teklif mekanizması değil, heuristic davranışların ekolojik etkileşimini yönetir                                  |
| CBBA / bundle methods      | Robotlar görev demetleri oluşturur            | AHE düşük veri merkezli bir strateji evrimi katmanı sunar ve heuristic davranışları açıklanabilir tutar              |
| Failure-aware reallocation | Arıza sonrası yeniden atama yapar             | Recovery yalnızca tetikleyici değil, ekosistemde bir strategy agent olarak diğer heuristic'lerle etkileşir           |
| Learning-based MRTA        | Politika öğrenimi veya RL kullanır            | AHE daha hafif, açıklanabilir ve gerçek zamanlı uygulanabilir bir heuristic ecosystem kullanır                       |
| Hyper-heuristic methods    | Heuristic seçimi veya heuristic üretimi yapar | AHE tek bir heuristic seçmek yerine heuristic katkılarını birlikte evrimleştirir ve maliyet ağırlıklarına dönüştürür |

## 3.3. Yenilik iddiasının güçlü formu

Bu çalışma şu şekilde konumlandırılmalıdır:

```text
AHE-MRTA is not a new single heuristic.
AHE-MRTA is an adaptive coordination framework that models existing MRTA heuristics as interacting ecological strategy agents.
```

Yenilik üç seviyede savunulmalıdır:

### Seviye 1: Algoritmik yenilik

Heuristic dominance, cooperation ve suppression terimleriyle görev dağıtım ağırlıkları çevrim içi güncellenir.

### Seviye 2: Mimari yenilik

Robotlara yalnızca görev kuyruğu gönderilir. Heuristic ecosystem state merkezde kalır. Bu, düşük veri paylaşımlı bir execution architecture üretir.

### Seviye 3: Deneysel yenilik

Yöntem yalnızca görev tamamlama oranıyla değil, heuristic dominance evolution, allocation instability, failure recovery time ve communication footprint ile değerlendirilir.

## 3.4. Yenilik riskleri ve güçlendirme önerileri

| Risk                                            | Hakem yorumu                                       | Düzeltme                                                                                                                            |
| ----------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Ekosistem metaforu soyut kalabilir              | “This is just adaptive weighting”                  | Dominance, cooperation, suppression matrisleri matematiksel olarak tanımlanmalı                                                     |
| Baseline karşılaştırması zayıf kalabilir        | “The comparison is not sufficient”                 | Seçilmiş baseline seti ve AHE ablation deneyleri aynı seed setiyle yürütülmeli; baseline ayrıntıları ek yöntem dosyasında tutulmalı |
| ROS/Gazebo uygulaması demo gibi görünebilir     | “This is a simulation-only prototype”              | Ölçeklenebilirlik, failure, congestion ve event-triggered replanning ölçülmeli                                                      |
| AHE'nin katkısı izole edilemeyebilir            | “It is unclear which component contributes”        | AHE without dominance, AHE without cooperation/suppression ve no event-triggered replanning ablation'ları eklenmeli                 |
| Geniş ölçek deneyleri deney süresini uzatabilir | “The evaluation may become unstable or too costly” | Ana sonuçlar 5 robot / 25 hedefte verilmeli; yalnızca kısa 3/15→5/25 ölçek kontrolü opsiyonel tutulmalıdır                          |

Q1/RA-L için bu risklerin en önemlisi ilk satırdır. Bu nedenle implementation ve makale yazımı boyunca aşağıdaki kural korunmalıdır:

```text
AHE-MRTA = dynamic weighting değildir.
AHE-MRTA = dominance + cooperation + suppression + context compatibility ile evrilen heuristic interaction layer'dır.
```

Bu fark yalnızca metinde değil, ablation sonuçlarında da gösterilmelidir. Full AHE'nin özellikle mixed stress, robot failure ve deadline pressure koşullarında `ahe_no_cooperation_suppression` ve fixed-weight yaklaşımlardan daha kararlı sonuç vermesi beklenir.

## 3.5. 2023 sonrası literatürle konumlandırma stratejisi

Nihai makale öncesinde 2023 sonrası MRTA literatürü ayrıca taranmalıdır. Bu tarama, yalnızca kaynak sayısını artırmak için değil, AHE-MRTA'nın hangi çizgiden ayrıldığını göstermek için kullanılmalıdır.

Güncel literatür genel olarak şu hatlarda ilerlemektedir:

| 2023 sonrası literatür hattı         | Tipik güçlü taraf                                           | AHE-MRTA'nın konumlandırması                                                                      |
| ------------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| SMT / solver-based dynamic MRTA      | Soundness, completeness, deadline ve constraint garantileri | AHE garanti odaklı solver değil, gerçek zamanlı ve hafif heuristic ecosystem katmanıdır           |
| Auction / market-based online MRTA   | Dağıtık karar ve teklif mekanizmaları                       | AHE bidding tasarımı değil, heuristic davranışların bağlam içi evrimidir                          |
| RL / MARL / GNN-based allocation     | Karmaşık ilişki öğrenme, policy generalization              | AHE daha açıklanabilir, düşük veri gerektiren ve daha kolay ROS 2 uygulanabilir bir yaklaşımdır   |
| Dynamic scheduling / warehouse MRTA  | Gerçek zamanlı görev akışı ve throughput optimizasyonu      | AHE özellikle failure, congestion, workload balance ve düşük iletişim yüküyle ayrışır             |
| Fault-tolerant / recovery-aware MRTA | Arıza sonrası yeniden atama                                 | AHE'de recovery yalnızca ayrı bir modül değil, diğer heuristic'lerle etkileşen strategy agent'tır |

Nihai makalede literatür boşluğu şu şekilde kurulmalıdır:

```text
Recent MRTA methods increasingly address dynamic task arrival, deadlines, learning-based scheduling, and solver-based guarantees. However, many approaches either rely on fixed cost designs, bidding structures, computationally demanding solvers, or data-intensive learning policies. AHE-MRTA targets a different gap: an explainable, lightweight, context-adaptive heuristic interaction layer that can be integrated with ROS 2/Nav2 and evaluated under failures, congestion, deadlines, and dynamic task arrivals.
```

## 3.6. Kabul edilebilir yenilik için minimum kanıt koşulları

RA-L/Q1 seviyesinde yenilik iddiası yalnızca metinle savunulamaz. Aşağıdaki deneysel kanıtlar zorunludur:

| Kanıt                                | Beklenen gösterim                                                                      | Neden gerekli?                                 |
| ------------------------------------ | -------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Fixed-weight kontrol karşılaştırması | Full AHE daha düşük delay, daha iyi workload balance veya daha hızlı recovery üretmeli | “Sadece adaptive weighting” eleştirisini önler |
| AHE without dominance                | Full AHE daha kararlı ve bağlama duyarlı olmalı                                        | Dominance update katkısını izole eder          |
| AHE without cooperation/suppression  | Full AHE özellikle mixed stress ve failure senaryosunda daha iyi olmalı                | Ekolojik etkileşimin gerçek katkısını gösterir |
| No event-triggered replanning        | Full AHE daha az instability ve daha iyi recovery göstermeli                           | Replanning mekanizmasını savunur               |
| Dominance evolution grafiği          | Heuristic baskınlıkları senaryoya göre anlamlı değişmeli                               | Açıklanabilir adaptasyon iddiasını destekler   |

Minimum kabul koşulu şu şekilde belirlenmelidir:

```text
Eğer Full AHE, fixed-weight baseline ve en az iki temel ablation varyantı karşısında
workload balance, failure recovery, allocation instability veya stress altındaki average delay
metriklerinden hiçbirinde anlamlı avantaj üretmiyorsa, Q1 yenilik iddiası zayıflar.
```

Bu nedenle sonuçlar her metrikte en iyi olma iddiasıyla değil, stres altında daha dengeli ve açıklanabilir adaptasyon üretme iddiasıyla yorumlanmalıdır.

## 3.7. Başarısız sonuç riskine karşı yorum stratejisi

AHE-MRTA her metrikte en iyi çıkmak zorunda değildir. RA-L için daha gerçekçi ve savunulabilir iddia şudur:

```text
AHE-MRTA does not necessarily minimize travel distance in every scenario. Its main advantage is robust online adaptation under stress, reflected in improved workload balance, lower allocation instability, faster failure recovery, and interpretable dominance evolution.
```

Bu nedenle travel distance tek başına ana başarı metriği yapılmamalıdır. AHE'nin güçlü görünmesi beklenen metrikler şunlardır:

```text
workload_balance
failure_recovery_time
allocation_instability
average_task_delay under stress
replanning_frequency stability
heuristic_dominance_evolution
```

---

# 4. Adaptive Heuristic Ecosystem Mekanizması

## 4.1. Strategy agent kavramı

AHE-MRTA'da her heuristic bağımsız bir nihai solver değildir. Her heuristic, görev dağıtım maliyet fonksiyonuna katkı yapan bir strategy agent olarak modellenir.

Kullanılacak strategy agent seti:

```text
H = {h_1, h_2, ..., h_K}
```

Önerilen ilk set:

```text
h_1 = Spatial Opportunist        → nearest-task behavior
h_2 = Criticality Guardian       → priority-aware behavior
h_3 = Temporal Regulator         → deadline-aware behavior
h_4 = Resource Distributor       → load-balancing behavior
h_5 = Energy Conservator         → battery-aware behavior
h_6 = Stability Controller       → reliability-aware behavior
h_7 = Recovery Coordinator       → failure-recovery behavior
```

## 4.2. Strategy agent ve literatür karşılıkları

| AHE Strategy Agent   | Literatürdeki karşılığı                             | Ana rol                                 | Kullanıldığı bağlam                 |
| -------------------- | --------------------------------------------------- | --------------------------------------- | ----------------------------------- |
| Spatial Opportunist  | Nearest-neighbor / greedy assignment                | Mesafeyi azaltmak                       | Normal görev yoğunluğu              |
| Criticality Guardian | Priority-based allocation                           | Kritik görevleri öne almak              | Yüksek öncelikli görevler           |
| Temporal Regulator   | Earliest Deadline First / deadline-aware scheduling | Deadline ihlalini azaltmak              | Zaman baskısı                       |
| Resource Distributor | Load-balancing allocation                           | Robotlar arası yükü dengelemek          | Yüksek görev yoğunluğu              |
| Energy Conservator   | Energy-aware / battery-aware allocation             | Batarya riskini azaltmak                | Düşük batarya                       |
| Stability Controller | Reliability-aware allocation                        | Güvenilir robotlara kritik görev vermek | Navigasyon başarısızlığı            |
| Recovery Coordinator | Failure recovery / dynamic reallocation             | Başarısız görevleri yeniden dağıtmak    | Robot arızası veya hedefe ulaşamama |

## 4.3. Context vector

Ecosystem Manager her allocation turunda bağlam vektörünü hesaplar:

```text
C_t = [
  task_density,
  robot_availability,
  battery_risk,
  deadline_pressure,
  failure_rate,
  workload_variance,
  allocation_instability
]
```

Her bileşen sayısallaştırılmalıdır:

```text
task_density = active_task_count / robot_count
robot_availability = available_robot_count / robot_count
battery_risk = low_or_critical_battery_robot_count / robot_count
deadline_pressure = near_deadline_task_count / active_task_count
failure_rate = failed_or_stuck_robot_count / robot_count
workload_variance = variance(queue_length_per_robot)
allocation_instability = reassigned_task_count / active_task_count
```

Bu tanımlar makalede mutlaka verilmelidir. Aksi hâlde AHE bağlam uyumu soyut görünür.

## 4.4. Dominance state

Her heuristic için bir dominance skoru tutulur:

```text
D_i(t) ∈ [0, 1]
```

Dominance vektörü:

```text
D(t) = [D_1(t), D_2(t), ..., D_K(t)]
```

Başlangıçta tüm heuristic'ler eşit başlatılabilir:

```text
D_i(0) = 1 / K
```

## 4.5. Performans katkısı

Her heuristic için performans katkısı şu metriklerden türetilebilir:

```text
P_i(t) =
  ρ_1 · normalized_task_completion_gain
- ρ_2 · normalized_delay_penalty
- ρ_3 · normalized_travel_cost
- ρ_4 · normalized_replan_penalty
- ρ_5 · normalized_failure_penalty
```

Basit MVP için daha hafif versiyon kullanılabilir:

```text
P_i(t) = completed_task_gain - delay_penalty - replan_penalty - failure_penalty
```

## 4.6. Context compatibility

Her heuristic'in mevcut bağlama uyumu:

```text
K_i(C_t) = similarity(v_i, C_t)
```

Burada `v_i`, heuristic'in hangi bağlamlarda etkili olduğunu tanımlayan prototip vektördür.

Örnek:

```text
Spatial Opportunist:
  high compatibility when task_density is moderate and failure_rate is low

Resource Distributor:
  high compatibility when workload_variance and task_density are high

Recovery Coordinator:
  high compatibility when failure_rate and allocation_instability are high
```

## 4.7. Cooperation ve suppression matrisleri

Cooperation matrix:

```text
A ∈ R^{K×K}
```

Suppression matrix:

```text
S ∈ R^{K×K}
```

`A_ij > 0` ise `h_j`, `h_i` heuristic'ini güçlendirir.

`S_ij > 0` ise `h_j`, `h_i` heuristic'ini baskılar.

Örnek işbirliği ilişkileri:

```text
A_EnergyConservator,RecoveryCoordinator > 0
A_CriticalityGuardian,TemporalRegulator > 0
A_StabilityController,RecoveryCoordinator > 0
A_SpatialOpportunist,ResourceDistributor > 0
```

Örnek baskılama ilişkileri:

```text
S_SpatialOpportunist,TemporalRegulator > 0 when deadline_pressure is high
S_SpatialOpportunist,EnergyConservator > 0 when battery_risk is high
S_ResourceDistributor,CriticalityGuardian > 0 when critical_task_count is high
```

## 4.8. Revize dominance update denklemi

Önerilen tam güncelleme:

```text
D_i(t+1) = clip[
  αD_i(t)
+ βP_i(t)
+ γK_i(C_t)
+ ηΣ_j A_ijD_j(t)
- λΣ_j S_ijD_j(t)
- δF_i(t)
]
```

Burada:

```text
α = geçmiş dominance hafızası
β = performans katkısı katsayısı
γ = bağlam uyumluluğu katsayısı
η = cooperation etkisi
λ = suppression etkisi
δ = failure penalty etkisi
F_i(t) = heuristic kaynaklı başarısızlık veya gecikme cezası
```

`clip` işlemi dominance değerlerini `[0, 1]` aralığında tutar.

Normalize edilmiş dominance:

```text
D_i(t+1) = D_i(t+1) / Σ_k D_k(t+1)
```

## 4.9. Dominance'tan allocation weights üretimi

Heuristic dominance değerleri doğrudan robotlara gönderilmez. Bunlar yalnızca merkezi Ecosystem Manager içinde allocation weights üretmek için kullanılır.

Heuristic-to-weight mapping matrisi:

```text
M ∈ R^{7×7}
```

Allocation weight üretimi:

```text
W(t) = softmax(M · D(t))
```

Burada:

```text
W(t) = [w_d, w_p, w_b, w_l, w_f, w_t, w_r]
```

Bu yapı AHE'yi fixed-weight assignment'tan ayırır.

Fixed-weight assignment:

```text
W(t) = W_0
```

AHE-MRTA:

```text
W(t) = softmax(M · D(t))
D(t+1) = f(D(t), P(t), C_t, A, S, F(t))
```

## 4.10. MVP için sadeleştirilmiş AHE

İlk çalışan sistemde tam matris yapısı kurulmak zorunda değildir. MVP için şu basit ama savunulabilir versiyon kullanılabilir:

```text
1. Context vector hesapla
2. Her heuristic için context compatibility hesapla
3. Son allocation turundaki performans katkısını güncelle
4. Dominance değerlerini normalize et
5. Allocation weights üret
6. Task Allocator'a gönder
```

MVP sonrasında cooperation ve suppression matrisleri eklenmelidir. RA-L makalesi için ise tam AHE versiyonu kullanılmalıdır.

---

# 5. Görev Dağıtım Mekanizması

## 5.1. İki katmanlı yapı

AHE-MRTA görev dağıtımını iki katmanda yürütür:

```text
Global task-to-robot allocation
        ↓
Robot-level task sequence optimization
```

## 5.2. Katman 1: Global task-to-robot allocation

Her aktif görev için robot bazlı maliyet hesaplanır. AHE tarafından üretilen `W(t)` ağırlıkları kullanılır.

```text
Cost(r_i, τ_j, t) =
 w_d(t) · D_ij(t)
+ w_p(t) · P_j(t)
+ w_b(t) · B_i(t)
+ w_l(t) · L_i(t)
+ w_f(t) · F_i(t)
+ w_t(t) · T_j(t)
+ w_r(t) · R_ij(t)
```

Görevler robotlara atanırken minimum maliyet seçimi yapılır. Ancak robot başına görev sayısı ve workload balance cezası dikkate alınır.

## 5.3. Katman 2: Robot-level task sequence optimization

Her robotun görev kümesi için optimize edilmiş ziyaret sırası oluşturulur.

İlk MVP için önerilen yöntem:

```text
Adaptive insertion heuristic
```

Bu yöntem şu nedenle uygundur:

- gerçek zamanlı çalışabilir
- ROS 2 içinde hızlı uygulanır
- görev ekleme ve yeniden planlama için esnektir
- ağır VRP solver gerektirmez
- RA-L için açıklanabilir kalır

## 5.4. Hungarian baseline için özel not

Hungarian Assignment yalnızca bire bir eşleştirme için uygundur. Bu çalışmada robot başına birden fazla görev bulunduğundan Hungarian baseline doğrudan ana yöntem gibi kullanılmamalıdır.

Kullanılacaksa şu şekilde tanımlanmalıdır:

```text
Repeated Hungarian Assignment + local insertion ordering
```

Ancak RA-L ana karşılaştırma setinde Hungarian zorunlu değildir. Karşılaştırma yöntemlerinin nihai listesi ve uygulama ayrıntıları ana dosyada tekrarlanmamalı; `ahe_mrta_recent_comparison_methods.md` içinde yönetilmelidir.

---

# 6. ROS 2 ve Gazebo Uygulama Mimarisi

## 6.1. Ana yazılım yığını

```text
Ubuntu 24.04 LTS
ROS 2 Jazzy
Gazebo Harmonic
ros_gz integration
TurtleBot3 Waffle Pi
Nav2
Python 3.12
rclpy
rosbag2
pandas
matplotlib
```

## 6.2. Önemli teknik uyarı

ROS 2 Jazzy ve Gazebo Harmonic için Gazebo Classic varsayımlarından kaçınılmalıdır.

Claude Code'a açıkça şu talimat verilmelidir:

```text
Use ros_gz-compatible Gazebo Harmonic integration. Do not assume Gazebo Classic gazebo_ros_pkgs APIs unless explicitly required by a compatible TurtleBot3 package.
```

## 6.3. Workspace yapısı

```text
multi_ahe/
├── src/
│   ├── m_ahe_mrta_bringup/
│   ├── m_ahe_mrta_msgs/
│   ├── m_ahe_mrta_gazebo/
│   ├── m_ahe_task_manager/
│   ├── m_ahe_robot_interface/
│   ├── m_ahe_ecosystem_manager/
│   ├── m_ahe_task_allocator/
│   ├── m_ahe_recovery_manager/
│   ├── m_ahe_evaluation/
│   └── m_ahe_nav2_config/
├── logs/
├── results/
├── scripts/
└── README.md
```

## 6.4. Paket görevleri

| Paket                   | Görev                                                                  |
| ----------------------- | ---------------------------------------------------------------------- |
| `ahe_mrta_bringup`      | Sistemi başlatan launch dosyaları                                      |
| `ahe_mrta_msgs`         | Custom ROS 2 mesajları                                                 |
| `ahe_mrta_gazebo`       | World, robot spawn, target marker modelleri                            |
| `ahe_task_manager`      | Görev havuzu, görev aktifleşmesi ve durum güncellemesi                 |
| `ahe_robot_interface`   | Robot status summary, task queue listener, Nav2 action interface       |
| `ahe_ecosystem_manager` | Context vector, dominance, cooperation, suppression, weight generation |
| `ahe_task_allocator`    | Maliyet matrisi, görev atama, görev sırası optimizasyonu               |
| `ahe_recovery_manager`  | Arıza, erişilemez hedef, delay ve replanning tetikleme                 |
| `ahe_evaluation`        | Rosbag, CSV, metrik hesaplama, grafik ve rapor üretimi                 |
| `ahe_nav2_config`       | Robot bazlı Nav2 parametreleri                                         |

## 6.5. Launch dosyaları

```text
ahe_mrta_bringup/launch/
├── phase1_test_messages.launch.py
├── single_robot_gazebo.launch.py
├── multi_robot_gazebo.launch.py
├── multi_robot_nav2.launch.py
├── ahe_system.launch.py
├── baseline_experiment.launch.py
└── full_demo.launch.py
```

## 6.6. Custom mesajlar

### TaskWaypoint.msg

```text
string task_id
geometry_msgs/PoseStamped target_pose
uint8 priority_level
float32 expected_arrival_time
float32 service_time
float32 local_cost
bool is_critical
bool allow_skip
```

### OptimizedTaskQueue.msg

```text
std_msgs/Header header
string robot_id
uint32 queue_version
TaskWaypoint[] waypoints
string execution_mode
float32 queue_cost
bool replan_required
```

### RobotStatusSummary.msg

```text
std_msgs/Header header
string robot_id
geometry_msgs/PoseStamped current_pose
string current_task_id
uint8 availability_state
uint8 battery_state
uint8 navigation_state
bool failure_flag
bool task_completed
string completed_task_id
```

Kodlama:

```text
availability_state:
0 = available
1 = busy
2 = unavailable

battery_state:
0 = normal
1 = low
2 = critical

navigation_state:
0 = idle
1 = navigating
2 = stuck
3 = failed
4 = reached
```

### LocalExecutionFeedback.msg

```text
std_msgs/Header header
string robot_id
string current_task_id
float32 task_progress
float32 local_delay
uint8 congestion_indicator
uint8 goal_reachability
float32 navigation_effort
bool temporary_failure
bool request_replan
```

Kodlama:

```text
congestion_indicator:
0 = none
1 = low
2 = medium
3 = high

goal_reachability:
0 = reachable
1 = uncertain
2 = unreachable
```

### TaskInfo.msg

```text
string task_id
geometry_msgs/PoseStamped target_pose
uint8 priority_level
float32 service_time
float32 deadline
bool active
bool completed
```

### TaskPool.msg

```text
std_msgs/Header header
TaskInfo[] tasks
uint32 pool_version
```

### AllocationEvent.msg

```text
std_msgs/Header header
string event_type
string robot_id
string task_id
uint8 severity
bool trigger_replan
```

### EcosystemState.msg

Bu mesaj robotlara yayınlanmamalıdır. Yalnızca debug ve offline analiz için kullanılmalıdır.

```text
std_msgs/Header header
float32[] dominance_values
float32[] cooperation_values
float32[] suppression_values
float32[] context_vector
string[] heuristic_names
float32[] allocation_weights
```

---

# 7. Düşük Veri Paylaşımlı Haberleşme Mimarisi

## 7.1. Temel ilke

Robotlara yalnızca kendi yürütmeleri için gerekli veri gönderilir. Global ekosistem durumu, tüm görev-robot maliyet matrisi ve diğer robotların görev kuyrukları robotlara yayınlanmaz.

Robotlara gönderilmeyecek bilgiler:

```text
heuristic dominance değerleri
cooperation matrix
suppression matrix
global context vector
tüm görev-robot maliyet matrisi
diğer robotların tam görev kuyrukları
ekolojik performans hafızası
```

## 7.2. Topic tablosu

| Topic                               | Yayınlayan                           | Dinleyen                             | Veri düzeyi | Amaç                                                            |
| ----------------------------------- | ------------------------------------ | ------------------------------------ | ----------- | --------------------------------------------------------------- |
| `/robot_i/status_summary`           | Robot i                              | Ecosystem Manager                    | Düşük       | Robotun uygunluk, görev ve hata durumunu bildirme               |
| `/robot_i/optimized_task_queue`     | Task Allocator                       | Robot i                              | Düşük       | Robotun optimize edilmiş hedef ziyaret sırasını gönderme        |
| `/robot_i/local_execution_feedback` | Robot i                              | Ecosystem Manager / Recovery Manager | Düşük       | Lokal gecikme, congestion ve erişilebilirlik bilgisini gönderme |
| `/robot_i/task_feedback`            | Robot i                              | Task Manager / Evaluation            | Düşük       | Görev tamamlandı veya başarısız oldu bilgisini gönderme         |
| `/tasks/global_pool`                | Task Manager                         | Ecosystem Manager / Allocator        | Orta        | Aktif görev havuzunu sağlama                                    |
| `/allocation/events`                | Ecosystem Manager / Recovery Manager | Allocator                            | Düşük       | Yeniden atama, arıza veya kritik görev olaylarını bildirme      |
| `/system/replan_trigger`            | Recovery Manager                     | Task Allocator                       | Düşük       | Olay tabanlı yeniden planlama tetikleme                         |
| `/ecosystem/debug_state`            | Ecosystem Manager                    | Evaluation only                      | Debug       | Heuristic state kaydı                                           |
| `/metrics/log`                      | Evaluation Logger                    | CSV / results                        | Düşük       | Deney metriklerini kaydetme                                     |

---

# 8. Gazebo Senaryo Kurgusu

## 8.1. Başlangıç ortamı

İlk ortam karmaşık iç mekân inspection ortamı olmalıdır.

Ortam özellikleri:

```text
merkez açık alan
sol dar koridor
sağ dar koridor
üst inspection bölgesi
alt inspection bölgesi
U şekilli engeller
robot başlangıç alanı
hedef marker bölgeleri
congestion bölgeleri
```

## 8.2. MVP ölçeği

```text
robot_count = 3
target_count = 15
```

Bu ölçek geliştirme ve debug için uygundur.

## 8.3. Makale ölçekleri

Robot ölçeğini gereksiz büyütmek deney süresini uzatacağı için ana makale deneyleri kompakt tutulmalıdır.

Debug/MVP ölçeği:

```text
robot_count = 3, target_count = 15
```

Ana makale ölçeği:

```text
robot_count = 5, target_count = 25
```

Opsiyonel kısa ölçek kontrolü:

```text
3 robot / 15 hedef  →  5 robot / 25 hedef
```

10 robot / 50 hedef ve 15 robot / 75 hedef bu sürümde zorunlu değildir. Bu deneyler yalnızca zaman ve donanım yeterliyse supplementary stress-test olarak eklenebilir; ana iddia bu büyük ölçeklere dayandırılmamalıdır.

## 8.4. Kompakt ölçek için teknik önlemler

```text
headless Gazebo önerilir
seçici rosbag topic kaydı yapılır
odom topic'i gerekirse seyreltilir
Nav2 parametreleri tüm yöntemlerde aynı tutulur
aynı seed, görev havuzu ve failure event seti kullanılır
```

---

# 9. Event-Triggered Replanning

## 9.1. Neden sürekli replanning yapılmamalı?

Sürekli replanning sistemde allocation instability yaratır. Ayrıca CPU yükünü artırır ve görev kuyruklarının sık sık değişmesine neden olur. Bu nedenle AHE-MRTA'da replanning yalnızca olay bazlı tetiklenmelidir.

## 9.2. Replanning tetikleyicileri

```text
yeni kritik görev oluşması
robot arızası
robotun hedefe ulaşamaması
batarya durumunun kritik hale gelmesi
dar koridor kaynaklı geçiş gecikmesinin artması
deadline riskinin artması
görev kuyruğunun geçersiz hale gelmesi
allocation_instability değerinin eşik üstüne çıkması
```

## 9.3. Replanning çıktısı

Replanning çıktısı yeni bir `OptimizedTaskQueue` mesajıdır.

```text
/robot_i/optimized_task_queue
```

Her yeni kuyruk `queue_version` ile işaretlenmelidir. Böylece deney sonrası allocation instability ölçülebilir.

---

# 10. Deney Tasarımı

## 10.1. Ana senaryolar

RA-L kısa formatı için senaryo sayısı sınırlı tutulmalıdır. Ana makalede en fazla beş ana senaryo kullanılmalıdır. Ek senaryolar repository veya ek deney raporunda verilebilir.

Ana senaryo seti:

| Senaryo               | Amaç                                                                             | RA-L açısından rolü                                                    |
| --------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Dynamic Task Arrival  | Çevrim içi görev oluşumu altında temel performans                                | Online MRTA iddiasını test eder                                        |
| High Task Density     | Yoğun görev baskısı altında load-balancing davranışı                             | Resource Distributor katkısını test eder                               |
| Deadline Pressure     | Deadline ihlali ve zaman baskısı davranışı                                       | Temporal Regulator katkısını test eder                                 |
| Robot Failure         | Arıza sonrası recovery ve yeniden atama                                          | Recovery Coordinator ve event-triggered replanning katkısını test eder |
| Mixed Stress Scenario | Görev yoğunluğu, deadline, congestion, batarya riski ve arızanın birlikte etkisi | Full AHE'nin asıl farkını göstermesi beklenen senaryo                  |

Opsiyonel veya ek rapor senaryoları:

| Senaryo                          | Kullanım önerisi                                                                  |
| -------------------------------- | --------------------------------------------------------------------------------- |
| Corridor Congestion              | Mixed Stress içinde alt bileşen olarak veya ek deneyde kullanılabilir             |
| Battery-Constrained Operation    | Gerçek batarya modeli yoksa simulated battery state olarak açıkça belirtilmelidir |
| 15 Robot Scalability Stress Test | Ana performans iddiası değil, ölçeklenebilirlik/stress-test kanıtı olmalıdır      |

## 10.2. Karşılaştırılacak yöntemler

Karşılaştırma yöntemlerinin isimleri, bibliyografik bilgileri, matematiksel uyarlamaları, Python-style kod iskeletleri, ROS 2/Gazebo adaptasyon notları ve fairness koşulları bu ana dosyada tekrar edilmez. Bu ayrıntılar ayrı dosyada tutulur:

```text
ahe_mrta_recent_comparison_methods.md
```

Bu ana dosyanın görevi, karşılaştırma yöntemlerinin tek tek metodolojisini açıklamak değil, deney altyapısının nasıl yürütüleceğini tanımlamaktır. Böylece proje rehberi ikiye ayrılır:

```text
Ana proje dosyası:
  - AHE-MRTA formülasyonu
  - ROS 2/Gazebo mimarisi
  - deney senaryoları
  - çıktı dosyaları
  - grafik/tablo üretim pipeline'ı
  - Claude Code faz planı

Ek karşılaştırma yöntemleri dosyası:
  - seçilen baseline yöntemleri
  - yöntemlerin makale bilgileri
  - matematiksel formülasyon
  - algoritmik akış
  - adil uyarlama koşulları
  - Python-style kod iskeleti
  - Claude Code uygulama notları
```

### 10.2.1. Ana dosyada korunacak yöntem kapsamı

Ana dosyada yalnızca şu kapsam bilgisi korunur:

| Yöntem grubu                 | Ana dosyadaki rolü                                                        | Ayrıntılı tanım nerede?                 |
| ---------------------------- | ------------------------------------------------------------------------- | --------------------------------------- |
| Seçilmiş baseline yöntemleri | AHE-MRTA ile aynı deney altyapısında karşılaştırılacak referans yöntemler | `ahe_mrta_recent_comparison_methods.md` |
| Full AHE-MRTA                | Önerilen yöntem                                                           | Bu ana dosya                            |
| AHE ablation varyantları     | Önerilen yöntemin bileşen katkılarını izole etmek                         | Bu ana dosya                            |

### 10.2.2. AHE ablation seti

Ablation varyantları AHE-MRTA'nın kendi bileşenlerini test ettiği için ana dosyada tutulur.

| Ablation varyantı                      | Kısa ad                          | Test edilen katkı                  |
| -------------------------------------- | -------------------------------- | ---------------------------------- |
| AHE without dominance                  | `ahe_no_dominance`               | Dominance evolution katkısı        |
| AHE without cooperation/suppression    | `ahe_no_cooperation_suppression` | Ekolojik etkileşim katkısı         |
| AHE without event-triggered replanning | `ahe_no_event_replanning`        | Replanning mekanizmasının katkısı  |
| AHE with fixed context compatibility   | `ahe_fixed_context`              | Context-adaptive weighting katkısı |

### 10.2.3. Kompakt deney matrisi

Robot ölçeğini gereksiz büyütmek deney süresini, Nav2/Gazebo kararlılık riskini ve log analiz yükünü artıracağı için ana makale deneyleri **kompakt tutulur**. Ana iddia 5 robot / 25 hedef ölçeğinde test edilir. 3 robot / 15 hedef yalnızca MVP ve debug ölçeği olarak kullanılır. 10 robot ve 15 robot deneyleri ana makale için zorunlu değildir; zaman kalırsa yalnızca kısa ek/stress analiz olarak yapılabilir.

| Deney grubu                      | Robot/hedef ölçeği                       | Yöntem kapsamı                                                             | Tekrar  | Zorunluluk                       |
| -------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------- | -------:| -------------------------------- |
| MVP/debug validation             | 3 robot / 15 hedef                       | Minimum baseline kontrolü + Full AHE                                       | 5 seed  | Zorunlu geliştirme kontrolü      |
| Main comparison                  | 5 robot / 25 hedef                       | Ek dosyada tanımlanan seçilmiş baseline seti + Full AHE                    | 20 seed | Ana makale sonucu                |
| Adaptive/robustness comparison   | 5 robot / 25 hedef                       | Ek dosyada tanımlanan adaptif/robustness odaklı baseline seti + Full AHE   | 20 seed | Adaptiflik ve robustness iddiası |
| Failure/recovery                 | 5 robot / 25 hedef                       | Ek dosyada tanımlanan failure/recovery için uygun baseline seti + Full AHE | 20 seed | Robustness iddiası               |
| Ablation                         | 5 robot / 25 hedef                       | Full AHE + 3 ana ablation                                                  | 20 seed | Yöntem bileşenlerini izole etme  |
| Compact scalability sanity check | 3 robot / 15 hedef ve 5 robot / 25 hedef | Ek dosyada tanımlanan seçilmiş küçük baseline seti + Full AHE              | 10 seed | Opsiyonel/kısa ek analiz         |

Bu yapı RA-L için daha kontrollüdür. Ana makale, çok geniş robot ölçeği yerine AHE-MRTA'nın üç temel iddiasını daha kısa ama daha sağlam deneylerle test eder:

```text
1. Online allocation quality
2. Adaptive robustness under failures and dynamic tasks
3. Communication-efficient execution
```

10 robot / 50 hedef ve 15 robot / 75 hedef deneyleri bu sürümde zorunlu değildir. Eğer zaman ve donanım yeterliyse yalnızca supplementary stress-test olarak eklenmelidir. Ana performans iddiası bu büyük ölçeklere dayandırılmamalıdır.

### 10.2.4. Senaryo-yöntem eşleştirmesi

Tüm yöntemleri tüm senaryolarda çalıştırmak yerine, her yöntemi en anlamlı olduğu senaryoda test etmek deney süresini azaltır ve sonuçların yorumlanmasını kolaylaştırır. Bu eşleştirme ana dosyada yöntem isimleriyle tekrarlanmaz; yöntem-senaryo eşleştirmesi ek dosyada tutulur.

| Senaryo                          | Ana dosyadaki kapsam                                                       | Gerekçe                                             |
| -------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------- |
| Dynamic Task Arrival             | Online görev oluşumuna uygun seçilmiş baseline seti + Full AHE             | Online MRTA iddiası                                 |
| Deadline Pressure                | Deadline-aware davranışı test edebilen seçilmiş baseline seti + Full AHE   | Deadline baskısı altında görev atama                |
| Robot Failure                    | Failure/recovery davranışı test edebilen seçilmiş baseline seti + Full AHE | Recovery Coordinator ve replanning katkısı          |
| Mixed Stress Scenario            | Stres altında karşılaştırmaya uygun seçilmiş baseline seti + Full AHE      | AHE'nin asıl farkını gösterecek ana stres senaryosu |
| Compact Scalability Sanity Check | 3/15 ve 5/25 ölçeklerinde seçilmiş küçük baseline seti + Full AHE          | Kısa ölçek etkisi kontrolü                          |

High Task Density ve Corridor Congestion ayrı ana senaryo olarak uzatılmak zorunda değildir. Bunlar **Mixed Stress Scenario** içine alt bileşen olarak gömülebilir. Böylece deney sayısı azaltılırken AHE'nin stres altındaki davranışı korunur.

### 10.2.5. Ek metrik notu

Karşılaştırma yöntemleri ayrı dosyada tutulduğu için yöntem-özel metrikler de o dosyada tanımlanmalıdır. Ana dosyada yalnızca tüm yöntemler için ortak loglanacak metrikler korunur:

```text
communication_footprint_bytes
allocation_message_count
mean_decision_latency
solver_or_allocator_runtime_ms
method_specific_failure_count
```

Yöntem-özel yorumlar, hangi baseline için hangi metriğin kritik olduğu ve adil karşılaştırma koşulları `ahe_mrta_recent_comparison_methods.md` içinde yönetilmelidir.

## 10.3. Tekrar sayısı ve seed planı

Deney süresini kontrol altında tutmak için seed planı iki düzeyli tutulmalıdır.

Debug aşaması:

```text
repeat_count = 5
seed_set = {1, 2, 3, 4, 5}
robot_count = 3
target_count = 15
```

Ana makale deneyleri:

```text
repeat_count = 20
seed_set = {1, 2, ..., 20}
robot_count = 5
target_count = 25
```

Opsiyonel compact scalability sanity check:

```text
repeat_count = 10
seed_set = {1, 2, ..., 10}
robot_count ∈ {3, 5}
target_count ∈ {15, 25}
```

Bu sürümde 10 ve 15 robotlu deneyler zorunlu değildir. Geniş ölçekli deneyler yapılacaksa yalnızca zaman kaldığında supplementary stress-test olarak ele alınmalıdır.

## 10.4. Ana metrikler

```text
task_completion_rate
average_task_delay
deadline_violation_rate
total_travel_distance
workload_balance
failure_recovery_time
replanning_frequency
mean_decision_latency
allocation_instability
communication_topic_count
rosbag_size
heuristic_dominance_evolution
```

## 10.5. Metrik tanımları

Görev tamamlama oranı:

```text
task_completion_rate = completed_task_count / activated_task_count
```

Ortalama görev gecikmesi:

```text
average_task_delay = mean(completion_time_j - activation_time_j)
```

Deadline ihlal oranı:

```text
deadline_violation_rate = violated_deadline_count / completed_task_count
```

Yük dengesi:

```text
workload_balance = 1 / (1 + variance(completed_tasks_per_robot))
```

Yeniden planlama sıklığı:

```text
replanning_frequency = replan_count / experiment_duration
```

Allocation instability:

```text
allocation_instability = reassigned_task_count / active_task_count
```

Failure recovery time:

```text
failure_recovery_time = time_of_successful_reassignment - time_of_failure_detection
```

Decision latency:

```text
mean_decision_latency = mean(allocation_end_time - allocation_start_time)
```

## 10.6. RA-L için başarı kriterleri

AHE-MRTA'nın kabul edilebilir deneysel iddiası şu şekilde kurulmalıdır:

| Metrik                        | Beklenen sonuç                                   | Yorum                                                  |
| ----------------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| task_completion_rate          | Full AHE en az baseline'larla eşit veya daha iyi | Temel görev başarısı korunmalı                         |
| average_task_delay            | Stress senaryolarında daha düşük                 | AHE'nin adaptasyon etkisi burada görünür               |
| workload_balance              | Full AHE daha iyi                                | Resource Distributor ve dominance etkisi               |
| failure_recovery_time         | Full AHE daha düşük                              | Recovery Coordinator katkısı                           |
| allocation_instability        | Full AHE daha düşük                              | Sürekli replanning yerine olay-tetiklemeli yapı etkisi |
| mean_decision_latency         | Kabul edilebilir düzeyde kalmalı                 | Gerçek zamanlı uygulanabilirlik için kritik            |
| heuristic_dominance_evolution | Senaryo değişimine anlamlı tepki vermeli         | Açıklanabilirlik iddiasını destekler                   |

Full AHE'nin travel distance metriğinde her zaman en iyi olması beklenmemelidir. Eğer travel distance biraz artarken recovery, workload balance ve delay iyileşiyorsa bu sonuç “robustness-performance trade-off” olarak yorumlanabilir.

### 10.6.1. Q1 için başarı anlatısı

Başarı anlatısı aşağıdaki öncelik sırasına göre kurulmalıdır:

```text
1. Task completion rate korunur.
2. Stress senaryolarında average task delay azalır.
3. Workload balance iyileşir.
4. Robot failure sonrası recovery time kısalır.
5. Allocation instability ve gereksiz replanning azalır.
6. Dominance evolution grafiği bağlama duyarlı değişimi açıklar.
7. Communication footprint düşük kalır.
```

Travel distance ve makespan sonuçları destekleyici metrik olarak kullanılmalıdır. AHE bazı koşullarda daha uzun rota seçerse bu, daha iyi deadline davranışı, recovery veya workload balance ile birlikte raporlanmalı ve `robustness-performance trade-off` olarak açıklanmalıdır.

## 10.7. İstatistiksel raporlama

Sonuçlar yalnızca ortalama ile verilmemelidir.

Önerilen raporlama:

```text
mean ± standard deviation
median
minimum-maximum aralığı
boxplot veya violin plot
confidence interval
```

Önerilen istatistiksel testler:

```text
Shapiro-Wilk normality test
ANOVA + Tukey if normality is satisfied
Kruskal-Wallis + Dunn if normality is not satisfied
Mann-Whitney U for pairwise non-parametric comparison
Cohen's d for effect size
Cliff's delta for non-parametric effect size
```

---

# 11. CSV-First Veri Arşivi, PNG ve Tablo Çıktı Sistemi

Bu bölüm, deneyler sonunda üretilecek tüm ham ve türetilmiş CSV dosyalarını, bu CSV dosyalarından üretilecek PNG figürleri ve RA-L/Q1 makale tablolarını tanımlar. Çıktı sistemi 3 robot sabit sütunlarına bağlı değildir; 3/15 debug ve 5/25 ana deney ölçeklerinde aynı şema çalışır.

Bu sürümde temel amaç yalnızca son metrikleri kaydetmek değil, deney sırasında oluşan ham olay verisini de yeniden kullanılabilir CSV dosyaları olarak arşivlemektir. Böylece ileride yeni grafik, yeni metrik, ek hakem analizi veya supplementary sonuç istendiğinde Gazebo deneylerinin yeniden çalıştırılmasına gerek kalmadan `processed/*.csv` dosyalarından yeni çıktılar üretilebilir.

Q1/RA-L için veri sistemi şu ilkeye dayanmalıdır:

```text
ROS/Gazebo run
      ↓
raw CSV per experiment
      ↓
processed merged CSV
      ↓
statistics
      ↓
PNG figures + manuscript tables
```

Bu nedenle grafikler doğrudan rosbag dosyalarından değil, CSV dosyalarından üretilmelidir. Rosbag kayıtları yalnızca hata ayıklama ve görsel doğrulama için opsiyonel destek çıktısı olarak tutulmalıdır.

Pipeline üç katmanlıdır:

```text
Katman 1 — Raw event logging / her deney koşusunda:
  results/raw/<experiment_id>/metadata.yaml
  results/raw/<experiment_id>/task_events.csv
  results/raw/<experiment_id>/robot_state_timeseries.csv
  results/raw/<experiment_id>/robot_workload.csv
  results/raw/<experiment_id>/allocation_events.csv
  results/raw/<experiment_id>/method_runtime.csv
  results/raw/<experiment_id>/communication_metrics.csv
  results/raw/<experiment_id>/ecosystem_metrics.csv      # yalnızca full_ahe_mrta ve AHE ablation için
  results/raw/<experiment_id>/summary.csv

Katman 2 — Processed / tüm deneyler bittikten sonra:
  scripts/consolidate_results.py → results/processed/all_summary.csv
                                 → results/processed/all_task_events.csv
                                 → results/processed/all_robot_state_timeseries.csv
                                 → results/processed/all_robot_workload.csv
                                 → results/processed/all_allocation_events.csv
                                 → results/processed/all_runtime.csv
                                 → results/processed/all_communication.csv
                                 → results/processed/all_ecosystem_metrics.csv

Katman 3 — Paper outputs / Phase 10:
  scripts/plot_results.py         → results/paper_figures/*.png
  scripts/statistical_analysis.py → results/reports/statistical_tables.md
  scripts/report_generator.py     → results/reports/summary_report.md
```

## 11.1. Dizin yapısı

```text
results/
├── raw/
│   ├── exp_001_dynamic_task_arrival_full_ahe_seed01/
│   │   ├── metadata.yaml
│   │   ├── task_events.csv
│   │   ├── robot_state_timeseries.csv
│   │   ├── robot_workload.csv
│   │   ├── allocation_events.csv
│   │   ├── method_runtime.csv
│   │   ├── communication_metrics.csv
│   │   ├── ecosystem_metrics.csv        # varsa
│   │   ├── summary.csv
│   │   └── rosbag/                      # opsiyonel debug kaydı
│   └── ...
├── processed/
│   ├── all_summary.csv
│   ├── all_task_events.csv
│   ├── all_robot_state_timeseries.csv
│   ├── all_robot_workload.csv
│   ├── all_allocation_events.csv
│   ├── all_runtime.csv
│   ├── all_communication.csv
│   └── all_ecosystem_metrics.csv
├── paper_figures/
│   ├── system_overview.png
│   ├── adaptive_ecosystem_mechanism.png
│   ├── baseline_comparison_multi_metric.png
│   ├── ablation_comparison.png
│   ├── dominance_evolution.png
│   ├── failure_recovery.png
│   ├── dominance_recovery_panel.png
│   ├── communication_footprint.png
│   ├── communication_scalability_panel.png
│   ├── allocation_instability.png
│   ├── decision_latency.png
│   ├── task_completion_timeline.png
│   ├── workload_distribution.png
│   └── compact_scalability_sanity.png
└── reports/
    ├── statistical_tables.md
    └── summary_report.md
```

## 11.1.1. CSV-first veri saklama ilkeleri

Deney altyapısı, yalnızca final skorları hesaplayan bir yapı olarak değil, sonradan tekrar analiz edilebilir bir veri arşivi olarak kurulmalıdır.

Temel ilkeler:

```text
1. Her deney koşusu benzersiz bir experiment_id ile kaydedilir.
2. Ham olay verileri kaybolmaması için her deney klasöründe ayrı CSV olarak tutulur.
3. Robot sayısına bağlı sabit sütunlar kullanılmaz; robot düzeyi bilgi ayrı satırlarda tutulur.
4. Tüm Phase 10 grafik ve tabloları processed CSV dosyalarından üretilir.
5. Rosbag zorunlu ana veri kaynağı değildir; CSV ana veri kaynağıdır.
6. Yeni grafik üretmek için simülasyon tekrar çalıştırılmamalıdır; processed CSV dosyaları yeterli olmalıdır.
7. Her CSV dosyasında experiment_id, scenario, strategy, seed, robot_count ve target_count alanları mümkün olduğunca korunmalıdır.
```

Bu karar, hakemlerin ek analiz talep etmesi durumunda büyük avantaj sağlar. Örneğin sonradan `idle_time`, `queue_version_change`, `robot_failure_timeline`, `task_delay_distribution` veya `dominance-response lag` gibi ek analizler istenirse yeni ROS/Gazebo koşusu yapılmadan mevcut CSV arşivinden üretilebilir.

## 11.2. task_events.csv şeması

Her görev için zamanlama, durum, deadline ve yeniden atama bilgilerini tutar.

```text
experiment_id,
scenario,
strategy,
seed,
robot_count,
target_count,
task_id,
robot_id,
task_priority,
activation_time,
deadline,
assigned_time,
nav_start_rel,
reached_rel,
completed_rel,
status,
was_reassigned,
reassignment_count,
failure_related,
travel_duration,
service_duration,
total_duration,
deadline_violation
```

`status` alanı şu değerleri alabilir:

```text
completed
failed
reassigned
expired
skipped
unreachable
```

Bu dosyadan üretilecek başlıca figürler:

```text
task_completion_timeline.png
deadline-related supplementary panels
```

## 11.3. summary.csv şeması

Her deney koşusunun tek satırlık özetidir. Robot sayısına bağlı sabit `robot_1`, `robot_2`, `robot_3` sütunları kullanılmaz.

```text
experiment_id,
scenario,
strategy,
seed,
robot_count,
target_count,
tasks_total,
tasks_completed,
task_completion_rate,
makespan_s,
average_task_delay,
deadline_violation_rate,
total_travel_distance,
workload_balance,
failure_recovery_time,
replanning_frequency,
allocation_instability,
mean_decision_latency_ms,
communication_messages,
communication_bytes,
rosbag_size_mb
```

`workload_balance` şu şekilde hesaplanır:

```text
workload_balance = 1 / (1 + variance(completed_tasks_per_robot))
```

Bu dosyadan üretilecek başlıca figürler:

```text
baseline_comparison_multi_metric.png
ablation_comparison.png
failure_recovery.png
allocation_instability.png
decision_latency.png
compact_scalability_sanity.png
```

## 11.4. robot_state_timeseries.csv şeması

Robotların zaman içindeki durumlarını ham zaman serisi olarak tutar. Bu dosya ana figürler için zorunlu olmayabilir; ancak ileride trajectory, failure timeline, idle/active state, robot state transition ve navigation behaviour analizleri istenirse deneyleri yeniden çalıştırmadan ek grafik üretmeyi sağlar.

```text
experiment_id,
scenario,
strategy,
seed,
robot_count,
target_count,
time,
robot_id,
x,
y,
yaw,
availability_state,
navigation_state,
battery_state,
battery_level,
current_task_id,
queue_version,
failure_flag,
active_task_count,
local_delay,
congestion_indicator,
goal_reachability
```

Bu dosyadan üretilebilecek olası ek figürler:

```text
robot_state_timeline.png
robot_trajectory_overlay.png
idle_active_time_distribution.png
failure_timeline.png
```

Ana makalede bu figürlerin verilmesi zorunlu değildir. Ancak repository veya supplementary analiz için ham veri hazır tutulmalıdır.

## 11.5. robot_workload.csv şeması

Robot başına görev dağılımı ayrı dosyada tutulur. Böylece robot sayısı değişse bile CSV şeması bozulmaz.

```text
experiment_id,
scenario,
strategy,
seed,
robot_count,
robot_id,
assigned_tasks,
completed_tasks,
failed_tasks,
travel_distance,
active_time,
idle_time
```

Bu dosyadan üretilecek başlıca figür:

```text
workload_distribution.png
```

Bu figür ana makalede zorunlu değildir. Ancak workload_balance panelini açıklamak için supplementary veya ek panel olarak kullanılabilir.

## 11.6. allocation_events.csv şeması

Yeniden atama, failure ve queue güncelleme olaylarını analiz etmek için kullanılır.

```text
experiment_id,
scenario,
strategy,
seed,
time,
event_type,
robot_id,
task_id,
queue_version,
trigger_reason,
severity,
replan_required
```

Bu dosyadan üretilecek başlıca figürler:

```text
failure_recovery.png
allocation_instability.png
dominance_evolution.png içindeki event marker'lar
```

## 11.7. method_runtime.csv şeması

Karar gecikmesi ve yöntem çalıştırma maliyeti için kullanılır.

```text
experiment_id,
scenario,
strategy,
seed,
allocation_round,
active_task_count,
available_robot_count,
runtime_ms,
matching_or_solver_time_ms,
queue_generation_time_ms
```

Bu dosyadan üretilecek başlıca figür:

```text
decision_latency.png
```

Runtime dağılımları genellikle değişken olacağı için bu figürde boxplot tercih edilmelidir.

## 11.8. communication_metrics.csv şeması

AHE-MRTA'nın communication-efficient iddiası ve iletişim odaklı karşılaştırma yöntemleri için zorunludur.

```text
experiment_id,
scenario,
strategy,
seed,
robot_count,
message_count,
bytes_transmitted,
topic_count,
queue_messages,
status_messages,
feedback_messages,
debug_messages,
rosbag_size_mb
```

Bu dosyadan üretilecek başlıca figür:

```text
communication_footprint.png
```

Bu figür, robotlara yalnızca kendi optimize edilmiş görev kuyruğunun gönderildiği ve global ekosistem durumunun robotlara yayınlanmadığı mimari iddiayı nicel hale getirir.

## 11.9. ecosystem_metrics.csv şeması

Bu dosya yalnızca `full_ahe_mrta` ve AHE ablation koşularında üretilir. Robotlara gönderilmez; sadece offline analiz içindir.

```text
experiment_id,
scenario,
strategy,
seed,
time,
spatial_opportunist,
criticality_guardian,
temporal_regulator,
resource_distributor,
energy_conservator,
stability_controller,
recovery_coordinator,
w_distance,
w_priority,
w_battery,
w_load,
w_failure,
w_deadline,
w_recovery,
task_density,
robot_availability,
battery_risk,
deadline_pressure,
failure_rate,
workload_variance,
allocation_instability
```

Bu dosyadan üretilecek başlıca figür:

```text
dominance_evolution.png
```

`dominance_evolution.png`, AHE-MRTA'nın en özgün figürlerinden biri olarak düşünülmelidir. Bu figürde event marker kullanılmalıdır:

```text
vertical dashed line = robot failure event
vertical dashed line = critical task arrival
vertical dashed line = deadline pressure increase
```

Bu sayede failure geldiğinde `Recovery Coordinator`, deadline baskısı arttığında `Temporal Regulator`, yük dengesizliği arttığında `Resource Distributor` davranışının anlamlı biçimde güçlenip güçlenmediği gösterilebilir.

## 11.10. scripts/pipeline dosyaları

| Dosya                     | Ne zaman çalışır             | Giriş                                         | Çıkış                                   |
| ------------------------- | ---------------------------- | --------------------------------------------- | --------------------------------------- |
| `parse_logs.py`           | Her deney sonunda            | Seçili ROS topic logları veya runtime logları | `results/raw/<experiment_id>/*.csv`     |
| `consolidate_results.py`  | Tüm deneyler bittikten sonra | `results/raw/*/*.csv`                         | `results/processed/all_*.csv`           |
| `plot_results.py`         | Phase 10                     | `results/processed/*.csv`                     | `results/paper_figures/*.png`           |
| `statistical_analysis.py` | Phase 10                     | `results/processed/all_summary.csv`           | `results/reports/statistical_tables.md` |
| `report_generator.py`     | Phase 10                     | Processed CSV + PNG + istatistik tabloları    | `results/reports/summary_report.md`     |

## 11.11. CSV → PNG dönüşüm haritası

| Kaynak CSV                                        | Üretilecek PNG                                             | Grafik tipi                   | Ana metin/supplementary    | Amaç                                                       |
| ------------------------------------------------- | ---------------------------------------------------------- | ----------------------------- | -------------------------- | ---------------------------------------------------------- |
| `summary.csv`                                     | `baseline_comparison_multi_metric.png`                     | Çok panelli bar + error bar   | Ana metin                  | Genel performans karşılaştırması                           |
| `summary.csv`                                     | `ablation_comparison.png`                                  | Çok panelli bar + error bar   | Ana metin                  | AHE bileşen katkılarını izole etmek                        |
| `ecosystem_metrics.csv` + `allocation_events.csv` | `dominance_evolution.png`                                  | Line plot + event marker      | Ana metin                  | Açıklanabilir adaptasyon göstermek                         |
| `summary.csv` + `allocation_events.csv`           | `failure_recovery.png`                                     | Bar/box plot                  | Ana metin                  | Failure sonrası toparlanma davranışı                       |
| `summary.csv` + `allocation_events.csv`           | `allocation_instability.png`                               | Bar/box plot                  | Ana metin veya ek panel    | Event-triggered replanning etkisi                          |
| `communication_metrics.csv`                       | `communication_footprint.png`                              | Bar/box plot                  | Ana metin                  | Düşük veri paylaşımlı mimari kanıtı                        |
| `method_runtime.csv` + `summary.csv`              | `decision_latency.png`                                     | Boxplot                       | Ana metin veya ek panel    | Gerçek zamanlı uygulanabilirlik                            |
| `task_events.csv`                                 | `task_completion_timeline.png`                             | Cumulative line chart         | Supplementary              | Görevlerin zamansal tamamlanma eğrisi                      |
| `robot_workload.csv`                              | `workload_distribution.png`                                | Boxplot veya grouped bar      | Supplementary              | Robot başına yük dağılımı                                  |
| `robot_state_timeseries.csv`                      | `robot_state_timeline.png`, `robot_trajectory_overlay.png` | Timeline veya trajectory plot | Supplementary / repository | Sonradan robot davranışı ve state geçişlerini analiz etmek |
| `summary.csv` + `method_runtime.csv`              | `compact_scalability_sanity.png`                           | Line/bar plot                 | Opsiyonel                  | 3/15 ve 5/25 kısa ölçek kontrolü                           |

## 11.12. Q1/RA-L için ana figür ve PNG çıktı planı

Ana makalede 6 figürden fazlası kullanılmamalıdır. Fig. 1 ve Fig. 2 yöntem/mimari şemalarıdır; doğrudan CSV'den üretilmez. Fig. 3–Fig. 6 ise deney CSV'lerinden üretilen veya deney panellerinin birleştirilmesiyle hazırlanan sonuç figürleridir.

| Makale figürü | Önerilen PNG dosyası                   | Kaynak                                                             | Zorunluluk | Amaç                                                                                            |
| ------------- | -------------------------------------- | ------------------------------------------------------------------ | ---------- | ----------------------------------------------------------------------------------------------- |
| Fig. 1        | `system_overview.png`                  | Manuel/Graphviz/Matplotlib şema                                    | Zorunlu    | ROS 2/Gazebo, task manager, allocator, robot interface ve evaluation akışını göstermek          |
| Fig. 2        | `adaptive_ecosystem_mechanism.png`     | Manuel/Graphviz/Matplotlib şema                                    | Zorunlu    | Context vector, dominance, cooperation/suppression ve weight generation mekanizmasını göstermek |
| Fig. 3        | `baseline_comparison_multi_metric.png` | `summary.csv`                                                      | Zorunlu    | Ana baseline karşılaştırmasını çok panelli vermek                                               |
| Fig. 4        | `ablation_comparison.png`              | `summary.csv`                                                      | Zorunlu    | AHE bileşen katkılarını izole etmek                                                             |
| Fig. 5        | `dominance_recovery_panel.png`         | `ecosystem_metrics.csv` + `allocation_events.csv` + `summary.csv`  | Zorunlu    | Dominance evolution ve failure recovery davranışını birlikte göstermek                          |
| Fig. 6        | `communication_scalability_panel.png`  | `communication_metrics.csv` + `summary.csv` + `method_runtime.csv` | Zorunlu    | Düşük iletişim yükü ve 3/15→5/25 kısa ölçek kontrolünü göstermek                                |

Phase 10 sırasında ayrıca aşağıdaki kaynak PNG'ler üretilebilir ve gerekirse Fig. 5/Fig. 6 panellerine dönüştürülebilir:

```text
baseline_comparison_multi_metric.png
ablation_comparison.png
dominance_evolution.png
failure_recovery.png
communication_footprint.png
compact_scalability_sanity.png
```

Supplementary veya repository için önerilen ek figürler:

| Ek figür | PNG dosyası                    | Kaynak CSV                              | Kullanım                              |
| -------- | ------------------------------ | --------------------------------------- | ------------------------------------- |
| Fig. S1  | `task_completion_timeline.png` | `task_events.csv`                       | Görevlerin zamansal tamamlanma eğrisi |
| Fig. S2  | `workload_distribution.png`    | `robot_workload.csv`                    | Robot başına görev dağılımı           |
| Fig. S3  | `allocation_instability.png`   | `summary.csv` + `allocation_events.csv` | Yeniden atama kararlılığı             |
| Fig. S4  | `decision_latency.png`         | `method_runtime.csv` + `summary.csv`    | Karar süresi dağılımı                 |

Radar chart ana makalede kullanılmamalıdır. Çünkü bazı metriklerde yüksek, bazı metriklerde düşük değer daha iyidir; radar chart için gereken ters normalizasyon hakem açısından yorum karmaşası yaratabilir.

## 11.13. Figürlerin içerik planı

### 11.13.1. `baseline_comparison_multi_metric.png`

Bu figür ana performans karşılaştırmasını verir.

Önerilen alt paneller:

```text
(a) Task completion rate
(b) Makespan
(c) Average task delay
(d) Workload balance
(e) Deadline violation rate
(f) Mean decision latency
```

Kaynak sütunlar:

```text
strategy
scenario
seed
task_completion_rate
makespan_s
average_task_delay
workload_balance
deadline_violation_rate
mean_decision_latency_ms
```

Sunum biçimi:

```text
bar chart + error bar
error bar = std veya 95% CI
```

### 11.13.2. `ablation_comparison.png`

Bu figür önerilen yöntemin bileşen katkılarını gösterir.

Önerilen alt paneller:

```text
(a) Average task delay
(b) Workload balance
(c) Failure recovery time
(d) Allocation instability
```

Karşılaştırılacak yöntem grubu:

```text
full_ahe_mrta
ahe_no_dominance
ahe_no_cooperation_suppression
ahe_no_event_replanning
ahe_fixed_context
```

### 11.13.3. `dominance_evolution.png`

Bu figür AHE-MRTA'nın açıklanabilir adaptasyonunu gösterir.

Önerilen alt paneller:

```text
(a) Dominance evolution of strategy agents
(b) Context vector evolution
(c) Allocation weight evolution
```

Sunum biçimi:

```text
x-axis = mission time
y-axis = dominance/context/weight value
plot type = line chart
event marker = robot failure, critical task arrival, deadline pressure increase
```

### 11.13.4. `failure_recovery.png`

Bu figür failure altında toparlanma performansını gösterir.

Önerilen alt paneller:

```text
(a) Failure recovery time
(b) Recovery success rate
(c) Replanning frequency
```

### 11.13.5. `allocation_instability.png`

Bu figür sürekli replanning yerine event-triggered replanning kullanılmasının etkisini gösterir.

Önerilen alt paneller:

```text
(a) Allocation instability
(b) Reassignment count
(c) Queue version changes
```

### 11.13.6. `communication_footprint.png`

Bu figür communication-efficient execution architecture iddiasını test eder.

Önerilen alt paneller:

```text
(a) Message count
(b) Bytes transmitted
(c) Topic count
```

### 11.13.7. `decision_latency.png`

Bu figür yöntemlerin karar üretme süresini gösterir.

Önerilen sunum:

```text
x-axis = strategy
y-axis = runtime_ms
plot type = boxplot
```

### 11.13.8. `task_completion_timeline.png`

Bu figür görevlerin zaman içinde nasıl tamamlandığını gösterir.

Önerilen sunum:

```text
x-axis = mission time
y-axis = cumulative completed tasks
line = strategy
```

Ana makale için zorunlu değildir; supplementary için uygundur.

### 11.13.9. `workload_distribution.png`

Bu figür robotlar arası görev dağılımını gösterir.

Önerilen sunum:

```text
x-axis = strategy
y-axis = completed_tasks per robot
plot type = boxplot
```

Ana makalede workload_balance paneli yeterli olursa bu figür supplementary'ye alınabilir.

## 11.14. Figür stil kuralları

Tüm PNG figürler aynı görsel standartla üretilmelidir:

```text
resolution = 300 dpi
font size = 8 veya 9
single column width = yaklaşık 3.5 inch
double column width = yaklaşık 7.0 inch
error bars = std veya 95% CI
method order = ek yöntem dosyasındaki sıraya göre sabit
proposed method = her figürde en sonda veya açıkça vurgulanmış konumda
metric direction = eksen etiketi veya caption içinde belirtilmeli
```

Radar chart ana makale için önerilmez. Çünkü bazı metriklerde yüksek değer iyi, bazılarında düşük değer iyidir ve radar chart için ters çevrilmiş metrik normalizasyonu gerekir. Ana makale için bar chart, boxplot ve line chart daha temiz ve hakem açısından daha anlaşılırdır.

## 11.15. Metrik yönleri

Grafiklerde hangi metrikte yüksek veya düşük değerin iyi olduğu açıkça belirtilmelidir.

| Metrik                     | İyi yön         |
| -------------------------- | --------------- |
| `task_completion_rate`     | Yüksek daha iyi |
| `workload_balance`         | Yüksek daha iyi |
| `tasks_completed`          | Yüksek daha iyi |
| `makespan_s`               | Düşük daha iyi  |
| `average_task_delay`       | Düşük daha iyi  |
| `deadline_violation_rate`  | Düşük daha iyi  |
| `failure_recovery_time`    | Düşük daha iyi  |
| `allocation_instability`   | Düşük daha iyi  |
| `mean_decision_latency_ms` | Düşük daha iyi  |
| `communication_bytes`      | Düşük daha iyi  |
| `message_count`            | Düşük daha iyi  |
| `runtime_ms`               | Düşük daha iyi  |

## 11.16. Table 1 — Karşılaştırma yöntemlerinin kısa karakterizasyonu

Karşılaştırma yöntemlerinin isimleri ve kısa karakterizasyonu bu ana dosyada tekrar edilmez. Bu tablo `ahe_mrta_recent_comparison_methods.md` içinde tutulmalıdır.

Ana dosyada yalnızca Table 1'in beklenen kolon yapısı belirtilir:

```text
Method name | Online? | Adaptive? | Distributed/decentralized?
```

Bu karar, ana proje rehberinin AHE-MRTA formülasyonu ve deney/çıktı pipeline'ına odaklı kalmasını sağlar. Yöntem isimleri, bibliyografik bilgiler ve detaylı uyarlama koşulları ek dosyada yönetilmelidir.

## 11.17. Table 2 — Deney senaryoları

| Scenario                   | Robot/target scale | Dynamic tasks | Deadline | Failure  | Congestion/battery stress | Compared method scope                                            |
| -------------------------- | ------------------ | ------------- | -------- | -------- | ------------------------- | ---------------------------------------------------------------- |
| Dynamic Task Arrival       | 5/25               | Yes           | Optional | No       | No                        | Ek dosyada tanımlanan online allocation baseline seti + Full AHE |
| Deadline Pressure          | 5/25               | Yes           | Yes      | No       | No                        | Ek dosyada tanımlanan deadline-aware baseline seti + Full AHE    |
| Robot Failure              | 5/25               | Yes           | Optional | Yes      | Optional                  | Ek dosyada tanımlanan recovery/failure baseline seti + Full AHE  |
| Mixed Stress               | 5/25               | Yes           | Yes      | Yes      | Yes                       | Ek dosyada tanımlanan ana baseline seti + Full AHE               |
| Ablation                   | 5/25               | Yes           | Yes      | Yes      | Yes                       | Full AHE + AHE ablations                                         |
| Compact Scalability Sanity | 3/15 and 5/25      | Yes           | Optional | Optional | Optional                  | Ek dosyada tanımlanan küçük baseline seti + Full AHE             |

## 11.18. Table 3 — Ana nicel sonuç tablosu

Table 3 şu metriklerle verilmelidir:

```text
Method
Task completion rate
Makespan
Average task delay
Deadline violation rate
Workload balance
Failure recovery time
Allocation instability
Mean decision latency
Communication bytes
```

Her hücre mümkünse şu formatta raporlanmalıdır:

```text
mean ± std
```

Ana metinde p-değerlerinin tamamı verilmemeli; istatistiksel ayrıntılar `statistical_tables.md` içinde tutulmalıdır.

## 11.19. statistical_tables.md içeriği

`statistical_tables.md` şu içeriği üretmelidir:

```text
Table S1: Descriptive statistics
  mean ± std
  median
  95% confidence interval

Table S2: Normality tests
  Shapiro-Wilk test per metric and method when sample size permits

Table S3: Pairwise significance tests
  ANOVA + Tukey if normality is satisfied
  Kruskal-Wallis + Dunn if normality is not satisfied

Table S4: Effect sizes
  Cohen's d for normal pairwise comparisons
  Cliff's delta for non-parametric pairwise comparisons
```

## 11.20. Kaydedilecek ROS topic'leri

```text
/tasks/global_pool
/allocation/events
/system/replan_trigger
/ecosystem/debug_state       ← yalnızca offline analiz, robotlara gönderilmez
/robot_i/status_summary
/robot_i/optimized_task_queue
/robot_i/local_execution_feedback
/robot_i/odom
/robot_i/tf veya /tf             ← gerekiyorsa seyreltilmiş trajectory analizi için
```

10+ robotlu deneyler zorunlu olmadığı için ana deneylerde seçici kayıt yeterlidir. Rosbag boyutu çok büyürse `/robot_i/odom` seyreltilmiş olarak kaydedilebilir.

## 11.21. Metadata dosyası

```yaml
experiment_id: exp_001
scenario_name: dynamic_task_arrival
method: full_ahe_mrta
robot_count: 5
target_count: 25
seed: 1
start_time: YYYY-MM-DD HH:MM:SS
ros2_distro: jazzy
gazebo_version: harmonic
nav2_enabled: true
headless: true
parse_logs_version: "1.0"
notes: ""
```

# 12. Claude Code ile Uygulama Stratejisi

## 12.1. Neden tek prompt ile başlanmamalı?

Bu proje çok paketli ROS 2, Gazebo, Nav2, custom message, namespace, TF ve deney kayıt sistemi içerir. Claude Code'a tüm sistemi tek seferde yazdırmak package dependency, launch order, TF prefix, import ve message build hatalarını artırır.

Bu nedenle Claude Code şu prensiple kullanılmalıdır:

```text
One phase
One build target
One runtime validation
Then next phase
```

## 12.2. Fazlar arası doğrulama kapıları

Claude Code bir sonraki faza ancak önceki fazın doğrulama kapısı geçildiğinde geçirilmelidir.

| Faz               | Doğrulama kapısı                                                                  | Başarısızlık durumunda yapılacak                                   |
| ----------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Workspace/message | `colcon build` hatasız çalışır                                                    | Package dependency ve msg import düzelt                            |
| Message test      | Test publisher/subscriber topic alışverişi yapar                                  | msg type ve setup.py/CMakeLists düzelt                             |
| Tek robot Gazebo  | Robot spawn olur, odom ve scan yayınlanır                                         | ros_gz, model path ve launch düzelt                                |
| Üç robot          | Her robot ayrı namespace ve TF üretir                                             | frame prefix ve remapping düzelt                                   |
| Nav2              | Her robot manuel hedefe gider                                                     | map, lifecycle ve action server kontrol et                         |
| Task Manager      | `/tasks/global_pool` düzenli yayınlanır                                           | task activation ve timestamp kontrol et                            |
| Phase 6           | 3 robot 5/5 görevi tamamlar, `task_events.csv` üretilir                           | robot_interface state machine ve allocator kontrol et              |
| Phase 7           | Minimum baseline allocator CSV üretir ve Phase 6 çıktılarıyla karşılaştırılabilir | sabit maliyet fonksiyonu, görev sıralama ve log üretimi kontrol et |
| AHE (Phase 8)     | dominance ve weight değerleri loglanır, `dominance_evolution` CSV üretilir        | normalization, clip ve softmax kontrol et                          |
| Replanning        | failure olayında queue_version artar                                              | trigger ve recovery manager kontrol et                             |
| Phase 9           | tüm strateji CSV'leri doldu, summary.csv karşılaştırılabilir                      | seed tutarlılığı ve parser çıktısı kontrol et                      |
| Phase 10          | `paper_figures/*.png` üretildi, istatistiksel tablolar hazır                      | plot_results.py ve statistical_analysis.py düzelt                  |

Bu kapılar proje yönetimi için önemlidir. Claude Code'a her faz sonunda “stop and report” talimatı verilmelidir.

## 12.3. Faz 0: Araştırma şartnamesi ve README

Amaç:

```text
Projeyi açıklayan ana README, research_spec.md ve package plan dosyalarını oluşturmak
```

Başarı kriteri:

```text
Dosya yapısı anlaşılır olmalı
Henüz kod yazılmamalı
```

## 12.4. Faz 1: Workspace ve message build

Amaç:

```text
ROS 2 workspace oluştur
Paketleri oluştur
Custom message dosyalarını ekle
package.xml ve CMakeLists.txt bağımlılıklarını düzelt
colcon build çalıştır
```

Başarı kriteri:

```bash
colcon build --symlink-install
source install/setup.bash
ros2 interface show ahe_mrta_msgs/msg/OptimizedTaskQueue
```

## 12.5. Faz 2: Message test nodes

Amaç:

```text
TaskPool publisher
RobotStatusSummary publisher
OptimizedTaskQueue subscriber
EcosystemState debug publisher
```

Başarı kriteri:

```bash
ros2 topic list
ros2 topic echo /tasks/global_pool
ros2 topic echo /robot_1/status_summary
```

## 12.6. Faz 3: Tek robot Gazebo spawn

Amaç:

```text
Gazebo Harmonic world aç
Bir TurtleBot3 Waffle Pi spawn et
Odom ve scan topic'lerini kontrol et
```

Başarı kriteri:

```bash
ros2 topic list | grep robot_1
ros2 topic echo /robot_1/odom
```

## 12.7. Faz 4: Üç robot namespace ve TF

Amaç:

```text
robot_1, robot_2, robot_3 namespace yapısı
Ayrı odom, scan, cmd_vel topic'leri
Ayrı TF frame isimleri
```

Başarı kriteri:

```bash
ros2 topic list | grep robot_1
ros2 topic list | grep robot_2
ros2 topic list | grep robot_3
```

## 12.8. Faz 5: Nav2 manuel hedef testi

Amaç:

```text
Her robot için ayrı Nav2 instance
Manuel NavigateToPose testi
```

Başarı kriteri:

```text
Her robot kendi namespace'i altında hedefe gidebilmeli
```

## 12.9. Faz 6: Task Manager ve Robot Interface

Amaç:

```text
Görev havuzu üret
Görevleri zamanla aktif hale getir
Robot interface optimized task queue dinlesin
Robot sıradaki hedefi Nav2 action ile yürütsün
```

Başarı kriteri:

```text
3 robot 15 hedef senaryosunda basit görev yürütme çalışmalı
```

## 12.10. Faz 7: Minimum baseline allocator

Amaç:

```text
Sabit maliyet ağırlıklarıyla çalışan minimum baseline allocator ve görev sırası üretme
```

Başarı kriteri:

```text
Minimum baseline allocator deneyleri CSV olarak kaydedilmeli
```

## 12.11. Faz 8: Full AHE-MRTA

Amaç:

```text
Context vector
Dominance update
Cooperation matrix
Suppression matrix
Weight generation
Event-triggered replanning
```

Başarı kriteri:

```text
AHE-MRTA ile dominance_evolution ve allocation_weights loglanmalı
```

## 12.12. Faz 9: Baseline, comparison-method ve ablation deneyleri

Amaç:

```text
Ek yöntem dosyasında tanımlanan karşılaştırma yöntemlerini, AHE ablation varyantlarını ve Full AHE-MRTA'yı aynı deney altyapısında çalıştırmak.
```

Karşılaştırma yöntemlerinin isimleri ve uygulama ayrıntıları ana dosyada tekrarlanmaz. Claude Code, Faz 9'a başlamadan önce aşağıdaki dosyayı okumalıdır:

```text
ahe_mrta_recent_comparison_methods.md
```

Bu fazda ana dosyada sabit tutulacak AHE varyantları:

```text
AHE ablations:
- ahe_no_dominance
- ahe_no_cooperation_suppression
- ahe_no_event_replanning
- ahe_fixed_context

Proposed method:
- full_ahe_mrta
```

Başarı kriteri:

```text
Ek dosyada tanımlanan her karşılaştırma yöntemi, aynı seed seti, aynı görev havuzu, aynı robot durumları, aynı failure olayları ve aynı Nav2 path-cost cache ile çalıştırılmalıdır.
Her deney sonunda `results/raw/<experiment_id>/` altında metadata.yaml, task_events.csv, robot_state_timeseries.csv, robot_workload.csv, allocation_events.csv, method_runtime.csv, communication_metrics.csv ve summary.csv üretilmelidir.
Full AHE-MRTA ve AHE ablation koşularında ecosystem_metrics.csv üretilmelidir.
Deneyler tamamlandıktan sonra `consolidate_results.py` ile `results/processed/all_*.csv` dosyaları oluşturulmalıdır.
```

Ek doğrulama:

```text
Karşılaştırma yöntemlerinin yöntem-özel doğrulama koşulları ek yöntem dosyasından alınmalıdır.
AHE varyantları için dominance, context, replanning ve cooperation/suppression loglarının beklenen şekilde açılıp kapanması kontrol edilmelidir.
```

## 12.13. Faz 10: Makale grafik ve tabloları

Amaç:

```text
Phase 6–9 deneyleriyle dolan CSV dosyalarını okuyarak RA-L/Q1 düzeyinde sunulabilecek çok panelli PNG figürler,
sade Table 1, deney senaryosu Table 2, ana sonuç Table 3 ve istatistiksel ek tablolar üretmek.
```

Phase 10, yalnızca grafik çizme aşaması değildir. Bu faz, her CSV dosyasını belirli bir makale figürüne veya tabloya bağlayan son değerlendirme aşamasıdır. Bu fazda `results/raw/` altındaki koşu bazlı CSV dosyaları önce `results/processed/` altında birleştirilir; grafik ve istatistik scriptleri doğrudan raw klasörleri değil, mümkün olduğunca processed CSV dosyalarını okur.

Çalıştırılacak scriptler:

```bash
# 1. Deney loglarını koşu bazlı raw CSV dosyalarına çevir
python3 scripts/parse_logs.py --input-dir results/raw/

# 2. Raw CSV dosyalarını processed tekil CSV dosyalarına birleştir
python3 scripts/consolidate_results.py \
  --raw-dir results/raw/ \
  --processed-dir results/processed/

# 3. PNG figürler üret
python3 scripts/plot_results.py \
  --processed-dir results/processed/ \
  --output-dir results/paper_figures/ \
  --methods-from ahe_mrta_recent_comparison_methods.md \
  --include full_ahe_mrta ahe_ablation_set \
  --compact-scale-only true \
  --dpi 300

# 4. İstatistiksel analiz
python3 scripts/statistical_analysis.py \
  --processed-dir results/processed/ \
  --output results/reports/statistical_tables.md \
  --group-by strategy scenario

# 5. Özet rapor
python3 scripts/report_generator.py \
  --processed-dir results/processed/ \
  --figures-dir results/paper_figures/ \
  --stats results/reports/statistical_tables.md \
  --output results/reports/summary_report.md
```

Zorunlu PNG başarı kriteri:

```text
results/paper_figures/ dizininde en az şu ana makale çıktıları bulunmalı:
  system_overview.png
  adaptive_ecosystem_mechanism.png
  baseline_comparison_multi_metric.png
  ablation_comparison.png
  dominance_recovery_panel.png
  communication_scalability_panel.png
  results/reports/statistical_tables.md
  results/reports/summary_report.md
```

`dominance_recovery_panel.png`, `dominance_evolution.png` ve `failure_recovery.png` panellerinden; `communication_scalability_panel.png` ise `communication_footprint.png` ve varsa `compact_scalability_sanity.png` panellerinden oluşturulabilir.

Önerilen ek PNG çıktıları:

```text
  allocation_instability.png
  decision_latency.png
  task_completion_timeline.png       # supplementary adayı
  workload_distribution.png          # supplementary adayı
  compact_scalability_sanity.png     # opsiyonel
```

10/50 ve 15/75 ölçekli deneyler Phase 10 için zorunlu değildir. `compact_scalability_sanity.png` yalnızca 3/15 ve 5/25 koşullarını karşılaştırır.

Figür üretiminde şu standartlar korunmalıdır:

```text
resolution = 300 dpi
font size = 8 veya 9
single column width = yaklaşık 3.5 inch
double column width = yaklaşık 7.0 inch
error bars = std veya 95% CI
method order = ek yöntem dosyasındaki sıraya göre sabit
proposed method = her figürde en sonda veya açıkça vurgulanmış konumda
radar chart kullanılmaz
```

# 13. Claude Code İçin Revize Ana Prompt

Aşağıdaki prompt Claude Code'a başlangıçta verilmelidir.

```text
You are developing a ROS 2 Jazzy and Gazebo Harmonic research prototype for a RA-L-level multi-robot task allocation paper.

The project is AHE-MRTA: Adaptive Heuristic Ecosystem for Robust Online Multi-Robot Task Allocation.

Do not implement the full system in one step. Develop the project in validated phases. Each phase must compile with colcon build and include a minimal runtime validation before moving to the next phase.

Use Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, ros_gz, Nav2, rclpy, rosbag2, pandas, matplotlib, and TurtleBot3 Waffle Pi models.

Important constraints:
1. Use ros_gz-compatible Gazebo Harmonic integration. Do not assume Gazebo Classic gazebo_ros_pkgs APIs unless a compatible TurtleBot3 package explicitly requires it.
2. Start with the workspace and custom messages only.
3. Then test messages with simple publisher and subscriber nodes.
4. Then spawn one robot in Gazebo.
5. Then extend to three robots with namespaces and TF separation.
6. Then integrate Nav2 and test manual NavigateToPose.
7. Then implement Task Manager and Robot Interface.
8. Then implement the minimum baseline allocator needed for validation.
9. Then implement Full AHE-MRTA with dominance, cooperation, suppression, context-adaptive weighting, and event-triggered replanning.
10. Do not reduce AHE-MRTA to adaptive weighting. The implementation must log dominance values, cooperation/suppression effects, context compatibility, and allocation weights separately.
11. Implement fixed-weight control and AHE ablations so that the contribution of dominance, cooperation/suppression, and event-triggered replanning can be isolated.
12. In evaluation, prioritize workload balance, failure recovery time, allocation instability, average task delay under stress, dominance evolution, and communication footprint. Do not treat travel distance as the primary success metric.
13. Implement detailed comparison methods only after reading ahe_mrta_recent_comparison_methods.md.
14. Do not implement deep RL, neural networks, or heavy VRP solvers unless explicitly required by the supplementary comparison-method file.
15. Robot agents must receive only their own optimized task queue.
16. The ecosystem internal state must remain centralized and only be logged for debugging and evaluation.
17. Every phase must include README instructions, launch commands, pass/fail checks, and a short troubleshooting note.
18. Use a CSV-first reusable data pipeline. Do not only compute final metrics. Store raw event-level CSV data per experiment and later merge it into processed CSV files.
19. All plotting and statistical scripts must read from processed CSV files under results/processed/ whenever possible. ROS bags are optional debugging artifacts, not the main paper data source.
20. Include robot_state_timeseries.csv so that future trajectory, idle/active state, failure timeline, and robot behavior plots can be produced without rerunning simulations.

Phase 1 task:
Create only the workspace, packages, custom messages, package dependencies, and build system. Do not implement Gazebo, Nav2, or allocation logic yet. The success criterion is that colcon build passes and ros2 interface show works for the custom messages.

After Phase 1, stop and report the created files, build commands, validation commands, and assumptions.
```

---

# 14. Claude Code Faz Bazlı Promptlar

## 14.1. Faz 1 promptu

```text
Create the AHE-MRTA ROS 2 Jazzy workspace skeleton.

Create the following packages:
- ahe_mrta_bringup
- ahe_mrta_msgs
- ahe_mrta_gazebo
- ahe_task_manager
- ahe_robot_interface
- ahe_ecosystem_manager
- ahe_task_allocator
- ahe_recovery_manager
- ahe_evaluation
- ahe_nav2_config

Implement only the custom message package and minimal package scaffolding. Add TaskWaypoint, OptimizedTaskQueue, RobotStatusSummary, LocalExecutionFeedback, TaskInfo, TaskPool, AllocationEvent, and EcosystemState messages.

Do not implement Gazebo, Nav2, or allocation algorithms yet.

The output must pass:
colcon build --symlink-install
ros2 interface show ahe_mrta_msgs/msg/OptimizedTaskQueue
```

## 14.2. Faz 2 promptu

```text
Implement minimal test publisher and subscriber nodes for the AHE-MRTA custom messages.

Create:
- task_pool_test_publisher.py
- robot_status_test_publisher.py
- optimized_queue_test_subscriber.py
- ecosystem_debug_test_publisher.py

Add launch file:
phase1_test_messages.launch.py

The launch file must start all test nodes and allow validation with ros2 topic list and ros2 topic echo.
```

## 14.3. Faz 3 promptu

```text
Implement a minimal Gazebo Harmonic world and spawn one TurtleBot3 Waffle Pi robot under /robot_1 namespace.

Use ros_gz-compatible integration.
Do not start Nav2 yet.
Verify that /robot_1/odom and /robot_1/scan are available.
Provide launch command and troubleshooting notes.
```

## 14.4. Faz 4 promptu

```text
Extend the Gazebo launch to spawn three TurtleBot3 Waffle Pi robots.

Use namespaces:
/robot_1
/robot_2
/robot_3

Ensure that odom, scan, cmd_vel, and TF frames are separated. Avoid frame conflicts.

Provide validation commands for each robot namespace.
```

## 14.5. Faz 5 promptu

```text
Add Nav2 support for the three robot setup.

Create robot-specific Nav2 parameter files and a multi_robot_nav2.launch.py file.
Use a shared static map for MVP.
Validate manual NavigateToPose for each robot.
Do not implement AHE yet.
```

## 14.6. Faz 6 promptu

```text
Implement the Task Manager and Robot Interface.

Task Manager:
- publishes /tasks/global_pool
- activates tasks according to scenario seed
- tracks active, completed, and failed tasks

Robot Interface:
- publishes /robot_i/status_summary
- subscribes to /robot_i/optimized_task_queue
- sends the next task pose to Nav2 NavigateToPose
- publishes task feedback and local execution feedback

Use three robots and fifteen tasks for the MVP.
```

## 14.7. Faz 7 promptu

```text
Implement a minimum baseline allocator for validation.

Use fixed allocation weights:
W0 = [w_d, w_p, w_b, w_l, w_f, w_t, w_r]

Build a robot-task cost matrix and assign tasks to robots. For each robot, create an ordered task queue using adaptive insertion heuristic.

Do not add the detailed comparison-method baselines in this phase. Those methods are defined in ahe_mrta_recent_comparison_methods.md and should be implemented in Phase 9.

Publish /robot_i/optimized_task_queue.
Log allocation latency and queue cost.
```

## 14.8. Faz 8 promptu

```text
Implement the full AHE-MRTA ecosystem manager.

Add:
- context vector calculation
- heuristic dominance vector
- context compatibility
- cooperation matrix
- suppression matrix
- failure penalty
- dominance update equation
- normalized allocation weight generation
- /ecosystem/debug_state publication for evaluation only

The ecosystem state must not be sent to robots.
Robots receive only optimized task queues.
```

## 14.9. Faz 9 promptu

```text
Implement experiment runner scripts for the AHE-MRTA benchmark.

Before implementation, read:
ahe_mrta_recent_comparison_methods.md

Do not hard-code the detailed comparison-method descriptions in the main project file.
Use the supplementary comparison-method file as the source of truth for:
- baseline method names
- method-specific algorithmic logic
- fairness conditions
- method-specific validation checks
- Python-style implementation sketches

AHE ablations to implement from the main project file:
- ahe_no_dominance
- ahe_no_cooperation_suppression
- ahe_no_event_replanning
- ahe_fixed_context

Proposed method:
- full_ahe_mrta

Scenarios:
- dynamic_task_arrival
- deadline_pressure
- robot_failure
- mixed_stress
- compact_scalability_sanity

Implementation requirements:
1. All methods must implement the same BaseAllocator interface.
2. All methods must use the same task pool, robot state input, seed set, failure events, and Nav2 path-cost cache.
3. Comparison-method-specific implementation details must be taken from ahe_mrta_recent_comparison_methods.md.
4. Full AHE-MRTA must log dominance, cooperation/suppression contribution, context vector, and allocation weights.
5. AHE ablations must disable only the component being tested, while keeping all other settings identical.

Each experiment must save under results/raw/<experiment_id>/:
- metadata.yaml
- selected topic logs or rosbag only for debugging
- task_events.csv
- robot_state_timeseries.csv
- robot_workload.csv
- allocation_events.csv
- method_runtime.csv
- communication_metrics.csv
- ecosystem_metrics.csv when available
- summary.csv

After all runs, create processed merged CSV files under results/processed/:
- all_summary.csv
- all_task_events.csv
- all_robot_state_timeseries.csv
- all_robot_workload.csv
- all_allocation_events.csv
- all_runtime.csv
- all_communication.csv
- all_ecosystem_metrics.csv

Stop after Phase 9 and report:
- implemented methods loaded from the supplementary comparison-method file
- files created
- test commands
- sample CSV rows
- assumptions made for adapting comparison methods to the ROS 2/Gazebo benchmark
```

## 14.10. Faz 10 promptu

```text
Implement the Phase 10 evaluation pipeline for the compact AHE-MRTA benchmark.

The benchmark does not require expanded 10-robot or 15-robot experiments. The mandatory paper-scale experiments use:
- debug scale: 3 robots / 15 targets
- main scale: 5 robots / 25 targets
- optional compact scalability sanity check: 3/15 vs 5/25

Input files expected under results/raw/<experiment_id>/:
- metadata.yaml
- task_events.csv
- robot_state_timeseries.csv
- robot_workload.csv
- allocation_events.csv
- method_runtime.csv
- communication_metrics.csv
- ecosystem_metrics.csv when available
- summary.csv

Create scripts/consolidate_results.py.
The script must:
- read all per-run CSV files under results/raw/
- merge them into results/processed/all_*.csv files
- preserve experiment_id, scenario, strategy, seed, robot_count, and target_count columns
- validate that required columns exist and report missing columns clearly
- avoid fixed robot_1, robot_2, robot_3 assumptions

Create scripts/plot_results.py.
The script must:
- read processed CSV files under results/processed/
- group by strategy, scenario, and seed
- preserve a fixed method order imported from ahe_mrta_recent_comparison_methods.md
- place the proposed method in a consistent final or highlighted position
- avoid fixed robot_1, robot_2, robot_3 assumptions
- save all figures at 300 DPI
- use readable RA-L/Q1 style formatting, font size 8 or 9
- avoid radar charts

Generate the following mandatory PNG files needed to construct the 6 main manuscript figures in results/paper_figures/:

1. system_overview.png
   Source: architecture metadata or a static plotting/diagram script.
   Show Task Manager, Ecosystem Manager/AHE Allocator, Robot Interfaces, Nav2/Gazebo robots, Evaluation Logger, and the rule that robots receive only their own task queues.

2. adaptive_ecosystem_mechanism.png
   Source: a static plotting/diagram script.
   Show context vector, strategy agents, dominance update, cooperation/suppression, weight generation, and event-triggered replanning.

3. baseline_comparison_multi_metric.png
   Source: summary.csv
   Multi-panel figure:
   (a) task_completion_rate
   (b) makespan_s
   (c) average_task_delay
   (d) workload_balance
   (e) deadline_violation_rate
   (f) mean_decision_latency_ms
   Use bar charts with error bars showing std or 95% CI.

4. ablation_comparison.png
   Source: summary.csv
   Compare:
   full_ahe_mrta
   ahe_no_dominance
   ahe_no_cooperation_suppression
   ahe_no_event_replanning
   ahe_fixed_context
   Panels:
   (a) average_task_delay
   (b) workload_balance
   (c) failure_recovery_time
   (d) allocation_instability

5. dominance_evolution.png
   Source: ecosystem_metrics.csv + allocation_events.csv
   Line-plot panels:
   (a) dominance evolution of strategy agents
   (b) context vector evolution
   (c) allocation weight evolution
   Add vertical event markers for robot failure, critical task arrival, and deadline pressure increase when available.

6. failure_recovery.png
   Source: summary.csv + allocation_events.csv
   Panels:
   (a) failure_recovery_time
   (b) recovery success rate if available
   (c) replanning_frequency

7. communication_footprint.png
   Source: communication_metrics.csv
   Panels:
   (a) message_count
   (b) bytes_transmitted or communication_bytes
   (c) topic_count

8. dominance_recovery_panel.png
   Source: dominance_evolution.png + failure_recovery.png or direct CSV plotting.
   This is the preferred Fig. 5 for the manuscript. It should combine interpretable adaptation with recovery behavior.

9. communication_scalability_panel.png
   Source: communication_footprint.png + compact_scalability_sanity.png if available.
   This is the preferred Fig. 6 for the manuscript. It should combine communication efficiency with compact scalability.

Generate the following recommended optional PNG files if the required CSV columns exist:

10. allocation_instability.png
   Source: summary.csv + allocation_events.csv
   Panels:
   (a) allocation_instability
   (b) reassignment count
   (c) queue version changes

11. decision_latency.png
   Source: method_runtime.csv + summary.csv
   Boxplot of runtime_ms and/or mean_decision_latency_ms by strategy.

12. task_completion_timeline.png
   Source: task_events.csv
   Cumulative completed tasks over mission time per strategy.

13. workload_distribution.png
   Source: robot_workload.csv
   Boxplot of completed_tasks per robot by strategy.

14. compact_scalability_sanity.png
   Source: summary.csv + method_runtime.csv
   Compare only 3/15 and 5/25 conditions.

Metric direction must be clearly indicated in axis labels or captions:
- higher is better: task_completion_rate, workload_balance, tasks_completed
- lower is better: makespan_s, average_task_delay, deadline_violation_rate, failure_recovery_time, allocation_instability, mean_decision_latency_ms, communication_bytes, message_count, runtime_ms

Create scripts/statistical_analysis.py:
- read results/processed/all_summary.csv
- compute mean ± std, median, and 95% CI per metric per strategy
- run Shapiro-Wilk normality test when sample size permits
- if normal: ANOVA + Tukey HSD
- if not normal: Kruskal-Wallis + Dunn post-hoc
- compute Cohen's d or Cliff's delta for selected pairwise comparisons
- output results/reports/statistical_tables.md with:
  Table S1: descriptive statistics
  Table S2: normality tests
  Table S3: pairwise p-values
  Table S4: effect sizes

Create scripts/report_generator.py:
- collect all PNG paths from results/paper_figures/ and statistical_tables.md from results/reports/
- write results/reports/summary_report.md
- include Table 1 by importing the method-characterization table from ahe_mrta_recent_comparison_methods.md
- keep only this column structure for Table 1:
  Method name | Online? | Adaptive? | Distributed/decentralized?
- include Table 2 scenario summary without duplicating detailed method descriptions
- include Table 3 main quantitative results with mean ± std
- include a manuscript-output checklist with exactly 6 main figures and 3 main tables
- place supplementary outputs separately from main-paper figures

Do not use fixed robot_1, robot_2, robot_3 columns in summary.csv.
Robot-level information must come from robot_workload.csv.
Do not create rosbag_to_csv.py; log parsing is handled by parse_logs.py.
Use pandas, matplotlib, scipy.stats, and scikit_posthocs.
Stop after Phase 10 and report generated figures, tables, and missing data if any.
```

# 15. Makale Yapısı

RA-L sayfa sınırı kısa olduğu için makale çok odaklı yazılmalıdır.

## 15.1. Önerilen RA-L makale iskeleti

```text
1. Introduction
   - Problem
   - Gap
   - AHE-MRTA idea
   - Contributions

2. Related Work
   - MRTA and online allocation
   - Heuristic and market-based methods
   - Adaptive and failure-aware MRTA
   - Positioning of AHE-MRTA

3. Problem Formulation
   - Robot and task model
   - Online MRTA formulation
   - Objective and constraints

4. Adaptive Heuristic Ecosystem
   - Strategy agents
   - Context vector
   - Dominance update
   - Cooperation and suppression
   - Weight generation
   - Event-triggered replanning

5. ROS 2/Gazebo Implementation and Experimental Setup
   - Architecture
   - Scenario design
   - Baselines and ablations
   - Metrics

6. Results and Discussion
   - Baseline comparison
   - Ablation study
   - Failure and congestion behavior
   - Scalability
   - Dominance evolution analysis

7. Conclusion
   - Main findings
   - Limitations
   - Future work
```

## 15.2. RA-L için figür ve tablo planı

Robot ölçeğini büyütmek deney süresini artırdığı için ana makale figürleri geniş ölçek iddiası yerine **kompakt, açıklanabilir ve bileşen katkısını gösteren** sonuçlara odaklanmalıdır.

### Ana figürler

| Figür  | İçerik                                                       | Amaç                                                                                      |
| ------ | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| Fig. 1 | AHE-MRTA architecture                                        | Mimari katkıyı göstermek                                                                  |
| Fig. 2 | Adaptive heuristic ecosystem mechanism                       | Context vector, dominance, cooperation/suppression ve weight generation akışını göstermek |
| Fig. 3 | Main baseline comparison                                     | 5 robot / 25 hedefte ana yöntem karşılaştırması                                           |
| Fig. 4 | Ablation study                                               | Dominance, cooperation/suppression ve event-triggered replanning katkısını izole etmek    |
| Fig. 5 | Dominance evolution and failure recovery                     | Açıklanabilir adaptasyon ve robustness davranışını birlikte göstermek                     |
| Fig. 6 | Communication footprint and compact scalability sanity check | Düşük iletişim iddiası ve 3/15→5/25 kısa ölçek kontrolü                                   |

### Ana tablolar

| Tablo   | İçerik                                                      | Not                         |
| ------- | ----------------------------------------------------------- | --------------------------- |
| Table 1 | Method name, Online?, Adaptive?, Distributed/decentralized? | Sade tutulacak              |
| Table 2 | Deney senaryoları ve yöntem eşleştirmesi                    | 5/25 ana ölçek vurgulanacak |
| Table 3 | Ana nicel sonuçlar                                          | mean ± std formatında       |

RA-L kısa formatı için ana metinde 6 figürden fazlası kullanılmamalıdır. `completion_timeline`, ayrıntılı `task_distribution` ve geniş istatistik tabloları supplementary veya `summary_report.md` içinde tutulabilir.

## 15.3. RA-L sayfa bütçesi

Makale 6 sayfa hedeflenerek yazılmalıdır. Ek sayfa kullanma olasılığı olsa bile ilk taslak 6 sayfaya göre sıkı tutulmalıdır.

| Bölüm               | Önerilen uzunluk | Not                                |
| ------------------- | ----------------:| ---------------------------------- |
| Introduction        | 0.75 sayfa       | Problem, gap ve katkılar çok kısa  |
| Related Work        | 0.75 sayfa       | Yalnızca konumlandırma odaklı      |
| Problem Formulation | 0.75 sayfa       | Denklem ve kısıtlar sıkı yazılmalı |
| AHE Method          | 1.5 sayfa        | Makalenin ana teknik kısmı         |
| Experiments         | 1.0 sayfa        | Senaryolar, baseline, metrik       |
| Results             | 1.5 sayfa        | Ana grafikler ve ablation          |
| Conclusion          | 0.25 sayfa       | Kısa ve sınırlılık içeren sonuç    |

## 15.4. Makale anlatı stratejisi

Makalenin anlatısı şu sırada ilerlemelidir:

```text
Problem: Online MRTA değişen görev yoğunluğu, deadline, congestion ve robot arızalarında kararsızlaşabilir.
Gap: Mevcut yöntemler çoğunlukla sabit maliyet, bidding, solver veya veri yoğun öğrenme tabanlıdır.
Idea: Klasik heuristic davranışları ekosistem ajanlarına dönüştürülür.
Mechanism: Dominance, cooperation, suppression ve context compatibility ağırlıkları çevrim içi üretir.
Evidence: Seçilmiş baseline ve ablation deneyleri AHE'nin stres altında daha kararlı olduğunu gösterir.
```

Makalede “framework” kelimesi kullanılabilir, ancak sonuçlar algoritmik ve deneysel olmalıdır. Sadece mimari anlatım RA-L için zayıf kalır.

---

# 16. Beklenen Hakem Soruları ve Yanıt Stratejisi

## Soru 1: Bu yöntem yalnızca adaptif weighted assignment değil mi?

Yanıt stratejisi:

AHE-MRTA'da ağırlıklar doğrudan elle ayarlanmaz. Ağırlıklar heuristic dominance vektörü, cooperation matrix, suppression matrix, context compatibility ve failure penalty üzerinden üretilir. Fixed-weight kontrol karşılaştırması ve AHE without dominance ablation'ı bu farkı deneysel olarak gösterir.

## Soru 2: Neden RL kullanılmadı?

Yanıt stratejisi:

Çalışmanın amacı yüksek veri gerektiren policy learning değil, açıklanabilir, düşük hesaplama maliyetli ve ROS 2 üzerinde gerçek zamanlı uygulanabilir bir adaptive heuristic framework geliştirmektir. RL tabanlı yöntemler ileride karşılaştırma veya genişletme olarak eklenebilir.

## Soru 3: Auction-based yöntemlerle fark nedir?

Yanıt stratejisi:

Auction-based yöntemlerde robotlar görevler için teklif üretir. AHE-MRTA ise heuristic davranışların bağlama göre nasıl baskın, işbirlikçi veya baskılanmış hâle geldiğini modelleyen üst düzey bir adaptasyon katmanıdır. Auction-based yöntem baseline olarak kullanılabilir.

## Soru 4: Gazebo simülasyonu yeterli mi?

Yanıt stratejisi:

RA-L için simülasyon yeterli olabilir ancak deneyler çoklu baseline, ablation, failure scenario, congestion scenario, scalability ve decision latency ile desteklenmelidir. Çalışma ayrıca ROS 2/Nav2 üzerinde gerçek robotlara taşınabilecek bir mimariyle tasarlanmalıdır.

## Soru 5: Neden 10 veya 15 robotlu geniş ölçekli deney yapılmadı?

Yanıt stratejisi:

Çalışmanın amacı geniş ölçekli filo optimizasyonu değil, AHE-MRTA'nın çevrim içi adaptasyon, failure recovery, allocation stability ve communication-efficient execution iddialarını kontrollü biçimde test etmektir. Bu nedenle ana deneyler 5 robot / 25 hedef ölçeğinde yürütülür. 3 robot / 15 hedef debug ölçeği, 3/15→5/25 karşılaştırması ise kısa scalability sanity check olarak kullanılır. 10 ve 15 robotlu deneyler, deney süresini ve Gazebo/Nav2 belirsizliğini artırdığı için bu sürümde zorunlu değildir.

## Soru 6: AHE hangi durumda başarısız olur?

Yanıt stratejisi:

AHE çok hızlı değişen görev akışlarında veya aşırı dar geçitlerde replanning frequency yükseldiğinde kararsızlaşabilir. Bu nedenle allocation_instability ve mean_decision_latency açıkça raporlanmalıdır. Sınırlılık olarak gerçek robot deneylerinin gelecekte yapılacağı belirtilmelidir.

## Soru 7: Battery-aware davranış gerçek batarya modeli mi?

Yanıt stratejisi:

Eğer fiziksel enerji modeli kullanılmıyorsa batarya bileşeni “simulated battery state variable” olarak açıkça tanımlanmalıdır. Gerçek enerji tüketimi veya donanım batarya ömrü iddiası yapılmamalıdır.

## Soru 8: AHE merkezi mi, dağıtık mı?

Yanıt stratejisi:

AHE merkezi bir ekosistem yönetim katmanıdır, ancak robotlara düşük boyutlu görev kuyruğu gönderir ve robotlardan yalnızca düşük veri özetleri alır. Bu nedenle çalışma tam dağıtık MRTA iddiası kurmamalıdır. Doğru ifade “communication-efficient centralized adaptation with decentralized execution” olmalıdır.

---

# 17. Uygulanabilirlik Değerlendirmesi

## 17.1. MVP uygulanabilirliği

MVP uygulanabilirliği yüksektir.

MVP kapsamı:

```text
3 TurtleBot3 Waffle Pi
15 hedef
statik karmaşık world
namespace yapısı
Nav2 hedef yürütme
Task Manager
Robot Interface
minimum baseline allocator
basit AHE dominance update
CSV logging
```

## 17.2. Makale sistemi uygulanabilirliği

Makale sistemi orta-yüksek zorluktadır. Deney ölçeği gereksiz büyütülmediği için uygulanabilirlik önceki geniş plana göre daha yüksektir.

Gerekli ekler:

```text
baseline deneyleri
recent comparison baseline deneyleri
ablation deneyleri
failure scenario
mixed stress scenario
compact scalability sanity check
csv/log parsing pipeline
statistical analysis
dominance evolution plots
communication footprint plots
```

## 17.3. En zor teknik parçalar

| Teknik parça                | Zorluk      | Öneri                                                                                |
| --------------------------- | ----------- | ------------------------------------------------------------------------------------ |
| Çok robotlu Nav2            | Yüksek      | Önce tek robot, sonra üç robot, sonra beş robot                                      |
| Gazebo Harmonic integration | Orta-yüksek | ros_gz uyumluluğu açıkça kontrol edilmeli                                            |
| TF namespace yönetimi       | Yüksek      | Her robot için prefix zorunlu olmalı                                                 |
| Rosbag ve metrik çıkarımı   | Orta        | Başta seçici topic kaydı yapılmalı                                                   |
| Geniş robot ölçeği          | Yüksek      | Bu sürümde zorunlu değil; yalnızca zaman kalırsa supplementary stress test yapılmalı |
| AHE formalizasyonu          | Orta        | Dominance, cooperation, suppression net tanımlanmalı                                 |

## 17.4. Sınırlılıklar ve dürüst raporlama

RA-L/Q1 makalesinde sınırlılıklar saklanmamalı, kontrollü biçimde yazılmalıdır:

- Çalışma ilk aşamada Gazebo/ROS 2 simülasyonu ile doğrulanacaktır.
- Battery-aware bileşen gerçek batarya donanım modeli değilse simüle edilmiş durum değişkeni olarak raporlanmalıdır.
- AHE merkezi bir decision layer kullanır; tam dağıtık MRTA iddiası yapılmamalıdır.
- 10 veya 15 robotlu deneyler bu sürümde zorunlu değildir; çalışma ana iddiasını 5 robot / 25 hedef ölçeğinde kontrollü baseline ve ablation deneyleriyle savunur.
- AHE her metrikte en iyi sonucu üretmek zorunda değildir; temel iddia stres altında dayanıklılık, yük dengesi, toparlanma ve açıklanabilir adaptasyondur.

Bu sınırlılıkları açık yazmak makaleyi zayıflatmaz. Aksine hakem açısından yöntemin daha güvenilir ve kontrollü sunulmasını sağlar.

---

# 18. Kısa Geliştirme Yol Haritası

## Hafta 1

```text
Workspace
Custom messages
Test publisher/subscriber
README ve build sistemi
```

## Hafta 2

```text
Gazebo world
Tek robot spawn
Üç robot spawn
Namespace ve TF doğrulama
```

## Hafta 3

```text
Nav2 manuel hedef yürütme
Task Manager
Robot Interface
```

## Hafta 4

```text
Phase 7: Minimum baseline allocator → task_events.csv + summary.csv (otomatik)
Phase 8: AHE-MRTA Ecosystem Manager → dominance CSV + task_events.csv (otomatik)
Phase 9: Ek dosyada tanımlanan karşılaştırma yöntemleri
```

## Hafta 5

```text
AHE Ecosystem Manager
Dominance update
Context vector
Weight generation
```

## Hafta 6

```text
Cooperation/suppression
Event-triggered replanning
Failure scenario
Congestion scenario
```

## Hafta 7

```text
5 robot / 25 hedef ana baseline deneyleri
Recent comparison yöntemleri
Ablation deneyleri
Failure ve mixed stress koşuları
Repeat seeds
Seçici rosbag/log kayıtları
```

## Hafta 8

```text
Phase 10: plot_results.py → paper_figures/*.png
Phase 10: statistical_analysis.py → statistical_tables.md
Phase 10: report_generator.py → summary_report.md
Table 1/2/3 çıktıları
RA-L LaTeX taslağı ve figür yerleşimi
```

Bu takvim ideal şartlarda geçerlidir. Çok robotlu Nav2 ve Gazebo entegrasyonu beklenenden uzun sürebilir.

---

# 19. Makale İçin Nihai Kontrol Listesi

## 19.1. Yenilik kontrolü

- [ ] Makalenin ana iddiası tek cümlede `explainable, lightweight, communication-efficient adaptive heuristic ecosystem` olarak kuruluyor mu?
- [ ] AHE fixed-weight assignment yaklaşımından matematiksel olarak ayrılıyor mu?
- [ ] Dominance update denklemi açık mı?
- [ ] Cooperation matrix tanımlı mı?
- [ ] Suppression matrix tanımlı mı?
- [ ] Context vector bileşenleri ölçülebilir mi?
- [ ] AHE ağırlıkları nasıl üretiyor açık mı?
- [ ] Ablation deneyleri katkıları izole ediyor mu?

## 19.2. Deney kontrolü

- [ ] Aynı seed seti tüm yöntemlerde kullanıldı mı?
- [ ] En az 20 tekrar yapıldı mı?
- [ ] Ek yöntem dosyasında tanımlanan karşılaştırma yöntemleri uygulandı mı?
- [ ] Tüm karşılaştırma yöntemleri aynı seed/görev/failure setiyle çalıştı mı?
- [ ] AHE ablation'ları var mı?
- [ ] Failure scenario var mı?
- [ ] Congestion scenario var mı?
- [ ] Compact scalability sanity check var mı?

## 19.3. ROS 2/Gazebo kontrolü

- [ ] ROS 2 Jazzy kullanılıyor mu?
- [ ] Gazebo Harmonic kullanılıyor mu?
- [ ] ros_gz uyumluluğu kontrol edildi mi?
- [ ] Her robotun namespace'i ayrı mı?
- [ ] TF frame çakışması yok mu?
- [ ] Nav2 her robot için ayrı çalışıyor mu?
- [ ] Robotlar yalnızca kendi task queue mesajını alıyor mu?
- [ ] Ecosystem debug state robotlara gönderilmiyor mu?

## 19.4. Veri ve grafik kontrolü

**CSV pipeline (her deney fazı sonunda):**

- [ ] `metadata.yaml` her deney dizininde var mı?
- [ ] `task_events.csv` üretildi mi?
- [ ] `summary.csv` üretildi mi ve sabit `robot_1`, `robot_2`, `robot_3` sütunları kullanılmadı mı?
- [ ] `robot_workload.csv` üretildi mi?
- [ ] `allocation_events.csv` üretildi mi?
- [ ] `method_runtime.csv` üretildi mi?
- [ ] `communication_metrics.csv` üretildi mi?
- [ ] `ecosystem_metrics.csv` full AHE ve ablation koşularında üretildi mi?

**PNG pipeline (Phase 10):**

- [ ] `baseline_comparison_multi_metric.png` üretildi mi?
- [ ] `ablation_comparison.png` üretildi mi?
- [ ] `dominance_evolution.png` üretildi mi?
- [ ] `failure_recovery.png` üretildi mi?
- [ ] `allocation_instability.png` üretildi mi?
- [ ] `communication_footprint.png` üretildi mi?
- [ ] `compact_scalability_sanity.png` üretildi mi? (opsiyonel)

**İstatistiksel tablolar (Phase 10):**

- [ ] Shapiro-Wilk testi yapıldı mı?
- [ ] ANOVA/Kruskal-Wallis yapıldı mı?
- [ ] Pairwise karşılaştırmalar ve p-değerleri var mı?
- [ ] Effect size (Cohen's d / Cliff's delta) hesaplandı mı?
- [ ] `statistical_tables.md` Table I / II / III formatında mı?
- [ ] `summary_report.md` üretildi mi?

---

# 20. Temel Kaynaklar

Bu liste makale için başlangıç kaynak setidir. Nihai makale öncesinde 2023 sonrası güncel MRTA, online allocation, failure-aware allocation, event-triggered coordination ve learning-assisted MRTA literatürü ayrıca taranmalıdır.

## MRTA temel kaynakları

- Gerkey, B. P., & Matarić, M. J. (2004). A formal analysis and taxonomy of task allocation in multi-robot systems. *International Journal of Robotics Research, 23*(9), 939–954.

- Korsah, G. A., Stentz, A., & Dias, M. B. (2013). A comprehensive taxonomy for multi-robot task allocation. *International Journal of Robotics Research, 32*(12), 1495–1512.

## Fault-tolerant ve cooperative MRTA

- Parker, L. E. (1998). ALLIANCE: An architecture for fault tolerant multirobot cooperation. *IEEE Transactions on Robotics and Automation, 14*(2), 220–240.

- Parker, L. E. (2008). Distributed intelligence: Overview of the field and its application in multi-robot systems. *Journal of Physical Agents*.

## Market-based ve auction tabanlı MRTA

- Zlot, R., Stentz, A., Dias, M. B., & Thayer, S. (2002). Multi-robot exploration controlled by a market economy. *IEEE International Conference on Robotics and Automation*.

- Kalra, N., Ferguson, D., & Stentz, A. (2005). Hoplites: A market-based framework for planned tight coordination in multirobot teams. *IEEE International Conference on Robotics and Automation*.

- Tang, F., & Parker, L. E. (2007). A complete methodology for generating multi-robot task solutions using ASyMTRe-D and market-based task allocation. *IEEE International Conference on Robotics and Automation*.

## Deadline ve zaman kısıtlı görevler

- Liu, C. L., & Layland, J. W. (1973). Scheduling algorithms for multiprogramming in a hard-real-time environment. *Journal of the ACM, 20*(1), 46–61.

- Alighanbari, M., Kuwata, Y., & How, J. P. (2003). Coordination and control of multiple UAVs with timing constraints and loitering. *American Control Conference*.

## Energy-aware allocation

- Mei, Y., Lu, Y.-H., Hu, Y. C., & Lee, C. S. G. (2005). Energy-efficient motion planning for mobile robots. *IEEE International Conference on Robotics and Automation*.

- Dasgupta, P., & Woosley, B. (2013). Multiagent coalition formation for energy-aware task allocation. *International Journal of Distributed Sensor Networks*.

## 2023 sonrası taranması gereken güncel hatlar

Nihai makaleye geçmeden önce aşağıdaki güncel kaynak hatları sistematik biçimde taranmalıdır:

- Recent MRTA systematic reviews and surveys, especially 2024 sonrası MRTA SLR çalışmaları.
- SMT-based dynamic MRTA çalışmaları. Bu hat deadline ve constraint guarantee açısından güçlüdür.
- Real-time warehouse/dynamic task allocation çalışmaları. Bu hat throughput ve online task stream açısından karşılaştırma sağlar.
- RL, MARL, GNN, graph transformer veya attention-based multi-robot scheduling çalışmaları. Bu hat AHE'nin açıklanabilir ve düşük veri gerektiren alternatif olarak konumlandırılması için gereklidir.
- Fault-tolerant ve recovery-aware MRTA çalışmaları. Recovery Coordinator agent bu literatürle ilişkilendirilmelidir.

Nihai related work yazılırken eski klasik MRTA kaynakları temel/taksonomi için kullanılmalı, özgünlük karşılaştırması ise güncel 2023 sonrası çalışmalarla yapılmalıdır.

## Teknik ve yayın formatı kaynak notları

- IEEE RA-L author information: RA-L yazıları iki sütunlu kısa formatta hazırlanır ve genellikle 6 sayfa, en fazla 2 ek sayfa yapısına sahiptir.
- ROS 2 Jazzy ve Gazebo Harmonic kullanımı için `ros_gz` entegrasyonu dikkate alınmalıdır.
- Gazebo Classic varsayımları yeni Gazebo Harmonic ortamına doğrudan taşınmamalıdır.

---

# 21. Son Karar

Bu proje RA-L/Q1 SCI-E çerçevesinde geliştirilebilir ve doğru deney sonuçlarıyla güçlü bir makale adayına dönüşebilir. Mevcut hali bir “tamamlanmış makale” değil, RA-L odaklı uygulanabilir araştırma ve geliştirme planıdır.

En kritik başarı koşulları şunlardır:

1. AHE dominance, cooperation ve suppression matematiği kodda gerçekten çalışmalı ve deney loglarında görünmelidir.
2. Ek yöntem dosyasında tanımlanan karşılaştırma yöntemleriyle adil karşılaştırma yapılmalıdır.
3. AHE without dominance, AHE without cooperation/suppression ve no event-triggered replanning ablation'ları katkıları izole etmelidir.
4. Ana sonuçlar 5 robot / 25 hedef ölçeğinde verilmelidir; 3/15→5/25 karşılaştırması yalnızca kısa compact scalability sanity check olarak kullanılmalıdır.
5. Makale “yeni bir heuristic” değil, “heuristic etkileşimini çevrim içi evrimleştiren açıklanabilir ve düşük veri paylaşımlı MRTA framework'ü” olarak yazılmalıdır.
6. Claude Code geliştirmesi her fazda `colcon build`, launch testi, topic doğrulama ve metrik doğrulama ile ilerlemelidir.

Bu koşullar sağlanırsa AHE-MRTA, yalnızca görev atama yapan bir simülasyon değil; açıklanabilir, adaptif, düşük veri paylaşımlı, event-triggered ve dayanıklı çevrim içi MRTA framework'ü olarak savunulabilir.

Nihai makale iddiası şu cümleye indirgenmelidir:

```text
AHE-MRTA enables robust online multi-robot task allocation by evolving the relative dominance and interaction of classical heuristic behaviors under dynamic task arrivals, failures, congestion, and deadline pressure, while preserving a lightweight communication-efficient ROS 2 execution architecture.
```

## Nihai CSV-first veri arşivi hedefi

Bu ana MD'nin güncellenmiş veri stratejisi, bütün deney verilerini yalnızca final figür üretimi için değil, ileride istenebilecek her türlü ek grafik ve metrik için yeniden kullanılabilir şekilde saklamayı hedefler.

Zorunlu veri arşivi çıktısı:

```text
results/raw/<experiment_id>/
results/processed/all_*.csv
results/paper_figures/*.png
results/reports/statistical_tables.md
results/reports/summary_report.md
```

Bu yapı kurulduğunda yeni bir grafik talebi geldiğinde izlenecek yol şudur:

```text
Yeni grafik fikri
      ↓
processed CSV kontrolü
      ↓
eksik kolon yoksa plot_results.py'ye yeni panel ekleme
      ↓
Gazebo deneylerini yeniden çalıştırmadan yeni PNG üretme
```

## Nihai Q1/RA-L çıktı hedefi

```text
Ana makale: 6 figür + 3 tablo
Supplementary/repository: 4 istatistiksel ek tablo + opsiyonel detay figürleri
Deney çekirdeği: 5 robot / 25 hedef, 20 seed
Debug çekirdeği: 3 robot / 15 hedef, 5 seed
Ana savunma: dominance + cooperation + suppression + event-triggered replanning
Ana başarı metrikleri: workload balance, failure recovery, allocation instability, stress altında delay, dominance evolution, communication footprint
```
