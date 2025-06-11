"""
Tests for the wallet module.
"""

import os
import json
import tempfile
import unittest
from eth_account import Account
from web3 import Web3

from scripts.python.volume_bot.wallet import Wallet


class TestWallet(unittest.TestCase):
    """Test cases for the Wallet class."""
    
    def setUp(self):
        """Set up test environment."""
        self.private_key = "0x" + "1" * 64  # Simple private key for testing
        self.account = Account.from_key(self.private_key)
        self.wallet = Wallet(private_key=self.private_key)
    
    def test_wallet_initialization(self):
        """Test wallet initialization with private key."""
        self.assertEqual(self.wallet.get_address(), self.account.address)
    
    def test_create_new_wallet(self):
        """Test creating a new wallet."""
        new_wallet_info = Wallet.create_new_wallet()
        self.assertIn('private_key', new_wallet_info)
        self.assertIn('address', new_wallet_info)
        
        # Verify private key format
        self.assertTrue(new_wallet_info['private_key'].startswith('0x'))
        self.assertEqual(len(new_wallet_info['private_key']), 66)  # 0x + 64 hex chars
        
        # Verify address format
        self.assertTrue(Web3.is_checksum_address(new_wallet_info['address']))
    
    def test_keystore_save_load(self):
        """Test saving wallet to keystore and loading it back."""
        # Create a temporary directory for keystore
        with tempfile.TemporaryDirectory() as temp_dir:
            password = "test_password"
            
            # Save to keystore
            keystore_path = self.wallet.save_to_keystore(temp_dir, password)
            self.assertTrue(os.path.exists(keystore_path))
            
            # Verify the keystore is properly formatted
            with open(keystore_path, 'r') as f:
                keystore_json = json.load(f)
                self.assertIn('crypto', keystore_json)
                self.assertIn('ciphertext', keystore_json['crypto'])
            
            # Load from keystore
            loaded_wallet = Wallet(keyfile_path=keystore_path, password=password)
            self.assertEqual(loaded_wallet.get_address(), self.wallet.get_address())
    
    def test_sign_transaction(self):
        """Test transaction signing."""
        transaction = {
            'nonce': 0,
            'gasPrice': 20000000000,
            'gas': 21000,
            'to': '0x' + '2' * 40,
            'value': 1000000000000000000,
            'data': '0x',
            'chainId': 1
        }
        
        signed_tx = self.wallet.sign_transaction(transaction)
        self.assertIsNotNone(signed_tx)
        self.assertTrue(isinstance(signed_tx, bytes))


if __name__ == '__main__':
    unittest.main() 