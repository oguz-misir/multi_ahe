# AHE-MRTA — Claude Code Çalışma Kuralları

## KRİTİK: Yük Koruması

Bu proje ROS2 + Gazebo + Nav2 çalıştırır. Sistem kolayca aşırı yüklenir.

### ROS2 süreç başlatmadan ÖNCE her zaman kontrol et:

```bash
uptime  # load average > 10 ise önceki deney çalışıyordur — BAŞLATMA
pgrep -fc "gz sim|gzserver|ros2 launch|parameter_bridge|experiment_runner"
```

**Sıfır değilse** → temizle:

```bash
pkill -9 -f "gz sim|gz_server|gzserver|parameter_bridge|ros_gz_bridge"
pkill -9 -f "robot_interface_node|experiment_runner_node|ecosystem_manager"
pkill -9 -f "nav2|amcl|bt_navigator|planner_server|controller_server|lifecycle_manager"
pkill -9 -f "ros2 launch|ros2 run|run_paper_experiments|run_experiments_robust"
rm -f /dev/shm/fastrtps_* /tmp/fastrtps_* /dev/shm/gz_* /tmp/gz_*
sleep 5
```

**Load 5'in altına düşmeden yeni Gazebo deneyi başlatma.**

---

## Deney Koşturma (çökme-güvenli)

- Gazebo deneyleri **tek tek** — paralel deney yok.
- **Çökme-güvenli sürücü (tercih edilen):**
  `nohup bash run_until_complete.sh > results/until_complete.log 2>&1 &`
  - DONE olan deneyleri atlar → **kaldığı yerden devam eder** (donma/çökme/reboot sonrası).
  - Her deney öncesi `load_guard` (yük + zombie koruması, `scripts/exp_lib.sh`).
  - Her DONE → `results/PROGRESS.md` + MEMORY ledger (`experiment_progress.md`) güncellenir.
  - `.batch_active` bayrağı sürerken `@reboot` cron batch'i otomatik sürdürür; bitince silinir.
  - Her 30 dk ETA raporu: `results/status_report.log` + `results/PROGRESS_STATUS.md` (cron).
  - Tek tur runner: `bash run_experiments_robust.sh` (ölçek: `--robots N --tasks M`).
- DONE dosyaları: `results/raw/gazebo/exp_<scenario>_<strategy>_<scale>_seed<NN>/DONE`
- Yük koruması eşiği: `MAX_LOAD` (varsayılan 10; 16 çekirdek). Manuel temizlik için
  `source scripts/exp_lib.sh && cleanup_ros_gz`.
- Simülatör testleri (Gazebo yok): `source install/setup.bash && python3 scripts/simulate_and_tune.py --seeds 100 --scenario all`

## Gerekli Düğümler (3 robot)

| Süreç | Adet |
|-------|------|
| gz sim (headless) | 1 |
| parameter_bridge | 1–2 |
| robot_state_publisher | 3 |
| amcl | 3 |
| controller_server | 3 |
| planner_server | 3 |
| bt_navigator | 3 |
| lifecycle_manager | 3 |
| robot_interface_node | 3 |
| experiment_runner_node | 1 |
| ecosystem_manager_node | 1 |

Toplam ~26–28 süreç. Fazlası varsa zombie temizle.
