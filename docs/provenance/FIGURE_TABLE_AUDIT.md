# main.tex — Figür / Tablo / Grafik Görsel Denetim Raporu
Tarih: 2026-06-27 · Yöntem: derlenmiş PDF sayfaları görüntüye çevrilip (pdftoppm) her öğe tek tek incelendi.
EN: 17 sayfa, TR: 18 sayfa, 0 çözümsüz referans/atıf.

## 🔴 BULUNAN SORUN (düzeltildi): Box plot'lar bozuk görünüyordu

**Şekil 11 (TR) / Fig 10 (EN) — `dominance_recovery_panel`, panel (c-e) box plot'lar:**
- **Belirti:** panel (e)'de AHE* kutusu dev, içi dolu turuncu bir blok gibi — medyan/whisker yok ("gömülmemiş gibi").
- **Kök neden (gerçek bug):** kod box plot'ları `target_count==15` ile filtreliyordu → sadece r3t15 = **n=5**. Çift-modlu n=5 veri (AHE re-dispatch `[0,0,0,0.133,0.133]` → Q1=0, medyan=0, Q3=0.133) kutuyu dejenere ediyordu. Üstelik caption "**n=15** per method" diyordu → tutarsızlık.
- **Düzeltme:** filtre `robot_count==3` yapıldı (3 yoğunluk × 5 tohum = **n=15**, caption ile uyumlu). Yeniden üretildi → (c)(d)(e) artık düzgün kutular (medyan çizgisi, whisker, 15 nokta görünür).

---

## ADIM ADIM — her öğe (sayfa sırasıyla)

### Sayfa 5-6 — Mimari diyagramlar (statik, veriye bağlı değil)
| # | Öğe | Kaynak | Durum |
|---|-----|--------|-------|
| Tablo (V, A) | Context prototip vektörleri + cooperation matrisi | elle (§III) | ✓ render OK |
| Şekil 1 | `adaptive_ecosystem_mechanism.png` — EDPS mekanizması | make_ahe_diagram.py | ✓ OK |
| Şekil 2 | `system_overview.png` — sistem mimarisi | plot_results (matplotlib) | ✓ OK |
| Şekil 3 | `scenario_maps_panel.png` — 3 senaryo haritası | generate_scenario_maps.py | ✓ OK |

### Sayfa 7-9 — Düzlem A (sim) sonuçları
| # | Öğe | Kaynak | Durum |
|---|-----|--------|-------|
| Tablo tab:scales | Gazebo ölçekleri (300 deney tasarımı) | elle | ✓ OK |
| Tablo tab:fitness | Fitness 5r/25t (4 yöntem × 3 senaryo) | elle (sim_fitness.csv ile birebir doğrulandı) | ✓ OK |
| Şekil 4 | `fitness_comparison.png` — fitness bar±std | plot_results ← sim_fitness.csv | ✓ OK |
| Tablo tab:scalability | Scalability 3/5/10 (fitness+latency) | elle (sim_scalability.csv ile birebir) | ✓ OK |
| Şekil 5 | `scalability_panel.png` — 3-panel çizgi (latency log-eksen) | plot_results ← sim_scalability.csv | ✓ OK |

### Sayfa 10 — Deney kurulumu
| # | Öğe | Kaynak | Durum |
|---|-----|--------|-------|
| Şekil 6/7 | `arena_occupancy_map` + `grid_r5t25_mixed_stress` (2×2 yol-grafiği montajı) | render_arena + plot_method_paths (güncel veriden yeniden üretildi) | ✓ OK |
| Tablo tab:deadline | Deadline 5r/25t (n=5) | statistical_analysis.py ← all_summary (deterministik) | ✓ OK |

### Sayfa 11-13 — Düzlem B (Gazebo) sonuçları + tablolar
| # | Öğe | Kaynak | Durum |
|---|-----|--------|-------|
| Tablo tab:main_comparison | Ana karşılaştırma 5r (n=5) | statistical_analysis.py | ✓ OK |
| Tablo tab:efficiency | Verimlilik 3r (n=15) | make_extra_tables.py | ✓ OK |
| Tablo tab:effectsize | Etki büyüklüğü (Cliff δ) 5r | make_extra_tables.py | ✓ OK |
| Şekil 8/9 | `baseline_comparison_multi_metric` — 6-panel 5r | plot_results (df_primary=5r/t25) | ✓ OK |
| Şekil (10r) | `baseline_comparison_10r` — 6-panel 10r | plot_results ← gazebo_10r | ✓ OK |
| Şekil 10 | `failure_recovery` — 3-panel bar (Recovery/CR/**Re-dispatch**) | plot_results (df_primary) | ✓ OK (panel 3 önceki turda boş-preemption→re-dispatch düzeltildi) |

### Sayfa 14 — Yorumlanabilir uyum (box plot'lar)
| # | Öğe | Durum |
|---|-----|-------|
| Şekil 11 (a) | Dominans evrimi + arıza-çizgisi (75s) | ✓ OK (önceki tur 360→75s düzeltildi) |
| Şekil 11 (b) | Kümülatif tamamlama + medyan-arıza (164s) | ✓ OK |
| Şekil 11 (c-e) | **Box plot'lar (recovery/delay/re-dispatch)** | ✓ **DÜZELTİLDİ** (n=5→n=15, dejenere kutu giderildi) |
| Şekil 12 | `task_completion_timeline` — 3r kümülatif (a/b) | ✓ OK |

### Sayfa 15-16 — Ablation + iletişim
| # | Öğe | Durum |
|---|-----|-------|
| Tablo (ablation) | EDPS ablation (8 varyant, fitness) | ✓ OK |
| Şekil 13 | `communication_footprint` — bar | ✓ OK |

---

## ÖZET
- **17 figür/grafik + 8 tablo** tek tek görsel denetlendi.
- **Tek render sorunu**: Şekil 11 box plot'ları (n=5 dejenere) → **düzeltildi** (n=15).
- Diğer tüm figür/tablolar düzgün gömülü ve render oluyor.
- Önceki turlardaki düzeltmeler (Şekil 7 yol-grafiği güncel veri, Şekil 10 panel-3 re-dispatch, Şekil 11 a/b arıza-çizgisi) yerinde ve doğrulandı.
- Tüm generated tablolar deterministik (yeniden üretince değişmiyor); hardcoded sim tabloları CSV ile birebir.
