from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import math

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

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        orders: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data = ""

        # --- Time-based exponential decay ---
        time_to_expiry = max(0.1, 7 - state.timestamp / 100_000)
        decay_factor = math.exp(-1.5 * (1 - time_to_expiry / 7))  # Tighter decay

        # --- Compute rock fair price ---
        rock_depth = state.order_depths.get("VOLCANIC_ROCK")
        if not rock_depth:
            return {}, conversions, trader_data

        buy_prices = sorted(rock_depth.buy_orders.keys(), reverse=True)
        sell_prices = sorted(rock_depth.sell_orders.keys())

        if not buy_prices or not sell_prices:
            return {}, conversions, trader_data

        best_bid, best_ask = buy_prices[0], sell_prices[0]
        rock_mid_price = (best_bid + best_ask) / 2

        # --- Process vouchers ---
        vouchers = {
            "VOLCANIC_ROCK_VOUCHER_9500": 9500,
            "VOLCANIC_ROCK_VOUCHER_9750": 9750,
            "VOLCANIC_ROCK_VOUCHER_10000": 10000,
            "VOLCANIC_ROCK_VOUCHER_10250": 10250,
            "VOLCANIC_ROCK_VOUCHER_10500": 10500,
        }

        for voucher, strike in vouchers.items():
            depth = state.order_depths.get(voucher)
            if not depth:
                continue

            pos = state.position.get(voucher, 0)
            limit = self.position_limits[voucher]
            product_orders = []

            # Fair value estimation with buffer for spread protection
            intrinsic_value = max(0, rock_mid_price - strike)
            fair_price = intrinsic_value * decay_factor
            safety_margin = 1.5  # Minimum profit margin in absolute terms

            # Buy side logic
            for ask_price in sorted(depth.sell_orders.keys()):
                if ask_price >= fair_price - safety_margin or pos >= limit:
                    break
                ask_volume = -depth.sell_orders[ask_price]
                volume = min(limit - pos, ask_volume)
                if volume > 0:
                    product_orders.append(Order(voucher, ask_price, volume))
                    pos += volume  # Update simulated position

            # Sell side logic
            for bid_price in sorted(depth.buy_orders.keys(), reverse=True):
                if bid_price <= fair_price + safety_margin or pos <= -limit:
                    break
                bid_volume = depth.buy_orders[bid_price]
                volume = min(limit + pos, bid_volume)
                if volume > 0:
                    product_orders.append(Order(voucher, bid_price, -volume))
                    pos -= volume  # Update simulated position

            if product_orders:
                orders[voucher] = product_orders

        return orders, conversions, trader_data
