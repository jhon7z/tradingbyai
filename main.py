#!/usr/bin/env python3
"""
XAUUSD Shinciro POI/AOI + OC Bot
With Live Market Scanner Logs & Auto-Fallback AI
"""
import time, signal, sys, json, requests
from datetime import datetime, timezone
from config import (SYMBOL, TIMEFRAME_MAIN, TIMEFRAME_ENTRY,
                    MAX_OPEN_TRADES, SESSION_START_HOUR, SESSION_END_HOUR,
                    SIGNAL_COOLDOWN_SEC, CHECK_INTERVAL_SEC,
                    TRIGGER_PIPS, STEP_PIPS, FIRST_BE,
                    ROUTER_BASE_URL, ROUTER_API_KEY, ROUTER_MODELS, USE_AI_VALIDATION)
from mt5_handler import MT5Handler
from telegram_handler import TelegramHandler
from strategy import ShinciroStrategy
from risk_manager import RiskManager
from logger import get_logger

log = get_logger("main")

_last_signal_time: dict = {}
_processed:        set  = set()
_trailing_tracker: dict = {}
_running = True

def _stop(sig, frame):
    global _running
    _running = False
    log.info("Shutdown...")

signal.signal(signal.SIGINT,  _stop)
signal.signal(signal.SIGTERM, _stop)

def in_session() -> bool:
    h = datetime.now(timezone.utc).hour
    return SESSION_START_HOUR <= h < SESSION_END_HOUR

def sig_key(s) -> str:
    return f"{s.direction}_{s.poi_type}_{s.entry_price:.2f}"

def in_cooldown(s) -> bool:
    return (time.time() - _last_signal_time.get(sig_key(s), 0)) < SIGNAL_COOLDOWN_SEC

def mark_time(s):
    _last_signal_time[sig_key(s)] = time.time()


# ─── 9Router Multi-Model Auto-Fallback ───────────────────────────────────────
def validate_with_9router(sig) -> tuple[bool, str]:
    if not USE_AI_VALIDATION or not ROUTER_API_KEY:
        return True, "AI disabled"

    url = f"{ROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {ROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "You are an expert XAUUSD Price Action & SMC quantitative trader specializing in "
        "Shinciro POI & AOI with Order Confirmation (OC).\n"
        "Evaluate setup. Respond ONLY in JSON: {\"valid\": true|false, \"confidence\": 1-10, \"reason\": \"short reason\"}"
    )

    user_prompt = (
        f"Symbol: {sig.symbol} | Direction: {sig.direction}\n"
        f"POI Type: {sig.poi_type} | Details: {sig.details}\n"
        f"Order Confirmation (M1): {sig.oc_type}\n"
        f"Entry Price: {sig.entry_price:.2f}\n"
        f"Stop Loss: {sig.sl_price:.2f} | Take Profit: {sig.tp_price:.2f}"
    )

    for model_name in ROUTER_MODELS:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            log.info(f"🤖 Validasi ke 9Router [{model_name}]...")
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.ok:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content: content = content.split("```")[1].split("```")[0].strip()

                res = json.loads(content)
                is_valid   = res.get("valid", True)
                confidence = res.get("confidence", 7)
                reason     = res.get("reason", "OK")

                log.info(f"✅ [{model_name}] valid={is_valid} | Score={confidence}/10 | {reason}")
                if is_valid and confidence >= 6:
                    return True, f"Approved ({confidence}/10 via {model_name}): {reason}"
                else:
                    return False, f"Rejected ({confidence}/10 via {model_name}): {reason}"
            else:
                log.warning(f"⚠️ [{model_name}] Gagal HTTP {resp.status_code}. Beralih ke model cadangan...")
        except Exception as e:
            log.warning(f"⚠️ [{model_name}] Timeout/Error. Beralih ke model cadangan...")

    return True, "Fallback Pass (Semua AI offline/timeout)"


# ─── Main Program ────────────────────────────────────────────────────────────
def main():
    log.info("=" * 65)
    log.info("  XAUUSD Shinciro POI/AOI + OC Bot [Live Scanner Active]")
    log.info("=" * 65)

    mt5   = MT5Handler()
    if not mt5.connect():
        log.critical("Tidak bisa konek MT5. Exit.")
        sys.exit(1)

    tg    = TelegramHandler(mt5)
    risk  = RiskManager(mt5)
    pt    = mt5.get_point(SYMBOL)
    strat = ShinciroStrategy(SYMBOL, pt)

    tg.start_polling()
    tg.notify_start(mt5.get_balance())
    log.info(f"Bot Aktif! Models Cadangan: {ROUTER_MODELS}")

    while _running:
        try:
            _tick(mt5, tg, strat, risk, pt)
        except Exception as e:
            log.exception(f"Error loop: {e}")
            tg.notify_error(str(e))
        time.sleep(CHECK_INTERVAL_SEC)

    mt5.disconnect()
    tg.send("🔴 <b>Bot STOPPED.</b>")


