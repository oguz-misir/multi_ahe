# Revizyon planı — Q1 gönderimi

Bu plan 2026-07-30 denetiminin sonucudur. Kısa teşhis: **mühendislik ve dürüstlük
Q1 seviyesinde, ama iddia edilen katkı makalenin kendi kanıtıyla desteklenmiyor.**

| Ölçüm | Sonuç | Kaynak |
|---|---|---|
| 5 paradigmadan kaçı seçiliyor | **3** (priority-first, commit-once hiç aktive olmuyor) | Limitasyon (viii) |
| Baskınlık katmanı kaç kararı belirliyor | %24.8 — %99.9'unda spatial-greedy | 9989 durum replay |
| Katmanı sabitle değiştirsen | 9989 kararın **3'ü** değişir (%0.03) | aynı |
| Ablasyon: 8 varyant | hepsi **0.9 yp** içinde, hiçbiri ayrışmıyor | `tab:ablation` |

Hakemin yazacağı cümle hazır: *"EDPS öneriyorsunuz, kendi ablasyonunuz fark
yaratmadığını gösteriyor, eşleşmiş Gazebo ablasyonunu hiç koşmamışsınız."*
Bu, Limitasyon (x)'te zaten yazılı.

## Kararlar (kullanıcı, 2026-07-30) — üçü de kapandı

| | Karar | Sonucu |
|---|---|---|
| **D1** | **Tam uzunluk: T-ASE / RAS / JFR.** RA-L bırakıldı. | 24 sayfa korunur, dürüstlük katmanı (12 maddelik limitasyon, negatif ablasyon) budanmaz. A = yeniden çerçeveleme, kısaltma değil. `\thanks` içindeki "submitted to IEEE RA-L" güncellenecek. |
| **A1** | **İddia indirilecek, "Ecosystem" başlıktan çıkacak.** `ahe_mrta_v3` kod/veri/dosya adı KORUNUR. | Satılan iddia: bağlam-override kaskadı + geodezik ETA + sınırlı terminal onarım. Paradigma seçimi alt-mekanizma olarak kalır, katkı olarak sunulmaz. A2–A5 açıldı. |
| **D2** | **5r'yi n=20'ye çıkar, B ile birlikte.** | Birincil çıkarımsal ölçek 5r kalır. B4'ün `full` kolu AHE kolonunu verir; marjinal maliyet 3 baseline = 180 koşu. Toplam **420 koşu ≈ 34–69 sa**. |

## Karar (kullanıcı, 2026-07-30): **A ve B paralel**, C ertelendi

- **A — çerçeveyi gerçeğe indirme:** AKTİF. Sıfır hesaplama; B'nin 20–39 saatlik
  makine süresi boyunca paralel yürür. Aynı zamanda B'nin sigortası: ablasyon
  negatif çıkarsa A zaten zorunlu hâle gelir, pozitif çıkarsa A'nın geri
  çekilmesi kolayca geri alınır (bir paragraf terfi ettirilir).
- **B — eşleşmiş Gazebo ablasyonu:** AKTİF. Asıl kazanç burada.
- **C — ikinci arena:** ertelendi (B'den sonra).

**Paralellik neden işe yarıyor:** A yalnız metin/figür, B yalnız makine.
İkisi birbirini beklemez; tek çakışma B5'te (ablasyon sonucu Bölüm VII'yi
değiştirir), o da A2'nin yeniden yazdığı Bölüm III'ün üstüne biner.

---

## B · Eşleşmiş Gazebo ablasyonu

**Amaç:** kapalı çevrimde farkın seçiciden gelip gelmediğini ölçmek. Dört-yöntem
kıyaslaması bunu yapamaz, çünkü yöntemler seçiciden fazlasında farklı.

### Tasarım

| | |
|---|---|
| Kollar | `full` · `no-override` · `fixed-EDF` · `fixed-orphan` |
| Ölçek | 5r/25t (birincil) |
| Senaryo | üçü de (robot_failure, mixed_stress, deadline_pressure) |
| Tohum | 20, **ortak** (eşli test için) |
| Harita | 1 (C ertelendi) |
| Toplam | **240 koşu** |
| Süre | koşu başına medyan **4.9 dk** / ortalama 9.8 dk → **20–39 saat** |

