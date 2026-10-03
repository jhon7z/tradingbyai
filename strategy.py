"""
Shinciro POI & AOI + Order Confirmation (OC) Strategy
Realistic Gold Volatility Edition (M5 POI + M1 CHoCH)
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Literal, Optional
from scipy.signal import argrelextrema
from logger import get_logger

log = get_logger("strategy")


@dataclass
class POI:
    poi_type:   str           # RBS | SBR | QM_BULL | QM_BEAR
    direction:  Literal["BUY", "SELL"]
    price:      float
    sl_level:   float
    has_aoi:    bool = False  # Confluence dengan OB / FVG
    aoi_desc:   str  = ""


@dataclass
class Signal:
    direction:     Literal["BUY", "SELL"]
    symbol:        str
    entry_price:   float
    sl_price:      float
    tp_price:      float
    poi_type:      str
    oc_type:       str        # CHoCH | REJECTION
    confidence:    int
    timeframe:     str = "M5/M1"
    details:       str = ""


class ShinciroStrategy:
    def __init__(self, symbol: str, point: float):
        self.symbol     = symbol
        self.point      = point
        # Di Gold: 1 pip = 0.10 (point=0.01 -> 10 point = 1 pip)
        self.pip_size   = point * 10
        self.zone_pips  = 15.0 * self.pip_size   # Toleransi zona POI: 15 pips (~$1.50)
        self.sl_buffer  = 30.0 * point           # Buffer SL: 3 pips

    # ─── 1. Scan POI M5 ──────────────────────────────────────────────────────
    def find_m5_pois(self, df5: pd.DataFrame) -> list[POI]:
        if len(df5) < 50:
            return []

        df = df5.copy().reset_index(drop=True)
        pois: list[POI] = []

        high_idx = argrelextrema(df["high"].values, np.greater_equal, order=3)[0]
        low_idx  = argrelextrema(df["low"].values, np.less_equal, order=3)[0]

        cur_price = df.iloc[-1]["close"]

        # A. RBS (Resistance Become Support -> BUY)
        for i in high_idx[-12:]:
            r_level = df.iloc[i]["high"]
            subsequent = df.iloc[i + 1:]
            # Pernah ditembus ke atas
            if len(subsequent) > 2 and subsequent["high"].max() > (r_level + self.zone_pips * 0.5):
                # Harga baru-baru ini (3 bar terakhir) pernah nyentuh atau deket level ini
                recent_low = df["low"].iloc[-3:].min()
                recent_high = df["high"].iloc[-3:].max()
                if (recent_low <= r_level + self.zone_pips) and (cur_price >= r_level - self.zone_pips):
                    pois.append(POI(
                        poi_type="RBS", direction="BUY", price=r_level,
                        sl_level=round(r_level - self.zone_pips - self.sl_buffer, 2)
                    ))

        # B. SBR (Support Become Resistance -> SELL)
        for i in low_idx[-12:]:
            s_level = df.iloc[i]["low"]
            subsequent = df.iloc[i + 1:]
            # Pernah ditembus ke bawah
            if len(subsequent) > 2 and subsequent["low"].min() < (s_level - self.zone_pips * 0.5):
                recent_low = df["low"].iloc[-3:].min()
                recent_high = df["high"].iloc[-3:].max()
                if (recent_high >= s_level - self.zone_pips) and (cur_price <= s_level + self.zone_pips):
                    pois.append(POI(
                        poi_type="SBR", direction="SELL", price=s_level,
                        sl_level=round(s_level + self.zone_pips + self.sl_buffer, 2)
                    ))

        # C. Quasimodo (QM)
        if len(high_idx) >= 2 and len(low_idx) >= 2:
            h1, h2 = high_idx[-2], high_idx[-1]
            l1, l2 = low_idx[-2], low_idx[-1]
            # Bearish QM: HH lalu LL -> Left Shoulder SELL
            if df.iloc[h2]["high"] > df.iloc[h1]["high"] and df.iloc[l2]["low"] < df.iloc[l1]["low"]:
                left_shoulder = df.iloc[h1]["high"]
                if abs(cur_price - left_shoulder) <= self.zone_pips * 1.5:
                    pois.append(POI(
                        poi_type="QM_BEAR", direction="SELL", price=left_shoulder,
                        sl_level=round(df.iloc[h2]["high"] + self.sl_buffer, 2)
                    ))

            # Bullish QM: LL lalu HH -> Left Shoulder BUY
            if df.iloc[l2]["low"] < df.iloc[l1]["low"] and df.iloc[h2]["high"] > df.iloc[h1]["high"]:
                left_shoulder = df.iloc[l1]["low"]
                if abs(cur_price - left_shoulder) <= self.zone_pips * 1.5:
                    pois.append(POI(
                        poi_type="QM_BULL", direction="BUY", price=left_shoulder,
                        sl_level=round(df.iloc[l2]["low"] - self.sl_buffer, 2)
                    ))

        # D. Cek Confluence AOI (OB / FVG)
        for p in pois:
            has_aoi, desc = self._check_aoi(df, p.price, p.direction)
            p.has_aoi = has_aoi
            p.aoi_desc = desc

        return pois

    def _check_aoi(self, df: pd.DataFrame, poi_price: float, direction: str) -> tuple[bool, str]:
        for i in range(len(df) - 10, len(df) - 1):
            if i < 2: continue
            # FVG Check
            if direction == "BUY" and df.iloc[i]["low"] > df.iloc[i - 2]["high"]:
                return True, "FVG_Demand"
            elif direction == "SELL" and df.iloc[i]["high"] < df.iloc[i - 2]["low"]:
                return True, "FVG_Supply"
            # OB Check
            c = df.iloc[i]
            if direction == "BUY" and c["close"] < c["open"] and abs(c["low"] - poi_price) <= self.zone_pips:
                return True, "Bullish_OB"
            elif direction == "SELL" and c["close"] > c["open"] and abs(c["high"] - poi_price) <= self.zone_pips:
                return True, "Bearish_OB"
        return False, "Standard"

    # ─── 2. Order Confirmation (OC) di M1 ────────────────────────────────────
    def check_m1_confirmation(self, df1: pd.DataFrame, poi: POI) -> Optional[Signal]:
        if len(df1) < 10:
            return None

        last  = df1.iloc[-1]
        prev1 = df1.iloc[-2]
        cur_price = last["close"]

        # Swing lokal M1 (7 candle terakhir)
        m1_highs = df1["high"].iloc[-8:-2].values
        m1_lows  = df1["low"].iloc[-8:-2].values
        swing_h  = np.max(m1_highs) if len(m1_highs) > 0 else prev1["high"]
        swing_l  = np.min(m1_lows) if len(m1_lows) > 0 else prev1["low"]

        oc_type = None

        if poi.direction == "BUY":
            # CHoCH: Close M1 berhasil nembus swing high lokal
            if last["close"] > swing_h:
                oc_type = "CHoCH_BULL"
            # Atau Rejection: Pinbar ekor bawah panjang
            elif (min(last["open"], last["close"]) - last["low"]) >= (abs(last["close"] - last["open"]) * 1.3) and last["close"] >= last["open"]:
                oc_type = "REJECTION_BULL"

            if oc_type:
                sl = round(min(poi.sl_level, df1["low"].iloc[-5:].min() - self.sl_buffer), 2)
                risk = max(abs(cur_price - sl), 15 * self.pip_size)
                tp = round(cur_price + (risk * 2.0), 2)
                return Signal(
                    direction="BUY", symbol=self.symbol,
                    entry_price=round(cur_price, 2), sl_price=sl, tp_price=tp,
                    poi_type=poi.poi_type, oc_type=oc_type,
                    confidence=8 if poi.has_aoi else 7,
                    details=f"POI={poi.poi_type} | AOI={poi.aoi_desc} | OC={oc_type}"
                )

        else: # SELL
            # CHoCH: Close M1 berhasil jebol swing low lokal
            if last["close"] < swing_l:
                oc_type = "CHoCH_BEAR"
            # Atau Rejection: Pinbar ekor atas panjang
            elif (last["high"] - max(last["open"], last["close"])) >= (abs(last["close"] - last["open"]) * 1.3) and last["close"] <= last["open"]:
                oc_type = "REJECTION_BEAR"

            if oc_type:
                sl = round(max(poi.sl_level, df1["high"].iloc[-5:].max() + self.sl_buffer), 2)
                risk = max(abs(sl - cur_price), 15 * self.pip_size)
                tp = round(cur_price - (risk * 2.0), 2)
                return Signal(
                    direction="SELL", symbol=self.symbol,
                    entry_price=round(cur_price, 2), sl_price=sl, tp_price=tp,
                    poi_type=poi.poi_type, oc_type=oc_type,
                    confidence=8 if poi.has_aoi else 7,
                    details=f"POI={poi.poi_type} | AOI={poi.aoi_desc} | OC={oc_type}"
                )

        return None