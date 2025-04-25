from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import numpy as np
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
            "VOLCANIC_ROCK_VOUCHER_10500": 200
        }
        self.historical_data = {}
        self.fair_values = {}
        self.volatility = {}

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {}
        conversions = 0
        trader_data = ""

        time_left = 7 - int(state.timestamp / 100000)  # Approx rounds to expiry (1 round = 1 day)
        rock_price = None

        # Track VOLCANIC_ROCK mid price
        if "VOLCANIC_ROCK" in state.order_depths:
            best_bid = max(state.order_depths["VOLCANIC_ROCK"].buy_orders.keys(), default=0)
            best_ask = min(state.order_depths["VOLCANIC_ROCK"].sell_orders.keys(), default=0)
            if best_bid and best_ask:
                rock_price = (best_bid + best_ask) / 2
                self.fair_values["VOLCANIC_ROCK"] = rock_price

        # For each voucher
        vouchers = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }

        for product, strike in vouchers.items():
            if product not in state.order_depths or rock_price is None:
                continue

            order_depth = state.order_depths[product]
            best_bid = max(order_depth.buy_orders.keys(), default=0)
            best_ask = min(order_depth.sell_orders.keys(), default=0)
            mid = (best_bid + best_ask) / 2 if best_bid and best_ask else None
            current_position = state.position.get(product, 0)
            limit = self.position_limits[product]

            expected_value = max(0, rock_price - strike)
            time_decay_factor = max(0.2, time_left / 7)
            fair_value = expected_value * time_decay_factor

            orders = []
            if best_ask and best_ask < fair_value and current_position < limit:
                buy_vol = min(limit - current_position, -order_depth.sell_orders[best_ask])
                orders.append(Order(product, best_ask, buy_vol))

            if best_bid and best_bid > fair_value and current_position > -limit:
                sell_vol = min(limit + current_position, order_depth.buy_orders[best_bid])
                orders.append(Order(product, best_bid, -sell_vol))

            if orders:
                result[product] = orders

        return result, conversions, trader_data
