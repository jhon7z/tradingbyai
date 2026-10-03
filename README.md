<div align="center">

# 🦅 XAUUSD Shinciro POI/AOI + 9Router AI
### Full Autonomous Hybrid Quantitative Trading Bot for MetaTrader 5

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-MetaTrader%205-green?logo=metatrader5)](https://www.metatrader5.com)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-9Router%20Multi--Model-orange)](https://github.com)
[![Control](https://img.shields.io/badge/Remote-Telegram%20Bot-blue?logo=telegram)](https://telegram.org)
[![Status](https://img.shields.io/badge/Status-Live%20Production-brightgreen)](#)

*Bot trading emas (XAUUSD) otomatis berbasis Price Action SMC (Smart Money Concepts), divalidasi oleh dewan juri AI dengan Auto-Fallback, dan dieksekusi secara instan dengan manajemen risiko presisi.*

---

</div>

## 📌 Sekilas Pandang (Overview)

**XAUUSD Shinciro AI Bot** menggabungkan presisi teknikal kuantitatif dengan kecerdasan buatan (LLM). Bot ini memetakan zona institusional pada timeframe **M5**, menunggu konfirmasi pergeseran struktur (*Order Confirmation*) pada timeframe **M1**, lalu memvalidasi probabilitas setup menggunakan **9Router AI Multi-Model** sebelum mengirim order ke **MetaTrader 5**.

---

## 🏗️ Alur Kerja Sistem (System Architecture)

```mermaid
flowchart TD
    Market([📊 Live Market: XAUUSD-VIP]) --> M5Scan[🔍 M5: Scan POI & AOI<br>RBS / SBR / QM + OB / FVG]
    M5Scan -->|Zona Aktif Tersentuh| M1Confirm[⏱️ M1: Order Confirmation<br>MSS / CHoCH & Wick Rejection]
    M1Confirm -->|CHoCH Terkonfirmasi| AIValidate{🤖 9Router Multi-Model AI<br>Evaluasi Setup}
    
    subgraph AI_Fallback [Multi-Model Auto-Fallback]
        M1[🥇 Gemini 3.8 Flash High] -->|503 / Timeout| M2[🥈 Gemini 3.5 Flash Lite]
        M2 -->|Error / Limit| M3[🥉 DeepSeek 3.2]
    end
    
    AIValidate -.-> AI_Fallback
    AIValidate -->|Approved Score ≥ 6/10| Exec[⚡ MT5 Market Execution<br>Dynamic Lot Sizing]
    AIValidate -->|Rejected| Skip[⛔ Skip Trade / Log Reason]
    
    Exec --> TG[📱 Telegram Alert & Control]
    Exec --> Trail[🛡️ Stepped Trailing SL<br>+35 pips ➔ BE+10, step +10 pips]