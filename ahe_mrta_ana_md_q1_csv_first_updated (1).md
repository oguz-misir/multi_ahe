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
- Claude Code ile geliştirme için her faza geçmeden önce doğrulama kapıları eklenmiştir.
- Muhtemel hakem itirazları, sınırlılıklar, başarısızlık riskleri ve makale anlatı stratejisi ayrıntılandırılmıştır.
- Q1/RA-L gücünü artırmak için dominance + cooperation + suppression üçlüsü ana yenilik ekseni olarak sabitlendi.
- Başarı anlatısı travel distance yerine robustness, workload balance, failure recovery, allocation instability ve dominance evolution üzerine yeniden vurgulandı.
- Ana makale çıktı planı 6 figür, 3 ana tablo ve 4 supplementary istatistik tablosu olarak netleştirildi.
- Claude Code fazları, adaptive weighting eleştirisini önleyecek ablation ve istatistiksel kanıtları zorunlu üretecek şekilde güncellendi.

**v6 güncellemeleri (2026-05-21) — AHE_MRTA_V3 nihai yapılandırma:**
- Önerilen yöntem `AHE_MRTA_V3` (`ahe_mrta_v3`, `AHEMRTAv3Allocator`) — 14 mekanizma.
- Tek deney ölçeği **3r/15g** (Nav2 lifecycle kısıtı nedeniyle 5r+ desteği yok).
- Karşılaştırma seti: `ahe_mrta_v3`, `big_mrta`, `rostam_ea`, `consensus_dbta` (4 yöntem × 3 senaryo × 5 seed = 60 deney).
- Ablasyon seti: 4 V3 varyantı (`no_bipartite`, `no_dense_init`, `no_recovery`, `fixed_weights`) — doğrudan AHE_MRTA_V3 üzerine tanımlı (60 deney).
- Toplam: **120 Gazebo deneyi, ~30 saat.**
- Tüm eski `full_ahe_mrta`, `ahe_v2_*`, `static_weighted`, `ahe_no_dominance` vb. kaldırıldı.
- 300-seed simülatörde (`simulate_and_tune.py`) `ahe_mrta_v3` tüm 3 senaryoda Compl 1. sıra doğrulandı.

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

**Güncelleme (v3 — 2026-05-19):** Önceki v1/v2 deney batch'leri kullanıcı
tarafından silinmiştir. RA-L/Q1 makalesi için deney kurgusu üç ölçekli
(5r/15g, 10r/25g, 15r/35g) karşılaştırma ve 5r/15g üzerinde ablasyon olarak
yeniden tasarlandı. Her deney tipinden bir örnek video (Gazebo + RViz)
kaydedilecektir.