def _tick(mt5, tg, strat, risk, pt):
    if tg.is_paused:
        return

    # 1. Pantau Trailing SL tiap detik loop
    _monitor_trailing_sl(mt5, tg, pt)

    if not in_session():
        log.debug("Di luar sesi.")
        return
    if risk.is_daily_loss_exceeded():
        tg.send("⚠️ <b>Daily loss limit hit! Bot pause.</b>")
        return
    if mt5.count_open_trades(SYMBOL) >= MAX_OPEN_TRADES:
        return

    # 2. Ambil data M5 (Scan POI & AOI)
    df5 = mt5.get_rates(SYMBOL, TIMEFRAME_MAIN, 200)
    if df5 is None or len(df5) < 50:
        return

    tick = mt5.get_tick(SYMBOL)
    if not tick:
        return
    cur_price = tick.bid

    pois = strat.find_m5_pois(df5)

    # ── LIVE SCANNER LOG (Biar keliatan botnya lagi kerja!) ──
    if not pois:
        log.info(f"📡 [SCAN] Harga {SYMBOL}: {cur_price:.2f} | Belum ada POI M5 di dekat harga")
        return
    else:
        poi_info = ", ".join([f"{p.poi_type} @ {p.price:.2f}" for p in pois[:2]])
        log.info(f"🔥 [SCAN] Harga: {cur_price:.2f} | POI Aktif: [{poi_info}] | Memantau M1...")

    # 3. Cek Order Confirmation di M1
    df1 = mt5.get_rates(SYMBOL, TIMEFRAME_ENTRY, 50)
    if df1 is None or len(df1) < 10:
        return

    for poi in pois:
        sig = strat.check_m1_confirmation(df1, poi)
        if not sig:
            continue

        key = sig_key(sig)
        if key in _processed or in_cooldown(sig):
            continue

        log.info(f"🎯 POI TERKONFIRMASI M1: {sig.direction} | {sig.poi_type} | OC={sig.oc_type} | Entry={sig.entry_price:.2f}")

        # 4. Validasi ke 9Router AI
        ai_ok, ai_msg = validate_with_9router(sig)
        if not ai_ok:
            log.warning(f"⛔ AI Skip Setup: {ai_msg}")
            mark_time(sig)
            continue

        # 5. Kirim Sinyal ke Telegram
        sig.details += f"\n💡 AI: {ai_msg}"
        tg.notify_signal(sig)

        # 6. Risk Check
        bal = mt5.get_balance()
        ok, reason = risk.validate_signal(sig, bal)
        if not ok:
            log.warning(f"Risk Reject: {reason}")
            continue

        # 7. Eksekusi Order
        sl_dist = abs(sig.entry_price - sig.sl_price) / pt
        lot     = risk.calculate_lot(SYMBOL, sl_dist)
        tp      = risk.calculate_tp(sig.entry_price, sig.sl_price, sig.direction)

        r = mt5.place_market_order(SYMBOL, sig.direction, lot, sig.sl_price, tp, comment=f"SH_{sig.poi_type}")
        if r:
            tg.notify_order(sig.direction, SYMBOL, lot, sig.entry_price, sig.sl_price, tp, r.order)
            _processed.add(key)
            mark_time(sig)
        else:
            tg.notify_error(f"Order gagal: {sig.direction} {SYMBOL}")


def _monitor_trailing_sl(mt5, tg, pt):
    global _trailing_tracker
    positions = mt5.get_open_positions(SYMBOL)
    pip_size  = pt * 10

    for pos in positions:
        is_buy    = (pos.type == 0)
        tick      = mt5.get_tick(pos.symbol)
        if not tick: continue

        cur_price = tick.bid if is_buy else tick.ask
        profit_pips = ((cur_price - pos.price_open) / pip_size if is_buy
                       else (pos.price_open - cur_price) / pip_size)

        if profit_pips < TRIGGER_PIPS: continue

        extra_steps   = int((profit_pips - TRIGGER_PIPS) / STEP_PIPS)
        target_be_pip = FIRST_BE + (extra_steps * STEP_PIPS)

        last_be = _trailing_tracker.get(pos.ticket, 0)
        if target_be_pip <= last_be: continue

        new_sl = (round(pos.price_open + target_be_pip * pip_size, 2) if is_buy
                  else round(pos.price_open - target_be_pip * pip_size, 2))

        sl_better = (new_sl > (pos.sl or 0)) if is_buy else ((pos.sl == 0) or (new_sl < pos.sl))
        if not sl_better: continue

        old_sl  = pos.sl
        success = mt5.modify_sl(pos, new_sl)
        if success:
            _trailing_tracker[pos.ticket] = target_be_pip
            direction = "BUY" if is_buy else "SELL"
            header = "🟡 <b>TRAILING SL AKTIF!</b>" if last_be == 0 else f"📈 <b>TRAILING SL NAIK (+{STEP_PIPS} pip)</b>"
            tg.send(
                f"{header}\n━━━━━━━━━━━━━━━━\n"
                f"🎫 Ticket : #{pos.ticket} [{direction}]\n"
                f"💹 Profit : +{profit_pips:.1f} pip\n"
                f"🛡 SL Baru: <b>{new_sl:.2f}</b> (BE+{target_be_pip} pip)\n"
                f"🕐 {datetime.now():%H:%M:%S}"
            )
            log.info(f"Trailing #{pos.ticket} | Profit={profit_pips:.1f}p | SL {old_sl:.2f} -> {new_sl:.2f}")


if __name__ == "__main__":
    main()