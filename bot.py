# Polymarket Copy Trading Bot
# Monitors new wallets created in the last 24 hours

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
class WalletInfo:
    address: str
    first_trade_time: int
    total_trades: int
    total_volume: float

class PolymarketCopyBot:
    def __init__(self):
        # Polymarket API endpoints
        self.data_api = "https://data-api.polymarket.com"
        self.gamma_api = "https://gamma-api.polymarket.com"
        
        # State tracking
        self.tracked_wallets: Dict[str, WalletInfo] = {}
        self.seen_wallets: Set[str] = set()
        
        # Configuration
        self.lookback_hours = 24
        
    def get_recent_markets(self, limit: int = 50) -> List[Dict]:
        """Get recently active markets"""
        try:
            url = f"{self.gamma_api}/events"
            params = {"limit": limit, "active": "true"}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    def get_market_trades(self, condition_id: str) -> List[Dict]:
        """Get recent trades for a specific market"""
        try:
            url = f"{self.data_api}/trades"
            params = {
                "conditionId": condition_id,
                "limit": 100
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.debug(f"Could not fetch trades for {condition_id}: {e}")
            return []
    
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
            logger.debug(f"Error fetching wallet activity for {wallet}: {e}")
            return []
    
    def analyze_wallet(self, wallet: str, current_time: int) -> WalletInfo:
        """Analyze a wallet's trading history"""
        activity = self.get_wallet_activity(wallet)
        
        if not activity:
            return None
        
        # Get all trade timestamps
        trade_times = [act.get("timestamp", 0) for act in activity if act.get("type") == "TRADE"]
        
        if not trade_times:
            return None
        
        first_trade = min(trade_times)
        total_volume = sum(float(act.get("usdcSize", 0)) for act in activity)
        
        return WalletInfo(
            address=wallet,
            first_trade_time=first_trade,
            total_trades=len(trade_times),
            total_volume=total_volume
        )
    
    def is_new_wallet(self, wallet_info: WalletInfo, current_time: int) -> bool:
        """Check if wallet made its first trade within lookback period"""
        cutoff_time = current_time - (self.lookback_hours * 3600)
        return wallet_info.first_trade_time >= cutoff_time
    
    def scan_for_wallets(self) -> List[str]:
        """Scan recent market activity for unique wallets"""
        logger.info("🔍 Scanning markets for wallet activity...")
        
        markets = self.get_recent_markets(limit=50)
        all_wallets = set()
        
        for event in markets:
            markets_list = event.get("markets", [])
            
            for market in markets_list:
                condition_id = market.get("conditionId")
                if not condition_id:
                    continue
                
                # Get trades for this market
                trades = self.get_market_trades(condition_id)
                
                # Extract unique wallet addresses
                for trade in trades:
                    wallet = trade.get("user", "").lower()
                    if wallet and wallet not in self.seen_wallets:
                        all_wallets.add(wallet)
        
        logger.info(f"📊 Found {len(all_wallets)} unique wallets from recent trades")
        return list(all_wallets)
    
    def process_new_wallets(self, wallets: List[str], current_time: int):
        """Process wallets and identify new ones"""
        new_wallets_found = []
        
        for wallet in wallets:
            if wallet in self.seen_wallets:
                continue
            
            # Analyze wallet
            wallet_info = self.analyze_wallet(wallet, current_time)
            
            if not wallet_info:
                continue
            
            # Mark as seen
            self.seen_wallets.add(wallet)
            
            # Check if new wallet
            if self.is_new_wallet(wallet_info, current_time):
                self.tracked_wallets[wallet] = wallet_info
                new_wallets_found.append(wallet_info)
                
                # Log the new wallet
                first_trade_dt = datetime.fromtimestamp(wallet_info.first_trade_time)
                logger.info(f"""
╔══════════════════════════════════════════════════════════╗
║ 🆕 NEW WALLET DETECTED                                   ║
╠══════════════════════════════════════════════════════════╣
║ Address: {wallet_info.address[:42]}...║
║ First Trade: {first_trade_dt.strftime('%Y-%m-%d %H:%M:%S')}                     ║
║ Total Trades: {wallet_info.total_trades}                                        ║
║ Total Volume: ${wallet_info.total_volume:,.2f}                           ║
╚══════════════════════════════════════════════════════════╝
                """)
        
        return new_wallets_found
    
    def run(self, interval: int = 120):
        """Main bot loop"""
        logger.info("=" * 70)
        logger.info("🤖 Polymarket New Wallet Scanner")
        logger.info("=" * 70)
        logger.info(f"⏰ Tracking wallets with first trade in last {self.lookback_hours} hours")
        logger.info(f"🔄 Scanning every {interval} seconds")
        logger.info("=" * 70)
        
        scan_count = 0
        
        while True:
            try:
                scan_count += 1
                current_time = int(time.time())
                
                logger.info(f"\n🔄 Scan #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Get wallets from recent market activity
                wallets = self.scan_for_wallets()
                
                # Process and identify new wallets
                new_wallets = self.process_new_wallets(wallets, current_time)
                
                # Summary
                logger.info(f"""
📈 Scan Summary:
   ├─ Wallets scanned this round: {len(wallets)}
   ├─ New wallets found: {len(new_wallets)}
   ├─ Total new wallets tracked: {len(self.tracked_wallets)}
   └─ Next scan in {interval} seconds
{"-" * 70}
                """)
                
                # Wait before next iteration
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Bot stopped by user")
                logger.info(f"📊 Final Stats: Tracked {len(self.tracked_wallets)} new wallets")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                time.sleep(interval)

def main():
    """Entry point"""
    bot = PolymarketCopyBot()
    bot.run(interval=120)  # Check every 2 minutes

if __name__ == "__main__":
    main()
