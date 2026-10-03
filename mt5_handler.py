"""
MT5 Handler — Auto-Detect Active Session & Execution
"""
from __future__ import annotations
import time
from datetime import datetime
from typing import Optional
import MetaTrader5 as mt5
import pandas as pd
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, LOT_SIZE, MAX_RISK_PERCENT
from logger import get_logger

log = get_logger("mt5")


class MT5Handler:
    def __init__(self):
        self._connected = False

    def connect(self) -> bool:
        if not mt5.initialize():
            log.error(f"MT5 initialize gagal: {mt5.last_error()}")
            return False

        # 1. Cek apakah MT5 yang lagi kebuka di laptop udah otomatis login
        info = mt5.account_info()
        if info is not None:
            self._connected = True
            log.info(f"✅ MT5 Connected (Auto-Detect Akun Aktif) | #{info.login} | Balance: {info.balance:.2f} {info.currency}")
            return True

        # 2. Kalau belum login, coba login pake data di .env
        try:
            login_num = int(MT5_LOGIN)
            if login_num > 0 and MT5_PASSWORD and MT5_SERVER:
                if not mt5.login(login_num, password=MT5_PASSWORD, server=MT5_SERVER):
                    log.error(f"MT5 login gagal: {mt5.last_error()}")
                    mt5.shutdown()
                    return False
        except Exception as e:
            log.warning(f"Login manual dilewati: {e}")

        info = mt5.account_info()
        if info is None:
            log.error("MT5 belum terhubung ke akun broker mana pun!")
            mt5.shutdown()
            return False

        self._connected = True
        log.info(f"✅ MT5 Connected | #{info.login} | Balance: {info.balance:.2f} {info.currency}")
        return True

    def disconnect(self):
        mt5.shutdown()
        self._connected = False

    def ensure_connected(self) -> bool:
        if not self._connected or not mt5.terminal_info():
            self._connected = False
            return self.connect()
        return True

    def get_rates(self, symbol: str, timeframe: int, n: int = 300) -> Optional[pd.DataFrame]:
        if not self.ensure_connected():
            return None
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def get_tick(self, symbol: str):
        self.ensure_connected()
        return mt5.symbol_info_tick(symbol)

    def get_point(self, symbol: str) -> float:
        self.ensure_connected()
        info = mt5.symbol_info(symbol)
        if info is None:
            mt5.symbol_select(symbol, True)
            time.sleep(0.3)
            info = mt5.symbol_info(symbol)
        return info.point if info else 0.01

    def get_balance(self) -> float:
        self.ensure_connected()
        info = mt5.account_info()
        return info.balance if info else 0.0

    def get_equity(self) -> float:
        self.ensure_connected()
        info = mt5.account_info()
        return info.equity if info else 0.0

    def count_open_trades(self, symbol: str) -> int:
        self.ensure_connected()
        pos = mt5.positions_get(symbol=symbol)
        return len(pos) if pos else 0

    def get_open_positions(self, symbol: str) -> list:
        self.ensure_connected()
        pos = mt5.positions_get(symbol=symbol)
        return list(pos) if pos else []

    def get_daily_pnl(self, symbol: str) -> float:
        self.ensure_connected()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(today, datetime.now(), group=f"*{symbol}*")
        return sum(d.profit for d in deals) if deals else 0.0

    def get_history_deals(self, days: int = 7) -> list:
        from datetime import timedelta
        self.ensure_connected()
        date_from = datetime.now() - timedelta(days=days)
        deals = mt5.history_deals_get(date_from, datetime.now())
        return list(deals) if deals else []

    def calculate_lot(self, symbol: str, sl_distance_points: float) -> float:
        balance = self.get_balance()
        if balance <= 0 or sl_distance_points <= 0:
            return LOT_SIZE
        info = mt5.symbol_info(symbol)
        if info is None:
            return LOT_SIZE
        risk   = balance * (MAX_RISK_PERCENT / 100)
        pip_v  = info.trade_tick_value * (info.trade_tick_size / info.point)
        lot    = round(risk / (sl_distance_points * pip_v), 2)
        return max(info.volume_min, min(info.volume_max, lot))

    def _send_order(self, request: dict) -> Optional[object]:
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return result
        log.error(f"Order gagal retcode={getattr(result, 'retcode', '?')} | {mt5.last_error()}")
        return None

    def place_market_order(self, symbol, direction, lot, sl, tp, comment="SH_POI"):
        if not self.ensure_connected():
            return None
        tick = self.get_tick(symbol)
        if not tick:
            return None
        ot    = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if direction == "BUY" else tick.bid
        r = self._send_order({
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       symbol,
            "volume":       lot,
            "type":         ot,
            "price":        price,
            "sl":           sl,
            "tp":           tp,
            "deviation":    20,
            "magic":        20260925,
            "comment":      comment,
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        })
        if r:
            log.info(f"✅ MARKET {direction} {symbol} lot={lot} @ {price:.2f} sl={sl:.2f} tp={tp:.2f} #{r.order}")
        return r

    def modify_sl(self, position, new_sl: float) -> bool:
        if not self.ensure_connected():
            return False
        result = mt5.order_send({
            "action":   mt5.TRADE_ACTION_SLTP,
            "position": position.ticket,
            "symbol":   position.symbol,
            "sl":       new_sl,
            "tp":       position.tp,
        })
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            log.info(f"✅ SL modified → {new_sl:.2f} | #{position.ticket}")
            return True
        log.error(f"Gagal modify SL: {mt5.last_error()}")
        return False

    def close_position(self, position) -> bool:
        tick = self.get_tick(position.symbol)
        if not tick:
            return False
        is_buy = (position.type == mt5.POSITION_TYPE_BUY)
        r = self._send_order({
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       position.symbol,
            "volume":       position.volume,
            "type":         mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
            "position":     position.ticket,
            "price":        tick.bid if is_buy else tick.ask,
            "deviation":    20,
            "magic":        20260925,
            "comment":      "SH_Close",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        })
        if r:
            log.info(f"Position #{position.ticket} closed")
            return True
        return False

    def close_all_positions(self, symbol: str) -> int:
        return sum(1 for p in self.get_open_positions(symbol) if self.close_position(p))