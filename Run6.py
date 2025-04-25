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
            "MAGNIFICENT_MACARONS": 75,
        }

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        orders: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data = ""

        # --- Time-based exponential decay for rock vouchers ---
        time_to_expiry = max(0.1, 7 - state.timestamp / 100_000)
        decay_factor = math.exp(-1.5 * (1 - time_to_expiry / 7))

        # --- Estimate Volcanic Rock Mid Price ---
        rock_depth = state.order_depths.get("VOLCANIC_ROCK")
        rock_mid_price = None
        if rock_depth:
            buy_prices = sorted(rock_depth.buy_orders.keys(), reverse=True)
            sell_prices = sorted(rock_depth.sell_orders.keys())
            if buy_prices and sell_prices:
                rock_mid_price = (buy_prices[0] + sell_prices[0]) / 2

        # --- Process Rock Vouchers ---
        if rock_mid_price:
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

                intrinsic_value = max(0, rock_mid_price - strike)
                fair_price = intrinsic_value * decay_factor
                margin = 1.5  # profit threshold

                # Buy logic
                for ask in sorted(depth.sell_orders):
                    if pos >= limit:
                        break
                    if ask > fair_price - margin:
                        break
                    volume = min(-depth.sell_orders[ask], limit - pos)
                    if volume > 0:
                        product_orders.append(Order(voucher, ask, volume))
                        pos += volume

                # Sell logic
                for bid in sorted(depth.buy_orders, reverse=True):
                    if pos <= -limit:
                        break
                    if bid < fair_price + margin:
                        break
                    volume = min(depth.buy_orders[bid], limit + pos)
                    if volume > 0:
                        product_orders.append(Order(voucher, bid, -volume))
                        pos -= volume

                if product_orders:
                    orders[voucher] = product_orders

        # --- MACARONS Trading with Pristine Cuisine ---
        macarons = "MAGNIFICENT_MACARONS"
        mac_depth = state.order_depths.get(macarons)
        if mac_depth:
            pos = state.position.get(macarons, 0)
            limit = self.position_limits[macarons]
            max_convert = 10

            bid_prices = sorted(mac_depth.buy_orders.keys(), reverse=True)
            ask_prices = sorted(mac_depth.sell_orders.keys())

            if bid_prices and ask_prices:
                best_bid = bid_prices[0]
                best_ask = ask_prices[0]
                mid_price = (best_bid + best_ask) / 2

                # Fee constants (replace with real values if known)
                TRANSPORT_FEES = 1
                IMPORT_TARIFF = 1
                EXPORT_TARIFF = 1
                STORAGE_COST = 0.1  # cost per long unit per timestamp

                # Buy MACARONS if effective cost is profitable
                effective_buy = best_ask + TRANSPORT_FEES + IMPORT_TARIFF + STORAGE_COST
                if effective_buy < mid_price and pos < limit:
                    volume = min(max_convert, limit - pos, -mac_depth.sell_orders[best_ask])
                    if volume > 0:
                        conversions += volume

                # Sell MACARONS if effective return is profitable
                effective_sell = best_bid - TRANSPORT_FEES - EXPORT_TARIFF
                if effective_sell > mid_price and pos > -limit:
                    volume = min(max_convert, limit + pos, mac_depth.buy_orders[best_bid])
                    if volume > 0:
                        conversions -= volume  # sell is negative conversion

        return orders, conversions, trader_data
