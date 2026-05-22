# AHE-MRTA Navigasyon Düzeltme — Devam Durumu

**Tarih:** 2026-05-20  
**Bağlam:** Smoke test #12 hazır; sistem şu an tamamen temiz (0 süreç).

---

## Temel Sorun

Robotlar hiçbir görevi tamamlayamıyordu — "Resulting plan has 0 poses in it" hatası.

---

## Kök Nedenler ve Uygulanan Düzeltmeler

### Fix 1 — QoS uyumsuzluğu (UYGULANMIŞ ✓)
**Dosya:** `src/m_ahe_mrta_bringup/src/odom_to_tf.cpp`  
`SensorDataQoS()` (BEST_EFFORT) → `rclcpp::QoS(10)` (RELIABLE)  
**Neden:** Gazebo bridge RELIABLE yayımlıyor, eski QoS ile odom mesajı hiç gelmiyordu.

### Fix 2 — TF timestamp (UYGULANMIŞ ✓)
**Dosya:** `src/m_ahe_mrta_bringup/src/odom_to_tf.cpp`  
`latest_->header.stamp` → `this->now()`  
**Neden:** Eski timestamp Gazebo bridge'in daha taze TF'si tarafından reddediliyordu (TF_OLD_DATA).

### Fix 3 — Sim-time aware timer (UYGULANMIŞ ✓)
**Dosya:** `src/m_ahe_mrta_bringup/src/odom_to_tf.cpp`  
`create_wall_timer(...)` → `rclcpp::create_timer(this, this->get_clock(), rclcpp::Duration::from_seconds(0.1), ...)`  
**Neden:** Wall timer sim time ile senkronize değildi → AMCL laser scan'ları düşürüyordu.  
**Rebuild:** `colcon build --packages-select m_ahe_mrta_bringup` → başarılı ✓

### Fix 4 — AMCL kaldırıldı, static map→odom TF eklendi (UYGULANMIŞ, TEST BEKLİYOR)
**Dosya:** `src/m_ahe_mrta_bringup/launch/multi_robot_nav2.launch.py`

**Değişiklikler:**
- `NAV2_NODES` listesinden `amcl` çıkarıldı
- AMCL node kaldırıldı
- `static_tf_map_odom_{robot_ns}` eklendi: `robot_N/map → robot_N/odom` identity TF
- `_nav2_nodes()` fonksiyonu `spawn_x, spawn_y` parametresi aldı (ileride gerekirse offset için)
- `_launch_setup()` spawn pozisyonlarını `_nav2_nodes`'a geçiriyor

**Gerekçe:** AMCL lokalizasyonu simülasyonda sürekli hata yapıyordu (harita dışına çıkıyordu). Gazebo Harmonic diff_drive odom'unu absolute world koordinatlarıyla başlatır. map = world frame (world→map identity). Bu nedenle map→odom = identity ✓. Simülasyon deneyleri için ground-truth lokalizasyon daha uygun.

**Doğrulanacak:** Gazebo diff_drive'ın odom'u spawn pozisyonundan mı (absolute world) yoksa (0,0)'dan mı başlattığı.  
- Eğer absolute world: identity map→odom doğru ✓  
- Eğer (0,0): `str(spawn_x), str(spawn_y), '0'` kullanılmalı (kod yorumda var)

---

## Smoke Test #12 — HAZIR

Sistem temiz (0 süreç, load 3.3). Başlatmak için:

```bash
cd /home/oguz/multi_ahe
source install/setup.bash
nohup ros2 launch m_ahe_mrta_bringup phase9_experiments.launch.py \
    strategy:=greedy_nearest scenario:=dynamic_task_arrival seed:=0 \
    robot_count:=3 task_count:=5 \
    startup_delay:=60.0 \
    > /tmp/smoke12.log 2>&1 &
echo "PID: $!"
```

**İzleme:**
```bash
# Nav2 aktif olunca:
grep -E "Managed nodes are active" /tmp/smoke12.log | wc -l  # 3 olmalı

# AMCL artık yok, lokalizasyon sorunları olmamalı
grep -E "0 poses|outside bounds" /tmp/smoke12.log | head -5

# Görev tamamlama:
grep -E "task.*complet|DONE|arrived" /tmp/smoke12.log | tail -20
```

**Dikkat:** Eğer robotlar harita dışına çıkarsa (outside bounds), odom başlangıç noktası (0,0) demektir → spawn offset gereklidir. Bu durumda `map_odom_tf` argümanlarını değiştir:
```python
arguments=[str(spawn_x), str(spawn_y), '0', '0', '0', '0', f'{robot_ns}/map', f'{robot_ns}/odom']
```

---

## Dosya Değişiklikleri Özeti

| Dosya | Değişiklik |
|-------|-----------|
| `src/m_ahe_mrta_bringup/src/odom_to_tf.cpp` | Fix 1+2+3 (QoS, timestamp, sim timer) |
| `src/m_ahe_mrta_bringup/launch/multi_robot_nav2.launch.py` | AMCL kaldırıldı, static map→odom TF eklendi |

Rebuild yapılmış: `colcon build --packages-select m_ahe_mrta_bringup` ✓

---

## Sonraki Adımlar

1. Smoke #12 çalıştır → görev tamamlamayı doğrula
2. Eğer "outside bounds" varsa → spawn offset yaklaşımına geç
3. Eğer başarılıysa → tam batch başlat:
   ```bash
   nohup bash run_paper_experiments.sh >> results/raw/gazebo/paper_run.log 2>&1 &
   ```
4. **Bekleyen özellik:** Her deneyde robot yol planlarını PNG ve video olarak kaydet (kullanıcı isteği)

---

## Arka Plan: Kullanılmayan Düğümler

Mevcut smoke test'te manuel başlattık:
- `robot_interface_node` (3x)
- `ecosystem_manager_node`
- `experiment_runner_node`

`phase9_experiments.launch.py` bunların hepsini otomatik başlatıyor (`robots_and_nav2.launch.py` → `multi_robot_nav2.launch.py` + robot_interface'ler + ecosystem_manager + experiment_runner). Doğru kullanım budur.