Birincil uç nokta: `deadline_pressure`'da zamanında-etkin tamamlama
`CR×(1−DVR)`. İkincil: `robot_failure`'da CR ve toparlanma süresi.
Eşli Wilcoxon + Cliff δ, senaryo ailesi içinde Bonferroni.

### Adımlar

1. **B1 — bayrakları yaz. ✅ BİTTİ (2026-07-30).**
   `AHE_FORCE_PARADIGM=0..4`, `AHE_NO_OVERRIDE=1`, `AHE_NO_RECOVERY_BOOST=1`
   eklendi (`ahe_variants.py`); üçü de varsayılan kapalı, çözülmüş değerler
   `metadata.yaml: allocator_env`'e yazılıyor.
   **Kabul ölçütü tuttu:** bayraklar kapalıyken B1-öncesi kodla vekil düzlemde
   5r/25g × 3 senaryo × 20 tohumda AHE **60/60 hücrede tam ondalık özdeş**.
   (Kabul ölçütü kanonik `sim_fitness.csv` yerine eşli pre/post koşuma
   çevrildi: kanonik dosya `de797bd` öncesinden, dolayısıyla mutlak referans
   değil — bkz. aşağıdaki iki yan bulgu.)
   *Yan bulgu 1:* `simulate_and_tune.py` allokatörü tohumlamıyordu, Gazebo
   runner'ı (`experiment_runner_node.py:173`) tohumluyor → RoSTAM vekil
   düzlemde koşudan koşuya yeniden üretilemiyordu (aynı kod, iki koşu: 56/60
   hücre farklı). Düzeltildi.
   *Yan bulgu 2:* `--fitness-summary-name` yalnız özeti koruyordu; seedwise
   dosya adı sabit kodluydu ve gitignore'da → kısa bir keşif koşusu 500
   tohumluk veriyi sessizce eziyordu. Düzeltildi (seedwise adı özet adını izler).
2. **B2 — ön-kayıt. ✅ BİTTİ.** `paper/PREREGISTRATION.md` yazıldı; kampanyadan
   ÖNCE commit edilecek. n=5 hücrelerin eleştirisi post-hoc seçim şüphesiydi.
3. **B3 — ucuz ön-kontrol.** `scripts/run_ablation_precheck.sh` — aynı 4 kol
   önce vekil düzlemde (dakikalar). Kollar birbirinin aynısı çıkarsa bayrak
   bağlanmamıştır ve script exit 1 verir; 240 koşu harcanmaz.
4. **B4 — kampanya.** `run_ablation_campaign.sh` →
   `results/raw/gazebo_ablation/<kol>/`. Çökme-güvenli (SKIP_DONE=1), tek
   seferde tek deney, `load<5`. 420 koşu (240 ablasyon + 180 D2 baseline).
5. **B5 — analiz ve metin.** Limitasyon (x) kaldırılıp yerine sonuç yazılır.

### Üç olası sonuç — üçü de yazılabilir

| Sonuç | Ne yapılır |
|---|---|
| EDPS anlamlı önde | Asıl iddia kanıtlanır; A gereksizleşir. Makale güçlü Q1. |
| **Fark yok** (vekil ablasyonuna bakılırsa en olası) | Negatif sonuç dürüstçe raporlanır; **A zorunlu hâle gelir**. Yayımlanabilir bulgu: "bu rejimde switching machinery gerekli değil." |
| Sabit paradigma önde | Yöntem sadeleştirilir; makale "iki override yeter" iddiasına döner. |

---

## A · Çerçeveyi gerçeğe indirme (AKTİF, B ile paralel)

Satılacak iddia: *bağlam-override kaskadı + geodezik ETA + sınırlı terminal yük
onarımı, kapalı çevrimde arıza ve deadline baskısı altında zamanında
tamamlamayı korur.*

