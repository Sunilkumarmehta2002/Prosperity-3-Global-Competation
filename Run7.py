from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import numpy as np

class Trader:
    def __init__(self):
        self.position_limits = {
            "VOLCANIC_ROCK": 400,
            "VOLCANIC_ROCK_VOUCHER_9500": 200,
            "VOLCANIC_ROCK_VOUCHER_9750": 200,
            "VOLCANIC_ROCK_VOUCHER_10000": 200,
            "VOLCANIC_ROCK_VOUCHER_10250": 200,
            "VOLCANIC_ROCK_VOUCHER_10500": 200,
        }
        self.history = {}
        self.pnl = 0.0
        self.voucher_strikes = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        orders = {}
        conversions = 0

        # Countdown from 7 to 1
        days_left = max(1, 7 - int(state.timestamp / 100000))
        rock_price = self.get_mid_price(state.order_depths.get("VOLCANIC_ROCK"))
        if rock_price:
            self.log_price("VOLCANIC_ROCK", rock_price)

        for voucher, strike in self.voucher_strikes.items():
            order_depth = state.order_depths.get(voucher)
            if not order_depth or rock_price is None:
                continue

            best_bid = max(order_depth.buy_orders.keys(), default=None)
            best_ask = min(order_depth.sell_orders.keys(), default=None)
            if best_bid is None or best_ask is None:
                continue

            pos = state.position.get(voucher, 0)
            limit = self.position_limits[voucher]

            # Fair value and confidence window
            fair_value = self.calculate_fair_value(rock_price, strike, days_left)
            self.log_price(voucher, (best_ask + best_bid) / 2)
            std_dev = self.get_std_dev(voucher, fallback=3)

            z_buy = (fair_value - best_ask) / std_dev
            z_sell = (best_bid - fair_value) / std_dev

            action_list = []

            # Buy logic
            if z_buy > 1 and pos < limit:
                qty = min(limit - pos, -order_depth.sell_orders[best_ask])
                if qty > 0:
                    action_list.append(Order(voucher, best_ask, qty))
                    self.pnl -= best_ask * qty

            # Sell logic
            if z_sell > 1 and pos > -limit:
                qty = min(pos + limit, order_depth.buy_orders[best_bid])
                if qty > 0:
                    action_list.append(Order(voucher, best_bid, -qty))
                    self.pnl += best_bid * qty

            if action_list:
                orders[voucher] = action_list

        # Estimate value of open positions (floating PnL)
        float_pnl = 0.0
        for voucher, strike in self.voucher_strikes.items():
            mid = self.get_mid_price(state.order_depths.get(voucher))
            if mid:
                float_pnl += mid * state.position.get(voucher, 0)

        trader_data = f"Realized PnL: {self.pnl:.2f} | Floating: {float_pnl:.2f} | Total: {self.pnl + float_pnl:.2f}"
        return orders, conversions, trader_data

    def calculate_fair_value(self, spot: float, strike: int, tte: int) -> float:
        """Fair value = Intrinsic Value + Time Value"""
        intrinsic = max(0, spot - strike)
        time_value = (tte / 7) ** 1.5
        return intrinsic * time_value + 5  # Add fixed premium

    def get_mid_price(self, order_depth: OrderDepth) -> float:
        if not order_depth or not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        return (max(order_depth.buy_orders.keys()) + min(order_depth.sell_orders.keys())) / 2

    def log_price(self, product: str, price: float):
        if product not in self.history:
            self.history[product] = []
        self.history[product].append(price)
        if len(self.history[product]) > 300:
            self.history[product] = self.history[product][-300:]

    def get_std_dev(self, product: str, fallback: float = 2.0) -> float:
        prices = self.history.get(product, [])
        if len(prices) < 20:
            return fallback
        return np.std(prices[-20:])
