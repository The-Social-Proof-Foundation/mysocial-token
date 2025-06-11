"""
Volume Generator Bot for creating trading volume on a token.

This module implements a bot that creates artificial trading volume
by buying and selling tokens in random intervals with random amounts.
"""

import os
import json
import time
import random
import asyncio
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from decimal import Decimal
from functools import wraps

from web3 import Web3
from web3.types import Wei, ChecksumAddress, TxReceipt
from web3.exceptions import TimeExhausted
from eth_account import Account

from scripts.volume_bot.multi_wallet_manager import MultiWalletManager
from scripts.volume_bot.trader import Trader, UNISWAP_V4_ROUTER_ABI
from scripts.volume_bot.wallet import Wallet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("volume_generator")

# Uniswap V3 Router address (Swap Router 02) on Base Mainnet
UNISWAP_V3_ROUTER_ADDRESS = "0x2626664c2603336E57B271c5C0b26F421741e481"

# Universal Router address for Base - this is the correct router for V4 swaps
UNIVERSAL_ROUTER_ADDRESS = "0x198EF79F1F515F02dFE9e3115eD9fC07183f02fC"

# Get Alchemy RPC URL from environment variable or use fallbacks
ALCHEMY_RPC_URL = os.environ.get("BASE_MAINNET_RPC", None)

# Multiple RPC endpoints for redundancy
BASE_RPC_URLS = [
    ALCHEMY_RPC_URL if ALCHEMY_RPC_URL else "https://mainnet.base.org",
    "https://base.blockpi.network/v1/rpc/public",
    "https://base.meowrpc.com",
    "https://base-mainnet.public.blastapi.io",
    "https://base.drpc.org"
]

# Filter out None values (in case ALCHEMY_RPC_URL is None)
BASE_RPC_URLS = [url for url in BASE_RPC_URLS if url]

