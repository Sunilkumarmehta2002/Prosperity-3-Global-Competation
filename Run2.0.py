from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import numpy as np
import math
from statistics import NormalDist

class Trader:
    def __init__(self):
        # Initialize state tracking for all products with updated position limits
        self.position_limits = {
            "PEARLS": 20,
            "BANANAS": 20,
            "CROISSANT": 250,
            "JAM": 350,
            "DJEMBE": 60,
            "PICNIC_BASKET1": 60,
            "PICNIC_BASKET2": 100
        }
        self.fair_values = {}  # Track fair values for each product
        self.historical_data = {}  # Store historical market data
        self.volatility = {}  # Track product volatility
        self.spread_thresholds = {}  # Dynamic spread thresholds
        self.basket_components = {
            "PICNIC_BASKET1": {"CROISSANT": 6, "JAM": 3, "DJEMBE": 1},
            "PICNIC_BASKET2": {"CROISSANT": 4, "JAM": 2}
        }
        
    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {}
        conversions = 0
        trader_data = ""
        
        # Update historical data
        self.update_historical_data(state)
        
        # First, calculate fair values for all individual products
        for product in state.order_depths:
            if product not in self.historical_data:
                self.initialize_product_state(product)
            
            if product == "PEARLS":
                self.fair_values[product] = self.calculate_pearls_fair_value(state, product)
            elif product == "BANANAS":
                self.fair_values[product] = self.calculate_bananas_fair_value(state, product)
            else:
                self.fair_values[product] = self.calculate_vwap(state.order_depths[product])
        
        # Then calculate basket fair values based on components
        self.calculate_basket_fair_values(state)
        
        # Generate orders for all products
        for product in state.order_depths:
            position_limit = self.position_limits.get(product, 20)
            current_position = state.position.get(product, 0)
            
            orders = self.generate_orders(
                product,
                state.order_depths[product],
                self.fair_values[product],
                current_position,
                position_limit
            )
            
            if orders:
                result[product] = orders
        
        # Add basket arbitrage opportunities
        basket_arb_orders = self.generate_basket_arbitrage_orders(state)
        for product, orders in basket_arb_orders.items():
            if product in result:
                result[product].extend(orders)
            else:
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
        return 10000  # PEARLS have a known fair value of 10000
    
    def calculate_bananas_fair_value(self, state: TradingState, product: str) -> float:
        """Specialized fair value calculation for BANANAS"""
        prices = self.historical_data[product]['prices']
        if not prices:
            return self.calculate_vwap(state.order_depths[product])
        
        # Use EMA with faster reaction to recent prices
        if len(prices) < 5:
            weights = np.ones(len(prices))
        else:
            # More aggressive weighting on recent prices
            weights = np.exp(np.linspace(0, 2, len(prices)))
        weights /= weights.sum()
        return np.dot(prices, weights)
    
    def calculate_basket_fair_values(self, state: TradingState):
        """Calculate fair values for baskets based on their components"""
        # PICNIC_BASKET1 = 6*CROISSANT + 3*JAM + 1*DJEMBE
        if "CROISSANT" in self.fair_values and "JAM" in self.fair_values and "DJEMBE" in self.fair_values:
            self.fair_values["PICNIC_BASKET1"] = (
                6 * self.fair_values["CROISSANT"] + 
                3 * self.fair_values["JAM"] + 
                self.fair_values["DJEMBE"]
            )
        
        # PICNIC_BASKET2 = 4*CROISSANT + 2*JAM
        if "CROISSANT" in self.fair_values and "JAM" in self.fair_values:
            self.fair_values["PICNIC_BASKET2"] = (
                4 * self.fair_values["CROISSANT"] + 
                2 * self.fair_values["JAM"]
            )
    
    def generate_basket_arbitrage_orders(self, state: TradingState) -> Dict[str, List[Order]]:
        """Generate arbitrage orders between baskets and their components"""
        orders = {}
        
        # Check if we have all necessary fair values
        if "PICNIC_BASKET1" in self.fair_values and all(c in self.fair_values for c in ["CROISSANT", "JAM", "DJEMBE"]):
            basket1_value = self.fair_values["PICNIC_BASKET1"]
            components_value = (
                6 * self.fair_values["CROISSANT"] + 
                3 * self.fair_values["JAM"] + 
                self.fair_values["DJEMBE"]
            )
            
            # Check for arbitrage opportunities (0.5% threshold)
            if basket1_value > components_value * 1.005:
                # Basket is overpriced - sell basket and buy components
                pass  # Implement this strategy carefully considering execution risk
            
            elif basket1_value < components_value * 0.995:
                # Basket is underpriced - buy basket and sell components
                pass  # Implement this strategy carefully considering execution risk
        
        # Similar logic for PICNIC_BASKET2
        if "PICNIC_BASKET2" in self.fair_values and all(c in self.fair_values for c in ["CROISSANT", "JAM"]):
            basket2_value = self.fair_values["PICNIC_BASKET2"]
            components_value = (
                4 * self.fair_values["CROISSANT"] + 
                2 * self.fair_values["JAM"]
            )
            
            if basket2_value > components_value * 1.005:
                # Sell basket and buy components
                pass
            
            elif basket2_value < components_value * 0.995:
                # Buy basket and sell components
                pass
        
        return orders
    
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
        
        # More aggressive market making for liquid products
        if len(self.historical_data[product]['prices']) > 5:
            spread = best_ask - best_bid
            avg_spread = np.mean(self.historical_data[product]['spreads'][-5:])
            
            # More aggressive price adjustment based on volatility
            price_adjustment = self.volatility[product] * 0.7  # Increased from 0.5
            
            # Calculate bid/ask prices with tighter spreads for liquid products
            if self.historical_data[product]['volumes'][-1] > 100:  # High volume
                my_bid = round(fair_value - price_adjustment * 0.8)
                my_ask = round(fair_value + price_adjustment * 0.8)
            else:
                my_bid = round(fair_value - price_adjustment)
                my_ask = round(fair_value + price_adjustment)
            
            # Ensure we're competitive but not too aggressive
            my_bid = min(my_bid, best_bid + 1)
            my_ask = max(my_ask, best_ask - 1)
            
            # Dynamic position sizing based on volatility
            base_size = min(10, max(2, int(10 / (1 + self.volatility[product] * 10))))
            buy_size = min(base_size, max_buy)
            sell_size = min(base_size, max_sell)
            
            # Position-based adjustments
            position_ratio = current_position / position_limit
            if position_ratio > 0.6:  # Reduce buy size if too long
                buy_size = max(1, buy_size // 2)
            elif position_ratio < -0.6:  # Reduce sell size if too short
                sell_size = max(1, sell_size // 2)
            
            # Place orders
            if max_buy > 0 and my_bid > 0:
                orders.append(Order(product, my_bid, buy_size))
            if max_sell > 0 and my_ask > 0:
                orders.append(Order(product, my_ask, -sell_size))
        
        # More aggressive arbitrage - tighter thresholds (0.3% instead of 0.5%)
        if best_ask < fair_value * 0.997 and max_buy > 0:
            buy_quantity = min(-order_depth.sell_orders[best_ask], max_buy)
            orders.append(Order(product, best_ask, buy_quantity))
        
        if best_bid > fair_value * 1.003 and max_sell > 0:
            sell_quantity = min(order_depth.buy_orders[best_bid], max_sell)
            orders.append(Order(product, best_bid, -sell_quantity))
        
        return orders