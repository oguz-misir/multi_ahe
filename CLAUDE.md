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

## Deney Koşturma

- Gazebo deneyleri **tek tek** — paralel deney yok.
- Batch runner (v3): `nohup bash run_paper_experiments_v3.sh >> results/raw/gazebo_v3/paper_run_v3.log 2>&1 &`
- DONE dosyaları: `results/raw/gazebo_v3/exp_<scenario>_<strategy>_<scale>_seed<NN>/DONE`
- Simülatör testleri (Gazebo yok): `source install/setup.bash && python3 scripts/simulate_and_tune.py --seeds 300 --scenario all --no-ablation`

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
