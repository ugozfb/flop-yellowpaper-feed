# flop-yellowpaper-feed

**Türkçe** | [English](README.md)

[FLOP Network Yellow Paper](https://github.com/flop-labs/yellowpaper) için makinenin okuyabileceği bir değişiklik akışı.

Protokol hâlâ değişiyor ve FLOP Labs, FLOP üzerinde bir şey kuranlardan ajanlarına Yellow Paper
reposunu izletmelerini istedi. O reponun hiç release'i ya da etiketi yok: değişiklikler `main`
dalına `docs(yellowpaper): sync 0.5.0 (draft) from flop-core@…` adlı commit'lerle geliyor. Bu repo
`main` dalını üç saatte bir kontrol eder ve her yeni commit'te neyin değiştiğini, bir ajanın
Markdown farklarıyla uğraşmadan okuyabileceği biçimde kaydeder.

Resmî olmayan bir topluluk aracıdır. FLOP Labs ile bağlantısı yoktur.

## Ajandan kullanma

```
https://raw.githubusercontent.com/ugozfb/flop-yellowpaper-feed/main/feed.json
```

Ajanınız `last_commit` değerini saklasın. Bir sonraki kontrolde değer değiştiyse, sakladığı
commit'ten daha yeni girişleri okusun. Bunu yaptıran bir istem:

> https://raw.githubusercontent.com/ugozfb/flop-yellowpaper-feed/main/feed.json adresini oku.
> `last_commit` kaydettiğinden farklıysa, kaydettiğin commit'ten yeni olup `content_change` değeri
> true olan her girişi listele: önce `params` içindeki değer değişikliklerini, sonra `changelog`,
> sonra `sections`. Ayrıntı için `url` bağlantısını aç. Sonra yeni `last_commit` değerini kaydet.

RSS/Atom okuyucusu kullananlar aynı yerdeki `feed.xml` dosyasını ekleyebilir.

## Bir girişte ne var

| Alan | Anlamı |
|---|---|
| `commit`, `url`, `date`, `subject` | Yellow Paper commit'i, en yenisi en üstte |
| `flop_core` | Commit başlığında geçiyorsa, senkronun dayandığı flop-core sürümü |
| `content_change` | `yellowpaper.md`, parametre dosyası, `CHANGELOG.md` ya da `decisions/` değiştiyse true |
| `files` | Değişen her dosya, eklenen ve silinen satır sayısıyla |
| `sections` | Metni değişen Yellow Paper başlıkları; numarasız başlıklar üstlerindeki numaralı başlıkla birlikte yazılır (`8.2 … › Requirements`) |
| `params` | `params/flop-protocol-params.yaml` girişleri, `name` alanına göre eşleştirilir: `added`, `removed` ya da değişen `fields` ile `modified`; `value` değiştiyse `old` ve `new` |
| `changelog` | `CHANGELOG.md` dosyasına eklenen maddeler |
| `decisions` | `decisions/` klasöründe değişen satırlarda geçen karar numaraları (`D-0000`); her geçiş yeni bir karar anlamına gelmez |

Akış en son 100 commit'i tutar ve yalnız `main` ilerlediğinde değişir.

## Nasıl çalışıyor

`.github/workflows/watch.yml`, `watch.py` dosyasını zamanlanmış olarak (ve Actions sekmesinden elle)
çalıştırır. Yellow Paper'ı klonlar, `main` dalını `state.json` içindeki commit'le karşılaştırır,
`feed.json`, `feed.xml` ve `state.json` dosyalarını yazıp commit'ler. Bir commit içeriği
değiştirdiyse bu repoda bir issue da açar; repoyu izleyen herkese bildirim gider.

Kendi bilgisayarınızda çalıştırmak için (Python 3.10+, PyYAML):

```
git clone https://github.com/flop-labs/yellowpaper.git yp
YP_DIR=yp python watch.py
```

İlk çalıştırma, akış boş kalmasın diye son beş commit'i anlatır.

Sınırlar:

- GitHub zamanlanmış çalıştırmaları gecikmeli başlatabilir ve herkese açık bir repoda 60 gün
  hareket olmazsa zamanlanmış görevleri durdurur. Yellow Paper o kadar uzun süre değişmezse
  görevi Actions sekmesinden yeniden açın.
- Bölümler, değişen satırların üstündeki en yakın başlığa bakılarak bulunur.
- Alan alan karşılaştırılan tek dosya parametre dosyasıdır. Metindeki değişiklikler bölüm ve
  changelog maddesi olarak bildirilir, yorumlanmaz.

## Kaynak ve lisans

Akıştaki bölüm başlıkları ve changelog satırları FLOP Network Yellow Paper'dan alıntıdır,
© FLOP Labs, [CC BY 4.0](https://github.com/flop-labs/yellowpaper/blob/main/LICENSE) lisanslı.
Her giriş anlattığı commit'e bağlanır.

Bu repodaki kod [Apache License 2.0](LICENSE) ile lisanslıdır.
