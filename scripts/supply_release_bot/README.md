# Supply Release Bot

This bot monitors the MYSO/USDC Uniswap V3 pool and mints tokens when the price
moves more than 5% above the configured target price. Minted tokens are
immediately sold for USDC using the existing trading utilities to help stabilise
the price. The script is intended to be called from a cron job every 30 minutes.

## Usage

1. Install Python dependencies
   ```bash
   pip install -r scripts/volume_bot/requirements.txt
   ```
2. Create a configuration file based on the provided template:
   ```bash
   cp scripts/supply_release_bot/config_template.json scripts/supply_release_bot/config.json
   ```
3. Edit `config.json` with your owner private key and any desired parameters.
4. Run the bot:
   ```bash
   python -m scripts.supply_release_bot --config scripts/supply_release_bot/config.json
   ```

The bot keeps track of the total amount of tokens released in
`supply_release_state.json` in the same folder.
