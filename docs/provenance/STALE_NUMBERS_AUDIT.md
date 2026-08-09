# Bayat Sayı Denetimi — main.tex ↔ Veri
Tarih: 2026-06-26 · Veri kaynağı: results/processed/all_summary.csv (kilitli-v45, arşivle aynı) + regenere sim CSV'leri

## ÖZET
- **Tablolar/figürler** zaten veriye göre yeniden üretildi (doğru). **Gövde metni** birçok yerde bayat.
- **Sim (Plane A) fitness/scalability**: regenere edildi, paper'la eşleşiyor (yalnızca RoSTAM satırları ufak güncellendi — yapıldı).
- **5r + effect-size + 3r-sim prose**: STABİL veri, kesin bayat (aşağıda).
- **10r prose**: veri EKSİK (40/60, doldurma sürüyor) → tüm 10r sayıları doldurma bitince tekrar kontrol edilmeli.
- En kritik: 5r deadline'da bir **sonuç tersine dönüyor** (A2 aşağıda).

Kolon notu: effectsize tablosu sırası = vs BiG / RoSTAM / Cons.

---

## GRUP A — 5r gövde prose (STABİL, kesin bayat)

| # | Satır | Metindeki iddia | Mevcut veri (5r) | Not |
|---|------|------------------|------------------|-----|
| A1 | 909-911 | BiG CR deadline=**0.785**, mixed=**0.721** | deadline=**0.736**, mixed=**0.728** | sayı bayat |
| A2 | 913-916 | deadline DVR: AHE **0.232** < Cons 0.243 < RoSTAM 0.283; "AHE en yüksek etkin tamamlama ≈**0.77**" | AHE DVR=**0.360** > Cons=**0.320**; AHE eff=**0.640** < **Cons eff=0.680** | ⚠ **SONUÇ TERS**: Cons önde, AHE değil |
| A3 | 927-928 | rf delay AHE **87**s/BiG **51**s; deadline AHE **71**s/BiG **40**s | rf: AHE=**101**/BiG=**89**; deadline: AHE=**79**/BiG=**260** | BiG deadline delay 40→260 (büyük) |
| A4 | 930 | rf recovery AHE **66**s/BiG **39**s | AHE=**73**/BiG=**64** | bayat |
| A5 | 941 | AHE latency **0.22--0.25**ms tüm senaryolar | rf=0.27, mixed=0.29, deadline=0.30 → **0.27--0.30** | bayat |
| A6 | 943 | BiG **0.12--0.36**ms; RoSTAM **41--83**ms | BiG 0.12--0.28; RoSTAM **44--90**ms | bayat |
| A7 | 1009-1013 | "5r ... CR=1.000, DVR=**0.000**"; "BiG **0.785** deadline"; "AHE DVR **0.232** ~ EDF 0.243-0.283" | rf DVR=**0.008**; BiG deadline CR=0.736; AHE DVR=0.360 vs 0.320-0.400 | A1/A2 ile aynı |
| A8 | 1015 | 5r latency **0.22--0.25**ms | 0.27--0.30 | A5 ile aynı |

## GRUP B — Effect-size prose (STABİL, kesin bayat; satır 952-966)

| # | İddia | Metin | Veri (yeni effectsize) |
|---|-------|-------|------------------------|
| B1 | CR vs BiG (rf) | +0.30 | **+0.60** |
| B2 | DVR rf vs Cons / vs RoSTAM | +0.60 / +0.50 | **+0.68 / +1.00** |
| B3 | RecT rf vs BiG | −0.48 | **−0.28** |
| B4 | DVR deadline vs BiG | −0.84 | **−0.56** |
| B5 | Churn rf vs RoSTAM / vs Cons | +0.32 / +0.12 | **+0.76 / +0.64** |
| — | CR vs BiG mixed/deadline = +1.00 | +1.00 | +1.00 ✓ (doğru) |

## GRUP C — Sim (Plane A) prose

| # | Satır | İddia | Regenere sim | Not |
|---|------|-------|--------------|-----|
| C1 | 1156 | 3r deadline strict-fitness: "AHE **0.448** < BiG **0.461**" (AHE geride) | 3r deadline: AHE=**0.459** ≥ BiG=**0.458** | ⚠ yön şüpheli; eski sim koşusundan |
| C2 | ~1216 | Ablation tablosu (Full EDPS 0.538/0.483/0.538/0.520 vb.) | scripts/ablation_edps.py ile regenere edilip teyit edilmeli | bekliyor |
| — | Fitness tablosu (753-756) + scalability (821-824) | — | regenere, eşleşiyor (RoSTAM güncellendi ✓) |

## GRUP D — 3r prose (STABİL, çoğu DOĞRU)

