# AHE-MRTA Proje Durum Özeti

> Bu dosya her "özet güncelle" komutunda güncellenir.
> Son güncelleme: **2026-05-15**
>
> **Uygulama notu:** Tüm kaynak kod **Claude Code** (`claude-sonnet-4-6`) tarafından yazılır.
> Kullanıcı çalıştırma ve doğrulama yapar; Claude Code tüm node, launch ve script dosyalarını implement eder.

---

## Genel Bilgi

| Alan | Değer |
|------|-------|
| Proje | AHE-MRTA (Adaptive Heuristic Ecosystem MRTA) |
| Hedef dergi | IEEE RA-L (Q1) |
| Çalışma dizini | `/home/oguz/multi_ahe` |
| ROS 2 | Jazzy |
| Simülatör | Gazebo Harmonic (headless, WSL2) |
| Robot | TurtleBot3 Waffle Pi (SDF, 3 robot: mavi/yeşil/kırmızı) |

---

## Kaynak Belgeler

| Dosya | Kapsam |
|-------|--------|
| `ahe_mrta_ana_md_q1_csv_first_updated (1).md` | MİMARİ, mesajlar, fazlar, AHE formülasyonu (BİRİNCİL KAYNAK) |
| `ahe_mrta_recent_comparison_methods_compact (2).md` | Baseline yöntemler (BiG-MRTA, RoSTAM-EA, Consensus-DBTA) — Faz 9'dan itibaren |

Her ikisi de `/home/oguz/multi_ahe/` altında.

---

## Paket Yapısı (10 paket)

| Paket | Tür | İçerik |
|-------|-----|--------|
| `m_ahe_mrta_msgs` | CMake | 8 özel mesaj tipi |
| `m_ahe_mrta_bringup` | CMake | Launch dosyaları |
| `m_ahe_mrta_gazebo` | CMake | SDF dünyası, bridge config |
| `m_ahe_nav2_config` | CMake | Nav2 parametre dosyaları |
| `m_ahe_task_manager` | Python | Görev havuzu yönetimi |
| `m_ahe_robot_interface` | Python | Robot arayüzü, Nav2 action client |
| `m_ahe_task_allocator` | Python | Görev atama, baseline |
| `m_ahe_ecosystem_manager` | Python | AHE çekirdeği |
| `m_ahe_evaluation` | Python | CSV loglama, değerlendirme |
| `m_ahe_recovery_manager` | Python | Kurtarma yöneticisi |

---

## Özel Mesaj Tipleri (m_ahe_mrta_msgs)

| Mesaj | Kullanım |
|-------|---------|
| `TaskInfo` | Tekil görev (id, pose, priority, deadline) |
| `TaskPool` | Global görev havuzu |
| `TaskWaypoint` | Robot sırasındaki waypoint |
| `OptimizedTaskQueue` | Robot görev sırası (AHE çıkışı) |
| `RobotStatusSummary` | Robot durumu (konum, pil, navigation state) |
| `LocalExecutionFeedback` | Görev yürütme geri bildirimi |
| `AllocationEvent` | Atama olayı (replan tetikleyici) |
| `EcosystemState` | AHE iç durumu (DEBUG ONLY — robota gönderilmez) |

---

## Faz Durumu

| Faz | İçerik | Durum | Tarih |
|-----|--------|-------|-------|
| **Faz 1** | Workspace, 10 paket, 8 mesaj, build | ✅ TAMAM | 2026-05-14 |
| **Faz 2** | 4 test node, 8 topic, pub/sub round-trip | ✅ TAMAM | 2026-05-15 |
| **Faz 3** | Gazebo headless, 1 robot, odom+scan doğrulandı | ✅ TAMAM | 2026-05-15 |
| **Faz 4** | 3 robot namespace + TF ayrımı | ✅ TAMAM | 2026-05-15 |
| **Faz 5** | Nav2 manuel hedef testi | ✅ TAMAM | 2026-05-15 |
| **Faz 6** | Task Manager + Robot Interface | ✅ TAMAM | 2026-05-15 |
| **Faz 7** | Minimum baseline allocator | ✅ TAMAM | 2026-05-15 |
| **Faz 8** | Full AHE-MRTA ekosistemi | ✅ TAMAM | 2026-05-15 |
| **Faz 9** | Baseline + comparison + ablation deneyleri | ✅ TAMAM | 2026-05-15 |
| **Faz 10** | Analiz + makale çıktıları | ✅ TAMAM | 2026-05-15 |
| **Faz 11** | Gazebo demo + arena + görselleştirme altyapısı | ✅ TAMAM | 2026-05-15 |
| **Faz 12** | Gazebo gerçek deney altyapısı | ✅ ALTYAPI HAZIR | 2026-05-15 |
| **Faz 13** | IEEE RA-L LaTeX makale taslağı | ⏳ BEKLEMEDE | — |