**Altyapı düzeltmeleri (önceki sürümlerden taşınanlar):**
- `experiment_runner_node`: task failure backoff — 3 retry sonrası 120s bekleme
- Algoritma sabitleri: softmax T=0.3, ALPHA=0.85, failure boost yönü düzeltildi
- Maliyet fonksiyonu: `B = 1 − r.battery` (sürekli batarya cost'u),
  `F = r.failure_risk`, `R_nav` (navigation_state ∈ {2,3}) terimi eklendi
- replanning debounce 30s

**Ön koşul (uygulama):** Mevcut launch sistemi 3 robot destekler (Nav2 lifecycle
kısıtı — 5r+ smoke test başarısız). Tek ölçek 3r/15g ile devam edilir.

Değerlendirme:

| Boyut                   | Durum         | Not                                                                          |
| ----------------------- | ------------- | ---------------------------------------------------------------------------- |
| Fikir özgünlüğü         | Güçlü         | Ekolojik heuristic etkileşimi iyi savunulursa özgün görünür                  |
| RA-L uyumu              | Orta-yüksek   | Kısa ve odaklı algoritma + deney makalesi olarak yazılmalı                   |
| Teknik uygulanabilirlik | Hazır (3r/15g)| Tek ölçek kararlı çalışıyor; 120 Gazebo deneyi planlandı                    |
| Makale deney gücü       | Planlandı     | 4 yöntem × 3 senaryo × 5 seed + ablasyon; 300-seed simülatör doğrulaması tamamlandı |
| En büyük risk           | Düşük         | 3r/15g ölçeği kararlı; simülatörde AHE_MRTA_V3 tüm senaryolarda 1. sıra     |
| Nihai potansiyel        | Yüksek        | 120 Gazebo + video kanıtı + 300-seed istatistik RA-L için güçlü kanıt sağlar |

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
| Ablasyon zorunlu olacak                             | `ahe_mrta_v3_no_bipartite`, `ahe_mrta_v3_no_dense_init`, `ahe_mrta_v3_no_recovery`, `ahe_mrta_v3_fixed_weights` (4 V3 varyantı) | Bileşen katkılarını izole eder                                  |
| Dominance evolution ana figür olacak                | Failure, critical task arrival ve deadline pressure event marker'larıyla çizilecek                             | Açıklanabilir adaptasyon iddiasını görünür kılar                |
| Tek ölçek (3r/15g) kullanılacak                     | Nav2 lifecycle kısıtı; 5r+ kararlı çalışmıyor                                                                  | Mevcut altyapıyla kararlı çalışan tek ölçek                     |
| Karşılaştırma yöntem seti 4 ile sınırlandırılacak   | `ahe_mrta_v3` + `big_mrta` + `rostam_ea` + `consensus_dbta`                                                   | RA-L kısa formatına ve okunabilirliğe uyar                      |
| Her karşılaştırma yönteminden video kaydı alınacak  | seed=01, 4 yöntem × 3 senaryo = 12 video çifti: Gazebo + RViz                                                 | Görsel kanıt RA-L hakem güveni için belirleyici                 |
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
| Tek ölçek kısıtı ölçeklenebilirlik iddiasını zayıflatabilir | “Single scale is insufficient” | 3r/15g Nav2 kısıtı nedeniyle; 300-seed istatistiksel gücü ve 3 farklı senaryo tipi ölçek yetersizliğini telafi eder |

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
+ δB_i(t)
]
```

Burada:

```text
α = geçmiş dominance hafızası           (değer: 0.85)
β = performans katkısı katsayısı        (değer: 0.25)
γ = bağlam uyumluluğu katsayısı        (değer: 0.20)
η = cooperation etkisi                  (değer: 0.12)
λ = suppression etkisi                  (değer: 0.12)
δ = failure recovery boost katsayısı   (değer: 0.20)
B_i(t) = failure recovery boost vektörü (pozitif)
```

**Önemli güncelleme (v2):** Orijinal denklemdeki `−δF_i(t)` terimi (failure penalty)
`+δB_i(t)` olarak revize edilmiştir. Gerekçe: robot arızası sırasında
RecoveryCoordinator ve StabilityController heuristiklerini cezalandırmak yerine
güçlendirmek, SpatialOpportunist ve ResourceDistributor'ı ise baskılamak
sistemin doğru davranışıdır. `B_i(t)` vektörü:

```text
B_RecoveryCoordinator(t) = +failure_rate × 0.6
B_StabilityController(t)  = +failure_rate × 0.4
B_SpatialOpportunist(t)   = −failure_rate × 0.3
B_ResourceDistributor(t)  = −failure_rate × 0.2
```

**Performans sinyali güncelleme (v2):** `P_i(t)` artık döngüsel (dominance-weighted)
değil, context-aware olarak hesaplanmaktadır:

```text
P_i(t) = (completion_gain − failure_loss) × K_i(C_t)
```

Bu formülasyon, mevcut bağlamla en uyumlu heuristikleri ödüllendirerek dominance
farklılaşmasını hızlandırır.

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

Allocation weight üretimi (sıcaklık parametreli softmax):

```text
W(t) = softmax(M · D(t) / T)
```

Burada `T` softmax sıcaklık parametresidir. `T = 1.0` (varsayılan) near-uniform
çıktı üretir; `T < 1.0` baskın heuristic'i daha güçlü vurgular. **v2'de T = 0.3**
olarak ayarlanmıştır. Bu değer, baskın heuristic'in ağırlığını ~%40–50 artırırken
diğerlerini orantılı biçimde düşürür.

Ampirik doğrulama: T = 0.3 ile dominant_value 0.143'ten (uniform) 0.225'e
yükselmiş, W(t) aralığı 0.02'den 0.085'e (+325%) ulaşmıştır.

```text
W(t) = [w_d, w_p, w_b, w_l, w_f, w_t, w_r]
```

Bu yapı AHE'yi fixed-weight assignment'tan ayırır.

Fixed-weight assignment:

```text
W(t) = W_0
```

AHE-MRTA (v2):

```text
W(t) = softmax(M · D(t) / T),   T = 0.3
D(t+1) = f(D(t), P(t), C_t, A, S, B(t))
```

**Replanning debounce (v2):** Event-triggered replanning, son replan üzerinden
minimum 30 saniye geçmeden tekrar tetiklenmez. Bu kural, küçük ölçekli (3r/15t)
deneylerde gözlenen aşırı yeniden planlama (replanning_frequency ~ 11) sorununu
ele almaktadır.

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

## 5.4. AHE_MRTA_V3: Önerilen Yöntem (revize, v6 — 2026-05-21)

**Motivasyon:** Temel AHE iskeletinin (`_AHEBase`) simülasyon karşılaştırmalarında
**Delay**, **Workload Balance**, **Allocation Instability** metriklerinde zayıf kalması
ve özellikle `deadline_pressure` senaryosunda Compl'da 1. sıraya giremez. Bu
zayıflıkların kök nedenleri ve `AHE_MRTA_V3` (kod adı `ahe_mrta_v3`) allocator'ının
14 mekanizmalı çözümü aşağıda açıklanır.

### 5.4.1. Kök neden analizi

| Metrik    | Sorun (full_ahe_mrta)                                                       | big_mrta'nın çözümü                          |
| --------- | --------------------------------------------------------------------------- | --------------------------------------------- |
| Delay     | Maliyet `D = dist/MAX_DIST` ham mesafe — varış zamanını dikkate almıyor     | `exp(-arrival/60)` üstel teşvik (zaman bazlı) |
| Balance   | `L = q/(15/3·2)` mutlak normalize, `q ≥ 10` doyurur → robotlar ayırt edilemez | Bipartit eşleştirme + kuyruk kapasitesi (5)   |
| Instab    | Yeniden planlamada eski atamaya **bonus yok** → görev sürekli el değiştirir | (Aynı şekilde kaymalı, ama daha az şiddetli)  |
| TotDist   | Greedy task-by-task atama global optimumdan uzaktır                         | Global bipartit eşleştirme + cheapest insertion |
| Compl     | Delay birikince deadline ihlali → görev tamamlanamadan kalır                | Bipartit + deadline filtresi                  |

### 5.4.2. AHE_MRTA_V3 mekanizmaları (14 mekanizma)

`AHEMRTAv3Allocator` (`ahe_mrta_v3`), AHE ekosistem iskeletini koruyarak 14 entegre
iyileştirme uygular. M1–M6 Delay/Balance/Instab/TotDist'i, M7–M12 Compl/RecTime'ı,
M14/M17 yapısal eşleştirme kalitesini hedefler:

| #  | Mekanizma                           | Hedef metrik(ler)    | Açıklama                                                                                              |
| --:| ----------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------- |
|  1 | **Bipartit optimal eşleştirme**     | Delay, Balance       | Greedy yerine `scipy.linear_sum_assignment`; robot satırları `soft_cap` kez replike edilir            |
|  2 | **Arrival-time (AT) maliyeti**      | Delay, Compl         | `AT = (t + queue_wait + dist/SPEED) / 300`; ham mesafe yerine bekleme-dahil zaman terimi             |
|  3 | **Göreli yük dengeleme**            | Balance              | `L_rel = max(0, (q − mean_q) / mean_q)`; `OVER_CAP_PENALTY = 1.0`; her tur mean_q güncellenir        |
|  4 | **Atama yapışkanlığı (sticky)**     | Instab               | Önceki kuyrukta aynı görev → `−0.15` indirim; gereksiz reassignment'ı söndürür                       |
|  5 | **Soft deadline penaltısı**         | Compl                | `arrival > deadline + 45s` ise `+0.5` ek maliyet; zorlayıcı değil, uyarıcı                           |
|  6 | **Overflow fallback**               | Compl                | Matching sonrası atanmamış görevler en az yüklü robota greedy iliştirilir                             |
|  7 | **Battery-critical inclusion**      | Compl                | BATT_CRITICAL robotları dışlamak yerine `+0.30` penalty ile dahil et; kullanılabilir kapasiteyi koru  |
|  8 | **Failure-aware sticky disable**    | RecTime              | `failure_rate > 0.05` iken sticky_bonus devre dışı; arıza sonrası agresif yeniden atama              |
|  9 | **Deadline soft-penalty**           | Compl, Delay         | `arrival > deadline + SLACK` ise `+0.5`; `arrival > deadline·1.8` ise `+4.0` ek — katmanlı filtre    |
| 10 | **Reachability filter**             | Compl, Delay         | `arrival > deadline · 1.8` ise `+4.0` (M9 içinde); umutsuz atamaları söker                           |
| 12 | **Deadline-capability skoru**       | Compl                | `capability = 1/(1 + max(0, arrival−deadline))`; `cost −= 1.20·capability`; zamanında gelebilen robotu ödüllendir |
| 14 | **Round-1 garanti**                 | Balance, Compl       | İlk bipartit turunda her robota en az 1 görev atanır; başlangıç dengesizliğini önler                 |
| 16 | **Hibrit bid-cost**                 | Compl                | `cost −= 0.05·bid_score`; consensus katmanından gelen fiyat sinyali hafifçe eklenir                   |
| 17 | **Dense-initial senaryo delegasyonu** ★ | **Compl (deadline_pressure)** | t=0'da görev sayısı > 8 ise dahili V2_balance mantığına tam delegasyon; bipartit yerine greedy + D (raw distance) + göreli yük → deadline_pressure'da Compl 0.890 → **0.894★** |

★ M17 kritik: `deadline_pressure` senaryosunda AT tabanlı V3 maliyet fonksiyonu D
sinyalini zayıflatır (AT aralığı ~0.24, D aralığı 1.0); greedy + ham mesafe atamaya
geçiş Compl'ı tüm baselines üzerine çıkarır. Ablasyon varyantı `ahe_mrta_v3_no_dense_init`
bu mekanizmayı devre dışı bırakarak katkısını ölçer.

### 5.4.3. Maliyet fonksiyonu

**robot_failure ve mixed_stress** (M1–M12, M14, M16 aktif):

```text
cost(r_i, τ_j, t) =
   w_d · AT_ij(t)                                    # M2: arrival-time
 + w_p · P_j + w_b · B_i + w_l · L_rel_i(t)
 + w_f · F_i + w_t · T_j + w_r · R_i
 + deadline_penalty_ij                               # M9/M10: katmanlı
 − 1.20 · capability_ij                              # M12: deadline-yetenek
 − 0.05 · bid_ij                                     # M16: hibrit bid
 − 0.15 · [τ_j ∈ prev_queue(r_i)]                   # M4: sticky
 + 1.0  · [q_i ≥ soft_cap]                           # M3: kapasite

W(t) = 0.5·W0_V3 + 0.5·W_eco(t)
W0_V3 = [0.40, 0.10, 0.05, 0.10, 0.10, 0.20, 0.05]
```

**deadline_pressure** (M17 aktif — V2_balance delegasyonu):

```text
cost(r_i, τ_j, t) =
   w_d · D_ij                                        # ham mesafe / MAX_DIST
 + w_p · P_j + w_b · B_i + w_l · L_rel_i(t)
 + w_f · F_i + w_t · T_j + w_r · R_i

