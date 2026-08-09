# Keşif arşivi — reddedilmiş araştırma kolları

Bu dizindeki scriptler **makalede yer alan hiçbir sayıyı üretmiyor.** Hepsi tek
seferlik keşif koşuları; hangi yolların denendiğinin ve neden elendiğinin kaydı
olarak duruyorlar. Aktif işlem hattının parçası değiller.

| Script | Ne denedi | Sonuç |
|---|---|---|
| `exp_dynsel.py` | Çevrim içi öğrenilen paradigma seçimi vs statik bağlam haritası | Statik seçim doğrulandı; dinamik kol eklenmedi |
| `exp_lightsel.py` | EDPS yerine hafif, bağlam-anahtarlı seçici | Tam EDPS'in yerini tutmadı |
| `ahe_lever_explore.py` | W0_V3 ağırlık vektörü / sınıf özniteliği taraması | Realize edilebilir kazanç çıkmadı |
| `diag_wlbal.py` | `robot_failure`'da AHE↔BiG iş yükü dengesi farkının kaynağı | Teşhis amaçlı; düzeltme F45'e gitti |
| `tune_v41.py` | v4.1 (F22–F24) parametre araması | v4.5 tarafından aşıldı |
| `paradigm_audit.py` | Paradigma kullanım histogramı + zorlama modu | Yerini `../audit_paradigm_selection.py` aldı (limitation (viii) sayılarını o üretiyor) |

## Çalıştırma

Bu dosyalar `simulate_and_tune`'u import ediyor; o `scripts/` altında kaldığı
için arşivden doğrudan çalışmazlar. Üst dizini yola ekleyerek çağır:

```bash
PYTHONPATH=scripts python3 scripts/_explore/exp_dynsel.py
```

Sim düzlemini yeniden koşuyorsan F58 + geodezik bayraklarını export etmeyi unutma
(Öklid tuzağı) — ayrıntı `results/README.md`.
