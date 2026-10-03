<div align="center">

# 🦅 XAUUSD Shinciro POI/AOI + 9Router AI
### Full Autonomous Hybrid Quantitative Trading Bot for MetaTrader 5

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-MetaTrader%205-green?logo=metatrader5)](https://www.metatrader5.com)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-9Router%20Multi--Model-orange)](http://127.0.0.1:20128)
[![Control](https://img.shields.io/badge/Remote-Telegram%20Bot-blue?logo=telegram)](https://telegram.org)
[![Pair](https://img.shields.io/badge/Pair-XAUUSD--VIP-gold)](#)
[![Status](https://img.shields.io/badge/Status-Live%20Active-brightgreen)](#)

*Bot trading emas (XAUUSD-VIP) otomatis berbasis Price Action Smart Money Concepts (SMC), divalidasi oleh dewan juri AI dengan Auto-Fallback, dan dieksekusi secara instan dengan proteksi modal ketat.*

---

</div>

## 📌 Ringkasan Proyek

**XAUUSD Shinciro AI Bot** menggabungkan presisi analisa teknikal kuantitatif dengan kecerdasan buatan (LLM). Bot ini secara mandiri:
1. Memetakan zona institusional pada timeframe **M5** (RBS, SBR, QM, OB, FVG).
2. Menunggu konfirmasi pergeseran struktur (*Order Confirmation*) pada timeframe **M1** (CHoCH / Pinbar Rejection).
3. Memvalidasi probabilitas setup menggunakan **9Router AI Multi-Model** (Auto-Fallback).
4. Mengeksekusi order instan ke **MetaTrader 5 (MT5)** dengan lot dinamis.
5. Mengaktifkan **Stepped Trailing SL** otomatis untuk mengunci keuntungan bebas risiko.

---

## 🏗️ Alur Kerja Sistem (Workflow)

```mermaid
flowchart TD
    Market([📊 Live Market: XAUUSD-VIP]) --> M5Scan[🔍 M5: Scan POI & AOI<br>RBS / SBR / QM + OB / FVG]
    M5Scan -->|Zona Aktif Tersentuh| M1Confirm[⏱️ M1: Order Confirmation<br>MSS / CHoCH & Wick Rejection]
    M1Confirm -->|CHoCH Terkonfirmasi| AIValidate{🤖 9Router Multi-Model AI<br>Evaluasi Setup}
    
    subgraph AI_Fallback [Multi-Model Auto-Fallback System]
        M1[🥇 Gemini 3.8 Flash High] -->|503 / Timeout| M2[🥈 Gemini 3.5 Flash Lite]
        M2 -->|Error / Rate Limit| M3[🥉 DeepSeek 3.2]
    end
    
    AIValidate -.-> AI_Fallback
    AIValidate -->|Approved Score ≥ 6/10| Exec[⚡ MT5 Market Execution<br>Dynamic Lot Sizing]
    AIValidate -->|Rejected| Skip[⛔ Skip Trade / Log Reason]
    
    Exec --> TG[📱 Telegram Alert & Control]
    Exec --> Trail[🛡️ Stepped Trailing SL<br>+35 pips ➔ BE+10, step +10 pips]

    🎯 Strategi Inti: Shinciro POI & AOI + OC
1. Higher Timeframe (M5) — POI & AOI Mapping
POI (Point Of Interest):
RBS (Resistance Become Support): Resistance swing yang dijebol impulsif ke atas, menjadi lantai pijakan BUY saat harga retest.
SBR (Support Become Resistance): Support swing yang ditembus ke bawah, menjadi atap plafon SELL saat harga retest.
QM (Quasimodo): Deteksi struktur manipulasi harga (High-Low-Higher High-Lower Low) untuk SELL pada Left Shoulder, dan sebaliknya untuk BUY.
AOI (Area Of Interest):
OB (Order Block): Candle berlawanan arah terakhir sebelum ekspansi harga besar.
FVG (Fair Value Gap): Ketidakseimbangan harga (imbalance) antara 3 candle sebagai magnet likuiditas.
2. Lower Timeframe (M1) — Order Confirmation (OC)
MSS / CHoCH (Change of Character): Menghindari jebakan harga dengan mewajibkan adanya penembusan swing lokal M1 yang membuktikan pembalikan arah nyata.
Rejection Pinbar: Candle ekor panjang penolakan zona (>1.3x ukuran body).
3. Multi-Model AI Auto-Fallback (9Router)

Sistem memiliki 3 lapis otak AI cadangan untuk memastikan bot tidak pernah mogok akibat gangguan server:

ag/gemini-3.8-flash-high (Kecepatan tinggi & analisa mendalam)
gemini/gemini-3.5-flash-lite (Cadangan kilat ultra-responsif)
kr/deepseek-3.2 (Ahli kalkulasi numerik & risk-reward)

🛡️ Manajemen Risiko & Trailing SL
Lot Sizing Dinamis: Dihitung otomatis berdasarkan toleransi risiko persentase saldo (default: 1% per trade).
Hard SL & Fixed TP: Rasio Risk:Reward default 1:2.
Stepped Trailing SL Otomatis:
Profit +35 pips ➔ SL otomatis digeser ke BE + 10 pips (Risk-Free Trade).
Tiap nambah +10 pips ➔ SL dinaikkan lagi +10 pips untuk mengunci keuntungan berjalan.
Daily Loss Circuit Breaker: Bot otomatis berhenti trading jika akumulasi kerugian harian menyentuh batas 3%.
📱 Notifikasi & Remote Telegram

Bot terintegrasi penuh dengan Telegram melalui protokol Pure HTTP (Zero Library Conflict):
🎯 SHINCIRO POI & OC [BUY]
━━━━━━━━━━━━━━━━
📊 Symbol : XAUUSD-VIP | M5/M1
🏛 POI    : RBS
⚡ OC (M1): CHoCH_BULL
⭐ Score  : 8/10
━━━━━━━━━━━━━━━━
💵 Entry  : 4292.15
🛑 SL     : 4280.86
🎯 TP     : 4314.73
━━━━━━━━━━━━━━━━
POI=RBS | AOI=Bullish_OB | OC=CHoCH_BULL
💡 AI: Approved (8/10 via gemini-3.5-flash-lite): Valid liquidity sweep
🕐 00:04:31

🎮 Perintah Bot Telegram:
/status — Memeriksa status bot, saldo, ekuitas, dan daftar posisi aktif.
/close — Menutup paksa seluruh posisi yang terbuka secara darurat.
/report — Menampilkan rekap win rate dan total P&L 7 hari terakhir.
/pause — Menghentikan pembukaan posisi baru sementara waktu.
/resume — Mengaktifkan kembali bot trading.

🚀 Panduan Instalasi & Menjalankan
1. Clone Repositori
bash
git clone https://github.com/jhon7z/tradingbyai.git
cd tradingbyai
2. Pasang Dependencies
bash
pip install -r requirements.txt
3. Konfigurasi Sistem

Buka file config.py dan sesuaikan parameter berikut:

MT5 Credentials: Nomor Login, Password, dan Server Broker Anda.
Telegram Credentials: Token Bot dari @BotFather dan Chat ID dari @userinfobot.
9Router AI Config: Masukkan API Key dan daftarkan model yang aktif di 9Router Proxy.
Symbol Pair: Pastikan nama simbol sesuai dengan broker (contoh: XAUUSD-VIP).
4. Pengaturan MetaTrader 5
Buka aplikasi MT5 di Windows.
Masuk ke menu Tools ➔ Options ➔ Expert Advisors.
Centang opsi:
[x] Allow automated trading
[x] Allow DLL imports
5. Jalankan Bot
bash
python main.py

⚙️ Struktur Proyek
text
tradingbyai/
├── config.py              # Konfigurasi credentials, pair, dan parameter
├── strategy.py            # Logika Shinciro POI/AOI M5 + CHoCH M1
├── mt5_handler.py         # Eksekusi order, data rates, & trailing SL
├── telegram_handler.py    # Notifikasi & polling perintah via HTTP
├── risk_manager.py        # Kalkulasi lot dan proteksi modal
├── logger.py              # Sistem logging konsol & file harian
├── main.py                # Main loop scanner & 9Router Auto-Fallback
├── update_github.py       # Skrip utilitas push otomatis ke GitHub
├── requirements.txt       # Daftar dependensi Python
└── README.md              # Dokumentasi teknis proyek

⚖️ Disclaimer

PERINGATAN RISIKO: Perdagangan instrumen keuangan berleverage seperti Gold (XAUUSD) memiliki risiko tinggi terhadap modal Anda. Bot ini dikembangkan sebagai alat bantu komputasi kuantitatif. Pengembang tidak bertanggung jawab atas segala bentuk kerugian finansial yang terjadi. Selalu uji bot pada Akun Demo terlebih dahulu sebelum menggunakannya pada akun riil.