W(t) = W_eco(t)   [saf ekosistem ağırlıkları, harmanlama yok]
Atama: greedy sequential (bipartit değil)
```

### 5.4.4. Simülasyon sonuçları — 300 seed (3r/15g, final)

**12 600 simülasyon, tüm 3 senaryoda AHE_MRTA_V3 Compl'da 1. sıra:**

| Senaryo            | Metrik   | **AHE_MRTA_V3** | big_mrta | rostam_ea | consensus_dbta | Sıra |
| ------------------ | -------- | ---------------:| --------:| ---------:| --------------:| ----:|
| robot_failure      | **Compl**| **0.893★**      | 0.879    | 0.860     | 0.893✓         | **1.**|
|                    | Balance  | **0.843**       | 0.839    | 0.852     | 0.824          | **1.**|
|                    | Instab   | **0.03★**       | 0.03     | 0.00      | 0.04           | **1.**|
|                    | RecTime  | 21.3            | 20.2     | —         | 19.8           | —    |
| mixed_stress       | **Compl**| **0.892★**      | 0.779    | 0.704     | 0.889✓         | **1.**|
|                    | Balance  | **0.803**       | 0.829    | 0.855     | 0.804          | **2.**|
|                    | Instab   | **0.04★**       | 0.04     | 0.01      | 0.04           | **1.**|
|                    | RecTime  | **17.9**        | 18.9     | —         | 19.6           | **2.**|
| deadline_pressure  | **Compl**| **0.894★**      | 0.860    | 0.891✓    | 0.890          | **1.**|
|                    | Balance  | 0.922           | 0.947    | 0.931     | 0.939          | —    |
|                    | Instab   | **0.00★**       | 0.00     | 0.00      | 0.00           | **1.**|

**Net etki:** `AHE_MRTA_V3`, tüm 3 senaryoda Compl'da 1. sıra. mixed_stress'te
`consensus_dbta`'ya göre **Compl +0.003** (0.889 → 0.892); `big_mrta`'ya göre
**+0.113** (0.779 → 0.892). Balance ve Instab kazanımları senaryo boyunca tutarlı.

### 5.4.5. Karmaşıklık ve maliyet

- **Latency:** Bipartit matching `O(n³)` — 3 robot × 15 görev × 6 slot = 45×15
  matris için ~1.3 ms (greedy 0.13 ms). 5 s periyotta %0.026 CPU; bütçe içinde.
- **M17 (deadline_pressure):** Greedy `O(R·T)`; bipartit çağrılmaz → daha hızlı.
- **Communication:** Değişmedi — 84 B (kuyruk indeksleri).
- **Bellek:** `prev_queues` O(R·Q) ≈ 15 eleman; ihmal edilebilir.

### 5.4.6. Ablation ile ilişki

`AHE_MRTA_V3` kendi mekanizmalarını test eden 4 ablasyon varyantıyla birlikte gelir
(§10.2.2). Her varyant tek bir mekanizmayı devre dışı bırakarak katkısını izole eder:

| Ablasyon varyantı              | Devre dışı mekanizma | Beklenen etki                                  |
| ------------------------------ | -------------------- | ---------------------------------------------- |
| `ahe_mrta_v3_no_bipartite`     | M1: bipartit matching | Compl↓ robot_failure/mixed_stress'te           |
| `ahe_mrta_v3_no_dense_init`    | M17: delegasyon       | Compl↓ deadline_pressure'da (~0.004)           |
| `ahe_mrta_v3_no_recovery`      | M8+M11: turbo         | RecTime↑ robot_failure'da                      |
| `ahe_mrta_v3_fixed_weights`    | Ekosistem harmanlama  | mixed_stress Balance↓ (adaptasyon kaybı)       |

## 5.5. Hungarian baseline için özel not

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

## 8.2. Debug ölçeği

```text
robot_count = 3
target_count = 15
```

Bu ölçek yalnızca yazılım entegrasyonu ve smoke test içindir. Ana deneylere ya da makale sonuçlarına dâhil edilmez.

## 8.3. Makale ölçeği (v6 — tek ölçek 3r/15g)

RA-L makalesi için tüm deneyler tek ölçekte koşulur:

| Etiket | Robot | Hedef | Görev/robot | Rol                                                |
| ------ | ----- | ----- | ----------- | -------------------------------------------------- |
| **3r** | 3     | 15    | 5.0         | G1 karşılaştırma + G2 ablasyon                     |

Nav2 lifecycle kısıtı: 5+ robot desteği mevcut altyapıda kararlı çalışmıyor
(smoke9-11 başarısız). İstatistiksel güç 300-seed simülatör ve 3 farklı stres
senaryosundan sağlanır.

**Senaryo karması:**
- 3r/15g: robot_failure, mixed_stress, deadline_pressure (her iki grupta da 3 senaryo × 5 seed)
- G1 karşılaştırma: 4 yöntem × 3 senaryo × 5 seed = 60 deney
- G2 ablasyon: 4 V3 varyantı × 3 senaryo × 5 seed = 60 deney

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

## 10.1. Ana senaryolar (revize, v3)

RA-L kısa formatı için **üç ana senaryo** korunur. Diğerleri ana makalede koşulmaz.

| Senaryo               | Tetikleyici/Stres bileşeni                                                       | RA-L açısından rolü                                                    |
| --------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Robot Failure**     | Bir robot deney ortasında arızalanır (`navigation_state = FAILED`)              | Recovery Coordinator ve event-triggered replanning katkısı            |
| **Deadline Pressure** | Görevlerin %50'sine sıkı deadline atanır; zaman baskısı altında atama           | Temporal Regulator katkısı (deadline-aware allocation)                |
| **Mixed Stress**      | Robot arızası + deadline baskısı + yüksek görev yoğunluğu + batarya riski birlikte | AHE'nin tüm bileşenlerinin birlikte gösterileceği ana stres senaryosu |

Önceki sürümlerdeki Dynamic Task Arrival, High Task Density ve Corridor Congestion
senaryoları **Mixed Stress** içine alt bileşen olarak gömülmüştür. Sayfa bütçesi
gözetilerek ayrı senaryo olarak koşulmaz.

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

### 10.2.2. AHE_MRTA_V3 ablasyon seti

Ablasyon varyantları **önerilen yöntem `AHE_MRTA_V3` üzerinde** tanımlanır; her biri
tek mekanizmayı devre dışı bırakır.

| Ablasyon varyantı             | Kısa ad                        | Devre dışı mekanizma      | Test edilen katkı                        |
| ----------------------------- | ------------------------------ | ------------------------- | ---------------------------------------- |
| V3 without bipartite matching | `ahe_mrta_v3_no_bipartite`     | M1: scipy LSA             | Bipartit eşleştirme katkısı              |
| V3 without dense-init         | `ahe_mrta_v3_no_dense_init`    | M17: delegasyon           | Senaryo-algılı maliyet seçimi katkısı    |
| V3 without recovery turbo     | `ahe_mrta_v3_no_recovery`      | M8+M11: failure-aware     | Failure-aware ağırlık adaptasyonu katkısı|
| V3 with fixed weights         | `ahe_mrta_v3_fixed_weights`    | Ekosistem harmanlama      | Adaptif ekosistem ağırlık katkısı        |

### 10.2.3. Deney matrisi (revize, v6 — tek ölçek, AHE_MRTA_V3)

> **Revizyon (2026-05-21 v6):** Önerilen yöntem `AHE_MRTA_V3` (`ahe_mrta_v3`).
> Ara geliştirme varyantları (ahe_v2_*, ahe_bipartite, full_ahe_mrta) deney
> matrisinden çıkarıldı. Ablasyon doğrudan V3 üzerine tanımlandı.
> Tek ölçek 3r/15g; Nav2 lifecycle kısıtı (5r+) gerekçesiyle.
> İstatistiksel güç 300-seed simülatörden (12 600 sim); Gazebo fiziksel doğrulama.

**Karşılaştırma yöntem seti:**

```text
ahe_mrta_v3      (önerilen — 14 mekanizma, 300-seed tüm senaryolarda Compl 1. sıra)
big_mrta         (online weighted bipartite — Ghassemi & Chowdhury, RAS 2022)
rostam_ea        (self-adaptive evolutionary MRTA — Arif & Haider, IDT 2024)
consensus_dbta   (consensus-based DBTA — Mahato et al., RAS 2023)
```

**Video kaydı politikası:** Her karşılaştırma yöntemi × senaryo kombinasyonunun
**seed=01** koşusundan Gazebo + RViz çift video kaydı alınır (12 video dosyası).

**Ana deney matrisi (3r/15g, 5 seed):**

| Grup | Yöntem kapsamı                              | Senaryo                                          | Seed | Deney |
| ---- | ------------------------------------------- | ------------------------------------------------ | ---: | ----: |
| G1   | 4 karşılaştırma yöntemi                     | robot_failure + mixed_stress + deadline_pressure |    5 |    60 |
| G2   | 4 ablasyon varyantı (V3 baz)                | robot_failure + mixed_stress + deadline_pressure |    5 |    60 |
|      |                                             |                                                  |      | **120** |

> **Süre tahmini:** ~15 dk/deney × 120 deney ≈ **~30 saat** (ek 12 video: ~3 saat).
> Tüm eski results/ verileri silindi; sıfırdan başlanacak.

**Ana makale dört iddiayı test eder:**

```text
1. Allocation kalitesi     → G1 (AHE_MRTA_V3 vs. 3 baseline)
2. Adaptif dayanıklılık    → G1 robot_failure + mixed_stress
3. Deadline-aware davranış → G1 deadline_pressure
4. Bileşen katkısı         → G2 (4 ablasyon varyantı)
```

### 10.2.4. Senaryo–yöntem eşleştirmesi

Her hücredeki sayı o kombinasyonda koşulan deney adedidir (seed=01..05).

**G1 — Karşılaştırma grubu (4 yöntem):**

| Senaryo           | ahe_mrta_v3 | big_mrta | rostam_ea | consensus_dbta | Toplam |
| ----------------- | ----------: | -------: | --------: | -------------: | -----: |
| robot_failure     |           5 |        5 |         5 |              5 |     20 |
| mixed_stress      |           5 |        5 |         5 |              5 |     20 |
| deadline_pressure |           5 |        5 |         5 |              5 |     20 |
|                   |             |          |           |                | **60** |

**G2 — Ablasyon grubu (4 V3 varyantı, ahe_mrta_v3 referans G1'den alınır):**

| Senaryo           | no_bipartite | no_dense_init | no_recovery | fixed_weights | Toplam |
| ----------------- | -----------: | ------------: | ----------: | ------------: | -----: |
| robot_failure     |            5 |             5 |           5 |             5 |     20 |
| mixed_stress      |            5 |             5 |           5 |             5 |     20 |
| deadline_pressure |            5 |             5 |           5 |             5 |     20 |
|                   |              |               |             |               | **60** |

**Toplam Gazebo:** 60 + 60 = **120 deney.**

**İstatistiksel doğrulama:** 300-seed simülatör (12 600 simülasyon) tüm yöntemleri
kapsar; Wilcoxon, Page's L ve Cliff's delta bu veriden hesaplanır. Gazebo fiziksel
doğrulama işlevi görür.

### 10.2.5. Ek metrik notu

Ana dosyada yalnızca tüm yöntemler için ortak loglanacak metrikler korunur:

```text
communication_footprint_bytes
allocation_message_count
mean_decision_latency_ms
solver_runtime_ms
```

Yöntem-özel yorumlar ve adil karşılaştırma koşulları `ahe_mrta_recent_comparison_methods.md` içinde yönetilir.

## 10.3. Tekrar sayısı ve seed planı (v6 — tek ölçek)

> **Revizyon (2026-05-21 v6):** Tek ölçek 3r/15g; 5 seed. İstatistiksel güç
> 300-seed simülatörden sağlanır; Gazebo fiziksel doğrulama işlevi görür.

```text
# Tüm gruplar
repeat_count = 5
seed_set     = {1, 2, 3, 4, 5}
ölçek        = 3 robot / 15 görev

