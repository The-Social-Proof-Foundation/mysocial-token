"""
Multi-wallet manager for handling multiple trading wallets.
"""

import os
import json
from typing import List, Dict, Any, Optional

from web3 import Web3
from web3.types import Wei
from eth_account import Account

from scripts.volume_bot.wallet import Wallet

class MultiWalletManager:
    """Manages multiple trading wallets for the volume bot."""
    
    def __init__(self, wallets_file_path: str):
        """
        Initialize the wallet manager.
        
        Args:
            wallets_file_path: Path to the wallets storage file
        """
        self.wallets_file_path = wallets_file_path
        self.wallets: List[Wallet] = []
        self._load_wallets()
    
    def _load_wallets(self) -> None:
        """Load wallets from storage file."""
        if not os.path.exists(self.wallets_file_path):
            # Create empty wallet file if it doesn't exist
            self._save_wallets([])
            return
        
        try:
            with open(self.wallets_file_path, 'r') as f:
                wallets_data = json.load(f)
                
            self.wallets = []
            for wallet_data in wallets_data:
                if wallet_data.get('active', True):
                    self.wallets.append(Wallet(private_key=wallet_data['private_key']))
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading wallets: {str(e)}")
            self.wallets = []
    
    def _save_wallets(self, wallets_data: List[Dict[str, Any]]) -> None:
        """
        Save wallets to storage file.
        
        Args:
            wallets_data: List of wallet data dictionaries
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(self.wallets_file_path)), exist_ok=True)
        
        with open(self.wallets_file_path, 'w') as f:
            json.dump(wallets_data, f, indent=2)
    
    def get_all_wallets(self) -> List[Wallet]:
        """Get all active wallets."""
        return self.wallets
    
    def get_wallet_data(self) -> List[Dict[str, Any]]:
        """Get data for all wallets including addresses and stats."""
        wallets_data = []
        
        # If file exists, load all data first
        if os.path.exists(self.wallets_file_path):
            try:
                with open(self.wallets_file_path, 'r') as f:
                    wallets_data = json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading wallet data: {str(e)}")
                wallets_data = []
        
        # Update with current wallet data
        current_addresses = [wallet.get_address() for wallet in self.wallets]
        
        # Mark wallets as active/inactive
        for wallet_data in wallets_data:
            wallet_data['active'] = wallet_data['address'] in current_addresses
        
        return wallets_data
    
    def create_wallet(self) -> Wallet:
        """
        Create a new wallet and save it.
        
        Returns:
            The created wallet
        """
        wallet_info = Wallet.create_new_wallet()
        wallet = Wallet(private_key=wallet_info['private_key'])
        
        # Add to memory
        self.wallets.append(wallet)
        
        # Save to storage
        wallets_data = self.get_wallet_data()
        wallets_data.append({
            'address': wallet_info['address'],
            'private_key': wallet_info['private_key'],
            'active': True,
            'stats': {
                'trades': 0,
                'volume': 0
            }
        })
        self._save_wallets(wallets_data)
        
        return wallet
    
    def ensure_wallets(self, count: int) -> List[Wallet]:
        """
        Ensure that at least 'count' wallets exist, creating new ones if needed.
        
        Args:
            count: Required number of wallets
            
        Returns:
            List of wallet instances
        """
        while len(self.wallets) < count:
            self.create_wallet()
        
        return self.wallets[:count]
    
    async def fund_wallets(self, web3: Web3, treasury_key: str, usdc_contract, token_contract, 
                     usdc_amount: Wei, token_amount: Wei) -> None:
        """
        Fund wallets with USDC and tokens from the treasury.
        
        Args:
            web3: Web3 instance
            treasury_key: Treasury private key
            usdc_contract: USDC contract instance
            token_contract: Token contract instance
            usdc_amount: Amount of USDC to fund each wallet with
            token_amount: Amount of tokens to fund each wallet with
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Create a treasury wallet from the key
        # 2. For each wallet, send USDC and tokens
        for wallet in self.wallets:
            print(f"Would fund wallet {wallet.get_address()} with {usdc_amount} USDC and {token_amount} tokens")
    
    def update_wallet_stats(self, address: str, trade_amount_usd: float) -> None:
        """
        Update trading statistics for a wallet.
        
        Args:
            address: Wallet address
            trade_amount_usd: USD value of the trade
        """
        wallets_data = self.get_wallet_data()
        
        # Find and update wallet stats
        for wallet_data in wallets_data:
            if wallet_data['address'].lower() == address.lower():
                if 'stats' not in wallet_data:
                    wallet_data['stats'] = {'trades': 0, 'volume': 0}
                
                wallet_data['stats']['trades'] = wallet_data['stats'].get('trades', 0) + 1
                wallet_data['stats']['volume'] = wallet_data['stats'].get('volume', 0) + trade_amount_usd
                break
        
        self._save_wallets(wallets_data)
    
    def deactivate_wallets(self, count: int) -> List[str]:
        """
        Deactivate the specified number of wallets.
        
        Args:
            count: Number of wallets to deactivate
            
        Returns:
            List of deactivated wallet addresses
        """
        if count >= len(self.wallets):
            deactivated = [w.get_address() for w in self.wallets]
            self.wallets = []
        else:
            deactivated = [w.get_address() for w in self.wallets[-count:]]
            self.wallets = self.wallets[:-count]
        
        # Update storage
        wallets_data = self.get_wallet_data()
        for wallet_data in wallets_data:
            if wallet_data['address'] in deactivated:
                wallet_data['active'] = False
        
        self._save_wallets(wallets_data)
        
        return deactivated 