---

## Faz 2 Detayları

**Test node'lar:**

| Node | Paket | Topic | Frekans |
|------|-------|-------|---------|
| `task_pool_test_pub` | `m_ahe_task_manager` | `/tasks/global_pool` pub | 1 Hz |
| `robot_status_test_pub` | `m_ahe_robot_interface` | `/robot_1/status_summary` pub, `/robot_1/local_execution_feedback` pub, `/robot_1/optimized_task_queue` sub | 1 Hz |
| `task_queue_test_pub` | `m_ahe_task_allocator` | `/robot_1/optimized_task_queue` pub | 0.5 Hz |
| `ecosystem_test_pub` | `m_ahe_ecosystem_manager` | `/ecosystem/debug_state` pub, `/allocation/events` pub (her 5 tick) | 1 Hz |

**Launch:** `ros2 launch m_ahe_mrta_bringup phase2_test_messages.launch.py`

**Not:** `ros2 topic echo` → `--no-daemon` flag gerekir (daemon custom msg tiplerini tanımaz).

---

## Faz 3 Detayları

**Dünya:** `ahe_inspection_mvp.sdf` — 3 robot (robot_1 @ (0,0), robot_2 @ (0,2), robot_3 @ (0,-2))

**SDF fix:** `type="lidar"` → `type="gpu_lidar"` (Gazebo Harmonic CPU lidar desteklemiyor)

**WSL2 fix:** `LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe` (OGRE2 software rendering)
- Launch dosyalarına `SetEnvironmentVariable` ile eklendi — ek bash komutu gerekmez.

**Launch:** `ros2 launch m_ahe_mrta_bringup single_robot_gazebo.launch.py`

**Doğrulanan topic'ler:**

| Topic | Tip | Frame |
|-------|-----|-------|
| `/robot_1/odom` | `nav_msgs/Odometry` | `robot_1/odom` → `robot_1/base_link` |
| `/robot_1/scan` | `sensor_msgs/LaserScan` | `robot_1/base_scan/lidar_sensor` |
| `/robot_1/cmd_vel` | `geometry_msgs/Twist` | — |
| `/robot_1/imu` | `sensor_msgs/Imu` | — |
| `/tf` | `tf2_msgs/TFMessage` | odom→base_link TF |
| `/clock` | `rosgraph_msgs/Clock` | — |

---

## Temel Kısıtlar (Değiştirilemez)

1. Paket isimleri `m_` prefix kullanır
2. AHE çekirdeği = dominance + cooperation + suppression + context compatibility + event-triggered replanning
3. **AHE basit adaptive weighting'e indirgenemez**
4. Deney ölçekleri: 3 robot/15 görev (MVP), 5 robot/25 görev (makale)
5. CSV-first loglama; grafikler çalışmalardan sonra üretilir
6. `EcosystemState` sadece debug — robota gönderilmez

---

## Faz 4 Detayları

**Launch:** `ros2 launch m_ahe_mrta_bringup multi_robot_gazebo.launch.py`

**Bridge config:** `all_robots_bridge.yaml` — 3 robot × 4 topic + /tf + /clock = 16 topic

**Doğrulanan topic'ler (16):**

| Topic | Tip |
|-------|-----|
| `/robot_1/cmd_vel`, `/robot_2/cmd_vel`, `/robot_3/cmd_vel` | `geometry_msgs/Twist` |
| `/robot_1/odom`, `/robot_2/odom`, `/robot_3/odom` | `nav_msgs/Odometry` |
| `/robot_1/scan`, `/robot_2/scan`, `/robot_3/scan` | `sensor_msgs/LaserScan` |
| `/robot_1/imu`, `/robot_2/imu`, `/robot_3/imu` | `sensor_msgs/Imu` |
| `/tf`, `/clock` | paylaşılan |

