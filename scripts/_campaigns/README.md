# Biten kampanya sürücüleri

Buradaki scriptler **tek seferlik** koşulardır ve hepsi tamamlanmıştır. Aktif
işlem hattının parçası değiller; makalede yer alan sayıların hangi
yapılandırmayla üretildiğini belgeledikleri için silinmediler.

Yeniden koşturmak veriyi ÜZERİNE YAZAR. Önce `results/README.md`'deki ilgili
satırı oku — çoğu hücrenin kanonik çıktısı orada haritalı.

| Script | Ne üretti | Durum |
|---|---|---|
| `run_alloc_only_rebuild.sh` | `stats/f58_allocation_only*` → `tab:allocation`, düzeltilmiş senaryo parametreleriyle | 2026-08-02 18:15 bitti |
| `run_prio_ab_when_ready.sh` | Öncelik çarpanı $\rho$ eşli A/B, 500 tohum → Sınırlılık (xii) | 2026-08-02 19:02 bitti |
| `run_ablation_arm5.sh` | 5. ablasyon kolu (fixed spatial-greedy), **ön-kayıt DIŞI** — keşifsel raporlanır | 2026-08-02 bitti |
| `run_warmup_campaign.sh` | Warm-up ON latency sütunu (makalenin bildirdiği her hücre) | 2026-07-30 bitti |
| `run_warmup_ab.sh` | Eşli warm-up on/off A/B — OFF kolunun kanonik veriyi ürettiğini gösterdi | 2026-07-30 bitti |
| `run_warmup_3r_fill.sh` | 3 robot hücrelerini n=15'e tamamladı (tohum 3–5) | 2026-07-30 bitti |
| `run_f53_gazebo_validation.sh` | **Reddedilen** F53 adil-tamamlama özelliğinin kanıtı | Özellik 2026-06-29'da çıkarıldı |

Üçü (`run_alloc_only_rebuild`, `run_prio_ab_when_ready`, `run_ablation_arm5`)
2026-08-02'de birbirine kilitli bir zincir olarak koştu; hiçbiri diğeriyle CPU
yarışmadı. Zincirin bekleyici parçası (`run_arm5_analysis_when_done.sh`) yalnız
orkestrasyondu ve silindi — çağırdığı iki analiz scripti
(`scripts/analyze_arm5_exploratory.py`, `scripts/analyze_ablation.py`) duruyor.

`run_ablation_arm5.sh`'nin 5. kolunu `analyze_ablation.py`'ın ARMS listesine
EKLEME: kesişimi 4→5 kola çıkarır ve kayıtlı Bonferroni p'lerini değiştirir.
