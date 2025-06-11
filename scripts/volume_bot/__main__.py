"""
Main module entry point for the volume trading bot.
Allows running the bot as a module with `python -m scripts.volume_bot`.
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.volume_bot.volume_generator import (
    create_wallets,
    fund_wallets,
    test_trade,
    deactivate_wallets,
    start_bot,
    VolumeGeneratorBot
)

async def main():
    """Main entry point for the volume trading bot."""
    parser = argparse.ArgumentParser(description="Volume Trading Bot")
    parser.add_argument("--command", type=str, default="test-trade", 
                        choices=["create-wallets", "fund-wallets", "start", "deactivate", "test-trade"], 
                        help="Command to execute")
    parser.add_argument("--treasury-key", type=str, help="Treasury private key (required for funding)")
    parser.add_argument("--wallet-count", type=int, default=3, help="Number of wallets to create/deactivate")
    parser.add_argument("--usdc-amount", type=float, help="Amount of USDC to send to each wallet when funding")
    parser.add_argument("--eth-amount", type=float, help="Amount of ETH to send to each wallet when funding")
    
    args = parser.parse_args()
    
    # Execute the appropriate command
    try:
        if args.command == "create-wallets":
            await create_wallets(args.wallet_count)
        elif args.command == "fund-wallets":
            if not args.treasury_key:
                print("ERROR: Treasury key is required for funding wallets")
                sys.exit(1)
            await fund_wallets(args.treasury_key, args.usdc_amount, args.eth_amount)
        elif args.command == "start":
            await start_bot(args.treasury_key, args.usdc_amount, args.eth_amount)
        elif args.command == "deactivate":
            await deactivate_wallets(args.wallet_count)
        elif args.command == "test-trade":
            await test_trade(args.treasury_key)
        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)
    except Exception as e:
        print(f"Error executing command: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

async def start_bot(treasury_key: str = None, usdc_amount_per_wallet: float = None, eth_amount_per_wallet: float = None) -> None:
    """Start the trading bot."""
    bot = VolumeGeneratorBot()
    
    # Fund wallets if treasury key is provided
    if treasury_key:
        await fund_wallets(treasury_key, usdc_amount_per_wallet, eth_amount_per_wallet)
    
    # Start the bot - no need to wait for user input here
    bot.start_continuous_trading()

if __name__ == "__main__":
    asyncio.run(main()) 