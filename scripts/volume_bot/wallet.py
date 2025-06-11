"""
Wallet module for the volume bot.

This module provides a wallet interface for Ethereum transactions.
"""

import os
import json
from typing import Dict, Optional, Union, Any

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from web3 import Web3

class Wallet:
    """Ethereum wallet for signing transactions."""
    
    def __init__(self, private_key: Optional[str] = None, keyfile_path: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize wallet with either a private key or keystore file.
        
        Args:
            private_key: Private key as hex string (with or without 0x prefix)
            keyfile_path: Path to keystore file
            password: Password for keystore file
        """
        if private_key:
            # Ensure private key has 0x prefix
            if not private_key.startswith('0x'):
                private_key = f"0x{private_key}"
            self.account = Account.from_key(private_key)
        elif keyfile_path and password:
            with open(keyfile_path, 'r') as keyfile:
                encrypted_key = keyfile.read()
                self.account = Account.from_key(Account.decrypt(encrypted_key, password))
        else:
            raise ValueError("Either private_key or (keyfile_path and password) must be provided")
    
    def get_address(self) -> str:
        """Get the wallet's public address."""
        return self.account.address
    
    def sign_transaction(self, transaction: Dict) -> bytes:
        """
        Sign an Ethereum transaction.
        
        Args:
            transaction: Transaction dict with nonce, gas_price, gas, to, value, data fields
        
        Returns:
            Signed transaction as hex string
        """
        signed_tx = self.account.sign_transaction(transaction)
        return signed_tx.raw_transaction
    
    def save_to_keystore(self, directory: str, password: str) -> str:
        """
        Save wallet to keystore file.
        
        Args:
            directory: Directory to save keystore file
            password: Password to encrypt keystore file
            
        Returns:
            Path to saved keystore file
        """
        os.makedirs(directory, exist_ok=True)
        
        encrypted_key = Account.encrypt(self.account.key, password)
        keystore_filename = f"UTC--{self.get_address()}"
        keystore_path = os.path.join(directory, keystore_filename)
        
        with open(keystore_path, 'w') as keyfile:
            keyfile.write(json.dumps(encrypted_key))
        
        return keystore_path
    
    @staticmethod
    def create_new_wallet() -> Dict[str, str]:
        """
        Create a new random wallet.
        
        Returns:
            Dict with private_key and address
        """
        account = Account.create()
        return {
            'private_key': '0x' + account.key.hex(),
            'address': account.address
        }
