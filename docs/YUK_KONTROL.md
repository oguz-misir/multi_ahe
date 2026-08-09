# Yük Kontrol Protokolü

Bu depo üzerinde çalışan otomasyonlar, özellikle ROS 2, Gazebo, RViz, Nav2,
LaTeX ve toplu deney komutları, bilgisayarın masaüstünü kullanılmaz hâle
getirmemelidir. Ağır bir komuttan önce ve uzun süren komut boyunca
`scripts/load_guard.sh` kullanılmalıdır.

## Zorunlu kurallar

1. Aynı anda yalnızca bir Gazebo/ROS 2 deneyi çalıştırılır.
2. Yeni deneyden önce şu kontrol başarılı olmalıdır:

   ```bash
   bash scripts/load_guard.sh preflight
   ```

3. Bir dakikalık yük ortalaması `8.0` değerini aşarsa yeni ağır komut
   başlatılmaz.
4. Kullanılabilir bellek `6 GiB` altındaysa yeni Gazebo/Nav2 koşusu
   başlatılmaz.
5. Önceden çalışan bir ROS 2/Gazebo/RViz süreci varsa ikinci koşu
   başlatılmaz.
6. 10 robotlu Nav2 ile Gazebo ve RViz'i aynı anda yazılımsal render eden tam
   koşu varsayılan olarak yasaktır. Böyle bir koşu ancak ayrıca izin verilerek,
   CPU/bellek sınırı ve çalışma sırasındaki yük gözlemcisi ile başlatılabilir.
7. Yük sınırı aşılırsa yalnızca o komutun oluşturduğu süreç grubu durdurulur;
   genel `pkill` kullanılmaz.
8. `rg`, dosya okuma ve küçük sözdizimi kontrolleri gibi hafif komutlarda da
   sistem durumu şüpheliyse önce yük kontrolü yapılır. Birden fazla pahalı
   doğrulama komutu paralel çalıştırılmaz.

## Eşiklerin anlamı

- `load1 <= 8.0`: 16 mantıksal işlemcili bu bilgisayarda masaüstü için
  işlemci payı bırakır.
- `MemAvailable >= 6144 MiB`: Gazebo/RViz yazılımsal render ve VS Code için
  güvenli bellek payı bırakır.
- `heavy_processes == 0`: ikinci ROS 2/Gazebo/Nav2 ağacının yanlışlıkla
  açılmasını önler.

Eşikler yalnızca bilinçli bir bakım/deney oturumunda ortam değişkenleriyle
daraltılabilir veya genişletilebilir:

```bash
LOAD_GUARD_MAX_LOAD=6 \
LOAD_GUARD_MIN_MEM_MB=7168 \
LOAD_GUARD_MAX_HEAVY=0 \
bash scripts/load_guard.sh preflight
```

## Fig. 7 için güvenli yöntem

Fig. 7 yeniden üretiminde öncelik, tek bir kaydedilmiş durumun Gazebo ve RViz
tarafından sırayla görselleştirilmesidir. Böylece iki panel aynı robot
koordinatlarını ve aynı ortamı gösterirken 10 ayrı Nav2 yığınının iki GUI ile
eşzamanlı çalıştırılması gerekmez. Tam eşzamanlı koşu kullanılacaksa yakalama
betiğinin ön kontrolü ve çalışma sırasındaki kontrolleri atlanamaz.

Ortam eşitliği, hiçbir ROS node'u başlatmadan şu komutla doğrulanır:

```bash
bash scripts/load_guard.sh environment-validation
python3 scripts/validate_fig7_environment.py
```

Bu doğrulama Gazebo SDF engellerini 0.05 m/piksel çözünürlükte rasterleştirir,
RViz'in `obstacle_map.pgm` maskesiyle karşılaştırır ve arena ortasından geçen
kesintisiz bir şerit bulunmadığını denetler. Fig. 7 yakalama betiği de aynı
doğrulamayı ağır süreçleri başlatmadan önce otomatik çalıştırır.
