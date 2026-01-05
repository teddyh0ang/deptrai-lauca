# Polymarket New Wallet Scanner
# Finds wallets that made their first trade in the last 24 hours

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Set
import logging
from dataclasses import dataclass

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
    markets_traded: int

class PolymarketNewWalletScanner:
    def __init__(self):
        # Polymarket API endpoints
        self.data_api = "https://data-api.polymarket.com"
        self.gamma_api = "https://gamma-api.polymarket.com"
        
        # State tracking
        self.checked_wallets: Set[str] = set()
        self.new_wallets: Dict[str, WalletInfo] = {}
        
        # Configuration
        self.lookback_hours = 24
        self.markets_to_scan = 100  # Scan top 100 markets
        
    def get_active_markets(self) -> List[Dict]:
        """Get list of active markets"""
        try:
            url = f"{self.gamma_api}/events"
            params = {
                "limit": self.markets_to_scan,
                "active": "true",
                "order": "volume24hr"  # Sort by 24h volume
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    def get_market_holders(self, condition_id: str) -> List[str]:
        """Get top holders/traders in a market"""
        try:
            url = f"{self.data_api}/holders"
            params = {
                "market": condition_id,
                "limit": 100  # Get top 100 holders per market
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            holders_data = response.json()
            wallets = []
            
            # Extract wallet addresses from holders
            for token_data in holders_data:
                holders = token_data.get("holders", [])
                for holder in holders:
                    wallet = holder.get("proxyWallet", "").lower()
                    if wallet:
                        wallets.append(wallet)
            
            return wallets
            
        except Exception as e:
            logger.debug(f"Could not fetch holders for {condition_id}: {e}")
            return []
    
    def get_wallet_trades(self, wallet: str) -> List[Dict]:
        """Get all trades for a wallet"""
        try:
            url = f"{self.data_api}/trades"
            params = {
                "user": wallet,
                "limit": 500  # Get up to 500 trades
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.debug(f"Could not fetch trades for {wallet[:10]}...: {e}")
            return []
    
    def analyze_wallet(self, wallet: str, current_time: int) -> WalletInfo:
        """Analyze if wallet is new and get stats"""
        trades = self.get_wallet_trades(wallet)
        
        if not trades:
            return None
        
        # Get timestamps
        timestamps = [trade.get("timestamp", 0) for trade in trades]
        
        if not timestamps:
            return None
        
        first_trade = min(timestamps)
        
        # Calculate stats
        total_volume = sum(
            float(trade.get("price", 0)) * float(trade.get("size", 0))
            for trade in trades
        )
        
        unique_markets = len(set(trade.get("conditionId") for trade in trades))
        
        wallet_info = WalletInfo(
            address=wallet,
            first_trade_time=first_trade,
            total_trades=len(trades),
            total_volume=total_volume,
            markets_traded=unique_markets
        )
        
        # Check if new wallet (first trade within lookback period)
        cutoff_time = current_time - (self.lookback_hours * 3600)
        
        if first_trade >= cutoff_time:
            return wallet_info
        
        return None
    
    def log_new_wallet(self, wallet_info: WalletInfo):
        """Log discovered new wallet"""
        first_trade_dt = datetime.fromtimestamp(wallet_info.first_trade_time)
        hours_ago = (time.time() - wallet_info.first_trade_time) / 3600
        
        logger.info(f"""
╔════════════════════════════════════════════════════════════════╗
║ 🆕 NEW WALLET FOUND                                            ║
╠════════════════════════════════════════════════════════════════╣
║ Address: {wallet_info.address[:42]}...    ║
║ First Trade: {first_trade_dt.strftime('%Y-%m-%d %H:%M:%S')} ({hours_ago:.1f}h ago)          ║
║ Total Trades: {wallet_info.total_trades:<3}                                            ║
║ Total Volume: ${wallet_info.total_volume:,.2f}                                  ║
║ Markets Traded: {wallet_info.markets_traded:<3}                                          ║
╚════════════════════════════════════════════════════════════════╝
        """)
    
    def scan_markets(self) -> int:
        """Scan markets for new wallets"""
        logger.info("📊 Fetching active markets...")
        
        markets = self.get_active_markets()
        logger.info(f"Found {len(markets)} active markets to scan")
        
        all_wallets = set()
        current_time = int(time.time())
        
        # Get holders from each market
        for i, event in enumerate(markets, 1):
            markets_list = event.get("markets", [])
            
            for market in markets_list:
                condition_id = market.get("conditionId")
                if not condition_id:
                    continue
                
                logger.info(f"Scanning market {i}/{len(markets)}: {market.get('question', 'Unknown')[:50]}...")
                
                holders = self.get_market_holders(condition_id)
                all_wallets.update(holders)
                
                time.sleep(0.1)  # Rate limiting
        
        logger.info(f"✅ Found {len(all_wallets)} unique wallets across all markets")
        
        # Check each wallet
        new_count = 0
        for wallet in all_wallets:
            if wallet in self.checked_wallets:
                continue
            
            self.checked_wallets.add(wallet)
            
            # Analyze wallet
            wallet_info = self.analyze_wallet(wallet, current_time)
            
            if wallet_info:
                self.new_wallets[wallet] = wallet_info
                self.log_new_wallet(wallet_info)
                new_count += 1
            
            time.sleep(0.1)  # Rate limiting
        
        return new_count
    
    def run(self, interval: int = 300):
        """Main bot loop"""
        logger.info("=" * 70)
        logger.info("🤖 Polymarket New Wallet Scanner")
        logger.info("=" * 70)
        logger.info(f"⏰ Finding wallets with first trade in last {self.lookback_hours} hours")
        logger.info(f"🔄 Scanning every {interval} seconds ({interval//60} minutes)")
        logger.info(f"📈 Checking top {self.markets_to_scan} markets by volume")
        logger.info("=" * 70)
        
        scan_count = 0
        
        while True:
            try:
                scan_count += 1
                logger.info(f"\n🔄 Scan #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("-" * 70)
                
                # Scan markets for new wallets
                new_found = self.scan_markets()
                
                # Summary
                logger.info(f"""
📊 Scan Complete:
   ├─ New wallets this scan: {new_found}
   ├─ Total new wallets found: {len(self.new_wallets)}
   ├─ Wallets checked: {len(self.checked_wallets)}
   └─ Next scan in {interval} seconds ({interval//60} minutes)
{"=" * 70}
                """)
                
                # Wait before next iteration
                logger.info(f"💤 Sleeping for {interval//60} minutes...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Bot stopped by user")
                logger.info(f"📊 Final Stats: Found {len(self.new_wallets)} new wallets")
                
                if self.new_wallets:
                    logger.info("\n📋 Summary of all new wallets found:")
                    for wallet_info in sorted(self.new_wallets.values(), 
                                            key=lambda x: x.first_trade_time, 
                                            reverse=True):
                        logger.info(f"   {wallet_info.address}: ${wallet_info.total_volume:,.2f} volume")
                
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                time.sleep(60)

def main():
    """Entry point"""
    scanner = PolymarketNewWalletScanner()
    scanner.run(interval=300)  # Scan every 5 minutes

if __name__ == "__main__":
    main()
