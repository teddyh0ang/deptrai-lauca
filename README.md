
# Polymarket Copy Trading Bot

A Python bot that monitors Polymarket for new wallets and automatically copies trades over $1,000.

## Features

- **New Wallet Detection**: Identifies wallets created within the last 24 hours
- **Large Trade Monitoring**: Tracks trades over $1,000
- **Real-time Alerts**: Logs significant trading activity
- **Market Analysis**: Fetches detailed market information
- **Extensible Architecture**: Easy to add your own trading logic

## How It Works

1. Continuously polls Polymarket's API for recent trades
2. Identifies wallets that made their first trade within 24 hours
3. Filters for trades over $1,000
4. Logs trade signals with market details
5. (Optional) Executes copy trades based on your strategy

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/polymarket-copy-bot.git
cd polymarket-copy-bot

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Create a `.env` file with the following:

```env
# Optional: Custom Polygon RPC endpoint
POLYGON_RPC_URL=https://polygon-rpc.com

# For actual trading (not required for monitoring)
PRIVATE_KEY=your_private_key_here
POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_SECRET=your_secret_here
POLYMARKET_PASSPHRASE=your_passphrase_here
```

## Usage

### Basic Monitoring (No Trading)

```bash
python bot.py
```

This will start monitoring and logging significant trades without executing any trades.

### Implementing Copy Trading

To implement actual copy trading, modify the `execute_copy_trade` method in `bot.py`:

```python
def execute_copy_trade(self, trade: Trade):
    # Your trading logic here
    # Example: Place order via Polymarket API
    pass
```

## Configuration Options

Edit the bot configuration in `bot.py`:

```python
self.min_trade_amount = 1000  # Minimum trade size to track ($)
self.lookback_hours = 24      # Hours to consider wallet "new"
```

## API Endpoints Used

- **Gamma API**: `https://gamma-api.polymarket.com`
  - `/trades` - Recent trades
  - `/markets/{id}` - Market details
- **CLOB API**: `https://clob.polymarket.com`
  - Order book and trading

## Example Output

```
2024-01-05 10:30:15 - INFO - Starting Polymarket Copy Trading Bot...
2024-01-05 10:30:15 - INFO - Monitoring for trades > $1000
2024-01-05 10:30:15 - INFO - Tracking wallets created in last 24 hours
2024-01-05 10:30:16 - INFO - Fetched 1000 recent trades
2024-01-05 10:30:18 - INFO - NEW WALLET TRADE: 0x1234567... traded $1500.00 on market abc123...
2024-01-05 10:30:19 - INFO - 
═══════════════════════════════════════════════════════
COPY TRADE SIGNAL
═══════════════════════════════════════════════════════
Wallet: 0x1234567890abcdef...
Market: Will Bitcoin reach $100k by end of 2024?
Outcome: Yes
Amount: $1500.00
Time: 2024-01-05 10:25:30
═══════════════════════════════════════════════════════
```

## Risk Warnings

⚠️ **Important Disclaimers**:

- This bot is for educational purposes
- Copy trading carries significant risks
- You can lose money - trade responsibly
- Past performance doesn't guarantee future results
- Always test with small amounts first
- Not financial advice - DYOR (Do Your Own Research)

## Advanced Features (TODO)

- [ ] Position sizing based on wallet size
- [ ] Risk management (stop losses, max exposure)
- [ ] Wallet reputation scoring
- [ ] Multi-wallet tracking
- [ ] Discord/Telegram notifications
- [ ] Web dashboard
- [ ] Backtesting framework

## Troubleshooting

### "No trades found"
- Check your internet connection
- Verify Polymarket API is accessible
- Increase the lookback period

### Rate limiting
- Add delays between API calls
- Use caching for market data
- Implement exponential backoff

## Contributing

Pull requests are welcome! For major changes, please open an issue first.

## License

MIT License - See LICENSE file for details

## Disclaimer

This software is provided "as is" without warranty. Use at your own risk. The authors are not responsible for any losses incurred through the use of this bot.
