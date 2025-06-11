# Volume Trading Bot

A production-ready trading bot that monitors token volumes on Ethereum and other EVM chains to identify and trade high-volume tokens automatically.

## Features

- Volume-based trading strategy that identifies high-volume tokens
- Multi-wallet support for increased trading volume
- Random trade timing and sizing for natural-looking volume generation
- Support for any EVM-compatible chain
- Wallet management with stats tracking
- Automated trading with slippage protection
- Position management with stop-loss and take-profit

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r scripts/volume_bot/requirements.txt
```

3. Create a config file based on the template:

```bash
cp scripts/volume_bot/config_template.json scripts/volume_bot/config.json
```

4. Edit the config file with your specific parameters (RPC URL, tokens to monitor, etc.)

## Usage

### Volume Monitor Bot

This bot monitors token volumes and trades tokens that meet your volume criteria.

```bash
python -m scripts.volume_bot.bot --config scripts/volume_bot/config.json --key YOUR_PRIVATE_KEY
```

### Volume Generator Bot

A production-ready trading bot that generates artificial trading volume for tokens on Ethereum and other EVM chains.

## Features

- Random trade timing and sizing for natural-looking volume generation
- Multi-wallet support for distributed trading
- Support for any EVM-compatible chain
- Wallet management with stats tracking
- Configurable trading parameters

## Installation

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r scripts/volume_bot/requirements.txt
```

3. Generate the default configuration:

```bash
python -m scripts.volume_bot --command test-trade --config volume_generator_config.json
```

4. Edit the configuration file with your specific parameters (RPC URL, token addresses, etc.).

## Easy Usage (Interactive Menu)

For a simpler interface, use the interactive menu script:

```bash
# Make the script executable
chmod +x scripts/volume_bot/run_volume_bot.sh

# Run the interactive menu
./scripts/volume_bot/run_volume_bot.sh
```

The interactive menu provides options to:
- Create trading wallets
- Fund wallets
- Run test trades
- Start continuous trading
- Deactivate wallets
- Edit configuration
- View wallet information

This is the recommended way to use the bot for most users.

## Command-Line Usage

All commands should be run from the project root with the virtual environment activated.

### Creating Trading Wallets

Create new trading wallets:

```bash
python -m scripts.volume_bot --command create-wallets --wallet-count 3
```

### Testing a Single Trade

Run a single test trade to verify functionality:

```bash
python -m scripts.volume_bot --command test-trade
```

### Funding Wallets

Fund trading wallets from your treasury wallet:

```bash
python -m scripts.volume_bot --command fund-wallets --treasury-key YOUR_TREASURY_KEY
```

### Start Trading

Start continuous trading with random intervals:

```bash
python -m scripts.volume_bot --command start
```

### Available Commands

- `create-wallets`: Create new trading wallets
- `fund-wallets`: Fund wallets from treasury account
- `test-trade`: Execute a single test trade
- `start`: Start continuous trading
- `deactivate`: Deactivate trading wallets

## Running Tests

To run the tests:

```bash
python scripts/volume_bot/run_tests.py
```

## Configuration Options

The main configuration file (`volume_generator_config.json`) contains the following options:

- `rpc_url`: URL for the blockchain RPC endpoint (e.g., "https://mainnet.base.org")
- `token_address`: Address of the token to generate volume for
- `usdc_address`: Address of the USDC token (or other stablecoin)
- `router_address`: DEX router contract address
- `treasury_address`: Address of the treasury wallet for funding trading wallets
- `trade_interval_min`: Minimum minutes between trades
- `trade_interval_max`: Maximum minutes between trades
- `min_trade_size`: Minimum trade size in USDC
- `max_trade_size`: Maximum trade size in USDC
- `num_trading_wallets`: Number of wallets to use for trading
- `slippage_tolerance`: Maximum slippage tolerance in basis points
- `pool_fee`: DEX pool fee in basis points
- `wallets_storage_path`: Path to store wallet information

## Security Best Practices

- **NEVER** share your private key or keystore password
- Use environment variables or secure key management solutions in production
- Run on a dedicated machine with proper security measures
- Test with small amounts before running with significant capital
- Use a dedicated treasury wallet for funding trading wallets

## Disclaimer

This bot is provided for educational purposes only. Trading cryptocurrency carries significant risk. Use at your own risk. 