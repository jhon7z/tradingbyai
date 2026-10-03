"""Risk management: lot sizing, SL/TP, daily loss limit."""
from config import MAX_RISK_PERCENT, RR_RATIO, MAX_DAILY_LOSS_PCT
from logger import get_logger

log = get_logger("risk")


class RiskManager:

    def __init__(self, mt5_handler):
        self.mt5 = mt5_handler

    def is_daily_loss_exceeded(self) -> bool:
        balance = self.mt5.get_balance()
        if balance <= 0:
            return True
        pnl  = self.mt5.get_daily_pnl("XAUUSD")
        loss = abs(pnl) / balance * 100 if pnl < 0 else 0
        if loss >= MAX_DAILY_LOSS_PCT:
            log.warning(f"Daily loss limit: {loss:.2f}% >= {MAX_DAILY_LOSS_PCT}%")
            return True
        return False

    def calculate_lot(self, symbol: str, sl_distance_points: float) -> float:
        return self.mt5.calculate_lot(symbol, sl_distance_points)

    def calculate_tp(self, entry: float, sl: float, direction: str) -> float:
        risk = abs(entry - sl)
        return round(entry - risk * RR_RATIO, 2) if direction == "SELL" else round(entry + risk * RR_RATIO, 2)

    def validate_signal(self, sig, balance: float) -> tuple[bool, str]:
        sl_dist = abs(sig.entry_price - sig.sl_price)
        tp_dist = abs(sig.entry_price - sig.tp_price)
        if sl_dist < 5:
            return False, f"SL terlalu tipis: {sl_dist:.2f}"
        if tp_dist < sl_dist:
            return False, "TP < SL jarak"
        if balance < 100:
            return False, f"Balance terlalu kecil: {balance:.2f}"
        return True, "OK"