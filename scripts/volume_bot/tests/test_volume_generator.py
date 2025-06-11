"""
Tests for the volume generator module.
"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from scripts.python.volume_bot.volume_generator import (
    VolumeGeneratorBot,
    create_default_config,
    DEFAULT_TOKEN_ABI,
    DEFAULT_ROUTER_ABI
)


class TestVolumeGeneratorBot(unittest.TestCase):
    """Test cases for the VolumeGeneratorBot class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, 'test-config.json')
        
        # Create a minimal test config
        self.test_config = {
            "rpc_url": "https://mainnet.base.org",
            "token_address": "0xfdd6013bf2757018d8c087244f03e5a521b2d3b7",
            "usdc_address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            "router_address": "0x1efeb783d61a3b9788c758abf61a4b3efe7a9a6845644cff3d0ff80eea512876",
            "treasury_address": "0x0a9A62e77326953E5e17948a1A7374dB6eCBB229",
            "trade_interval_min": 1,
            "trade_interval_max": 2,
            "min_trade_size": "0.26",
            "max_trade_size": "4.44",
            "num_trading_wallets": 3,
            "wallets_storage_path": os.path.join(self.temp_dir.name, "trading-wallets.json"),
            "slippage_tolerance": 200,
            "pool_fee": 300,
            "token_abi": DEFAULT_TOKEN_ABI,
            "router_abi": DEFAULT_ROUTER_ABI
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    @patch('scripts.python.volume_bot.volume_generator.Web3')
    @patch('scripts.python.volume_bot.volume_generator.MultiWalletManager')
    def test_initialization(self, mock_wallet_manager, mock_web3):
        """Test bot initialization."""
        # Setup mock wallet manager and web3 instance
        mock_web3_instance = MagicMock()
        mock_web3.return_value = mock_web3_instance
        mock_web3_instance.eth.chain_id = 1337
        mock_web3.to_checksum_address.side_effect = lambda addr: addr
        
        # Create VolumeGeneratorBot instance
        bot = VolumeGeneratorBot(self.config_path)
        
        # Verify Web3 was initialized with the correct provider
        mock_web3.assert_called_once()
        
        # Verify token addresses are set
        self.assertEqual(bot.token_address, self.test_config['token_address'])
        self.assertEqual(bot.usdc_address, self.test_config['usdc_address'])
        self.assertEqual(bot.router_address, self.test_config['router_address'])
        
        # Verify trading parameters
        self.assertEqual(bot.min_trade_size, float(self.test_config['min_trade_size']))
        self.assertEqual(bot.max_trade_size, float(self.test_config['max_trade_size']))
        self.assertEqual(bot.trade_interval_min, self.test_config['trade_interval_min'])
        self.assertEqual(bot.trade_interval_max, self.test_config['trade_interval_max'])
        self.assertEqual(bot.num_trading_wallets, self.test_config['num_trading_wallets'])
        
        # Verify contracts were initialized
        self.assertIsNotNone(bot.token_contract)
        self.assertIsNotNone(bot.usdc_contract)
        self.assertIsNotNone(bot.router_contract)
        
        # Verify initial state
        self.assertFalse(bot.is_running)
        self.assertFalse(bot.stop_requested)
    
    def test_get_random_trade_size(self):
        """Test random trade size generation."""
        # Setup mock Web3 and MultiWalletManager for minimal initialization
        with patch('scripts.python.volume_bot.volume_generator.Web3') as mock_web3, \
             patch('scripts.python.volume_bot.volume_generator.MultiWalletManager'):
            
            mock_web3_instance = MagicMock()
            mock_web3.return_value = mock_web3_instance
            mock_web3.to_checksum_address.side_effect = lambda addr: addr
            
            # Create bot instance
            bot = VolumeGeneratorBot(self.config_path)
            
            # Generate 100 random trade sizes and verify they're within bounds
            for _ in range(100):
                trade_size = bot.get_random_trade_size()
                self.assertGreaterEqual(trade_size, bot.min_trade_size)
                self.assertLessEqual(trade_size, bot.max_trade_size)
    
    def test_get_random_delay(self):
        """Test random delay generation."""
        # Setup mock Web3 and MultiWalletManager for minimal initialization
        with patch('scripts.python.volume_bot.volume_generator.Web3') as mock_web3, \
             patch('scripts.python.volume_bot.volume_generator.MultiWalletManager'):
            
            mock_web3_instance = MagicMock()
            mock_web3.return_value = mock_web3_instance
            mock_web3.to_checksum_address.side_effect = lambda addr: addr
            
            # Create bot instance
            bot = VolumeGeneratorBot(self.config_path)
            
            # Generate 100 random delays and verify they're within bounds
            for _ in range(100):
                delay = bot.get_random_delay()
                self.assertGreaterEqual(delay, bot.trade_interval_min)
                self.assertLessEqual(delay, bot.trade_interval_max)
    
    def test_should_buy(self):
        """Test buy/sell decision logic."""
        # Setup mock Web3 and MultiWalletManager for minimal initialization
        with patch('scripts.python.volume_bot.volume_generator.Web3') as mock_web3, \
             patch('scripts.python.volume_bot.volume_generator.MultiWalletManager'):
            
            mock_web3_instance = MagicMock()
            mock_web3.return_value = mock_web3_instance
            mock_web3.to_checksum_address.side_effect = lambda addr: addr
            
            # Create bot instance
            bot = VolumeGeneratorBot(self.config_path)
            
            # Collect 1000 buy/sell decisions and verify reasonable distribution
            decisions = [bot.should_buy() for _ in range(1000)]
            
            # Count buys (True) and sells (False)
            buy_count = sum(decisions)
            sell_count = len(decisions) - buy_count
            
            # Both should be reasonably close to 50%
            self.assertGreater(buy_count, 400)
            self.assertLess(buy_count, 600)
            self.assertGreater(sell_count, 400)
            self.assertLess(sell_count, 600)
    
    @patch('scripts.python.volume_bot.volume_generator.VolumeGeneratorBot.execute_random_trade')
    @patch('scripts.python.volume_bot.volume_generator.asyncio.sleep')
    async def test_schedule_next_trade(self, mock_sleep, mock_execute_trade):
        """Test trade scheduling logic."""
        # Setup mock Web3 and MultiWalletManager for minimal initialization
        with patch('scripts.python.volume_bot.volume_generator.Web3') as mock_web3, \
             patch('scripts.python.volume_bot.volume_generator.MultiWalletManager'):
            
            mock_web3_instance = MagicMock()
            mock_web3.return_value = mock_web3_instance
            mock_web3.to_checksum_address.side_effect = lambda addr: addr
            
            # Create bot instance
            bot = VolumeGeneratorBot(self.config_path)
            
            # Mock dependencies
            mock_execute_trade.return_value = None
            mock_sleep.return_value = None
            
            # Set up running state and test recursion
            bot.is_running = True
            bot.stop_requested = False
            
            # Force a specific delay for testing
            bot.get_random_delay = MagicMock(return_value=5)
            
            # Schedule the first trade, which should schedule the next one
            await bot.schedule_next_trade()
            
            # Verify sleep and execute_trade were called
            mock_sleep.assert_called_once_with(5 * 60)
            mock_execute_trade.assert_called_once()
            
            # Test stopping
            bot.stop_requested = True
            mock_sleep.reset_mock()
            mock_execute_trade.reset_mock()
            
            await bot.schedule_next_trade()
            
            # Verify sleep was not called and is_running was set to False
            mock_sleep.assert_not_called()
            mock_execute_trade.assert_not_called()
            self.assertFalse(bot.is_running)
    
    def test_create_default_config(self):
        """Test creating a default configuration file."""
        test_config_path = os.path.join(self.temp_dir.name, 'default-config.json')
        
        # Ensure file doesn't exist yet
        self.assertFalse(os.path.exists(test_config_path))
        
        # Create default config
        create_default_config(test_config_path)
        
        # Verify file was created
        self.assertTrue(os.path.exists(test_config_path))
        
        # Read the config and verify essential fields
        with open(test_config_path, 'r') as f:
            config = json.load(f)
            
        # Check required fields are present
        essential_fields = [
            'rpc_url', 'token_address', 'usdc_address', 'router_address',
            'treasury_address', 'min_trade_size', 'max_trade_size', 'token_abi',
            'router_abi'
        ]
        
        for field in essential_fields:
            self.assertIn(field, config)
        
        # Calling again should not overwrite the file
        original_mtime = os.path.getmtime(test_config_path)
        create_default_config(test_config_path)
        new_mtime = os.path.getmtime(test_config_path)
        
        self.assertEqual(original_mtime, new_mtime)


class TestAsyncMethods(unittest.IsolatedAsyncioTestCase):
    """Test async methods of the VolumeGeneratorBot."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, 'test-config.json')
        
        # Create a minimal test config
        self.test_config = {
            "rpc_url": "https://mainnet.base.org",
            "token_address": "0xfdd6013bf2757018d8c087244f03e5a521b2d3b7",
            "usdc_address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            "router_address": "0x1efeb783d61a3b9788c758abf61a4b3efe7a9a6845644cff3d0ff80eea512876",
            "treasury_address": "0x0a9A62e77326953E5e17948a1A7374dB6eCBB229",
            "trade_interval_min": 1,
            "trade_interval_max": 2,
            "min_trade_size": "0.26",
            "max_trade_size": "4.44",
            "num_trading_wallets": 3,
            "wallets_storage_path": os.path.join(self.temp_dir.name, "trading-wallets.json"),
            "slippage_tolerance": 200,
            "pool_fee": 300,
            "token_abi": DEFAULT_TOKEN_ABI,
            "router_abi": DEFAULT_ROUTER_ABI
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    @patch('scripts.python.volume_bot.volume_generator.Web3')
    @patch('scripts.python.volume_bot.volume_generator.MultiWalletManager')
    @patch('scripts.python.volume_bot.volume_generator.VolumeGeneratorBot.execute_random_trade')
    async def test_test_trade(self, mock_execute_trade, mock_wallet_manager, mock_web3):
        """Test executing a test trade."""
        # Setup mock wallet manager and web3 instance
        mock_web3_instance = MagicMock()
        mock_web3.return_value = mock_web3_instance
        mock_web3_instance.eth.chain_id = 1337
        mock_web3.to_checksum_address.side_effect = lambda addr: addr
        
        # Setup wallet manager mock
        mock_wallet_manager_instance = MagicMock()
        mock_wallet_manager.return_value = mock_wallet_manager_instance
        mock_wallet_manager_instance.ensure_wallets = MagicMock()
        mock_wallet_manager_instance.fund_wallets = AsyncMock()
        
        # Mock execute_random_trade
        mock_execute_trade.return_value = None
        
        # Create VolumeGeneratorBot instance
        bot = VolumeGeneratorBot(self.config_path)
        
        # Call test_trade
        await bot.test_trade()
        
        # Verify wallet manager's ensure_wallets was called with 1
        mock_wallet_manager_instance.ensure_wallets.assert_called_once_with(1)
        
        # Verify execute_random_trade was called
        mock_execute_trade.assert_called_once()
    
    @patch('scripts.python.volume_bot.volume_generator.Web3')
    @patch('scripts.python.volume_bot.volume_generator.MultiWalletManager')
    @patch('scripts.python.volume_bot.volume_generator.VolumeGeneratorBot.schedule_next_trade')
    async def test_start(self, mock_schedule_trade, mock_wallet_manager, mock_web3):
        """Test starting the bot."""
        # Setup mock wallet manager and web3 instance
        mock_web3_instance = MagicMock()
        mock_web3.return_value = mock_web3_instance
        mock_web3_instance.eth.chain_id = 1337
        mock_web3.to_checksum_address.side_effect = lambda addr: addr
        
        # Setup wallet manager mock
        mock_wallet_manager_instance = MagicMock()
        mock_wallet_manager.return_value = mock_wallet_manager_instance
        mock_wallet_manager_instance.ensure_wallets = MagicMock()
        mock_wallet_manager_instance.fund_wallets = AsyncMock()
        
        # Mock schedule_next_trade
        mock_schedule_trade.return_value = None
        
        # Create VolumeGeneratorBot instance
        bot = VolumeGeneratorBot(self.config_path)
        
        # Call start
        await bot.start()
        
        # Verify wallet manager's ensure_wallets was called with num_trading_wallets
        mock_wallet_manager_instance.ensure_wallets.assert_called_once_with(bot.num_trading_wallets)
        
        # Verify schedule_next_trade was called
        mock_schedule_trade.assert_called_once()
        
        # Verify running state
        self.assertTrue(bot.is_running)
        self.assertFalse(bot.stop_requested)
    
    def test_stop(self):
        """Test stopping the bot."""
        # Setup mock Web3 and MultiWalletManager for minimal initialization
        with patch('scripts.python.volume_bot.volume_generator.Web3') as mock_web3, \
             patch('scripts.python.volume_bot.volume_generator.MultiWalletManager'):
            
            mock_web3_instance = MagicMock()
            mock_web3.return_value = mock_web3_instance
            mock_web3.to_checksum_address.side_effect = lambda addr: addr
            
            # Create VolumeGeneratorBot instance
            bot = VolumeGeneratorBot(self.config_path)
            
            # Set running state
            bot.is_running = True
            bot.stop_requested = False
            
            # Call stop
            bot.stop()
            
            # Verify stop_requested was set to True
            self.assertTrue(bot.stop_requested)


if __name__ == '__main__':
    unittest.main() 