# G1 — Karşılaştırma
combo = 4 yöntem (ahe_mrta_v3, big_mrta, rostam_ea, consensus_dbta)
        × 3 senaryo (robot_failure, mixed_stress, deadline_pressure)
        → 60 deney

# G2 — Ablasyon
combo = 4 V3 varyantı (no_bipartite, no_dense_init, no_recovery, fixed_weights)
        × 3 senaryo
        → 60 deney

Toplam: 120 deney
```

**Deney süresi:**

```text
3r/15g  :  ~15 dk/deney  (startup 120s + sim + teardown)

G1 — 60 × 15 dk  =  15 saat
G2 — 60 × 15 dk  =  15 saat
──────────────────────────────
Toplam  120 deney = ~30 saat  (≈ 1.25 gün)
```

**İstatistiksel raporlama:** Her metrik için median ± IQR. Yöntem çiftleri arası
Wilcoxon signed-rank (paired by seed). Etki büyüklüğü Cliff's delta. p < 0.05 eşiği.
Simülatör verisi (300 seed, 12 600 simülasyon) birincil istatistiksel güç kaynağı;
Gazebo (120 deney) fiziksel doğrulama işlevi görür.

## 10.3.1. Video kayıt planı

Her deney **tipinden** seed=01 olan koşuda Gazebo GUI ve RViz çift video kaydı alınır.
"Deney tipi" = (ölçek × yöntem × senaryo) kombinasyonu.

**Kapsam:**

| Grup | Deney tipi sayısı | Video çifti |
| ---- | ------------------ | ----------: |
| G1 (4 yöntem × 3 senaryo, seed=01) | 12 | 12 |
|                                     |    | **12 çift = 24 dosya** |

**Toplam disk:** ~50 MB/video × 24 ≈ **1.2 GB.**

**Mimari:**

```text
Gazebo GUI    → DISPLAY=:1 (Xvfb 1920×1080) → ffmpeg x11grab → video_gazebo.mp4
RViz2         → DISPLAY=:2 (Xvfb 1920×1080) → ffmpeg x11grab → video_rviz.mp4
Codec         : H.264 (libx264), CRF 23
Framerate     : 30 fps
Resolution    : 1280×720 (downscale)
```

**RViz görselleştirme zorunluları (her video'da görünür):**

```text
1. Arena haritası        (statik occupancy grid)
2. Robot konumları       (her robot farklı renk TF + URDF mesh)
3. İnspeksiyon hedefleri (renkli SPHERE marker — atandı/tamamlandı/başarısız)
4. Nav2 yol planı        (/robot_i/plan — her robot için ayrı çizgi)
5. Görev ataması okları  (/allocation_arrows — robot → hedef)
6. Heuristic dominance   (/dominance_display — 2D panel, opsiyonel)
```

**Gazebo görselleştirme zorunluları:**

```text
1. Arena 3D modeli       (raflar, silindirler, bölmeler görünür)
2. Robot 3D modelleri    (TurtleBot3 Waffle Pi — renkli işaretleyiciler)
3. Hedef marker'ları     (Gazebo visual marker plugin ile aynı sphere'lar)
4. Üst-orta perspektif   (sabit kamera açısı: x=0, y=0, z=18, pitch=−85°)
```

**Çıktı dizini:**

```text
results/raw/gazebo_v3/<exp_id>/
  ├─ video_gazebo.mp4   (yalnızca seed01)
  ├─ video_rviz.mp4     (yalnızca seed01)
  ├─ summary.csv
  └─ task_events.csv
