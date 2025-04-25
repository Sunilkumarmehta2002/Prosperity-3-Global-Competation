from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import numpy as np
import math
from statistics import NormalDist

class Trader:
    def __init__(self):
        # Initialize state tracking for all products
        self.position_limits = {
            "PEARLS": 20,
            "BANANAS": 20,
            # Add other products as they become available
        }
        self.fair_values = {}  # Track fair values for each product
        self.historical_data = {}  # Store historical market data
        self.volatility = {}  # Track product volatility
        self.spread_thresholds = {}  # Dynamic spread thresholds
        
    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {}
        conversions = 0
        trader_data = ""
        
        # Update historical data
        self.update_historical_data(state)
        
        for product in state.order_depths:
            if product not in self.historical_data:
                self.initialize_product_state(product)
            
            # Calculate fair value using appropriate strategy
            if product == "PEARLS":
                self.fair_values[product] = self.calculate_pearls_fair_value(state, product)
            elif product == "BANANAS":
                self.fair_values[product] = self.calculate_bananas_fair_value(state, product)
            else:
                # Default fair value calculation
                self.fair_values[product] = self.calculate_vwap(state.order_depths[product])
            
            # Determine position limits
            position_limit = self.position_limits.get(product, 20)
            current_position = state.position.get(product, 0)
            
            # Generate orders based on strategy
            orders = self.generate_orders(
                product,
                state.order_depths[product],
                self.fair_values[product],
                current_position,
                position_limit
            )
            
            if orders:
                result[product] = orders
        
        return result, conversions, trader_data
    
    def initialize_product_state(self, product: str):
        """Initialize tracking for a new product"""
        self.historical_data[product] = {
            'prices': [],
            'spreads': [],
            'volumes': []
        }
        self.volatility[product] = 0.1  # Default volatility
        self.spread_thresholds[product] = 2  # Default spread threshold
    
    def update_historical_data(self, state: TradingState):
        """Update historical market data for all products"""
        for product, order_depth in state.order_depths.items():
            if product not in self.historical_data:
                self.initialize_product_state(product)
            
            # Record best bid/ask and mid price
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else 0
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else 0
            if best_bid and best_ask:
                mid_price = (best_bid + best_ask) / 2
                self.historical_data[product]['prices'].append(mid_price)
                self.historical_data[product]['spreads'].append(best_ask - best_bid)
                
                # Update volatility
                if len(self.historical_data[product]['prices']) > 1:
                    returns = np.diff(np.log(self.historical_data[product]['prices']))
                    self.volatility[product] = np.std(returns) * np.sqrt(252)  # Annualized
            
            # Record volume
            total_volume = sum(abs(amt) for amt in order_depth.buy_orders.values()) + \
                          sum(abs(amt) for amt in order_depth.sell_orders.values())
            self.historical_data[product]['volumes'].append(total_volume)
    
    def calculate_vwap(self, order_depth: OrderDepth) -> float:
        """Calculate Volume Weighted Average Price"""
        total_value = 0
        total_volume = 0
        
        for price, volume in order_depth.buy_orders.items():
            total_value += price * volume
            total_volume += volume
            
        for price, volume in order_depth.sell_orders.items():
            total_value += price * abs(volume)
            total_volume += abs(volume)
            
        return total_value / total_volume if total_volume else 0
    
    def calculate_pearls_fair_value(self, state: TradingState, product: str) -> float:
        """Specialized fair value calculation for PEARLS"""
        # PEARLS have a known fair value of 10000
        return 10000
    
    def calculate_bananas_fair_value(self, state: TradingState, product: str) -> float:
        """Specialized fair value calculation for BANANAS"""
        # Use exponential moving average of mid prices
        prices = self.historical_data[product]['prices']
        if not prices:
            return self.calculate_vwap(state.order_depths[product])
        
        # Weight more recent prices higher
        weights = np.exp(np.linspace(0, 1, len(prices)))
        weights /= weights.sum()
        return np.dot(prices, weights)
    
    def generate_orders(
        self,
        product: str,
        order_depth: OrderDepth,
        fair_value: float,
        current_position: int,
        position_limit: int
    ) -> List[Order]:
        """Generate orders based on market conditions and fair value"""
        orders = []
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else 0
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else 0
        
        if not best_bid or not best_ask:
            return orders  # No orders if market is one-sided
        
        # Calculate available quantities
        max_buy = position_limit - current_position
        max_sell = position_limit + current_position
        
        # Market making strategy
        if len(self.historical_data[product]['prices']) > 5:  # Enough data for stats
            spread = best_ask - best_bid
            avg_spread = np.mean(self.historical_data[product]['spreads'][-5:])
            
            # Adjust quotes based on volatility
            price_adjustment = self.volatility[product] * 0.5
            
            # Calculate bid/ask prices
            my_bid = round(fair_value - price_adjustment)
            my_ask = round(fair_value + price_adjustment)
            
            # Ensure we're competitive
            my_bid = min(my_bid, best_bid + 1)
            my_ask = max(my_ask, best_ask - 1)
            
            # Determine order sizes (scaled by position)
            position_ratio = current_position / position_limit
            buy_size = min(5, max_buy)  # Base size
            sell_size = min(5, max_sell)  # Base size
            
            # Adjust sizes based on position
            if position_ratio > 0.5:  # Long position, reduce buy size
                buy_size = max(1, buy_size // 2)
            elif position_ratio < -0.5:  # Short position, reduce sell size
                sell_size = max(1, sell_size // 2)
            
            # Place orders
            if max_buy > 0:
                orders.append(Order(product, my_bid, buy_size))
            if max_sell > 0:
                orders.append(Order(product, my_ask, -sell_size))
        
        # Arbitrage strategy - take advantage of mispricing
        if best_ask < fair_value * 0.999 and max_buy > 0:
            # Buy undervalued
            buy_quantity = min(-order_depth.sell_orders[best_ask], max_buy)
            orders.append(Order(product, best_ask, buy_quantity))
        
        if best_bid > fair_value * 1.001 and max_sell > 0:
            # Sell overvalued
            sell_quantity = min(order_depth.buy_orders[best_bid], max_sell)
            orders.append(Order(product, best_bid, -sell_quantity))
        
        return orders