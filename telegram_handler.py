"""
Telegram Handler — Pure HTTP (Shinciro POI/AOI Edition)
"""
from __future__ import annotations
import threading, time, requests
from datetime import datetime
from typing import TYPE_CHECKING
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SYMBOL
from logger import get_logger

if TYPE_CHECKING:
    from mt5_handler import MT5Handler

log = get_logger("telegram")
BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


class TelegramHandler:
    def __init__(self, mt5: "MT5Handler"):
        self.mt5     = mt5
        self._paused = False
        self._offset = 0

    # ── Kirim Pesan ───────────────────────────────────────────
    def send(self, text: str):
        try:
            requests.post(f"{BASE}/sendMessage", json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       text,
                "parse_mode": "HTML"
            }, timeout=10)
        except Exception as e:
            log.error(f"Telegram send error: {e}")

    # ── Notifikasi Sinyal & Order ─────────────────────────────
    def notify_start(self, balance):
        self.send(
            f"🤖 <b>XAUUSD Shinciro POI/AOI Bot AKTIF</b>\n"
            f"📊 Symbol : {SYMBOL} | TF: M5 & M1\n"
            f"💰 Balance: ${balance:.2f}\n"
            f"🕐 {datetime.now():%Y-%m-%d %H:%M:%S}"
        )

    def notify_signal(self, sig):
        e = "🔴 SELL" if sig.direction == "SELL" else "🟢 BUY"
        poi_name = getattr(sig, "poi_type", "POI")
        oc_name  = getattr(sig, "oc_type", "M1 CHoCH")
        self.send(
            f"🎯 <b>SHINCIRO POI & OC [{e}]</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📊 Symbol : {sig.symbol} | {getattr(sig, 'timeframe', 'M5/M1')}\n"
            f"🏛 POI    : <b>{poi_name}</b>\n"
            f"⚡ OC (M1): <b>{oc_name}</b>\n"
            f"⭐ Score  : {sig.confidence}/10\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 Entry  : <b>{sig.entry_price:.2f}</b>\n"
            f"🛑 SL     : {sig.sl_price:.2f}\n"
            f"🎯 TP     : {sig.tp_price:.2f}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{getattr(sig, 'details', '')}\n"
            f"🕐 {datetime.now():%H:%M:%S}"
        )

    def notify_order(self, direction, symbol, lot, price, sl, tp, ticket):
        e = "🔴" if direction == "SELL" else "🟢"
        self.send(
            f"{e} <b>ORDER EXECUTED [{direction}]</b>\n"
            f"📊 {symbol} | Lot: {lot}\n"
            f"📌 Entry : {price:.2f}\n"
            f"🛑 SL    : {sl:.2f}\n"
            f"🎯 TP    : {tp:.2f}\n"
            f"🎫 Ticket: #{ticket}"
        )

    def notify_tp(self, ticket, profit):
        self.send(f"✅ <b>TP HIT! #{ticket}</b>\nProfit: +${profit:.2f} 🎉")

    def notify_sl(self, ticket, loss):
        self.send(f"🛑 <b>SL HIT #{ticket}</b>\nLoss: -${abs(loss):.2f}")

    def notify_error(self, msg):
        self.send(f"⚠️ <b>ERROR</b>\n{msg}")

    # ── Command Polling ───────────────────────────────────────
    def start_polling(self):
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()
        log.info("Telegram command polling started")

    def _poll_loop(self):
        while True:
            try:
                resp = requests.get(f"{BASE}/getUpdates", params={
                    "offset":          self._offset,
                    "timeout":         30,
                    "allowed_updates": ["message"]
                }, timeout=35)
                if resp.ok:
                    for upd in resp.json().get("result", []):
                        self._offset = upd["update_id"] + 1
                        self._handle(upd)
            except Exception as e:
                time.sleep(5)

    def _handle(self, update: dict):
        text = update.get("message", {}).get("text", "").strip().lower()
        if   text.startswith("/start"):  self._cmd_start()
        elif text.startswith("/status"): self._cmd_status()
        elif text.startswith("/close"):  self._cmd_close()
        elif text.startswith("/report"): self._cmd_report()
        elif text.startswith("/pause"):
            self._paused = True
            self.send("⏸ <b>Bot PAUSED.</b>")
        elif text.startswith("/resume"):
            self._paused = False
            self.send("▶️ <b>Bot RESUMED.</b>")
        elif text.startswith("/help"):   self._cmd_help()

    def _cmd_start(self):
        self.send("🤖 <b>XAUUSD Shinciro POI/AOI Bot</b>\nKetik /help untuk perintah.")

    def _cmd_status(self):
        bal = self.mt5.get_balance()
        eq  = self.mt5.get_equity()
        pos = self.mt5.get_open_positions(SYMBOL)
        pnl = self.mt5.get_daily_pnl(SYMBOL)
        st  = "⏸ PAUSED" if self._paused else "✅ RUNNING"
        pt  = ""
        for p in pos:
            d    = "BUY" if p.type == 0 else "SELL"
            sign = "+" if p.profit >= 0 else ""
            pt  += f"\n#{p.ticket} {d} {p.volume}lot @ {p.price_open:.2f} | {sign}{p.profit:.2f}"
        self.send(
            f"📊 <b>STATUS: {st}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💰 Balance : ${bal:.2f}\n"
            f"📈 Equity  : ${eq:.2f}\n"
            f"📅 P&L Hari Ini: {'+' if pnl>=0 else ''}{pnl:.2f}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"<b>Posisi ({len(pos)}):</b>"
            f"{pt if pt else chr(10)+'Tidak ada posisi.'}"
        )

    def _cmd_close(self):
        self.send("⏳ Menutup semua posisi...")
        n = self.mt5.close_all_positions(SYMBOL)
        self.send(f"✅ <b>{n} posisi ditutup.</b>")

    def _cmd_report(self):
        deals = self.mt5.get_history_deals(7)
        pd_   = [d for d in deals if d.profit != 0]
        wins  = [d for d in pd_ if d.profit > 0]
        loss  = [d for d in pd_ if d.profit < 0]
        total = sum(d.profit for d in pd_)
        wr    = len(wins) / (len(wins) + len(loss)) * 100 if pd_ else 0
        self.send(
            f"📅 <b>LAPORAN 7 HARI</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Total : {len(pd_)} trade\n"
            f"✅ Win  : {len(wins)}\n"
            f"❌ Loss : {len(loss)}\n"
            f"🎯 WR  : {wr:.1f}%\n"
            f"💵 P&L : {'+' if total>=0 else ''}{total:.2f}"
        )

    def _cmd_help(self):
        self.send(
            "📋 <b>PERINTAH BOT</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "/status — Posisi & balance\n"
            "/close  — Tutup semua posisi\n"
            "/report — Laporan 7 hari\n"
            "/pause  — Pause trading\n"
            "/resume — Resume trading\n"
            "/help   — Perintah ini"
        )

    @property
    def is_paused(self) -> bool:
        return self._paused