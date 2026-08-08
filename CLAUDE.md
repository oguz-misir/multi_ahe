# AHE-MRTA — Claude Code Çalışma Kuralları

## KRİTİK: Yük Koruması

Bu proje ROS2 + Gazebo + Nav2 çalıştırır. Sistem kolayca aşırı yüklenir.

### ROS2 süreç başlatmadan ÖNCE her zaman kontrol et:

```bash
cut -d' ' -f1-3 /proc/loadavg   # load1 > 5 ise BAŞLATMA
pgrep -fc "gz[ ]sim|experiment_runner_no[d]e"
```

**Sıfır değilse** → temizle. **Güvenli yol budur:**

```bash
source scripts/exp_lib.sh && cleanup_ros_gz
```

> **TUZAK — pkill desenlerini komut satırına YAZMA.** `pkill -f "gz sim|ros2 launch|
> experiment_runner_node|..."` deseni **kendi kabuğunun komut satırını da eşler** ve
> shell'i exit 144 ile öldürür; temizlik yarıda kalır. Aynı sebeple durum sorgularken
> `pgrep -f "gz sim"` yerine `pgrep -f "gz[ ]sim"` gibi kırık desen kullan.
> `cleanup_ros_gz` bunu doğru yapar (exit 144 döner, bu BEKLENEN).

**Load 5'in altına düşmeden yeni Gazebo deneyi başlatma.** 1 dakikalık ortalama
gecikmelidir: ağır bir iş yeni bittiyse `uptime` hâlâ düşük görünürken yük sönmemiş olabilir.

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
- Yük koruması eşiği: `MAX_LOAD` (`scripts/exp_lib.sh` varsayılanı 10; 16 çekirdek).
  **5 robot ve üzeri için 10 FAZLA GEVŞEK — `MAX_LOAD=5` export et.** Ölçüldü
  (2026-07-31): 5r bring-up'ın kendi yükü ~15; guard 10'da yeşil verince toplam yük
  320'ye çıktı, lifecycle servis çağrıları zaman aşımına uğradı, REKICK 42 kez denedi
  ve iki koşu `STARTUP FAILED: 0/5 Nav2 hazır` ile düştü. Aynı hücre boş makinede
  38 s'de 5/5 hazır oldu. Sürücü kendi eşiğini `source`'tan ÖNCE export etmeli;
  sonra yazılan `: "${MAX_LOAD:=5}"` no-op olur.
- **Kampanya koşarken ağır iş yapma** (sim kampanyası, LaTeX derlemesi, ikinci Gazebo).
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