```

**Uygulama:** `run_experiments_robust.sh` betiğine `--record-video` bayrağı eklenir;
sadece seed=01 olan koşularda aktif olur. Xvfb başlatma, ffmpeg child process'leri
ve teardown sırasında ffmpeg SIGTERM ile düzgün kapatma sorumluluğu betiğe verilir.

## 10.3b. Gazebo arena ve teknik durum (v3, 2026-05-19)

Tüm ölçekler **aynı arena ortamında** çalışır (`ahe_inspection_arena.sdf`). Sadece robot sayısı ve görev sayısı değişir; engel düzeni sabittir.

### Arena özellikleri (SDF'den)

```text
Boyut           : 20 × 20 m (iç alan: 19.92 × 19.92 m)
Raf direkleri   : 16 adet, 0.3 × 2.0 m kutu; x=±5.0,±7.5 / y=±4.5,±7.5
Bölme duvarlar  : 4 adet, 7.0 × 0.2 m; y=±3.0, x=[-8.5,-1.5]∪[1.5,8.5], orta boşluk 3 m
İç silindirler  : 4 adet, r=0.2 m; (±2.5, ±5.5)
inflation_radius: 0.30 m (Nav2)
Min güvenli mes.: silindir merkezi + robot_r + inflation = 0.20+0.22+0.30 = **0.72 m**
```

### Inspection target grid (engelsiz)

Tüm hedefler engellerden minimum 0.72 m uzaktadır. Görev ölçeklerine göre gerekli grid noktası sayısı:

| Ölçek | Görev sayısı | Grid noktası gereği | Mevcut grid |
| ----- | ------------ | ------------------- | ----------- |
| S1    | 15           | ≥ 15                | 28 ✓        |
| S2    | 25           | ≥ 25                | 28 ✓        |
| S3    | 35           | ≥ 35                | 28 → **40 noktaya genişletilecek** |

S3 için grid genişletilmesi gerekir; yeni noktalar aynı min-clearance kuralına uymalıdır.

### Çok-robot launch desteği (uygulama gereği)

Mevcut `robots_and_nav2.launch.py` ve `multi_robot_nav2.launch.py` dosyaları
**3 robot için hardcoded** durumdadır (`ROBOTS = ['robot_1', 'robot_2', 'robot_3']`).
S1/S2/S3 için aşağıdaki düzenlemeler gereklidir:

| Değişiklik | Etki |
| ---------- | ---- |
| `ROBOTS` listesi `robot_count` parametresinden türetilecek | 5/10/15 robot dinamik launch |
| `ROBOT_SPAWN_Y` sözlüğü kaldırılıp `compute_spawn_positions(N)` ile yer hesaplanacak | Robotlar arası min mesafe ≥ 1 m |
| AMCL initial_pose tüm robot sayılarında doğru atanacak | Particle filter divergence engellenir |
| Nav2 lifecycle her robot için ayrı node | N robot için 9N+1 Nav2 node |

Spawn pozisyonu kuralı (Y ekseninde merkez etrafında simetrik dağılım):

```text
N=5  : y ∈ {-4, -2, 0, 2, 4}             (x ≈ -9, başlangıç hattı)
N=10 : y ∈ {-4.5, -3.5, ... , 4.5}       (1 m aralık, 10 nokta)
N=15 : iki sıra: x = {-9, -8}, y ∈ {-4..4} (8+7 robot)
```

### Önceki sürümlerden taşınan altyapı düzeltmeleri

| Düzeltme | Açıklama |
|---|---|
| `inflation_radius` | 0.55 → 0.30 m (raf koridoru tıkanıklığı giderildi) |
| `_GRID` 8 nokta kaydırıldı | silindire <0.72 m olan noktalar y=±6.0'a taşındı |
| `tasks_failed` sayacı | Nav2 retry'ları değil kalıcı başarısızlık sayar |
| `startup_delay` tipi | `75` (INT) → `75.0` (DOUBLE) |
| Raf direği simetrisi | Üst direkler y=3.5,6.5'ten y=4.5,7.5'e taşındı |
| FastDDS SHM fix | UDP-only transport (`fastdds_udp_only.xml`) — SHM hataları sıfırlandı |
| Maliyet fonksiyonu | `B = 1−r.battery`, `F = r.failure_risk`, `R_nav` terimi eklendi |

### Çalışma durumu (v6 — 2026-05-21)

```text
Önceki batch'ler           : silindi (results/ temizlendi)
Güncel batch               : run_paper_experiments_v3.sh (120 deney, 3r/15g)
DONE                       : 0/120
Çıktı dizini               : results/raw/gazebo_v3/
Önkoşul                    : Tamamlandı — tüm yöntemler simülatörde doğrulandı
Tahmini süre               : ~30 saat (≈1.25 gün)
```

**İzleme komutları:**
```bash
tail -f ~/multi_ahe/results/raw/gazebo_v3/paper_run_v3.log
find ~/multi_ahe/results/raw/gazebo_v3 -name "DONE" | wc -l
```

---

## 10.3c. Ortam üzerinde görselleştirme

Deneylerin anlaşılırlığını artırmak ve makale için kaliteli figür üretmek amacıyla iki farklı görselleştirme katmanı planlanmıştır: deney sırasında gerçek zamanlı ve deney sonrasında CSV'den üretilen statik figürler.

### Gerçek zamanlı (deney sırasında — RViz2)

Deney çalışırken RViz2 veya rqt aracılığıyla aşağıdaki bilgiler ortam haritası üzerine çizdirilir:

| Görsel öğe | ROS topic / mesaj tipi | Açıklama |
|---|---|---|
| İnspeksiyon hedefleri | `/inspection_targets` → `MarkerArray` (SPHERE) | Her hedef için renkli küre; atandı/tamamlandı/başarısız durumuna göre renk değişir |
| Robot yol planı | `/robot_i/plan` → `nav_msgs/Path` | Nav2'nin her robot için hesapladığı anlık yol; RViz2'de otomatik görünür |
| Robot pozisyonu | `/robot_i/amcl_pose` → `PoseStamped` | Her robotun tahmini konumu ve yönelimi |
| Görev ataması okları | `/allocation_arrows` → `MarkerArray` (ARROW) | Robot → atanmış hedef arasında ok; yeniden atamada güncellenir |
| Heuristic dominance çubuğu | `/dominance_display` → `MarkerArray` (TEXT/CUBE) | Aktif heuristik ağırlıklarını 2D panel olarak gösterir (opsiyonel) |

RViz2 yapılandırma dosyası: `config/experiment_monitor.rviz`

Demo modunda (`phase9_demo.launch.py`) RViz2 otomatik açılır ve bu öğeler hazır yapılandırmayla görünür. Batch deneylerde RViz2 kapalıdır (headless); yalnızca video kaydı etkinleştirildiğinde Xvfb üzerinden açılır.

### Deney sonrası (CSV'den statik PNG — matplotlib)

Deney tamamlandıktan sonra `scripts/plot_arena.py` ile arena üzerine çizim yapılır:

```text
Girdiler:
  task_positions.csv          → hedef koordinatları (x, y, durum)
  robot_state_timeseries.csv  → robot (x, y, t) yol izi
  task_events.csv             → atama zamanları ve tamamlanma durumu

Çıktılar:
  results/paper_figures/arena_overview_<exp_id>.png
    → Arena planı + hedef konumları + robot izleri
  results/paper_figures/arena_assignment_<exp_id>.png
    → Hangi robot hangi hedefi aldı (renk kodlu ok)
```

Arena çizimi bileşenleri:

```text
zemin ızgarası     : 20×20 m, gri çizgi, 1 m aralık
sınır duvarları    : siyah dikdörtgen, 0.12 m kalınlık
raf direkleri (×16): mavi dolgu kutu, 0.3×2.0 m
bölme duvarları (×4): gri dolgu kutu, 7.0×0.2 m
iç silindirler (×4): kırmızı daire, r=0.2 m
inflation sınırı   : her engel etrafında r=0.30 m kesikli daire (Nav2 görünmez alan)
hedef noktaları    : renkli yıldız/üçgen (atandı=turuncu, tamamlandı=yeşil, başarısız=kırmızı)
robot izleri       : her robot farklı renk, plt.plot(x, y, alpha=0.6)
başlangıç konumu   : renkli kare
```

Supplementary figür olarak `robot_trajectory_overlay.png` (§11.11 CSV-PNG tablosundaki) bu scriptten üretilir.

### Performans izleme (deney sırasında — terminal)

MVP batch çalışırken `scripts/watch_progress.sh` terminalde her tamamlanan `ahe_mrta_v3` deneyinin anahtar metriklerini gösterir:

```text
Deney tamamlandıkça:
  summary.csv okunur → task_completion_rate, makespan_s, workload_balance yazdırılır
  Tablo formatında: strateji | senaryo | seed | TCR | makespan | wb
  Önerilen yöntem (ahe_mrta_v3) kırmızıyla vurgulanır
