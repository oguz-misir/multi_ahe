# `gazebo_benchmark_f58/` — bu kampanya hangi yapılandırmayla üretildi

Makalede raporlanan **300 koşunun tamamı** (3r×{9,15,24}, 5r/25, 10r/50 × 4 yöntem
× 3 senaryo × 5 tohum) bu dizindedir. Koşuların `metadata.yaml` dosyaları
ölçek/senaryo/tohum kaydeder ama **yapılandırma bayraklarını kaydetmez** (bu
eksiklik 2026-07-30 denetiminde bulundu; runner o tarihten sonra bayrakları
`metadata.yaml: allocator_env` altına yazıyor). Bu dosya, kampanya sırasında
geçerli olan yapılandırmayı kalıcı hâle getirir.

## Neden önemli

`AHEMRTAv3Allocator` sınıf varsayılanları **tarihsel F45 referansını** korur:
`F58_GEODESIC_ENABLED = False`, `F58_FAIR_REPAIR_ENABLED = False`. Yani bayraksız
bir kabukta `--strategy ahe_mrta_v3` çalıştırmak, **aynı isimle** Öklid mesafeli
ve terminal yük onarımı olmayan farklı bir yöntem koşar. Makalenin
`AHE-MRTA*` yıldızı tam olarak bu ayrımı gösterir (geodezik-ETA kâhini +
sınırlı terminal onarım).

## Kampanyanın env'i

```bash
export AHE_F58_GEODESIC=1
export AHE_F58_FAIR_REPAIR=1
export AHE_F58_FAIR_RESERVATION_GAP=2
export AHE_F58_FAIR_EXTRA_QUEUE=1
export AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3
# geri kalan her şey sınıf varsayılanı (F59_PRIORITY_COST_SCALE=0.10 dâhil)
```

`run_experiments_robust.sh` bu değerleri artık kendisi export eder (üzerine
yazmak isteyen çağırmadan önce export etsin), böylece dokümante edilen
yeniden-üretim yolu makalenin yöntemini üretir.

Sim düzlemi (`simulate_and_tune.py`) ek olarak `AHE_SIM_GEODESIC_EXECUTION=1`
ister; bayraksız koşulursa sessizce Öklid düzlemi üretir.

## Gecikme kolonu istisnası

`mean_decision_latency_ms` (yalnız AHE) bu kampanyadan DEĞİL,
`../gazebo_warmup_campaign/` içindeki eşleşen 75 koşudan gelir: geodezik kâhin
ilk zamanlanan karardan çıkarılıp başlangıç ısınmasına taşındı, kararlar
bit-özdeş kaldı. Zincir: `processed/ahe_latency_warmup.csv` →
`scripts/latency_override.py`.

## Haberleşme kolonu istisnası

`footprint_bytes` (yalnız AHE) bu kampanyada sabit 84 olarak kaydedildi; bu
değer başka bir varyantın 3-robot ağırlık-vektörü boyutuydu ve ne AHE'nin
protokolünü ne de filo boyutunu tarif ediyordu. `scripts/recompute_comm_footprint.py`
kuyruk yayınını görev-olay akışından yeniden kurup baseline'larla aynı
konvansiyonda sayar (`processed/ahe_comm_footprint.csv` →
`scripts/comm_override.py`). Yeniden koşum yapılmadı; diğer tüm kolonlar bu
kampanyanın kendisinden gelir.