| # | Satır | İddia | Veri (3r) | Durum |
|---|------|-------|-----------|-------|
| D1 | 1140-1145 | deadline CR: RoSTAM 0.985, Cons 0.978, AHE 1.000, BiG 0.636 | aynen | ✓ DOĞRU |
| D2 | 1079 | mixed makespan AHE **235**/Cons 217/RoSTAM 231 | AHE=238(med197)/Cons=217/RoSTAM=231 | AHE 235→238 ufak |

## GRUP E — 10r prose (VERİ EKSİK 40/60 — doldurma bitince TEKRAR)

Provizyonel uyuşmazlıklar (10r dolunca hepsi yeniden hesaplanacak):

| # | Satır | İddia | Mevcut 10r (eksik) |
|---|------|-------|--------------------|
| E1 | 67-72, 1045, 1162-165, 1330-334 | "10r her senaryoda en yüksek CR (0.996-1.000)" | mixed: AHE=0.995 < **Cons=1.000** → "her senaryoda" tutmuyor |
| E2 | 70, 1162 | "en düşük havuzlanmış makespan" | RoSTAM makespan birçok yerde daha düşük → şüpheli |
| E3 | 68, 1014, 134 | rf DVR=**0.012**, "≤0.012" | mevcut rf DVR=**0.030** |
| E4 | 991-997 | median makespan: Cons 171 vs AHE 224; AHE deadline 152 vs 358-387 | rf: AHE med=308/Cons med=387; deadline AHE med=355 |
| E5 | 73, 1045, 1146, 1334 | 10r deadline DVR: AHE 0.25, baseline 0.31-0.46 | AHE=0.227, Cons=0.376, RoSTAM=0.505 (aralık 0.38-0.51) |
| E6 | 1003 | mixed CR=0.996, makespan 165s | mevcut mixed AHE CR=0.995 |

## DOĞRULANAN (değişiklik gerekmez)
- Sim fitness tablosu (5r/25t) + scalability tablosu (3/5/10): regenere, eşleşiyor.
- Scalability gövde metni (satır 829-836: "N=3 0.488 vs 0.483", "N=10 0.493/0.488", "RoSTAM ~6.5ms"): aynen geçerli ✓.
- α=0.65, T=0.3 paper §III ↔ kod: hizalı (revert edildi).
- Düzeltilen caption'lar (n=5), ölçek filtreleri (stat/plot/extra): uygulandı.

---

## ÖNERİLEN AKSİYON (onayına bağlı)
1. **5r + effect-size (Grup A,B)**: stabil veri → şimdi metin→veri güncellenebilir; A2 için "AHE kazanır"→"Cons hafif önde / eş-lider" dürüst düzeltme.
2. **Grup C1**: 3r sim fitness yön iddiasını regenere sim'e göre düzelt (AHE ≥ BiG).
3. **Grup E (10r)**: Gazebo doldurma bitince hepsi yeniden hesaplanıp tek seferde güncellenecek.
4. Tüm zincir yeniden üretilip iki PDF derlenecek; metin↔tablo↔figür↔caption dörtlüsü tekrar doğrulanacak.

---

## EK BULGULAR (claim-seviyesi — regenere veriyle ortaya çıktı)

### F1 — İstatistiksel anlamlılık çöküyor (satır 972-985, 1263-1267)
- Metin: "5r'de 12/63 Bonferroni-anlamlı (7 AHE / 5 baseline)".
- Gerçek (doğru n=5): **0/63 Bonferroni-anlamlı** (ham p<0.05: 18). n=5 yetersiz güçlü
  (min iki-yönlü Mann-Whitney p≈0.008 > düzeltilmiş eşik 0.0024).
- 3r (n=15): **14/63** (metin 15 ≈ doğru). 10r (n=5): **0** (metin 0 ✓).
- → "5r'de 7 sonuç AHE lehine anlamlı" iddiası kalkmalı; güç 3r'de.

### F2 — "Where AHE costs" sahte-anlamlılık (DÜZELTİLDİ)
- Metin: "rf 87s vs 51s BiG p=0.001; deadline 71s vs 40s p<0.001; recovery EN YAVAŞ".
- Gerçek: rf delay AHE=101/BiG=89 p=0.421 (ns!); deadline AHE=79 < BiG=260 (AHE daha iyi);
  recovery AHE=73 mid-pack (Cons=103 en yavaş). Hiçbiri anlamlı değil.
- ✓ Paragraf veriye göre yeniden yazıldı.

### F3 — "Where AHE wins" deadline tersine (DÜZELTİLDİ)
- ✓ "AHE deadline kazanır ≈0.77" → "rf+mixed lider, deadline eş-lider (Cons 0.68 ≥ AHE 0.64)".

### UYGULANAN METİN DEĞİŞİKLİKLERİ (geri alınabilir, git)
- main.tex: "Where AHE wins" + "Where AHE costs" paragrafları veriye göre yeniden yazıldı.
- (main_tr.tex karşılıkları + effect-size prose + latency + abstract/conclusion HENÜZ yapılmadı.)
