# Polymarket Copy Trading Bot
# Monitors new wallets and tracks trades over $1,000

import os
import json
import time
import requests
from datetime import datetime, timedelta
from web3 import Web3
from typing import List, Dict, Set
import logging
from dataclasses import dataclass
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Trade:
    wallet: str
    market_id: str
    outcome: str
    amount: float
    timestamp: int
    tx_hash: str
    title: str

class PolymarketCopyBot:
    def __init__(self):
        # Polymarket API endpoints
        self.data_api = "https://data-api.polymarket.com"
        self.gamma_api = "https://gamma-api.polymarket.com"
        
        # Polygon RPC (for on-chain data)
        self.rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # State tracking
        self.tracked_wallets: Set[str] = set()
        self.wallet_first_seen: Dict[str, int] = {}
        self.processed_trades: Set[str] = set()
        
        # Configuration
        self.min_trade_amount = 1000  # $1,000 minimum
        self.lookback_hours = 24
        
    def get_wallet_activity(self, wallet: str) -> List[Dict]:
        """Fetch all activity for a wallet"""
        try:
            url = f"{self.data_api}/activity"
            params = {
                "user": wallet,
                "type": "TRADE"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching wallet activity for {wallet}: {e}")
            return []
    
    def is_new_wallet(self, wallet: str, current_time: int) -> bool:
        """Check if wallet is new (first trade within lookback period)"""
        if wallet in self.wallet_first_seen:
            first_seen = self.wallet_first_seen[wallet]
        else:
            # Fetch wallet's activity
            activity = self.get_wallet_activity(wallet)
            
            if not activity:
                return False
            
            # Get earliest timestamp
            timestamps = [act.get("timestamp", 0) for act in activity]
            first_seen = min(timestamps) if timestamps else 0
            self.wallet_first_seen[wallet] = first_seen
        
        if first_seen == 0:
            return False
        
        cutoff_time = current_time - (self.lookback_hours * 3600)
        return first_seen >= cutoff_time
    
    def scan_for_new_wallets(self) -> List[str]:
        """
        Scan blockchain for new wallet activity
        This is a simplified version - in production you'd want to:
        1. Monitor the CTF Exchange contract for OrderFilled events
        2. Use a service like Alchemy or Infura with webhooks
        3. Or use Polymarket's WebSocket API
        """
        logger.info("Scanning for new wallets...")
        
        # For this demo, we'll fetch recent trades from known markets
        # In production, you'd monitor the blockchain or use WebSocket feeds
        try:
            url = f"{self.gamma_api}/events"
            params = {"limit": 20, "active": "true"}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            events = response.json()
            new_wallets = []
            
            # For each market, check recent holders
            for event in events:
                markets = event.get("markets", [])
                for market in markets:
                    condition_id = market.get("conditionId")
                    if condition_id:
                        # Get holders/traders for this market
                        holders = self.get_market_holders(condition_id)
                        new_wallets.extend(holders)
            
            return list(set(new_wallets))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error scanning for wallets: {e}")
            return []
    
    def get_market_holders(self, condition_id: str) -> List[str]:
        """Get wallets that hold positions in a market"""
        try:
            url = f"{self.data_api}/holders"
            params = {"conditionId": condition_id, "limit": 50}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            holders_data = response.json()
            return [h.get("user", "").lower() for h in holders_data]
            
        except Exception as e:
            logger.debug(f"Could not fetch holders for {condition_id}: {e}")
            return []
    
    def check_wallet_trades(self, wallet: str, current_time: int) -> List[Trade]:
        """Check if a wallet has made large trades recently"""
        try:
            # Get recent activity
            activity = self.get_wallet_activity(wallet)
            
            significant_trades = []
            cutoff_time = current_time - (self.lookback_hours * 3600)
            
            for trade_data in activity:
                trade_type = trade_data.get("type")
                if trade_type != "TRADE":
                    continue
                
                timestamp = trade_data.get("timestamp", 0)
                if timestamp < cutoff_time:
                    continue
                
                # Calculate trade amount
                usdc_size = float(trade_data.get("usdcSize", 0))
                
                # Filter by minimum amount
                if usdc_size < self.min_trade_amount:
                    continue
                
                # Create unique trade ID
                tx_hash = trade_data.get("transactionHash", "")
                trade_id = f"{wallet}_{tx_hash}_{timestamp}"
                
                # Skip if already processed
                if trade_id in self.processed_trades:
                    continue
                
                self.processed_trades.add(trade_id)
                
                trade = Trade(
                    wallet=wallet,
                    market_id=trade_data.get("conditionId", ""),
                    outcome=trade_data.get("outcome", ""),
                    amount=usdc_size,
                    timestamp=timestamp,
                    tx_hash=tx_hash,
                    title=trade_data.get("title", "Unknown Market")
                )
                
                significant_trades.append(trade)
                
            return significant_trades
            
        except Exception as e:
            logger.error(f"Error checking trades for {wallet}: {e}")
            return []
    
    def execute_copy_trade(self, trade: Trade):
        """Execute a copy trade (placeholder - implement with your strategy)"""
        logger.info(f"""
        ═══════════════════════════════════════════════════════
        🚨 COPY TRADE SIGNAL 🚨
        ═══════════════════════════════════════════════════════
        Wallet: {trade.wallet}
        Market: {trade.title}
        Outcome: {trade.outcome}
        Amount: ${trade.amount:,.2f}
        Time: {datetime.fromtimestamp(trade.timestamp).strftime('%Y-%m-%d %H:%M:%S')}
        Tx: {trade.tx_hash[:20]}...
        ═══════════════════════════════════════════════════════
        """)
        
        # TODO: Implement actual trading logic here
        # This would involve:
        # 1. Connecting your wallet
        # 2. Checking available balance
        # 3. Placing order via Polymarket CLOB API
        # 4. Managing risk and position sizing
    
    def run(self, interval: int = 60):
        """Main bot loop"""
        logger.info("🤖 Starting Polymarket Copy Trading Bot...")
        logger.info(f"💰 Monitoring for trades > ${self.min_trade_amount:,}")
        logger.info(f"⏰ Tracking wallets created in last {self.lookback_hours} hours")
        logger.info("=" * 60)
        
        while True:
            try:
                current_time = int(time.time())
                
                # Scan for new wallets
                potential_wallets = self.scan_for_new_wallets()
                logger.info(f"Found {len(potential_wallets)} potential wallets to check")
                
                new_wallet_count = 0
                total_trades_found = 0
                
                # Check each wallet
                for wallet in potential_wallets:
                    if not wallet:
                        continue
                    
                    # Check if wallet is new
                    if not self.is_new_wallet(wallet, current_time):
                        continue
                    
                    new_wallet_count += 1
                    self.tracked_wallets.add(wallet)
                    
                    # Check for large trades
                    trades = self.check_wallet_trades(wallet, current_time)
                    
                    if trades:
                        logger.info(f"✅ NEW WALLET: {wallet[:10]}... made {len(trades)} large trade(s)")
                        
                        for trade in trades:
                            self.execute_copy_trade(trade)
                            total_trades_found += 1
                
                # Summary
                logger.info(f"""
📊 Scan Summary:
   - New wallets found: {new_wallet_count}
   - Total wallets tracked: {len(self.tracked_wallets)}
   - Significant trades: {total_trades_found}
   - Next scan in {interval} seconds
{"-" * 60}
                """)
                
                # Wait before next iteration
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                time.sleep(interval)

def main():
    """Entry point"""
    bot = PolymarketCopyBot()
    bot.run(interval=60)  # Check every 60 seconds

if __name__ == "__main__":
    main()