| Adım | İş | Ön koşul |
|---|---|---|
| **A1** | **KARAR (senin):** yeni iddia cümlesi + başlıktan "Ecosystem" çıkacak mı + AHE-MRTA adı korunacak mı | — (A2–A5'i blokluyor) |
| A2 | Bölüm III'ü override kaskadı önde olacak şekilde yeniden yaz; baskınlık dinamiği tek paragrafa insin | A1 |
| A3 | Özet (249 kelime sınırı) + Giriş katkı listesini yeni iddiaya hizala | A1 |
| A4 | Fig. 1'i yeniden çiz (override merkezde); okunabilirlik sorununu da burada çöz | A1 |
| A5 | Hormon tablolarını (V prototipleri, A/S) küçült ya da eke taşı — sayıları DEĞİŞTİRME | A1 |
| A6 | TR senkronu + derleme + değişen her sayının kaynağa karşı denetimi | A2–A5 |

Ad kararı notu: `ahe_mrta_v3` kod, veri dizinleri ve 300 koşunun dosya adlarına
gömülü. Adı korumayı, yalnız neyi temsil ettiğini değiştirmeyi öneriyorum —
yeniden adlandırma tüm veri zincirini kırar.

## C · İkinci arena (ertelendi)

`placement.py` ORIGIN/ARENA_LIM/GRID ve harita yolu **sabit kodlu** —
parametrize edilmeden ikinci haritada görevler duvara düşer. 60 koşu ≈ 5–10 saat.

---

## Dergi uyumu — ayrı karar

24 sayfalık metin RA-L'nin 6+2 sınırına girmiyor. Bu hacim **IEEE T-ASE**,
**RAS** veya **JFR** için doğal (üçü de Q1, tam uzunluk). RA-L'de kalmak
içeriğin ~2/3'ünü atmayı gerektirir ve dürüstlük katmanının çoğu gider.

---

## D · Denetim değerlendirmesinden gelen, A/B/C dışında kalan maddeler

| | İş | Not |
|---|---|---|
| **D1** | **KARAR: dergi.** Tam uzunluk (T-ASE / RAS / JFR) mı, RA-L (6+2, ~2/3 kısaltma) mı? | **A2'yi blokluyor** — A'nın kapsamını bu belirliyor. RA-L, dürüstlük katmanının çoğunu kaybettirir. |
| **D2** | **KARAR: birincil ölçekte güç.** n=5 → Bonferroni sonrası 0/63. | Aşağıdaki fırsata bak. |
| D3 | En güçlü kanıtı öne çıkar: deadline uyumu (0.79/0.66, 0.76/0.52, %38/%49) + 300 koşuluk kapalı çevrim. Şu an ikisi de anlatıda gömülü. | A3 iddiayı küçültür, D3 kanıtı büyütür — ayrı işler. |
| D4 | Limitasyon bloğunu grupla; her maddeye "ne yapıyoruz" cümlesi ekle. | 12 madde şu an savunmasız yüzey; (viii) ve (xi) yan yana kötü okunuyor. |

### D2 — üç seçenek ve bir maliyet fırsatı

1. **Sıfır maliyet:** birincil çıkarımsal ölçeği **3r** yap (n=15, 13/63 düzeltmeyi
   geçiyor, 8'i AHE lehine). 5r/10r betimleyici kalır. Bedeli: 3r'de tamamlama
   ayrışmıyor + "3 robot multi-robot mu" eleştirisi.
2. **180 koşu (~15–29 sa):** 5r'yi n=20'ye çıkar.
   **FIRSAT:** B4'ün `full` kolu zaten 5r/25t × 3 senaryo × 20 tohum = 60 AHE
   koşusu üretiyor. Dolayısıyla dört-yöntem kıyaslamasını n=20'ye çıkarmanın
   **marjinal maliyeti yalnız üç baseline = 180 koşu**. B4 ile birlikte
   420 koşu ≈ **34–69 saat**. B zaten koşacaksa önerim budur.
3. **Değiştirme:** 500-tohumlu vekili birincil test olarak bırak, Gazebo'yu
   açıkça betimleyici ilan et (şu anki hâl).