```

Çıktı dosyası: `results/live_progress.tsv` (append-mode, deney bittikçe satır eklenir)

---

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

Bu bölüm, deneyler sonunda üretilecek tüm ham ve türetilmiş CSV dosyalarını, bu CSV dosyalarından üretilecek PNG figürleri ve RA-L/Q1 makale tablolarını tanımlar. Çıktı sistemi sabit robot sayısına bağlı değildir; S1=5r/15g, S2=10r/25g ve S3=15r/35g ölçeklerinin tümünde aynı şema çalışır.

Temel amaç yalnızca son metrikleri kaydetmek değil, deney sırasında oluşan ham olay verisini de yeniden kullanılabilir CSV dosyaları olarak arşivlemektir. Böylece ileride yeni grafik, yeni metrik, ek hakem analizi veya supplementary sonuç istendiğinde Gazebo deneylerinin yeniden çalıştırılmasına gerek kalmadan `processed/*.csv` dosyalarından yeni çıktılar üretilebilir.

Q1/RA-L için veri sistemi şu ilkeye dayanır:

```text
ROS/Gazebo run (120 deney, 3r/15g)
      ↓
raw CSV per experiment  (summary.csv + task_events.csv)
      ↓
processed merged CSV    (all_results.csv)
      ↓
statistics              (Wilcoxon, Cliff's delta)
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
│   └── scalability_S1_S2_S3.png
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
scalability_S1_S2_S3.png
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
| `summary.csv` + `method_runtime.csv`              | `scalability_S1_S2_S3.png`                                 | Line plot (3 nokta)           | Zorunlu                    | S1→S2→S3 ölçeklenebilirlik eğrisi (her metrik ayrı satır)  |

## 11.12. Q1/RA-L için ana figür ve PNG çıktı planı

Ana makalede 6 figürden fazlası kullanılmamalıdır. Fig. 1 ve Fig. 2 yöntem/mimari şemalarıdır; doğrudan CSV'den üretilmez. Fig. 3–Fig. 6 ise deney CSV'lerinden üretilen veya deney panellerinin birleştirilmesiyle hazırlanan sonuç figürleridir.

| Makale figürü | Önerilen PNG dosyası                   | Kaynak                                                             | Zorunluluk | Amaç                                                                                            |
| ------------- | -------------------------------------- | ------------------------------------------------------------------ | ---------- | ----------------------------------------------------------------------------------------------- |
| Fig. 1        | `system_overview.png`                  | Manuel/Graphviz/Matplotlib şema                                    | Zorunlu    | ROS 2/Gazebo, task manager, allocator, robot interface ve evaluation akışını göstermek          |
| Fig. 2        | `adaptive_ecosystem_mechanism.png`     | Manuel/Graphviz/Matplotlib şema                                    | Zorunlu    | Context vector, dominance, cooperation/suppression ve weight generation mekanizmasını göstermek |
| Fig. 3        | `baseline_comparison_multi_metric.png` | `summary.csv`                                                      | Zorunlu    | Ana baseline karşılaştırmasını çok panelli vermek                                               |
| Fig. 4        | `ablation_comparison.png`              | `summary.csv`                                                      | Zorunlu    | AHE bileşen katkılarını izole etmek                                                             |
| Fig. 5        | `scalability_S1_S2_S3.png`             | `summary.csv` + `method_runtime.csv`                               | Zorunlu    | S1=5r/15g → S2=10r/25g → S3=15r/35g ölçeklenebilirlik trendi (her metrik için bir alt panel)    |
| Fig. 6        | `dominance_recovery_panel.png`         | `ecosystem_metrics.csv` + `allocation_events.csv` + `summary.csv`  | Zorunlu    | Dominance evolution ve failure recovery davranışını birlikte göstermek                          |

Phase 10 sırasında ayrıca aşağıdaki kaynak PNG'ler üretilebilir ve gerekirse Fig. 5/Fig. 6 panellerine dönüştürülebilir:

```text
baseline_comparison_multi_metric.png
ablation_comparison.png
dominance_evolution.png
failure_recovery.png
communication_footprint.png
scalability_S1_S2_S3.png
```

Supplementary veya repository için önerilen ek figürler:

| Ek figür | PNG dosyası                    | Kaynak CSV                              | Kullanım                              |
| -------- | ------------------------------ | --------------------------------------- | ------------------------------------- |
| Fig. S0  | `arena_map.png`                | `obstacle_map.pgm` (harita)             | Arena düzeni, görev noktaları, başlangıç konumları |
| Fig. S1  | `task_completion_timeline.png` | `task_events.csv`                       | Görevlerin zamansal tamamlanma eğrisi |
| Fig. S2  | `workload_distribution.png`    | `robot_workload.csv`                    | Robot başına görev dağılımı           |
| Fig. S3  | `allocation_instability.png`   | `summary.csv` + `allocation_events.csv` | Yeniden atama kararlılığı             |
| Fig. S4  | `decision_latency.png`         | `method_runtime.csv` + `summary.csv`    | Karar süresi dağılımı                 |

Radar chart ana makalede kullanılmamalıdır. Çünkü bazı metriklerde yüksek, bazı metriklerde düşük değer daha iyidir; radar chart için gereken ters normalizasyon hakem açısından yorum karmaşası yaratabilir.

## 11.13. Figürlerin içerik planı

### 11.13.0. `arena_map.png`

**Şekil altı açıklaması (Fig. S0 caption):**
> Fig. S0. Simulation arena layout. Grey cells indicate static obstacles (shelves, pillars, divider walls, boundary walls). Blue squares mark the 42-point task grid; coloured markers show robot spawn positions for S1 (red circles, 5r), S2 (orange triangles, 10r), and S3 (green diamonds, 15r). Spawn columns are at x = −4, −3, −2 m, ensuring ≥5.9 m clearance from arena walls. Resolution: 0.05 m/cell; arena: 20 m × 20 m.

Kaynak: `src/m_ahe_nav2_config/maps/obstacle_map.pgm` + `generate_arena_map_png.py`

---

### 11.13.1. `baseline_comparison_multi_metric.png`

**Şekil altı açıklaması (Fig. 3 caption):**
> Fig. 3. Multi-metric performance comparison of AHE-MRTA, BiG-MRTA, and Consensus-DBTA under *robot_failure* and *mixed_stress* scenarios at scale S1 (5 robots, 15 goals). Each bar shows the mean over 5 random seeds; error bars represent one standard deviation. Higher task completion rate, lower makespan, and lower decision latency indicate better performance.

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

**Şekil altı açıklaması (Fig. 4 caption):**
> Fig. 4. Ablation study isolating the contribution of each AHE-MRTA component under *robot_failure* and *mixed_stress* scenarios at scale S1 (5 robots, 15 goals). Variants compared: full AHE-MRTA, w/o dominance (ahe_no_dominance), w/o event-triggered replanning (ahe_no_event_replanning), and fixed context weights (ahe_fixed_context). Error bars = std over 5 seeds. ↑ higher is better; ↓ lower is better.

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
ahe_no_event_replanning
ahe_fixed_context
```

### 11.13.3. `dominance_evolution.png`

**Şekil altı açıklaması (Fig. 6a caption):**
> Fig. 6a. Dominance evolution of AHE strategy agents during a representative *robot_failure* trial (S1, seed=01). Vertical dashed lines mark the robot failure event and subsequent reallocation. Panel (a): dominance scores over mission time; panel (b): context vector components; panel (c): allocation weight trajectory. AHE-MRTA adapts agent dominance in response to the failure without manual intervention.

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

**Şekil altı açıklaması (Fig. 6b caption):**
> Fig. 6b. Failure recovery performance across methods under the *robot_failure* scenario (S1 = 5r/15g, 5 seeds). Panel (a): mean failure recovery time (s); panel (b): recovery success rate (%); panel (c): replanning frequency (events/min). AHE-MRTA achieves faster recovery and higher success rate owing to event-triggered replanning and context-adaptive weight generation. Error bars = std.

Bu figür failure altında toparlanma performansını gösterir.

Önerilen alt paneller:

```text
(a) Failure recovery time
(b) Recovery success rate
(c) Replanning frequency
```

### 11.13.5. `allocation_instability.png`

**Şekil altı açıklaması (supplementary / Fig. S3 caption):**
> Fig. S3. Allocation instability comparison under *mixed_stress* scenario (S1, 5 seeds). Panel (a): allocation instability index (reassignments per completed task); panel (b): total reassignment count; panel (c): queue version changes per minute. Event-triggered replanning (AHE-MRTA) yields significantly lower instability than continuous replanning, without sacrificing task completion rate.

Bu figür sürekli replanning yerine event-triggered replanning kullanılmasının etkisini gösterir.

Önerilen alt paneller:

```text
(a) Allocation instability
(b) Reassignment count
(c) Queue version changes
```

### 11.13.6. `communication_footprint.png`

**Şekil altı açıklaması (supplementary / Fig. S caption):**
> Fig. S. Communication overhead comparison across methods under *robot_failure* and *mixed_stress* scenarios (S1, 5 seeds). Panel (a): total ROS message count per completed task; panel (b): total bytes transmitted; panel (c): active topic count. AHE-MRTA's centralised allocator design keeps communication footprint bounded as robot count increases.

Bu figür communication-efficient execution architecture iddiasını test eder.

Önerilen alt paneller:

```text
(a) Message count
(b) Bytes transmitted
(c) Topic count
```

### 11.13.7. `decision_latency.png`

**Şekil altı açıklaması (Fig. 3f / standalone caption):**
> Fig. 3f (or standalone). Decision latency distribution per method across all scenarios and scales (S1–S3, 5 seeds). Box shows IQR; whiskers = 1.5×IQR; dots = outliers. AHE-MRTA's polynomial heuristic computation yields sub-millisecond median latency, confirming real-time suitability on single-board hardware.

Bu figür yöntemlerin karar üretme süresini gösterir.

Önerilen sunum:

```text
x-axis = strategy
y-axis = runtime_ms
plot type = boxplot
```

### 11.13.8. `task_completion_timeline.png`

**Şekil altı açıklaması (Fig. S1 caption):**
> Fig. S1. Cumulative task completion over mission time for all three methods under *robot_failure* scenario (S1, seed=01). Vertical dashed line marks the robot failure event. AHE-MRTA resumes task completion faster following the failure event due to event-triggered reallocation, whereas BiG-MRTA and Consensus-DBTA exhibit a longer recovery plateau.

Bu figür görevlerin zaman içinde nasıl tamamlandığını gösterir.

Önerilen sunum:

```text
x-axis = mission time
y-axis = cumulative completed tasks
line = strategy
```

Ana makale için zorunlu değildir; supplementary için uygundur.

### 11.13.9. `workload_distribution.png`

**Şekil altı açıklaması (Fig. S2 caption):**
> Fig. S2. Per-robot task completion distribution for all methods under *mixed_stress* scenario (S1, 5 seeds). Each box represents one robot's completed task count across seeds. AHE-MRTA achieves more balanced distribution (lower interquartile spread) due to workload-aware context weighting, whereas BiG-MRTA and Consensus-DBTA show higher imbalance under deadline pressure.

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

## 11.17. Table 2 — Deney senaryoları (v3)

Her senaryo aşağıdaki üç ölçekte koşulur: **S1 = 5r/15g, S2 = 10r/25g, S3 = 15r/35g.**

| Scenario                | Ölçek(ler) | Dynamic tasks | Deadline | Failure | Congestion/battery stress | Yöntem kapsamı                                 |
| ----------------------- | ---------- | ------------- | -------- | ------- | ------------------------- | ---------------------------------------------- |
| Robot Failure (G1–G3)   | S1, S2, S3 | Yes           | Optional | Yes     | Optional                  | full_ahe + big_mrta + consensus_dbta           |
| Mixed Stress (G1–G3)    | S1, S2, S3 | Yes           | Yes      | Yes     | Yes                       | full_ahe + big_mrta + consensus_dbta           |
| Deadline Pressure (G4)  | S1, S2     | Yes           | Yes      | No      | No                        | full_ahe + big_mrta + consensus_dbta           |
| Ablation (G5)           | S1         | Yes           | Optional | Yes     | Yes (mixed_stress sub)    | full_ahe + 3 ablasyon varyantı                 |

Her (ölçek × yöntem × senaryo) kombinasyonu **5 seed** ile koşulur. seed=01 için
Gazebo + RViz video kaydı alınır (toplam 32 video çifti — bkz. §10.3.1).

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

`dominance_recovery_panel.png`, `dominance_evolution.png` ve `failure_recovery.png` panellerinden oluşur; `scalability_S1_S2_S3.png` ise üç ölçek özet verisini birleştirir.

Önerilen ek PNG çıktıları:

```text
  allocation_instability.png
  decision_latency.png
  task_completion_timeline.png       # supplementary adayı
  workload_distribution.png          # supplementary adayı
  scalability_S1_S2_S3.png           # zorunlu (Fig. 5)
```

20+ robotlu deneyler Phase 10 için kapsam dışıdır. `scalability_S1_S2_S3.png`
S1=5r/15g, S2=10r/25g ve S3=15r/35g koşullarını karşılaştırır.

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

## 12.14. Faz 11: Gazebo Demo + Arena Ortamı

Amaç:

```text
Gerçek Gazebo + Nav2 + RViz pipeline doğrulaması
Engelli arena ortamı (ahe_inspection_arena.sdf)
ROBOTIS TurtleBot3 Waffle Pi mesh modeli
RViz yol görselleştirme
```

Başarı kriteri:

```text
3 robot Gazebo'da spawn edilmeli
Nav2 3 robotta aktif hale gelmeli (active [3])
Laser scan /robot_N/scan → AMCL → TF zinciri çalışmalı
RViz'de robot modeli ve planlı yollar görünmeli
```

### Kritik Donanım/Platform Kısıtları

Bu proje NVIDIA GPU sürücüsü olmayan RTX 3050 Mobile üzerinde çalışır. Tüm Gazebo ve RViz işlemleri llvmpipe yazılım renderer ile yapılır.

### Zorunlu Ortam Değişkenleri

```bash
export DISPLAY=":1"                        # Desktop :1'de, :0'da değil (Linux)
export LIBGL_ALWAYS_SOFTWARE=1             # GPU driver yok → llvmpipe
export GALLIUM_DRIVER=llvmpipe
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
export MESA_GL_VERSION_OVERRIDE=4.5
unset GTK_PATH GTK_EXE_PREFIX GTK_MODULES GTK_IM_MODULE_FILE  # VS Code snap temizleme
```

Bu değişkenler her Gazebo/RViz launch dosyasına `SetEnvironmentVariable` ile eklenir; bash scriptlere `export` ile eklenir. Eksik olduğunda Gazebo veya RViz snap GTK kütüphanelerini yükler ve libpthread uyumsuzluğu nedeniyle crash eder.

### Nav2 ROS2 Jazzy Namespace Uyumu (KRİTİK)

ROS2 Jazzy'de `nav2_params.yaml` şablonundaki niteliksiz anahtarlar (ör. `controller_server:`) ad alanlı node'larla (`/robot_1/controller_server`) eşleşmez. `_make_nav2_params()` fonksiyonu (`multi_robot_nav2.launch.py`) her YAML anahtarını tam nitelikli forma dönüştürür:

```text
controller_server:              →  /robot_1/controller_server:
local_costmap.local_costmap:    →  /robot_1/local_costmap/local_costmap:
map_server:                     →  /robot_1/map_server:
```

Ayrıca `nav2_params.yaml`'a `map_server` altında `frame_id: robot_1/map` eklenmelidir. Aksi hâlde map_server `frame_id: 'map'` yayınlar, AMCL `robot_1/map` bekler ve TF zinciri tamamlanmaz.

### Gazebo Sensör Konfigürasyonu

gz-sim 8 (Gazebo Harmonic) `type="lidar"` CPU sensörünü desteklemez ("Sensor type LIDAR not supported yet"). Zorunlu yapılandırma:

```xml
<!-- ahe_inspection_arena.sdf -->
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
  <render_engine>ogre</render_engine>   <!-- OGRE1: GLX tabanlı, llvmpipe uyumlu -->
</plugin>

<!-- Her robot lidar sensörü -->
<sensor type="gpu_lidar" ...>
```

OGRE2 (varsayılan) EGL kullanır ve `LIBGL_ALWAYS_SOFTWARE=1`'i yok sayar; EGL doğrudan hardware device seçer → driCreateNewScreen3 segfault. OGRE1 GLX kullanır ve yazılım renderera uyar.

Gazebo sunucu-only modda çalıştırılır (`gz_args: '-r -s {world}'`), GUI yoktur.

### RViz Başlatma

```bash
~/multi_ahe/run_rviz.sh   # snap GTK değişkenlerini temizleyerek rviz2 başlatır
```

---

## 12.15. Faz 12: Gazebo Gerçek Deney Altyapısı

Amaç:

```text
Faz 9 deneylerini saf Python simülasyondan gerçek Gazebo + Nav2 ortamına taşımak.
experiment_runner_node Gazebo'da çalışacak şekilde güncellenmeli.
Batch deney scriptleri yazılmalı.
```

Başarı kriteri:

```text
run_gazebo_validation.sh ile en az 1 seed × core stratejiler × 3 senaryo başarıyla tamamlanmalı.
Her deneyde results/raw/gazebo/<exp_id>/DONE dosyası üretilmeli.
summary.csv makespan, deadline_violation_rate, workload_balance içermeli.
```

### experiment_runner_node Değişiklikleri

| Özellik | Açıklama |
|---|---|
| `startup_delay` parametresi | DOUBLE tipinde, Gazebo'da 45.0s, simülasyonda 0.0s |
| DONE sentinel dosyası | Deney bitince yazılır; shell script bunu bekler |
| Self-termination | `_finish()` + 2s sonra `os.kill(SIGTERM)` |

**Önemli:** `startup_delay:=45` INTEGER olarak geçirilmemelidir. Her zaman `startup_delay:=45.0` (noktalı) kullanılmalıdır.

### Batch Script Timeout Değerleri

```text
startup_delay   = 45s
experiment_time = 360s (EXPERIMENT_TIMEOUT_SEC)
cleanup_buffer  = 60s
TOTAL_TIMEOUT   = 465s  (< bu değerden düşük tutulmamalı)
```

### Deney Çalıştırma

```bash
# Hızlı doğrulama (1 seed, core stratejiler)
bash run_gazebo_validation.sh --quick --set core

# Tam set (3 seed, tüm stratejiler)
bash run_gazebo_validation.sh

# Gazebo sonuçlarını analiz et
python3 scripts/consolidate_results.py --raw-dir results/raw/gazebo --processed-dir results/processed_gazebo/
python3 scripts/plot_results.py --processed-dir results/processed_gazebo/ --output-dir results/paper_figures/gazebo/
```

---

## 12.16. Faz 13: Görselleştirme + Arena Map Figürleri

Amaç:

```text
Makale kalitesinde arena ortam haritası figürleri üretmek.
Robot trajektoryalarını görselleştirmek.
PNG export altyapısı kurumak.
```

Başarı kriteri:

```text
results/paper_figures/arena/arena_task_goals.pdf (ve .png) üretilmeli
results/paper_figures/arena/arena_trajectories.pdf (ve .png) üretilmeli
Her deney için trajectory PNG üretilebilmeli
```

### Arena Harita Figürleri

```bash
# Figür 1: Arena + görev hedefleri (öncelik renk kodlu)
# Figür 2: Arena + görev hedefleri + robot trajektoryaları
python3 scripts/plot_arena.py \
    --exp-dir results/raw/gazebo/exp_robot_failure_full_ahe_mrta_r3t15_seed01 \
    --out-dir results/paper_figures/arena
```

Figür özellikleri:
- PGM harita arka plan (obstacle_map.pgm, 0.05 m/px)
- Görev hedefleri: Öncelik 2 → mavi, Öncelik 3 → turuncu-kırmızı, numaralı
- Robot başlangıçları: üçgen marker (robot_1 mavi, robot_2 yeşil, robot_3 kırmızı)
- Trajektory: robot başına renkli çizgi + yön okları

### Deney Başına Trajectory PNG

```bash
python3 scripts/export_experiment_pngs.py \
    --raw-dir results/raw/gazebo \
    --output-dir results/paper_figures/trajectories \
    --dpi 200
```

---

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

AHE ablations to implement (v3, 3 variants):
- ahe_no_dominance
- ahe_no_event_replanning
- ahe_fixed_context

Proposed method:
- full_ahe_mrta

Comparison baselines (v3, 3 main methods):
- big_mrta
- consensus_dbta
- (static_weighted and rostam_ea are supplementary only — not in main comparison)

Scenarios:
- robot_failure
- deadline_pressure
- mixed_stress

Scales:
- S1 = 5 robots / 15 targets (main + ablation)
- S2 = 10 robots / 25 targets
- S3 = 15 robots / 35 targets

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

The benchmark uses three paper-scale experiment configurations:
- S1 (main + ablation scale): 5 robots / 15 targets
- S2 (mid scale): 10 robots / 25 targets
- S3 (large scale): 15 robots / 35 targets

Comparison group: 3 methods (full_ahe_mrta, big_mrta, consensus_dbta).
Ablation group (S1 only): full_ahe_mrta + ahe_no_dominance + ahe_no_event_replanning + ahe_fixed_context.
Each (scale × method × scenario) cell uses 5 seeds; seed=01 must additionally record Gazebo + RViz videos.

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

8. scalability_S1_S2_S3.png
   Source: summary.csv + method_runtime.csv across S1 (5r/15g), S2 (10r/25g), S3 (15r/35g).
   This is the preferred Fig. 5 for the manuscript. One subplot per metric;
   x-axis = robot count; lines = full_ahe_mrta, big_mrta, consensus_dbta.

9. dominance_recovery_panel.png
   Source: dominance_evolution.png + failure_recovery.png or direct CSV plotting.
   This is the preferred Fig. 6 for the manuscript. It should combine interpretable adaptation with recovery behavior.

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

14. scalability_S1_S2_S3.png
   Source: summary.csv + method_runtime.csv
   Compare S1 (5r/15g), S2 (10r/25g) and S3 (15r/35g) for full_ahe_mrta vs
   big_mrta vs consensus_dbta. One subplot per metric; x-axis = robot count.

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

## 15.2. RA-L için figür ve tablo planı (v3)

Üç ölçekli deney kurgusu, ölçeklenebilirliği ayrı bir figürde sergileme imkânı verir.
Ana makale figürleri **kompakt, açıklanabilir ve ölçek-boyutlu** sonuçlara odaklanır.

### Ana figürler

| Figür  | İçerik                                                       | Senaryo / Kapsam                                              | Şekil altı açıklaması (taslak caption)                                                                                                                                                                                                              |
| ------ | ------------------------------------------------------------ | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fig. 1 | AHE-MRTA architecture                                        | —                                                             | *Fig. 1. AHE-MRTA system architecture. ROS 2 nodes: task manager, adaptive allocator, robot interface, and evaluation module. The allocator maintains a dominance–cooperation–suppression ecosystem updated each allocation cycle.*                   |
| Fig. 2 | Adaptive heuristic ecosystem mechanism                       | —                                                             | *Fig. 2. Adaptive heuristic ecosystem mechanism. Context vector drives dominance/suppression updates; allocation weights are recomputed on each event trigger without human tuning.*                                                                  |
| Fig. 3 | Main baseline comparison (S1 = 5r/15g)                       | robot_failure + mixed_stress · 3 methods · 5 seeds            | *Fig. 3. Multi-metric performance under robot_failure and mixed_stress (S1: 5 robots, 15 goals, 5 seeds). Six panels: task completion rate, makespan, task delay, workload balance, deadline violation rate, decision latency. Error bars = std.*     |
| Fig. 4 | Ablation study (S1)                                          | robot_failure + mixed_stress · 4 variants · 5 seeds           | *Fig. 4. Ablation study (S1, 5 seeds). Panels compare full AHE-MRTA vs. ahe_no_dominance, ahe_no_event_replanning, ahe_fixed_context on four metrics. ↑ task completion rate, ↓ task delay, ↓ failure recovery time, ↓ allocation instability.*     |
| Fig. 5 | Scalability across S1 → S2 → S3                              | robot_failure + mixed_stress · 3 methods · 5 seeds · 3 scales | *Fig. 5. Scalability trends from S1 (5r/15g) to S3 (15r/35g) under robot_failure and mixed_stress (5 seeds). One line per method per metric. Page's L trend test confirms monotone improvement of AHE-MRTA advantage with scale (p < 0.05).*        |
| Fig. 6 | Dominance evolution + Failure recovery                       | robot_failure · full_ahe_mrta · seed=01 · S1                 | *Fig. 6. Qualitative analysis (S1, robot_failure, seed=01). Left panels: dominance evolution and context vector dynamics. Right panels: failure recovery time and replanning events. Dashed line = robot failure timestamp.*                          |

### Ana tablolar

| Tablo   | İçerik                                                      | Not                                              |
| ------- | ----------------------------------------------------------- | ------------------------------------------------ |
| Table 1 | Method name, Online?, Adaptive?, Distributed/decentralized? | Sade tutulacak                                   |
| Table 2 | Deney senaryoları, ölçekler ve yöntem eşleştirmesi          | S1/S2/S3 + 3 senaryo + 3+4 yöntem                |
| Table 3 | Ana nicel sonuçlar (S1)                                     | mean ± std + Wilcoxon p (AHE vs her baseline)    |
| Table 4 | Ölçeklenebilirlik tablosu (S1 → S2 → S3)                    | 5 metrik × 3 ölçek × 3 yöntem                    |

### Supplementary (video)

| Çıktı                | Adet         | Açıklama                                                                       |
| -------------------- | ------------ | ------------------------------------------------------------------------------ |
| Gazebo video çiftleri| 32 dosya     | seed=01 × her ölçek × her yöntem × her senaryo                                  |
| RViz video çiftleri  | 32 dosya     | Hedef marker'ları, Nav2 yol planları, atama okları görünür                      |
| Arena overview PNGs  | 32 dosya     | Robot trajektorisi + hedef konumları + atama renk kodu                          |

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

## Soru 5: Neden 20+ robotlu büyük ölçekli filo deneyi yapılmadı?

Yanıt stratejisi:

Çalışma üç ölçekte (S1 = 5r/15g, S2 = 10r/25g, S3 = 15r/35g) AHE-MRTA'nın çevrim içi adaptasyon, failure recovery, allocation stability ve communication-efficient execution iddialarını test eder. Bu üç ölçek, RA-L formatına uygun kontrollü deney süresini korurken ölçeklenebilirlik trendini istatistiksel olarak (Page's L) doğrular. 20+ robotlu deneyler, Gazebo Harmonic + Nav2'nin lifecycle yükü ve tek-makine simülasyon belirsizliği nedeniyle bu çalışmanın kapsamı dışındadır; gelecekteki çalışma olarak gerçek robot filo deneyi planlanmıştır.

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
- Çalışma ana iddiasını üç ölçekte (S1=5r/15g, S2=10r/25g, S3=15r/35g) kontrollü baseline ve ablation deneyleriyle savunur; 20+ robotlu filo deneyleri bu kapsam dışıdır ve gelecek çalışma olarak belirtilmiştir.
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
S1 (5r/15g) ana baseline + ablasyon deneyleri
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
- [ ] `scalability_S1_S2_S3.png` üretildi mi? (zorunlu — Fig. 5)
- [ ] seed=01 deneylerin Gazebo + RViz video kayıtları (toplam 64 dosya) üretildi mi?

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
3. `ahe_no_dominance`, `ahe_no_event_replanning` ve `ahe_fixed_context` ablation varyantları AHE bileşenlerinin katkısını izole etmelidir.
4. Ana sonuçlar üç ölçekte (S1=5r/15g, S2=10r/25g, S3=15r/35g) verilmelidir; S1→S2→S3 trendi ölçeklenebilirlik figüründe Page's L testi ile birlikte raporlanmalıdır.
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
Ana makale: 6 figür + 4 tablo
Supplementary/repository: 4 istatistiksel ek tablo + 32 video çifti + opsiyonel detay figürleri
Deney çekirdeği: S1 (5r/15g) + S2 (10r/25g) + S3 (15r/35g), 5 seed
Ablasyon çekirdeği: S1 (5r/15g), 5 seed, 3 ablasyon varyantı + full_ahe
Ana savunma: dominance + cooperation + suppression + event-triggered replanning
Ana başarı metrikleri: workload balance, failure recovery, allocation instability, stress altında delay, dominance evolution, communication footprint
```