# Retry decorator for handling rate limits
def retry_with_backoff(max_retries=5, initial_backoff=1, backoff_factor=2):
    """Retry decorator with exponential backoff for handling rate limits"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_backoff = initial_backoff
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.HTTPError, TimeExhausted) as e:
                    # Check if it's a rate limit error (429)
                    if hasattr(e, 'response') and e.response.status_code == 429:
                        logger.warning(f"Rate limited. Retrying in {current_backoff} seconds...")
                    else:
                        logger.warning(f"Request failed: {str(e)}. Retrying in {current_backoff} seconds...")
                    
                    time.sleep(current_backoff)
                    retries += 1
                    current_backoff *= backoff_factor
                    
                    # If we have multiple RPC endpoints, try switching to a different one
                    if hasattr(args[0], 'switch_rpc_endpoint'):
                        args[0].switch_rpc_endpoint()
                    
            # If we've exhausted all retries, raise the last exception
            raise Exception(f"Failed after {max_retries} retries")
        
        return wrapper
    return decorator

# Hardcoded configuration
DEFAULT_CONFIG = {
    "rpc_urls": BASE_RPC_URLS,
    "token_address": Web3.to_checksum_address("0xfdd6013bf2757018d8c087244f03e5a521b2d3b7"),  # Original token
    "usdc_address": Web3.to_checksum_address("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"),  # USDC on Base
    "eth_address": Web3.to_checksum_address("0x4200000000000000000000000000000000000006"),  # WETH on Base
    "router_address": Web3.to_checksum_address(UNISWAP_V3_ROUTER_ADDRESS),  # Using SwapRouter02 for V3
    "treasury_address": Web3.to_checksum_address("0x0a9A62e77326953E5e17948a1A7374dB6eCBB229"),
    "pool_fee": 3000,  # 0.3% fee tier
    "num_trading_wallets": 3,
    "wallets_storage_path": "trading-wallets.json",
    "trade_interval_min": 1,
    "trade_interval_max": 2,
    "min_trade_size": 0.26,
    "max_trade_size": 4.44,
    "slippage_tolerance": 100,  # 1% slippage tolerance
    "token_abi": [
        {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "payable": False, "stateMutability": "view", "type": "function"},
        {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
        {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"},
        {"constant": True, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
        {"constant": False, "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"}
    ],
    "router_abi": UNISWAP_V4_ROUTER_ABI
}

class VolumeGeneratorBot:
    """Bot for generating trading volume."""
    
    def __init__(self, config_path: str = "volume_generator_config.json"):
        """
        Initialize the volume generator bot.
        
        Args:
            config_path: Path to the configuration file
        """
        # Load configuration from file if it exists
        self.config = DEFAULT_CONFIG.copy()
        file_config = {}
        
        try:
            if os.path.exists(config_path):
                logger.info(f"Loading configuration from {config_path}")
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    
                # Update configuration with values from file
                for key, value in file_config.items():
                    if key in self.config:
                        self.config[key] = value
                        
                logger.info(f"Configuration loaded from {config_path}")
                
                # Convert numeric values to appropriate types
                if 'min_trade_size' in file_config:
                    self.config['min_trade_size'] = float(file_config['min_trade_size'])
                if 'max_trade_size' in file_config:
                    self.config['max_trade_size'] = float(file_config['max_trade_size'])
                if 'trade_interval_min' in file_config:
                    self.config['trade_interval_min'] = float(file_config['trade_interval_min'])
                if 'trade_interval_max' in file_config:
                    self.config['trade_interval_max'] = float(file_config['trade_interval_max'])
                if 'slippage_tolerance' in file_config:
                    self.config['slippage_tolerance'] = int(file_config['slippage_tolerance'])
                # Add conversion for MYSO trade sizes
                if 'min_trade_size_myso' in file_config:
                    self.config['min_trade_size_myso'] = float(file_config['min_trade_size_myso'])
                if 'max_trade_size_myso' in file_config:
                    self.config['max_trade_size_myso'] = float(file_config['max_trade_size_myso'])
                
                # Force pool_fee to be 3000 (0.3%) regardless of config file
                self.config['pool_fee'] = 3000
                    
                # Ensure all addresses are properly checksummed
                if 'token_address' in file_config:
                    self.config['token_address'] = Web3.to_checksum_address(file_config['token_address'])
                if 'usdc_address' in file_config:
                    self.config['usdc_address'] = Web3.to_checksum_address(file_config['usdc_address'])
                if 'eth_address' in file_config:
                    self.config['eth_address'] = Web3.to_checksum_address(file_config['eth_address'])
                if 'router_address' in file_config:
                    self.config['router_address'] = Web3.to_checksum_address(file_config['router_address'])
                if 'treasury_address' in file_config:
                    self.config['treasury_address'] = Web3.to_checksum_address(file_config['treasury_address'])
                    
                # Make sure hardcoded addresses are also checksummed
                if 'token_address' in self.config and not isinstance(self.config['token_address'], str):
                    self.config['token_address'] = Web3.to_checksum_address(self.config['token_address'])
                if 'usdc_address' in self.config and not isinstance(self.config['usdc_address'], str):
                    self.config['usdc_address'] = Web3.to_checksum_address(self.config['usdc_address'])
                if 'eth_address' in self.config and not isinstance(self.config['eth_address'], str):
                    self.config['eth_address'] = Web3.to_checksum_address(self.config['eth_address'])
                if 'router_address' in self.config and not isinstance(self.config['router_address'], str):
                    self.config['router_address'] = Web3.to_checksum_address(self.config['router_address'])
                    
                logger.info(f"Using router address from config: {self.config['router_address']}")
        except Exception as e:
            logger.warning(f"Error loading configuration file: {str(e)}. Using default configuration.")
            
        # Always ensure pool_fee is 3000
        self.config['pool_fee'] = 3000
        
        # Initialize Web3 after config is loaded
        self.current_rpc_index = 0
        self.initialize_web3()
        
        # Initialize wallet manager
        self.wallet_manager = MultiWalletManager(self.config["wallets_storage_path"])
        
        # Ensure we have enough wallets
        self.wallet_manager.ensure_wallets(self.config["num_trading_wallets"])
        
        logger.info("Initialized VolumeGeneratorBot with configuration")
        logger.info(f"Using token address: {self.config['token_address']}")
        logger.info(f"Using USDC address: {self.config['usdc_address']}")
        logger.info(f"Using pool fee: {self.config['pool_fee']}")
        logger.info(f"Trade intervals: {self.config['trade_interval_min']} to {self.config['trade_interval_max']} minutes")
        logger.info(f"Trade size: {self.config['min_trade_size']} to {self.config['max_trade_size']} USDC")
        logger.info(f"Connected to network: {self._get_network_name()}")
        logger.info(f"Using RPC endpoint: {self.config['rpc_urls'][self.current_rpc_index]}")
        logger.info(f"Using router address: {self.config['router_address']}")
    
    def initialize_web3(self):
        """Initialize Web3 with the current RPC endpoint"""
        try:
            current_rpc = self.config["rpc_urls"][self.current_rpc_index]
            logger.info(f"Connected to {current_rpc}")
            self.w3 = Web3(Web3.HTTPProvider(
                current_rpc,
                request_kwargs={'timeout': 30}  # 30 second timeout
            ))
            
            # Verify connection
            if not self.w3.is_connected():
                logger.warning(f"Failed to connect to {current_rpc}")
                self.switch_rpc_endpoint()
        except Exception as e:
            logger.error(f"Error initializing Web3: {str(e)}")
            self.switch_rpc_endpoint()
    
    def switch_rpc_endpoint(self):
        """Switch to the next available RPC endpoint"""
        self.current_rpc_index = (self.current_rpc_index + 1) % len(self.config["rpc_urls"])
        logger.info(f"Switching to RPC endpoint: {self.config['rpc_urls'][self.current_rpc_index]}")
        self.initialize_web3()
        
    def _get_network_name(self) -> str:
        """Get the name of the connected network"""
        try:
            chain_id = self.w3.eth.chain_id
            if chain_id == 8453:
                return "Base Mainnet"
            elif chain_id == 84531:
                return "Base Goerli Testnet"
            else:
                return f"Unknown (Chain ID: {chain_id})"
        except Exception as e:
            logger.warning(f"Could not determine network: {e}")
            return "Unknown"
    
    @retry_with_backoff(max_retries=5, initial_backoff=1, backoff_factor=2)
    def run_test_trade(self) -> None:
        """Execute a test trade to verify the setup."""
        try:
            logger.info("Executing test trade")
            
            # Select a random wallet
            wallets = self.wallet_manager.get_all_wallets()
            if not wallets:
                raise ValueError("No active wallets available for trading")
                
            wallet = random.choice(wallets)
            logger.info(f"Selected wallet {wallet.get_address()} for trading")
            
            # Check wallet balances before trade
            self._check_wallet_balances(wallet)
            
            # Initialize trader for this wallet
            trader = Trader(
                w3=self.w3,
                wallet=wallet,
                router_address=self.config["router_address"],
                router_abi=self.config["router_abi"]
            )
            
            # Add some delay between requests to avoid rate limiting
            time.sleep(1)
            
            # Get token decimals
            token_decimals = trader.get_token_contract(self.config["token_address"]).functions.decimals().call()
            time.sleep(1)  # Add delay between RPC calls
            
            usdc_decimals = trader.get_token_contract(self.config["usdc_address"]).functions.decimals().call()
            logger.info(f"MYSO token decimals: {token_decimals}, USDC decimals: {usdc_decimals}")
            
            # Prepare pool key - force fee to 3000 (0.3%)
            pool_key = {
                "fee": 3000,  # IMPORTANT: Hard-coded to 0.3% fee tier
                "tickSpacing": 60,  # Default tick spacing for 0.3% fee tier
                "hooks": Web3.to_checksum_address("0x0000000000000000000000000000000000000000")  # No hooks
            }
            
            # For test trade, use a small amount (0.04 USDC)
            test_amount = int(0.04 * (10 ** usdc_decimals))
            
            # Add delay between RPC calls
            time.sleep(1)
            
            # Check if wallet has enough USDC
            usdc_balance, _ = trader.get_token_balance(self.config["usdc_address"])
            if usdc_balance < test_amount:
                logger.warning(f"Wallet has insufficient USDC. Have: {usdc_balance / (10 ** usdc_decimals)}, Need: 0.04")
                logger.info("Please fund the wallet with USDC first.")
                return
            
            # Execute swap - USDC to MYSO token
            try:
                # Add delay before swap
                time.sleep(2)
                
                logger.info(f"Executing USDC -> MYSO token swap for {test_amount / (10**usdc_decimals)} USDC")
                tx_hash = trader.swap_tokens_for_tokens(
                    token_in=self.config["usdc_address"],
                    token_out=self.config["token_address"],  # Swap to MYSO token
                    amount_in=test_amount,
                    pool_key=pool_key
                )
                
                logger.info(f"Test trade executed with tx hash: {tx_hash}")
                
                # Add delay before checking receipt to avoid rate limiting
                time.sleep(2)
                
                # Wait for transaction confirmation
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
                if receipt.status == 1:
                    logger.info("Trade successful!")
                    
                    # Check wallet balances after trade
                    time.sleep(2)  # Add delay
                    self._check_wallet_balances(wallet)
                    
                    # Update wallet stats
                    self.wallet_manager.update_wallet_stats(wallet.get_address(), 0.04)  # 0.04 USDC volume
                else:
                    logger.error("Trade transaction failed")
                    # Print transaction details for debugging
                    logger.info(f"Transaction details: {self.w3.eth.get_transaction(tx_hash)}")
            except Exception as e:
                logger.error(f"Error during swap execution: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Error executing test trade: {str(e)}")
            raise
    
    @retry_with_backoff(max_retries=3, initial_backoff=1, backoff_factor=2)        
    def _check_wallet_balances(self, wallet):
        """Check and log wallet balances"""
        try:
            # Get token contracts
            token_contract = self.w3.eth.contract(
                address=self.config["token_address"],
                abi=self.config["token_abi"]
            )
            usdc_contract = self.w3.eth.contract(
                address=self.config["usdc_address"],
                abi=self.config["token_abi"]
            )
            eth_contract = self.w3.eth.contract(
                address=self.config["eth_address"],
                abi=self.config["token_abi"]
            )
            
            wallet_address = wallet.get_address()
            
            # Get decimals with delay between calls
            token_decimals = token_contract.functions.decimals().call()
            time.sleep(1)  # Delay between RPC calls
            
            usdc_decimals = usdc_contract.functions.decimals().call()
            time.sleep(1)  # Delay between RPC calls
            
            eth_decimals = eth_contract.functions.decimals().call()
            time.sleep(1)  # Delay between RPC calls
            
            # Get balances with delay between calls
            token_balance = token_contract.functions.balanceOf(wallet_address).call()
            time.sleep(1)  # Delay between RPC calls
            
            usdc_balance = usdc_contract.functions.balanceOf(wallet_address).call()
            time.sleep(1)  # Delay between RPC calls
            
            eth_token_balance = eth_contract.functions.balanceOf(wallet_address).call()
            time.sleep(1)  # Delay between RPC calls
            
            eth_balance = self.w3.eth.get_balance(wallet_address)
            
            # Format balances
            token_balance_formatted = token_balance / (10 ** token_decimals)
            usdc_balance_formatted = usdc_balance / (10 ** usdc_decimals)
            eth_token_balance_formatted = eth_token_balance / (10 ** eth_decimals)
            eth_balance_formatted = self.w3.from_wei(eth_balance, 'ether')
            
            logger.info(f"Wallet balances: {token_balance_formatted} TOKEN, {usdc_balance_formatted} USDC, {eth_token_balance_formatted} WETH, {eth_balance_formatted} ETH")
        except Exception as e:
            logger.warning(f"Error checking wallet balances: {str(e)}")
            raise  # Re-raise for retry decorator
            
    def start_continuous_trading(self) -> None:
        """Start continuous trading with random intervals."""
        logger.info("Starting continuous trading")
        logger.info(f"Trade intervals: {self.config['trade_interval_min']} to {self.config['trade_interval_max']} minutes")
        logger.info(f"Trade size: {self.config['min_trade_size']} to {self.config['max_trade_size']} USDC")
        logger.info(f"MYSO sell size: {self.config.get('min_trade_size_myso', 5)} to {self.config.get('max_trade_size_myso', 122)} MYSO")
        logger.info("Press any key to stop trading and return to menu...")
        
        # Get USDC decimals for later use
        wallets = self.wallet_manager.get_all_wallets()
        if not wallets:
            logger.error("No active wallets available for trading")
            return
            
        try:
            # Initialize trader with any wallet just to get token info
            trader = Trader(
                w3=self.w3,
                wallet=wallets[0],
                router_address=self.config["router_address"],
                router_abi=self.config["router_abi"]
            )
            usdc_decimals = trader.get_token_contract(self.config["usdc_address"]).functions.decimals().call()
        except Exception as e:
            logger.error(f"Error getting USDC decimals: {e}")
            usdc_decimals = 6  # Default USDC decimals
            
        # Prepare pool key
        pool_key = {
            "fee": 3000,  # IMPORTANT: Hard-coded to 0.3% fee tier
            "tickSpacing": 60,  # Default tick spacing for fee tier
            "hooks": Web3.to_checksum_address("0x0000000000000000000000000000000000000000")  # No hooks
        }
        
        import sys
        import select
        import termios
        import tty
        
        # Set up non-blocking input
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            
            while True:
                try:
                    # Check for user input (press any key to exit)
                    if select.select([sys.stdin], [], [], 0)[0]:
                        sys.stdin.read(1)
                        logger.info("Key pressed, stopping continuous trading...")
                        break
                        
                    # Random wait time between trades
                    wait_time = random.uniform(
                        self.config["trade_interval_min"],
                        self.config["trade_interval_max"]
                    )
                    logger.info(f"Waiting {wait_time:.2f} minutes before next trade")
                    
                    # Wait with periodic checks for key press
                    wait_seconds = wait_time * 60
                    wait_interval = 0.1  # Check for key press every 0.1 seconds
                    waited = 0
                    
                    while waited < wait_seconds:
                        if select.select([sys.stdin], [], [], 0)[0]:
                            sys.stdin.read(1)
                            logger.info("Key pressed, stopping continuous trading...")
                            return
                        time.sleep(wait_interval)
                        waited += wait_interval
                    
                    # Select a random wallet
                    wallet = random.choice(wallets)
                    logger.info(f"Selected wallet {wallet.get_address()} for trading")
                    
                    # Initialize trader for this wallet
                    trader = Trader(
                        w3=self.w3,
                        wallet=wallet,
                        router_address=self.config["router_address"],
                        router_abi=self.config["router_abi"]
                    )
                    
                    # Random trade size between min and max trade size
                    trade_size = random.uniform(
                        self.config["min_trade_size"],
                        self.config["max_trade_size"]
                    )
                    
                    # Convert to wei
                    trade_amount = int(trade_size * (10 ** usdc_decimals))
                    
                    # Check if wallet has enough USDC
                    usdc_balance, _ = trader.get_token_balance(self.config["usdc_address"])
                    if usdc_balance < trade_amount:
                        logger.warning(f"Wallet has insufficient USDC. Have: {usdc_balance / (10 ** usdc_decimals)}, Need: {trade_size}")
                        # Instead of skipping, try to sell MYSO tokens
                        logger.info("Automatically switching to MYSO sell operation")
                        
                        # Get MYSO balance
                        token_balance, token_decimals = trader.get_token_balance(self.config["token_address"])
                        
                        # Use dedicated MYSO amounts instead of rough estimate
                        myso_trade_size = random.uniform(
                            float(self.config.get("min_trade_size_myso", 5)),
                            float(self.config.get("max_trade_size_myso", 122))
                        )
                        token_amount = int(myso_trade_size * (10 ** token_decimals))
                        
                        if token_balance < token_amount:
                            logger.warning(f"Wallet also has insufficient MYSO tokens. Have: {token_balance / (10 ** token_decimals)}, Need: {myso_trade_size}")
                            logger.info("Skipping trade for this wallet")
                            continue
                        else:
                            logger.info(f"Executing MYSO -> USDC token swap for {myso_trade_size:.6f} MYSO")
                            tx_hash = trader.swap_tokens_for_tokens(
                                token_in=self.config["token_address"],
                                token_out=self.config["usdc_address"],
                                amount_in=token_amount,
                                pool_key=pool_key
                            )
                            
                            logger.info(f"Trade executed with tx hash: {tx_hash}")
                            
                            # Update wallet stats
                            self.wallet_manager.update_wallet_stats(wallet.get_address(), trade_size)
                            
                            # Skip the rest of this iteration
                            continue
                    
                    # 50% chance to buy, 50% chance to sell
                    operation = random.choice(["buy", "sell"])
                    
                    if operation == "buy":
                        # Buy MYSO with USDC
                        logger.info(f"Executing USDC -> MYSO token swap for {trade_size:.2f} USDC")
                        tx_hash = trader.swap_tokens_for_tokens(
                            token_in=self.config["usdc_address"],
                            token_out=self.config["token_address"],
                            amount_in=trade_amount,
                            pool_key=pool_key
                        )
                    else:
                        # Sell MYSO for USDC - first check if we have enough MYSO
                        token_balance, token_decimals = trader.get_token_balance(self.config["token_address"])
                        
                        # Use dedicated MYSO amounts instead of rough estimate
                        myso_trade_size = random.uniform(
                            float(self.config.get("min_trade_size_myso", 5)),
                            float(self.config.get("max_trade_size_myso", 122))
                        )
                        token_amount = int(myso_trade_size * (10 ** token_decimals))
                        
                        if token_balance < token_amount:
                            logger.warning(f"Wallet has insufficient MYSO tokens. Have: {token_balance / (10 ** token_decimals)}, Need: {myso_trade_size}")
                            # Fall back to buying instead
                            logger.info(f"Falling back to buying MYSO instead")
                            tx_hash = trader.swap_tokens_for_tokens(
                                token_in=self.config["usdc_address"],
                                token_out=self.config["token_address"],
                                amount_in=trade_amount,
                                pool_key=pool_key
                            )
                        else:
                            logger.info(f"Executing MYSO -> USDC token swap for {myso_trade_size:.6f} MYSO")
                            tx_hash = trader.swap_tokens_for_tokens(
                                token_in=self.config["token_address"],
                                token_out=self.config["usdc_address"],
                                amount_in=token_amount,
                                pool_key=pool_key
                            )
                    
                    logger.info(f"Trade executed with tx hash: {tx_hash}")
                    
                    # Update wallet stats
                    self.wallet_manager.update_wallet_stats(wallet.get_address(), trade_size)
                    
                except Exception as e:
                    logger.error(f"Error in continuous trading: {str(e)}")
                    time.sleep(60)  # Wait a minute before retrying
                    
        except Exception as e:
            logger.error(f"Error in continuous trading: {str(e)}")
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            logger.info("Continuous trading stopped. Returning to menu.")
        
    def run(self) -> None:
        """Run the volume generator bot."""
        try:
            while True:
                print("\n" + "=" * 42)
                print("       VOLUME GENERATOR BOT MENU        ")
                print("=" * 42)
                print("1. Create Trading Wallets")
                print("2. Fund Wallets")
                print("3. Run Test Trade")
                print("4. Start Continuous Trading")
                print("5. Deactivate Wallets")
                print("6. Edit Configuration")
                print("7. View Wallet Information")
                print("8. Exit")
                print("=" * 42)
                
                choice = input("Enter your choice [1-8]: ")
                
                if choice == "1":
                    self.create_trading_wallets()
                elif choice == "2":
                    self.fund_wallets()
                elif choice == "3":
                    self.run_test_trade()
                elif choice == "4":
                    self.start_continuous_trading()
                elif choice == "5":
                    self.deactivate_wallets()
                elif choice == "6":
                    self.edit_configuration()
                elif choice == "7":
                    self.view_wallet_info()
                elif choice == "8":
                    print("Exiting...")
                    break
                else:
                    print("Invalid choice. Please try again.")
                    
        except KeyboardInterrupt:
            print("\nExiting...")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            raise


# Module-level functions for CLI commands

async def create_wallets(wallet_count: int) -> None:
    """Create trading wallets."""
    logger.info(f"Creating {wallet_count} trading wallets")
    
    # Initialize wallet manager
    wallet_manager = MultiWalletManager(DEFAULT_CONFIG["wallets_storage_path"])
    
    # Create new wallets
    for _ in range(wallet_count):
        wallet_manager.create_wallet()
    
    logger.info(f"Created {wallet_count} new wallets")

async def fund_wallets(treasury_key: str, usdc_amount_per_wallet: float = None, eth_amount_per_wallet: float = None) -> None:
    """Fund trading wallets from treasury with both ETH and USDC."""
    logger.info("Funding trading wallets from treasury")
    
    # Initialize wallet manager
    wallet_manager = MultiWalletManager(DEFAULT_CONFIG["wallets_storage_path"])
    
    # Get active wallets
    wallets = wallet_manager.get_all_wallets()
    if not wallets:
        logger.error("No wallets to fund. Create wallets first.")
        return
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(DEFAULT_CONFIG["rpc_urls"][0]))
    
    # Treasury wallet
    treasury_wallet = Wallet(private_key=treasury_key)
    treasury_address = treasury_wallet.get_address()
    logger.info(f"Using treasury wallet: {treasury_address}")
    
    # USDC contract
    usdc_contract = w3.eth.contract(
        address=w3.to_checksum_address(DEFAULT_CONFIG["usdc_address"]),
        abi=DEFAULT_CONFIG["token_abi"]
    )
    
    # Get USDC decimals
    usdc_decimals = usdc_contract.functions.decimals().call()
    
    # Check treasury balances
    usdc_balance = usdc_contract.functions.balanceOf(treasury_address).call()
    usdc_balance_formatted = usdc_balance / (10 ** usdc_decimals)
    eth_balance = w3.eth.get_balance(treasury_address)
    eth_balance_formatted = w3.from_wei(eth_balance, 'ether')
    
    logger.info(f"Treasury balances: {usdc_balance_formatted} USDC, {eth_balance_formatted} ETH")
    
    # Calculate total amount needed
    total_wallets = len(wallets)
    
    # If ETH amount wasn't provided, use default (0.003 ETH should be enough for several transactions)
    if eth_amount_per_wallet is None:
        eth_amount_per_wallet = 0.003
    
    # If USDC amount wasn't provided, use default from config
    if usdc_amount_per_wallet is None:
        usdc_amount_per_wallet = float(DEFAULT_CONFIG["min_trade_size"])
        logger.info(f"Using default amount of {usdc_amount_per_wallet} USDC per wallet")
    
    # Calculate total needs
    total_usdc_needed = usdc_amount_per_wallet * total_wallets
    total_eth_needed = eth_amount_per_wallet * total_wallets
    
    # Check if treasury has enough funds
    if usdc_balance_formatted < total_usdc_needed:
        logger.warning(f"Treasury has insufficient USDC. Have: {usdc_balance_formatted}, Need: {total_usdc_needed}")
        return
    
    if eth_balance_formatted < total_eth_needed:
        logger.warning(f"Treasury has insufficient ETH. Have: {eth_balance_formatted}, Need: {total_eth_needed}")
        return
    
    # Convert amounts to wei
    usdc_amount = int(usdc_amount_per_wallet * (10 ** usdc_decimals))
    eth_amount = w3.to_wei(eth_amount_per_wallet, 'ether')
    
    logger.info(f"Funding {total_wallets} wallets with {eth_amount_per_wallet} ETH and {usdc_amount_per_wallet} USDC each")
    
    # Get starting nonce for ETH transactions
    eth_nonce = w3.eth.get_transaction_count(treasury_address, 'pending')
    
    # First, send ETH to all wallets (so they can handle transactions)
    logger.info("Step 1: Sending ETH to all wallets")
    eth_tx_hashes = []
    wallet_addresses = []
    
    for wallet in wallets:
        wallet_address = wallet.get_address()
        wallet_addresses.append(wallet_address)
        
        try:
            # Send ETH first - this is a simple transaction, not a contract call
            logger.info(f"Sending {eth_amount_per_wallet} ETH to {wallet_address} (nonce: {eth_nonce})")
            
            # Create transaction with current nonce
            eth_tx = {
                'to': wallet_address,
                'value': eth_amount,
                'gas': 30000,  # 30k gas should be enough for a simple ETH transfer
                'gasPrice': w3.eth.gas_price,
                'nonce': eth_nonce,
                'chainId': w3.eth.chain_id
            }
            
            # Sign transaction
            signed_tx = treasury_wallet.sign_transaction(eth_tx)
            
            # Send transaction
            tx_hash = w3.eth.send_raw_transaction(signed_tx)
            eth_tx_hashes.append(tx_hash)
            logger.info(f"ETH transfer transaction sent: {w3.to_hex(tx_hash)}")
            
            # Increment nonce for next transaction
            eth_nonce += 1
            
            # Brief pause to avoid rate limits
            await asyncio.sleep(0.2)
            
        except Exception as e:
            logger.error(f"Error sending ETH to wallet {wallet_address}: {str(e)}")
            # Still increment nonce in case of failure - just to keep nonces in sync
            eth_nonce += 1
    
    # Wait for ETH transactions with timeout
    logger.info("Waiting for ETH transfers to confirm (timeout: 60 seconds)...")
    
    eth_confirmations = 0
    eth_attempts = 0
    max_eth_attempts = 3  # Try up to 3 times to confirm all transactions
    
    while eth_confirmations < len(eth_tx_hashes) and eth_attempts < max_eth_attempts:
        eth_attempts += 1
        confirmed_hashes = set()
        
        for i, tx_hash in enumerate(eth_tx_hashes):
            if tx_hash in confirmed_hashes:
                continue
                
            try:
                # Use a short timeout to check receipt
                receipt = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash)
                    ),
                    timeout=20  # 20 second timeout per check
                )
                
                if receipt.status == 1:
                    logger.info(f"ETH transfer confirmed: {w3.to_hex(tx_hash)} to {wallet_addresses[i]}")
                    confirmed_hashes.add(tx_hash)
                    eth_confirmations += 1
                else:
                    logger.error(f"ETH transfer failed: {w3.to_hex(tx_hash)} to {wallet_addresses[i]}")
            except asyncio.TimeoutError:
                # Just log the timeout, but continue with other transactions
                logger.warning(f"Timeout waiting for ETH transfer: {w3.to_hex(tx_hash)} to {wallet_addresses[i]}")
            except Exception as e:
                logger.error(f"Error checking ETH transfer: {str(e)}")
        
        # If we haven't confirmed all transactions yet, wait a bit before checking again
        if eth_confirmations < len(eth_tx_hashes):
            logger.info(f"Confirmed {eth_confirmations}/{len(eth_tx_hashes)} ETH transfers. Checking again in 10 seconds...")
            await asyncio.sleep(10)
    
    logger.info(f"ETH transfers: {eth_confirmations}/{len(eth_tx_hashes)} confirmed")
    
    # Now send USDC to all wallets
    logger.info("Step 2: Sending USDC to all wallets")
    
    # Get fresh nonce for USDC transactions
    usdc_nonce = w3.eth.get_transaction_count(treasury_address, 'pending')
    usdc_tx_hashes = []
    
    for i, wallet in enumerate(wallets):
        wallet_address = wallet.get_address()
        
        try:
            # Send USDC
            logger.info(f"Sending {usdc_amount_per_wallet} USDC to {wallet_address} (nonce: {usdc_nonce})")
            
            # Prepare USDC transfer transaction with tracked nonce
            usdc_tx = usdc_contract.functions.transfer(
                wallet_address, usdc_amount
            ).build_transaction({
                'from': treasury_address,
                'nonce': usdc_nonce,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = treasury_wallet.sign_transaction(usdc_tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx)
            usdc_tx_hashes.append(tx_hash)
            logger.info(f"USDC transfer transaction sent: {w3.to_hex(tx_hash)}")
            
            # Increment nonce for next transaction
            usdc_nonce += 1
            
            # Brief pause between transactions
            await asyncio.sleep(0.2)
            
        except Exception as e:
            logger.error(f"Error sending USDC to wallet {wallet_address}: {str(e)}")
            # Still increment nonce in case of failure
            usdc_nonce += 1
    
    # Wait for USDC transactions with timeout
    logger.info("Waiting for USDC transfers to confirm (timeout: 60 seconds)...")
    
    usdc_confirmations = 0
    usdc_attempts = 0
    max_usdc_attempts = 3  # Try up to 3 times to confirm all transactions
    
    while usdc_confirmations < len(usdc_tx_hashes) and usdc_attempts < max_usdc_attempts:
        usdc_attempts += 1
        confirmed_hashes = set()
        
        for i, tx_hash in enumerate(usdc_tx_hashes):
            if tx_hash in confirmed_hashes:
                continue
                
            try:
                # Use a short timeout to check receipt
                receipt = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash)
                    ),
                    timeout=20  # 20 second timeout per check
                )
                
                if receipt.status == 1:
                    logger.info(f"USDC transfer confirmed: {w3.to_hex(tx_hash)} to {wallet_addresses[i]}")
                    confirmed_hashes.add(tx_hash)
                    usdc_confirmations += 1
                else:
                    logger.error(f"USDC transfer failed: {w3.to_hex(tx_hash)} to {wallet_addresses[i]}")
            except asyncio.TimeoutError:
                # Just log the timeout, but continue with other transactions
                logger.warning(f"Timeout waiting for USDC transfer: {w3.to_hex(tx_hash)} to {wallet_addresses[i]}")
            except Exception as e:
                logger.error(f"Error checking USDC transfer: {str(e)}")
        
        # If we haven't confirmed all transactions yet, wait a bit before checking again
        if usdc_confirmations < len(usdc_tx_hashes):
            logger.info(f"Confirmed {usdc_confirmations}/{len(usdc_tx_hashes)} USDC transfers. Checking again in 10 seconds...")
            await asyncio.sleep(10)
    
    logger.info(f"USDC transfers: {usdc_confirmations}/{len(usdc_tx_hashes)} confirmed")
    logger.info("Wallet funding complete")

async def test_trade(treasury_key: str = None) -> None:
    """Execute a test trade."""
    bot = VolumeGeneratorBot()
    bot.run_test_trade()

async def start_bot(treasury_key: str = None, amount_per_wallet: float = None) -> None:
    """Start the trading bot."""
    bot = VolumeGeneratorBot()
    
    # Fund wallets if treasury key is provided
    if treasury_key:
        await fund_wallets(treasury_key, amount_per_wallet)
    
    # Start the bot
    bot.start_continuous_trading()

async def deactivate_wallets(wallet_count: int) -> None:
    """Deactivate trading wallets."""
    logger.info(f"Deactivating {wallet_count} trading wallets")
    
    # Initialize wallet manager
    wallet_manager = MultiWalletManager(DEFAULT_CONFIG["wallets_storage_path"])
    
    # Deactivate wallets
    deactivated = wallet_manager.deactivate_wallets(wallet_count)
    logger.info(f"Deactivated wallets: {', '.join(deactivated)}") 