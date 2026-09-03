# Congress Trade Alert

ABD Kongre üyelerinin resmi olarak açıkladığı hisse senedi işlemlerini
(Periodic Transaction Report / PTR) **resmi kaynaklardan** (House Clerk +
Senate eFD) tarar, belirlenen kriterlere uyanlar için Telegram (birincil)
ve e-posta (yedek/acil ikinci kanal) ile bildirim gönderir. Yatırım tavsiyesi
vermez — sadece haber verir.

## Kurallar

- Kapsam: Tüm Kongre (Senato + Temsilciler Meclisi), tutar filtresi yok.
- **Temel filtre**: `bildirim tarihi − işlem tarihi < 15 gün` olmayan işlemler
  hiç bildirilmez.
- **Acil (🔴) — kapanışa yakınlık**: Sistemin filing'i *tespit ettiği an*,
  o günkü NYSE kapanışına ≤60 dakika kalmışsa → Telegram + e-posta birlikte,
  anında.
- **Acil (🔴) — dev şirket dışı satın alma**: İşlem bir **satın alma** ve
  şirket **S&P 500 üyesi değilse** → Telegram + e-posta birlikte, anında.
- Normalde: önce Telegram denenir, başarısız olursa e-postaya düşülür.

## Bilinen sınırlamalar (önemli)

- Resmi sistemler işlemi **anında değil, üye açıkladığında** gösterir (yasal
  üst sınır 45 gün; bu bot 15 günden uzun gecikmeleri zaten eliyor).
- Resmi filing kayıtlarında **saat bilgisi yok, sadece tarih var** — bu
  yüzden "kapanışa yakınlık" kriteri, işlemin gerçek bildirim saatine değil,
  **botun filing'i ilk gördüğü ana** göre hesaplanır (tarama sıklığı: ~20 dk).
- Bu proje bu ortamdan (Claude) **canlı test edilemedi** çünkü bu ortamın ağ
  erişimi House/Senate/Telegram'a kapalı. Kod, bu sitelerin bilinen yapısına
  göre yazıldı; siteler değişmiş olabilir. İlk GitHub Actions çalıştırmasında
  hata alırsan, **Actions sekmesindeki log çıktısını** bana yapıştır, birlikte
  düzeltiriz.
- House Clerk'te "kağıt" (taranmış PDF) eski usul filing'ler zor
  ayrıştırıldığından şimdilik atlanıyor (loglanıyor); elektronik filing'ler
  (güncel çoğu filing) işleniyor.

## Kurulum

### 1) GitHub reposu oluştur
GitHub'da yeni bir **public** repo aç (public → Actions dakika limiti yok,
kod zaten hassas bir şey içermiyor). İstersen private de yapabilirsin, ücretsiz
planda aylık 2000 dakika sınırı var, bu bot günde ~35-40 dakika kullanır.

Bu klasördeki tüm dosyaları (`.github/` dahil) o repoya yükle — ya `git push`
ile ya da GitHub web arayüzünden "Add file → Upload files".

### 2) Sırları (secrets) ekle
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| İsim | Değer |
|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather'dan aldığın token |
| `TELEGRAM_CHAT_ID` | Aşağıda anlatılan yöntemle bulacağın sayı |
| `GMAIL_ADDRESS` | Bildirimleri gönderecek gmail adresin |
| `GMAIL_APP_PASSWORD` | Aşağıda anlatılan uygulama şifresi |

**Telegram chat ID nasıl bulunur**: Telegram'da `@userinfobot`'a `/start`
yaz, sana kendi kullanıcı ID'ni (bir sayı) verecek. Kendi botunla özel
(1:1) sohbette bu sayı senin chat ID'ndir. (Ayrıca kendi botuna da bir kez
`/start` yazmayı unutma, yoksa bot sana mesaj gönderemez.)

**Gmail uygulama şifresi nasıl alınır**: Google hesabında 2 adımlı doğrulama
açık olmalı → myaccount.google.com/apppasswords → yeni bir uygulama şifresi
oluştur (16 haneli) → onu `GMAIL_APP_PASSWORD` olarak kullan (normal Gmail
şifreni DEĞİL).

### 3) Actions'ı etkinleştir ve test et
Repo → **Actions** sekmesi → "Congress Trade Monitor" workflow'unu seç →
**Run workflow** ile elle bir kez tetikle. Loglara bak, hata varsa bana
yapıştır.

Sorun yoksa iş, cron ile **her 20 dakikada bir** otomatik çalışacak.

## Yerel test (opsiyonel)

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
export GMAIL_ADDRESS=...
export GMAIL_APP_PASSWORD=...
python -m scraper.main
```
