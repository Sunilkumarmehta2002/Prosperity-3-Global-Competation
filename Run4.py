from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import math

class Trader:
    def __init__(self):
        self.position_limits = {
            "PEARLS": 20,
            "BANANAS": 20,
            "CROISSANT": 250,
            "JAM": 350,
            "DJEMBE": 60,
            "PICNIC_BASKET1": 60,
            "PICNIC_BASKET2": 100,
            "VOLCANIC_ROCK": 400,
            "VOLCANIC_ROCK_VOUCHER_9500": 200,
            "VOLCANIC_ROCK_VOUCHER_9750": 200,
            "VOLCANIC_ROCK_VOUCHER_10000": 200,
            "VOLCANIC_ROCK_VOUCHER_10250": 200,
            "VOLCANIC_ROCK_VOUCHER_10500": 200,
        }
        self.fair_values = {}

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        orders: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data = ""

        time_left = max(0.1, 7 - state.timestamp / 100_000)
        vouchers = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }

        rock_depth = state.order_depths.get("VOLCANIC_ROCK")
        if not rock_depth:
            return {}, conversions, trader_data

        rock_bid = max(rock_depth.buy_orders.keys(), default=None)
        rock_ask = min(rock_depth.sell_orders.keys(), default=None)

        if rock_bid is None or rock_ask is None:
            return {}, conversions, trader_data

        rock_mid = (rock_bid + rock_ask) / 2
        self.fair_values["VOLCANIC_ROCK"] = rock_mid

        decay = max(0.2, time_left / 7)

        for product, strike_price in vouchers.items():
            depth = state.order_depths.get(product)
            if not depth:
                continue

            bid = max(depth.buy_orders.keys(), default=None)
            ask = min(depth.sell_orders.keys(), default=None)

            if bid is None and ask is None:
                continue

            fair_value = max(0, rock_mid - strike_price) * decay
            pos = state.position.get(product, 0)
            limit = self.position_limits[product]
            product_orders = []

            # Buy opportunity
            if ask is not None and ask < fair_value and pos < limit:
                volume = min(limit - pos, -depth.sell_orders[ask])
                if volume > 0:
                    product_orders.append(Order(product, ask, volume))

            # Sell opportunity
            if bid is not None and bid > fair_value and pos > -limit:
                volume = min(limit + pos, depth.buy_orders[bid])
                if volume > 0:
                    product_orders.append(Order(product, bid, -volume))

            if product_orders:
                orders[product] = product_orders

        return orders, conversions, trader_data
