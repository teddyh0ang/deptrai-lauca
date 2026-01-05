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

class PolymarketCopyBot:
    def __init__(self):
        # Polymarket API endpoints
        self.api_base = "https://clob.polymarket.com"
        self.gamma_api = "https://gamma-api.polymarket.com"
        
        # Polygon RPC (for on-chain data)
        self.rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Polymarket contract addresses
        self.ctf_exchange = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
        self.neg_risk_adapter = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
        
        # State tracking
        self.tracked_wallets: Set[str] = set()
        self.wallet_creation_times: Dict[str, int] = {}
        self.recent_trades: Dict[str, List[Trade]] = defaultdict(list)
        
        # Configuration
        self.min_trade_amount = 1000  # $1,000 minimum
        self.lookback_hours = 24
        
    def get_recent_trades(self) -> List[Dict]:
        """Fetch recent trades from Polymarket API"""
        try:
            url = f"{self.gamma_api}/trades"
            params = {
                "limit": 1000,
                "_t": int(time.time())
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            trades = response.json()
            logger.info(f"Fetched {len(trades)} recent trades")
            return trades
            
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    def get_wallet_first_activity(self, wallet: str) -> int:
        """Get timestamp of wallet's first activity on Polymarket"""
        try:
            url = f"{self.gamma_api}/trades"
            params = {
                "maker": wallet,
                "limit": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            trades = response.json()
            if trades:
                return trades[0].get("timestamp", 0)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting wallet activity for {wallet}: {e}")
            return 0
    
    def is_new_wallet(self, wallet: str, current_time: int) -> bool:
        """Check if wallet was created within lookback period"""
        if wallet in self.wallet_creation_times:
            creation_time = self.wallet_creation_times[wallet]
        else:
            creation_time = self.get_wallet_first_activity(wallet)
            self.wallet_creation_times[wallet] = creation_time
        
        if creation_time == 0:
            return False
        
        cutoff_time = current_time - (self.lookback_hours * 3600)
        return creation_time >= cutoff_time
    
    def analyze_trades(self, trades: List[Dict]) -> List[Trade]:
        """Analyze trades and filter for large trades from new wallets"""
        current_time = int(time.time())
        significant_trades = []
        
        for trade_data in trades:
            try:
                wallet = trade_data.get("maker_address", "").lower()
                if not wallet:
                    continue
                
                # Check if new wallet
                if not self.is_new_wallet(wallet, current_time):
                    continue
                
                # Calculate trade amount in USD
                price = float(trade_data.get("price", 0))
                size = float(trade_data.get("size", 0))
                amount = price * size
                
                # Filter by minimum amount
                if amount < self.min_trade_amount:
                    continue
                
                trade = Trade(
                    wallet=wallet,
                    market_id=trade_data.get("market", ""),
                    outcome=trade_data.get("outcome", ""),
                    amount=amount,
                    timestamp=trade_data.get("timestamp", 0),
                    tx_hash=trade_data.get("transaction_hash", "")
                )
                
                significant_trades.append(trade)
                self.tracked_wallets.add(wallet)
                
                logger.info(
                    f"NEW WALLET TRADE: {wallet[:10]}... "
                    f"traded ${amount:.2f} on market {trade.market_id[:10]}..."
                )
                
            except Exception as e:
                logger.error(f"Error analyzing trade: {e}")
                continue
        
        return significant_trades
    
    def get_market_details(self, market_id: str) -> Dict:
        """Get market information"""
        try:
            url = f"{self.gamma_api}/markets/{market_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching market {market_id}: {e}")
            return {}
    
    def execute_copy_trade(self, trade: Trade):
        """Execute a copy trade (placeholder - implement with your strategy)"""
        market_details = self.get_market_details(trade.market_id)
        market_question = market_details.get("question", "Unknown")
        
        logger.info(f"""
        ═══════════════════════════════════════════════════════
        COPY TRADE SIGNAL
        ═══════════════════════════════════════════════════════
        Wallet: {trade.wallet}
        Market: {market_question}
        Outcome: {trade.outcome}
        Amount: ${trade.amount:.2f}
        Time: {datetime.fromtimestamp(trade.timestamp)}
        ═══════════════════════════════════════════════════════
        """)
        
        # TODO: Implement actual trading logic here
        # This would involve:
        # 1. Connecting your wallet
        # 2. Checking available balance
        # 3. Placing order via Polymarket API
        # 4. Managing risk and position sizing
    
    def run(self, interval: int = 60):
        """Main bot loop"""
        logger.info("Starting Polymarket Copy Trading Bot...")
        logger.info(f"Monitoring for trades > ${self.min_trade_amount}")
        logger.info(f"Tracking wallets created in last {self.lookback_hours} hours")
        
        while True:
            try:
                # Fetch recent trades
                trades = self.get_recent_trades()
                
                # Analyze for significant trades from new wallets
                significant_trades = self.analyze_trades(trades)
                
                # Execute copy trades
                for trade in significant_trades:
                    self.execute_copy_trade(trade)
                
                # Summary
                logger.info(
                    f"Tracking {len(self.tracked_wallets)} new wallets | "
                    f"Found {len(significant_trades)} significant trades"
                )
                
                # Wait before next iteration
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(interval)

def main():
    """Entry point"""
    bot = PolymarketCopyBot()
    bot.run(interval=60)  # Check every 60 seconds

if __name__ == "__main__":
    main()