**TF frame'leri:**
- `robot_1/odom → robot_1/base_link` ✅
- `robot_2/odom → robot_2/base_link` ✅
- `robot_3/odom → robot_3/base_link` ✅

**Pozisyonlar:** robot_1 @ (0,0), robot_2 @ (0,+2), robot_3 @ (0,-2)

---

## Faz 5 Detayları

**Nav2 parametre dosyası:** `m_ahe_nav2_config/params/nav2_params.yaml` (robot_1 template, multi-robot launch'ta string.replace ile her robot için üretilir)

**Launch dosyaları:**
- `nav2_single_robot.launch.py` — robot_1 + tek Nav2 stack
- `multi_robot_nav2.launch.py` — 3 robot × Nav2 stack (template → temp YAML)

**TF zinciri (her robot için):** `robot_N/map → robot_N/odom → robot_N/base_link → robot_N/base_scan → robot_N/base_scan/lidar_sensor`

**Doğrulama komutu (tek robot):**
```bash
ros2 launch m_ahe_mrta_bringup nav2_single_robot.launch.py
# Ayrı terminalde:
ros2 action send_goal /robot_1/navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: robot_1/map}, pose: {position: {x: 1.0, y: 0.5, z: 0.0}, orientation: {w: 1.0}}}}"
```

---

## Faz 6 Detayları

**Launch:** `ros2 launch m_ahe_mrta_bringup phase6_task_system.launch.py`

**Yeni node'lar:**

| Node | Paket | Açıklama |
|------|-------|----------|
| `task_manager_node` | `m_ahe_task_manager` | 15 görev üretir (seed=1), 3 batch halinde aktifleştirir, `/tasks/global_pool` yayınlar |
| `robot_interface_node` (×3) | `m_ahe_robot_interface` | `/robot_N/optimized_task_queue` dinler, Nav2 action client, `/robot_N/status_summary` + feedback yayınlar |

**Görev üretimi:** 20 adet inspection grid noktasından 15 tanesi seed'e göre seçilir. Batch zamanlaması: 0s / 30s / 60s.

**Robot durum makinesi:** `IDLE → NAVIGATING → REACHED/FAILED → IDLE`

**Pil simülasyonu:** Navigasyon sırasında %1.5/5s, bekleme sırasında %0.3/5s azalır. Eşikler: LOW < %30, CRITICAL < %10.

**Doğrulama:**
```bash
# Görev havuzu
ros2 topic echo --no-daemon /tasks/global_pool m_ahe_mrta_msgs/msg/TaskPool

# Robot durumu
ros2 topic echo --no-daemon /robot_1/status_summary m_ahe_mrta_msgs/msg/RobotStatusSummary

# Manuel kuyruk gönderimi (Faz 7 allocator çalışana kadar)
ros2 topic pub --once /robot_1/optimized_task_queue \
  m_ahe_mrta_msgs/msg/OptimizedTaskQueue \
  "{robot_id: 'robot_1', queue_version: 1, waypoints: [{task_id: 'task_001', \
    target_pose: {header: {frame_id: 'robot_1/map'}, \
      pose: {position: {x: 2.0, y: 1.0, z: 0.0}, orientation: {w: 1.0}}}, \
    priority_level: 2, service_time: 3.0}], execution_mode: 'sequential'}"
```

---

## Faz 7 Detayları

**Launch:** `ros2 launch m_ahe_mrta_bringup phase7_baseline_system.launch.py`

**Yeni node:** `baseline_allocator_node` (`m_ahe_task_allocator`)

**Algoritma:**
- Strateji: `static_weighted`
- Sabit ağırlık vektörü: `W0 = [0.40, 0.15, 0.10, 0.15, 0.05, 0.10, 0.05]` (w_d, w_p, w_b, w_l, w_f, w_t, w_r)
- Katman 1: Greedy atama — her görev için (öncelik azalan, deadline artan sırada) en düşük maliyetli robota ata
- Katman 2: Cheapest insertion heuristic — her robotun görev kümesini optimal sırayla dizdir
- Kısıtlar: UNAVAILABLE veya CRITICAL battery robotlar atlanır

**Maliyet fonksiyonu bileşenleri:**
- D: Euclidean mesafe (normalize: /28 m)
- P: Öncelik cezası (4 - priority) / 3
- B: Pil riski (battery_state / 2.0)
- L: Yük dengesi (mevcut kuyruk uzunluğu / max)
- F: Arıza bayrağı
- T: Deadline aciliyeti (geçen_süre / deadline)
- R: Yeniden atama cezası

**CSV çıktıları:** `~/multi_ahe/results/raw/phase7_baseline/`
- `method_runtime.csv` — timestamp, latency_ms, tasks_assigned, total_queue_cost
- `allocation_events.csv` — task_assigned / task_completed / task_failed

**Doğrulama:**
```bash
ros2 topic echo --no-daemon /robot_1/optimized_task_queue m_ahe_mrta_msgs/msg/OptimizedTaskQueue
cat ~/multi_ahe/results/raw/phase7_baseline/method_runtime.csv
```

---

## Faz 8 Detayları

**Launch:** `ros2 launch m_ahe_mrta_bringup phase8_ahe_system.launch.py`

**Yeni node'lar:**

| Node | Paket | Açıklama |
|------|-------|----------|
| `ecosystem_manager_node` | `m_ahe_ecosystem_manager` | Context vector, dominance update, cooperation/suppression, W(t) üretimi |
| `ahe_allocator_node` | `m_ahe_task_allocator` | Dinamik W(t) kullanan AHE allocator |

**AHE çekirdeği:**
- K=7 heuristic: SpatialOpportunist, CriticalityGuardian, TemporalRegulator, ResourceDistributor, EnergyConservator, StabilityController, RecoveryCoordinator
- Context vector: task_density, robot_availability, battery_risk, deadline_pressure, failure_rate, workload_variance, allocation_instability
- Cooperation matrix A ve Suppression matrix S: 7×7 sabit matrisler
- Dominance update: `D(t+1) = clip[αD(t) + βP(t) + γK(Ct) + ηA·D(t) - λS·D(t) - δF(t)]`
- α=0.6, β=0.2, γ=0.15, η=0.10, λ=0.10, δ=0.15
- Heuristic-to-weight mapping: M (7×7), W(t) = softmax(M·D(t))

**Veri akışı:**
- `EcosystemManager` → `/ecosystem/debug_state` → `AHEAllocator` (sadece ağırlıklar)
- Robotlar AHE iç durumunu **ALMAZ** — sadece `/robot_N/optimized_task_queue` alır

**CSV çıktıları:** `~/multi_ahe/results/raw/phase8_ahe/`
- `ecosystem_metrics.csv` — dominant_heuristic, context_*, weights, dominance_values
- `method_runtime.csv` — latency_ms, tasks_assigned, w_d..w_r (dinamik)
- `allocation_events.csv` — task_assigned / task_completed / task_failed

**Doğrulama:**
```bash
ros2 topic echo --no-daemon /ecosystem/debug_state m_ahe_mrta_msgs/msg/EcosystemState
cat ~/multi_ahe/results/raw/phase8_ahe/ecosystem_metrics.csv
```

---

## Faz 9 Detayları ✅

**Karşılaştırma belgesi:** `ahe_mrta_recent_comparison_methods_compact (2).md`

**Dosya yapısı:** `m_ahe_task_allocator/m_ahe_task_allocator/baselines/`

### Tamamlanan dosyalar

| Dosya | Açıklama |
|-------|----------|
| `baselines/__init__.py` | ✅ Paket init |
| `baselines/base_allocator.py` | ✅ RobotState, TaskState, EcosystemContext, AllocationResult, BaseAllocator, cheapest_insertion, measure |
| `baselines/greedy_nearest.py` | ✅ Greedy nearest-target (öncelik desc sıralamayla) |
| `baselines/deadline_aware.py` | ✅ EDF — min estimated arrival time atama, EDF sıralama |
| `baselines/auction_based.py` | ✅ SSI auction — bid = proximity + deadline + priority - load - battery |
| `baselines/static_weighted.py` | ✅ Sabit W0, BaseAllocator arayüzünde |
| `baselines/big_mrta.py` | ✅ scipy linear_sum_assignment, greedy fallback |
| `baselines/rostam_ea.py` | ✅ Evolutionary: pop=40, gen=40, OX crossover, adaptive penalty |
| `baselines/consensus_dbta.py` | ✅ Consensus DBTA2: top_k=2 bid, priority-1/2 allocation round |
| `baselines/ahe_variants.py` | ✅ FullAHE, NoDominance, NoCoopSupp, NoEventReplanning, FixedContext |
| `experiment_runner_node.py` | ✅ Orchestrator — 11 allocator registry, 4 senaryo, 9 CSV çıktısı |
| `setup.py` (entry_point) | ✅ `experiment_runner_node` kaydedildi |
| `robots_and_nav2.launch.py` | ✅ Gazebo + Nav2 + RobotInterface (task_manager olmadan) |
| `phase9_experiments.launch.py` | ✅ strategy/scenario/seed/robot_count/task_count/results_dir arg |

### ALLOCATOR_REGISTRY (12 strateji)

```python
{
  'greedy_nearest':                GreedyNearestAllocator,
  'deadline_aware':                DeadlineAwareAllocator,
  'auction_based':                 AuctionBasedAllocator,
  'static_weighted':               StaticWeightedAllocator,
  'big_mrta':                      BigMRTAAllocator,
  'rostam_ea':                     RoSTAMEAAllocator,
  'consensus_dbta':                ConsensusDBTAAllocator,
  'full_ahe_mrta':                 FullAHEAllocator,
  'ahe_no_dominance':              AHENoDominanceAllocator,
  'ahe_no_cooperation_suppression': AHENoCoopSuppAllocator,
  'ahe_no_event_replanning':       AHENoEventReplanningAllocator,
  'ahe_fixed_context':             AHEFixedContextAllocator,
}
```

### Senaryo listesi

| Senaryo | Açıklama |
|---------|----------|
| `dynamic_task_arrival` | 3 görev batch'i (0s / 90s / 180s arası) |
| `deadline_pressure` | Deadlines 0.4× kısaltıldı |
| `robot_failure` | robot_2 ~45s'te arızalanır |
| `mixed_stress` | Hepsi birlikte |

### CSV çıktıları (her deney için)

`results/raw/phase9/experiment_<id>/`
- `metadata.yaml` — deney konfigürasyonu
- `task_events.csv` — görev yaşam döngüsü zaman damgaları
- `robot_state_timeseries.csv` — her allocation tick'inde robot durumu
- `robot_workload.csv` — robot başına final yük özeti
- `allocation_events.csv` — her atama kararı + latency
- `method_runtime.csv` — allocator başına zamanlama
- `communication_metrics.csv` — round başına communication footprint
- `ecosystem_metrics.csv` — AHE dominance + context (AHE koşularında)
- `summary.csv` — karşılaştırma için scalar KPI'lar

### Kullanım

```bash
# Tek deney
ros2 launch m_ahe_mrta_bringup phase9_experiments.launch.py \
    strategy:=full_ahe_mrta scenario:=robot_failure seed:=1

# Tüm kombinasyonlar (örnek: bash döngüsü)
for strategy in full_ahe_mrta rostam_ea consensus_dbta big_mrta greedy_nearest deadline_aware; do
  for scenario in dynamic_task_arrival deadline_pressure robot_failure mixed_stress; do
    for seed in 1 2 3; do
      ros2 launch m_ahe_mrta_bringup phase9_experiments.launch.py \
          strategy:=$strategy scenario:=$scenario seed:=$seed
    done
  done
done
```

---

## Faz 10 Detayları ✅

**Makale pipeline scripti:** `scripts/` klasörü

### Tamamlanan dosyalar

| Dosya | Açıklama |
|-------|----------|
| `scripts/consolidate_results.py` | ✅ Raw CSV birleştirme → `results/processed/all_*.csv` |
| `scripts/plot_results.py` | ✅ 14 PNG figür üretimi (300 DPI, RA-L/Q1 stili) |
| `scripts/statistical_analysis.py` | ✅ Shapiro-Wilk, ANOVA/Kruskal-Wallis, Dunn/Tukey, Cohen's d / Cliff's δ |
| `scripts/report_generator.py` | ✅ `results/reports/summary_report.md` |

### Pipeline çalıştırma sırası

```bash
# 1. Deneyleri çalıştır (Phase 9 komutları) — results/raw/ dolar

# 2. Raw CSV'leri birleştir
python3 scripts/consolidate_results.py \
  --raw-dir results/raw/ \
  --processed-dir results/processed/

# 3. PNG figürleri üret
python3 scripts/plot_results.py \
  --processed-dir results/processed/ \
  --output-dir results/paper_figures/ \
  --dpi 300

# 4. İstatistiksel analiz
python3 scripts/statistical_analysis.py \
  --processed-dir results/processed/ \
  --output results/reports/statistical_tables.md

# 5. Özet rapor
python3 scripts/report_generator.py \
  --processed-dir results/processed/ \
  --figures-dir results/paper_figures/ \
  --stats results/reports/statistical_tables.md \
  --output results/reports/summary_report.md
```

### Üretilen PNG'ler (14 adet)

**Zorunlu makale figürleri (Fig. 1–6):**
- `system_overview.png` — sistem mimarisi şeması (statik, matplotlib)
- `adaptive_ecosystem_mechanism.png` — AHE mekanizması (statik, matplotlib)
- `baseline_comparison_multi_metric.png` — 6 panelli baseline karşılaştırması
- `ablation_comparison.png` — 4 panelli ablation analizi
- `dominance_recovery_panel.png` — dominance evrim + failure recovery (Fig. 5)
- `communication_scalability_panel.png` — iletişim verimliliği + ölçeklenebilirlik (Fig. 6)

**Destek/ek figürler:**
- `dominance_evolution.png`, `failure_recovery.png`, `communication_footprint.png`
- `allocation_instability.png`, `decision_latency.png`
- `task_completion_timeline.png`, `workload_distribution.png`
- `compact_scalability_sanity.png`

### Bağımlılıklar

```bash
# Sistem paketleri (zaten kurulu): matplotlib, numpy, scipy
# Ek paket (pip ile kuruldu):
~/.local/bin/pip install --break-system-packages pandas
```

---

## Faz 11 Detayları (2026-05-15)

### Gazebo Demo Hazırlığı

**run_gazebo_experiments.sh** — 24 hedefli Gazebo deneyi için batch script:
```bash
bash run_gazebo_experiments.sh                  # tüm 24 deney
bash run_gazebo_experiments.sh --set baseline   # AHE vs BiG-MRTA vs RoSTAM-EA vs SW
bash run_gazebo_experiments.sh --set ablation   # ablation seti
bash run_gazebo_experiments.sh --dry-run        # komutları göster, çalıştırma
bash run_gazebo_experiments.sh --no-rviz        # headless (RViz olmadan)
```

### Robot Model Güncellemesi (ROBOTIS Meshes)

**Sorun:** `waffle_pi.urdf` basit box/cylinder geometrisi kullanıyordu (görsel olarak yetersiz).

**Çözüm:**
- `nav2_minimal_tb3_sim` paketinden ROBOTIS `.dae` mesh dosyaları kullanıldı
- Mesh yolları: `package://nav2_minimal_tb3_sim/models/turtlebot3_model/meshes/`
  - `waffle_base.dae`, `tire.dae`, `lds.dae`, `r200.dae`
- KDL uyarısı: root link inertia kaldırıldı (KDL root link inertia kullanmaz)
- `base_link` root olarak korundu (Gazebo diff_drive `odom → base_link` yayınlar)

### Engelli Arena Ortamı

**Dünya dosyası:** `ahe_inspection_arena.sdf` (eski `ahe_inspection_mvp.sdf`'e ek olarak)

| Özellik | Değer |
|---------|-------|
| Arena boyutu | 20m × 20m (kapalı dikdörtgen) |
| Sınır duvarları | ±9.95m dış duvar |
| İç engeller | 16 raf kutusu (0.3m×2.0m×0.5m) |
| Bölücü duvarlar | 4 yatay bölücü (y=±3m) |
| Silindir direkleri | 4 adet (r=0.2m) |
| Toplam engel | 28 statik model |

**Harita:** `obstacle_map.pgm` / `obstacle_map.yaml`
- 400×400 px, 0.05 m/px çözünürlük
- %92.8 serbest alan, %7.2 engelli
- Origin: (-10, -10)

**Harita oluşturma script'i:** `scripts/generate_obstacle_map.py`

```bash
# Haritayı yeniden üretmek için:
python3 scripts/generate_obstacle_map.py
colcon build --packages-select m_ahe_nav2_config m_ahe_mrta_gazebo --symlink-install
```

**Robot başlangıç pozisyonları** (engelsiz merkez koridor):
- robot_1: (0, 0)
- robot_2: (0, 2)
- robot_3: (0, -2)

---

## Faz 12 Detayları (2026-05-15)

### Gazebo Gerçek Deney Altyapısı

**Sorun:** Faz 9'daki 1104 deney `scripts/run_experiments.py` (pure-Python sim, ROS2/Nav2 yok) ile yapıldı. Gerçek Gazebo navigasyon deneyleri yapılmamıştı.

**Yapılan değişiklikler:**

#### 1. `experiment_runner_node.py` — v2 (Gazebo-ready)

| Yeni özellik | Açıklama |
|---|---|
| `gazebo_startup_delay_sec` param | Nav2 başlamadan önce bekleme (varsayılan 0.0, Gazebo'da 45s) |
| Başlatma gecikme yönetimi | `_startup_done` flag; görev üretimi ve atama ancak Nav2 hazır olunca başlar |
| Görev zamanlama düzeltmesi | Görevler artık Nav2 hazır olduğunda (node başlangıcında değil) üretilir |
| Tam özet metrikleri | `summary.csv` artık makespan, avg_delay, deadline_violation_rate, workload_balance, failure_recovery_time, allocation_instability, mean_decision_latency_ms içeriyor |
| `DONE` sentinel dosyası | `_finish()` sonunda yazılır; shell script erken sonlanmayı tespit eder |
| Self-termination | `_finish()` + 2s sonra `os.kill(SIGTERM)` — launch sürecini temizler |
| `metadata.yaml` düzeltmesi | `target_count` alanı eklendi (consolidate_results.py uyumu) |

#### 2. `phase9_experiments.launch.py` — startup_delay argümanı

```bash
ros2 launch m_ahe_mrta_bringup phase9_experiments.launch.py \
    strategy:=full_ahe_mrta scenario:=robot_failure seed:=1 \
    startup_delay:=45.0 \
    results_dir:=results/raw/gazebo
```

#### 3. `run_gazebo_validation.sh` — Odaklanmış doğrulama seti

```bash
bash run_gazebo_validation.sh                 # 45 deney (5×3×3), ~4.5 saat
bash run_gazebo_validation.sh --seeds "1 2"   # 30 deney, ~3 saat
bash run_gazebo_validation.sh --quick         # 15 deney (1 seed), ~90 dk
bash run_gazebo_validation.sh --set core      # 18 deney (AHE+SW+BiG), ~1.8 saat
bash run_gazebo_validation.sh --dry-run       # komutları göster
```

**Deney seti (--set full, varsayılan):**
- Stratejiler: full_ahe_mrta, static_weighted, big_mrta, ahe_no_event_replanning, greedy_nearest
- Senaryolar: dynamic_task_arrival, robot_failure, deadline_pressure
- Seed'ler: 1, 2, 3 (varsayılan)

**Çıktı:** `results/raw/gazebo/<strategy>__<scenario>__seed<N>/`

**Analiz (Gazebo sonuçları için):**
```bash
python3 scripts/consolidate_results.py \
    --raw-dir results/raw/gazebo \
    --processed-dir results/processed_gazebo/

python3 scripts/plot_results.py \
    --processed-dir results/processed_gazebo/ \
    --output-dir results/paper_figures/gazebo/

python3 scripts/statistical_analysis.py \
    --processed-dir results/processed_gazebo/ \
    --output-dir results/reports/gazebo/
```

**ÖNEMLİ:** Deneyleri çalıştırmadan önce workspace'i yeniden build edin:
```bash
cd /home/oguz/multi_ahe
colcon build --packages-select m_ahe_task_allocator m_ahe_mrta_bringup --symlink-install
source install/setup.bash
bash run_gazebo_validation.sh --quick  # önce 15 deney ile test
```
