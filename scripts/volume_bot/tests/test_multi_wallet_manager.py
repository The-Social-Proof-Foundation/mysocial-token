"""
Tests for the multi wallet manager module.
"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from web3 import Web3

from scripts.python.volume_bot.multi_wallet_manager import MultiWalletManager


class TestMultiWalletManager(unittest.TestCase):
    """Test cases for the MultiWalletManager class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock Web3 provider
        self.w3 = MagicMock()
        self.w3.eth.chain_id = 1
        
        # Create a temporary file for wallet storage
        self.temp_dir = tempfile.TemporaryDirectory()
        self.wallets_file_path = os.path.join(self.temp_dir.name, 'test-wallets.json')
        
        # Sample treasury address
        self.treasury_address = "0x0a9A62e77326953E5e17948a1A7374dB6eCBB229"
        
        # Create wallet manager
        self.wallet_manager = MultiWalletManager(
            provider=self.w3,
            wallets_file_path=self.wallets_file_path,
            treasury_address=self.treasury_address
        )
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_create_wallet(self):
        """Test creating a new wallet."""
        # Check initial state
        self.assertEqual(len(self.wallet_manager.wallets), 0)
        
        # Create a wallet
        new_wallet = self.wallet_manager.create_wallet()
        
        # Verify wallet was created and saved
        self.assertEqual(len(self.wallet_manager.wallets), 1)
        self.assertTrue(os.path.exists(self.wallets_file_path))
        
        # Verify wallet properties
        self.assertIn('address', new_wallet)
        self.assertIn('private_key', new_wallet)
        self.assertIn('active', new_wallet)
        self.assertTrue(new_wallet['active'])
        self.assertIn('stats', new_wallet)
        self.assertEqual(new_wallet['stats']['buys'], 0)
        self.assertEqual(new_wallet['stats']['sells'], 0)
        
        # Verify the wallet was saved to file
        with open(self.wallets_file_path, 'r') as f:
            saved_wallets = json.load(f)
            self.assertEqual(len(saved_wallets), 1)
            self.assertEqual(saved_wallets[0]['address'], new_wallet['address'])
    
    def test_ensure_wallets(self):
        """Test ensuring a certain number of wallets exist."""
        # Initial state
        self.assertEqual(len(self.wallet_manager.wallets), 0)
        
        # Ensure 3 wallets
        self.wallet_manager.ensure_wallets(3)
        
        # Verify 3 wallets were created
        self.assertEqual(len(self.wallet_manager.wallets), 3)
        
        # Ensure 5 wallets (should add 2 more)
        self.wallet_manager.ensure_wallets(5)
        
        # Verify we now have 5 wallets
        self.assertEqual(len(self.wallet_manager.wallets), 5)
        
        # Ensure 2 wallets (should not remove any)
        self.wallet_manager.ensure_wallets(2)
        
        # Verify we still have 5 wallets
        self.assertEqual(len(self.wallet_manager.wallets), 5)
    
    def test_get_active_wallets(self):
        """Test getting active wallets."""
        # Create 3 wallets
        for _ in range(3):
            self.wallet_manager.create_wallet()
        
        # All wallets should be active
        active_wallets = self.wallet_manager.get_active_wallets()
        self.assertEqual(len(active_wallets), 3)
        
        # Deactivate one wallet
        self.wallet_manager.wallets[0]['active'] = False
        self.wallet_manager.save_wallets()
        
        # Should have 2 active wallets now
        active_wallets = self.wallet_manager.get_active_wallets()
        self.assertEqual(len(active_wallets), 2)
    
    def test_deactivate_wallets(self):
        """Test deactivating wallets."""
        # Create 5 wallets
        for _ in range(5):
            self.wallet_manager.create_wallet()
        
        # All wallets should be active
        self.assertEqual(len(self.wallet_manager.get_active_wallets()), 5)
        
        # Deactivate 2 wallets
        self.wallet_manager.deactivate_wallets(2)
        
        # Should have 3 active wallets now
        self.assertEqual(len(self.wallet_manager.get_active_wallets()), 3)
        
        # Verify the first 2 wallets were deactivated
        self.assertFalse(self.wallet_manager.wallets[0]['active'])
        self.assertFalse(self.wallet_manager.wallets[1]['active'])
        self.assertTrue(self.wallet_manager.wallets[2]['active'])
        
        # Try to deactivate more than we have active
        self.wallet_manager.deactivate_wallets(10)
        
        # All wallets should be deactivated now
        self.assertEqual(len(self.wallet_manager.get_active_wallets()), 0)
    
    def test_update_wallet_stats(self):
        """Test updating wallet statistics."""
        # Create a wallet
        wallet = self.wallet_manager.create_wallet()
        address = wallet['address']
        
        # Initial stats
        self.assertEqual(wallet['stats']['buys'], 0)
        self.assertEqual(wallet['stats']['sells'], 0)
        self.assertEqual(wallet['stats']['profit'], '0')
        self.assertEqual(wallet['stats']['volume'], '0')
        
        # Update stats for a buy
        self.wallet_manager.update_wallet_stats(address, True, 1000000000000000000, 0)
        
        # Verify stats were updated
        updated_wallet = next(w for w in self.wallet_manager.wallets if w['address'] == address)
        self.assertEqual(updated_wallet['stats']['buys'], 1)
        self.assertEqual(updated_wallet['stats']['sells'], 0)
        self.assertEqual(updated_wallet['stats']['profit'], '0')
        self.assertEqual(updated_wallet['stats']['volume'], '1.0')
        
        # Update stats for a sell with profit
        self.wallet_manager.update_wallet_stats(address, False, 2000000000000000000, 100000000000000000)
        
        # Verify stats were updated
        updated_wallet = next(w for w in self.wallet_manager.wallets if w['address'] == address)
        self.assertEqual(updated_wallet['stats']['buys'], 1)
        self.assertEqual(updated_wallet['stats']['sells'], 1)
        self.assertEqual(updated_wallet['stats']['profit'], '0.1')
        self.assertEqual(updated_wallet['stats']['volume'], '3.0')
    
    @patch('scripts.python.volume_bot.multi_wallet_manager.Wallet')
    async def test_fund_wallets(self, mock_wallet_class):
        """Test funding wallets with ETH and tokens."""
        # Skip this test for now as it requires more complex mocking of async methods
        pass


if __name__ == '__main__':
    unittest.main() 