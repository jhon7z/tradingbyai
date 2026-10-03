import os
import MetaTrader5 as mt5

# ─── MT5 Credentials (Langsung Isi Disini) ───────────────────────────────────
MT5_LOGIN    = 1342858
MT5_PASSWORD = "q%8THkE1"
MT5_SERVER   = "VTMarkets-Demo"

# ─── Telegram Credentials ────────────────────────────────────────────────────
TELEGRAM_TOKEN   = "8954717025:AAGSalXeXz6L7oHNF7VrcagybPK4NSN-RPo"
TELEGRAM_CHAT_ID = "1486922202"

# ─── 9Router AI Multi-Model Config ───────────────────────────────────────────
ROUTER_BASE_URL   = "http://127.0.0.1:20128/v1"
ROUTER_API_KEY    = "sk-ad47112bd364c7f6-bcpwyg-ba2d05d5"
ROUTER_MODELS     = ["ag/gemini-3.8-flash-high","gemini/gemini-3.5-flash-lite","kr/deepseek-3.2"]
USE_AI_VALIDATION = True

# ─── Symbol & Timeframes ─────────────────────────────────────────────────────
SYMBOL = "XAUUSD-VIP"
TIMEFRAME_MAIN    = mt5.TIMEFRAME_M5    # Mapping POI & AOI di M5
TIMEFRAME_ENTRY   = mt5.TIMEFRAME_M1    # Order Confirmation (CHoCH/MSS) di M1

# ─── Risk Management ─────────────────────────────────────────────────────────
LOT_SIZE          = 0.01
MAX_RISK_PERCENT  = 1.0     # Maksimal resiko 1% balance per trade
SL_BUFFER_POINTS  = 30      # Buffer SL 3 pips
RR_RATIO          = 2.0     # Risk:Reward 1:2

# ─── Parameter POI/AOI Shinciro ──────────────────────────────────────────────
TOLERANCE_POINTS  = 20      # Toleransi zona POI 2 pips di M5

# ─── Stepped Trailing SL (35 pips -> BE+10) ──────────────────────────────────
TRIGGER_PIPS      = 35      # Running profit 35 pips -> aktifkan SL BE+10
FIRST_BE          = 10      # Lock profit 10 pips diatas/dibawah entry
STEP_PIPS         = 10      # Tiap nambah 10 pips profit -> SL naik 10 pips

# ─── Bot Controls ────────────────────────────────────────────────────────────
SESSION_START_HOUR  = 2     # Jam 02:00 UTC (09:00 WIB)
SESSION_END_HOUR    = 21    # Jam 21:00 UTC (04:00 WIB)
MAX_OPEN_TRADES     = 3
SIGNAL_COOLDOWN_SEC = 180   # Cooldown sinyal 3 menit
CHECK_INTERVAL_SEC  = 10    # Cek market tiap 10 detik (cepat & responsif)
MAX_DAILY_LOSS_PCT  = 3.0