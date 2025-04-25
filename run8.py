from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import math

class Trader:
    def __init__(self):
        self.position_limits = {
            "PEARLS": 20,
            "BANANAS": 20,
            "VOLCANIC_ROCK": 400
        }

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}
        conversions = 0
        trader_data = ""

        for product, order_depth in state.order_depths.items():
            position = state.position.get(product, 0)
            limit = self.position_limits.get(product, 20)

            if not order_depth.buy_orders or not order_depth.sell_orders:
                continue

            best_bid = max(order_depth.buy_orders)
            best_ask = min(order_depth.sell_orders)
            mid_price = (best_bid + best_ask) / 2

            orders = []
            fair_buy = int(mid_price - 1)
            fair_sell = int(mid_price + 1)

            buy_qty = min(5, limit - position)
            sell_qty = min(5, limit + position)

            if buy_qty > 0:
                orders.append(Order(product, fair_buy, buy_qty))
            if sell_qty > 0:
                orders.append(Order(product, fair_sell, -sell_qty))

            result[product] = orders

        return result, conversions, trader_data
