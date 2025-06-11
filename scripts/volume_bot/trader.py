"""
Trader module for the volume trading bot.
Handles DEX interactions and trading operations.
"""

from typing import Dict, List, Optional, Tuple, Union
import time
import logging
from decimal import Decimal
import json

from web3 import Web3
from web3.contract import Contract
from web3.types import TxParams, Wei
from eth_account import Account
from eth_typing import Address

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VolumeTrader")

# Common ABI snippets for ERC20 and Uniswap interactions
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"}
]

# Token name mapping for common tokens
TOKEN_SYMBOLS = {
    "0xfdd6013bf2757018d8c087244f03e5a521b2d3b7": "MYSO",
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC",
    "0x4200000000000000000000000000000000000006": "WETH"
}

# Uniswap Universal Router ABI with V3 compatibility
UNISWAP_V4_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "bytes", "name": "commands", "type": "bytes"},
            {"internalType": "bytes[]", "name": "inputs", "type": "bytes[]"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "execute",
        "outputs": [{"internalType": "bytes[]", "name": "", "type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "approveMax",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"}
        ],
        "name": "getApprovalType",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "internalType": "struct ISwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    }
]

# For V3 Router compatibility - Swap Router 02 exact ABI for direct exactInputSingle
SWAP_ROUTER_V3_ABI = [{
    "inputs": [
        {
            "components": [
                {"internalType": "address", "name": "tokenIn", "type": "address"},
                {"internalType": "address", "name": "tokenOut", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                {"internalType": "address", "name": "recipient", "type": "address"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
            ],
            "internalType": "struct ISwapRouter.ExactInputSingleParams",
            "name": "params",
            "type": "tuple"
        }
    ],
    "name": "exactInputSingle",
    "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
    "stateMutability": "payable",
    "type": "function"
}]

# Fixed Uniswap V3 SwapRouter02 address for Base
UNISWAP_V3_ROUTER_ADDRESS = "0x2626664c2603336E57B271c5C0b26F421741e481"

# Add UniswapV3 Factory contract address and ABI
UNISWAP_V3_FACTORY_ADDRESS = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"  # Base Mainnet V3 Factory

UNISWAP_V3_FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"}
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class Trader:
    def __init__(self, w3: Web3, wallet, router_address: str, router_abi: list):
        """
        Initialize a trader for DEX operations.
        
        Args:
            w3: Web3 instance
            wallet: Wallet instance for signing transactions
            router_address: DEX router contract address
            router_abi: Router contract ABI
        """
        self.w3 = w3
        self.wallet = wallet
        self.router_address = Web3.to_checksum_address(router_address)
        
        # Try to detect which router version we're using based on the contract code
        self.router_version = self._detect_router_version()
        if self.router_version == 3:
            logger.info(f"Detected Uniswap V3 router at {self.router_address}")
            self.router = w3.eth.contract(address=self.router_address, abi=SWAP_ROUTER_V3_ABI)
        else:
            logger.info(f"Using Uniswap V4/Universal router at {self.router_address}")
            self.router = w3.eth.contract(address=self.router_address, abi=router_abi)
        
        # Initialize Uniswap V3 Factory contract
        self.factory = w3.eth.contract(
            address=Web3.to_checksum_address(UNISWAP_V3_FACTORY_ADDRESS), 
            abi=UNISWAP_V3_FACTORY_ABI
        )
        
        self.token_contracts: Dict[str, Contract] = {}
        self.gas_multiplier = 1.5  # 50% buffer for gas estimation
        self.max_gas_price = Web3.to_wei(100, 'gwei')  # Maximum gas price
        
        # Store ETH address for convenience
        self.eth_address = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")  # WETH on Base
        
        logger.info(f"Initialized trader with router address: {self.router_address}")
    
    def _detect_router_version(self) -> int:
        """
        Try to detect which router version we're using by checking the contract address.
        Returns:
            int: 3 for V3 router, 4 for V4/Universal router
        """
        try:
            # For Base, SwapRouter02 is hardcoded to a fixed address
            if self.router_address.lower() == "0x2626664c2603336e57b271c5c0b26f421741e481":
                logger.info(f"Detected Uniswap V3 SwapRouter02 at {self.router_address}")
                return 3
                
            # Universal Router can be detected by its bytecode
            code = self.w3.eth.get_code(self.router_address).hex()
            
            if "execute" in code and "0x42712a67" in code:  # Universal Router V4 signature
                return 4
                
            # Default to V3 for all other cases
            return 3
        except Exception as e:
            logger.warning(f"Error detecting router version: {e}. Defaulting to V3")
            return 3
        
    def get_token_contract(self, token_address: str) -> Contract:
        """Get a token contract instance, caching for efficiency."""
        token_address = Web3.to_checksum_address(token_address)
        if token_address not in self.token_contracts:
            self.token_contracts[token_address] = self.w3.eth.contract(
                address=token_address, 
                abi=ERC20_ABI
            )
        return self.token_contracts[token_address]
    
    def get_token_balance(self, token_address: str) -> Tuple[int, int]:
        """
        Get token balance and decimals.
        
        Args:
            token_address: Address of the token
            
        Returns:
            Tuple of (balance_in_wei, decimals)
        """
        token = self.get_token_contract(token_address)
        balance = token.functions.balanceOf(self.wallet.get_address()).call()
        decimals = token.functions.decimals().call()
        return balance, decimals
    
    def get_token_allowance(self, token_address: str, spender: str) -> int:
        """
        Get token allowance for a spender.
        
        Args:
            token_address: Address of the token
            spender: Address of the spender
            
        Returns:
            Allowance amount in wei
        """
        token = self.get_token_contract(token_address)
        return token.functions.allowance(
            self.wallet.get_address(), 
            Web3.to_checksum_address(spender)
        ).call()
    
    def get_token_symbol(self, token_address: str) -> str:
        """
        Get token symbol with fallback to hardcoded values.
        
        Args:
            token_address: Address of the token
            
        Returns:
            Token symbol string
        """
        token_address_lower = token_address.lower()
        
        # First try hardcoded symbols
        if token_address_lower in TOKEN_SYMBOLS:
            return TOKEN_SYMBOLS[token_address_lower]
            
        # Then try to get from contract
        try:
            token = self.get_token_contract(token_address)
            return token.functions.symbol().call()
        except Exception as e:
            # Return address truncated if we can't get symbol
            return f"{token_address[:6]}...{token_address[-4:]}"
    
    def approve_token(self, token_address: str, spender: str, amount: int = 2**256-1, retry_after_eth_swap=False) -> str:
        """
        Approve token spending.
        
        Args:
            token_address: Address of the token
            spender: Address of the spender
            amount: Amount to approve (default: unlimited)
            retry_after_eth_swap: Whether this is a retry after swapping USDC for ETH
            
        Returns:
            Transaction hash
        """
        token = self.get_token_contract(token_address)
        spender = Web3.to_checksum_address(spender)
        
        # Check current allowance first - avoid unnecessary approvals
        allowance = self.get_token_allowance(token_address, spender)
        if allowance >= amount:
            logger.info(f"Token {self.get_token_symbol(token_address)} already approved for {spender}, allowance: {allowance}")
            return "0x0"  # Return a dummy hash since no transaction was needed
        
        logger.info(f"Approving {self.get_token_symbol(token_address)} for {spender}")
        
        # Get current nonce and gas price with 20% boost to avoid replacement transaction error
        nonce = self.w3.eth.get_transaction_count(self.wallet.get_address())
        gas_price = int(self.w3.eth.gas_price * 1.2)  # 20% higher gas price
        
        tx = token.functions.approve(spender, amount).build_transaction({
            'from': self.wallet.get_address(),
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': gas_price
        })
        
        signed_tx = self.wallet.sign_transaction(tx)
        
        # Send the transaction with ETH funding check
        try:
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx)
            
            # Wait for the approval to be confirmed before proceeding
            try:
                logger.info(f"Waiting for approval transaction to be mined...")
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                if receipt.status == 1:
                    logger.info(f"Approval transaction confirmed: {self.w3.to_hex(tx_hash)}")
                else:
                    logger.error(f"Approval transaction failed: {self.w3.to_hex(tx_hash)}")
            except Exception as e:
                logger.warning(f"Error waiting for approval: {e}")
            
            return self.w3.to_hex(tx_hash)
            
        except Exception as e:
            error_str = str(e)
            # Check for insufficient ETH error
            if "insufficient funds for gas * price + value" in error_str and not retry_after_eth_swap:
                logger.warning(f"Insufficient ETH for approval gas: {error_str}")
                
                # Only attempt to swap for ETH if we have USDC and we're not already retrying
                usdc_address = Web3.to_checksum_address("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")
                
                # Don't try to swap USDC if we're already trying to approve USDC - that would create a circular dependency
                if token_address.lower() == usdc_address.lower():
                    logger.error("Cannot swap USDC for ETH because we don't have ETH to approve USDC")
                    raise ValueError("Need ETH to fund initial transaction. Please fund wallet with some ETH first.")
                
                usdc_balance, _ = self.get_token_balance(usdc_address)
                
                if usdc_balance > 0:
                    logger.info("Attempting to swap some USDC for ETH to cover approval gas fees")
                    eth_swap_tx = self.swap_usdc_for_eth()
                    
                    if eth_swap_tx:
                        logger.info(f"Successfully swapped USDC for ETH. Now retrying token approval")
                        # Wait a moment for the blockchain to update
                        time.sleep(3)
                        # Retry the approval with a fresh nonce, but prevent infinite recursion
                        return self.approve_token(token_address, spender, amount, True)
                else:
                    logger.error("Not enough USDC to swap for ETH")
            
            # Re-raise the exception if we couldn't handle it
            raise
    
    def estimate_gas(self, function, from_address, value=None) -> int:
        """
        Estimate gas for a transaction with safety margin.
        
        Args:
            function: Contract function to call
            from_address: Address sending the transaction
            value: ETH value to send (for payable functions)
            
        Returns:
            Gas limit with safety margin
        """
        try:
            # Setup transaction parameters for estimation
            tx_params = {'from': from_address}
            if value is not None:
                tx_params['value'] = value
                
            # Estimate gas
            gas_estimate = function.estimate_gas(tx_params)
            
            # Apply multiplier for safety margin
            return int(gas_estimate * self.gas_multiplier)
            
        except Exception as e:
            # If estimation fails, use a conservative default
            logger.warning(f"Gas estimation failed: {str(e)}. Using default gas limit.")
            return 500000  # Conservative default
    
    def get_gas_price(self) -> int:
        """
        Get current gas price with cap.
        
        Returns:
            Gas price in wei, capped at max_gas_price
        """
        try:
            current_gas_price = self.w3.eth.gas_price
            return min(current_gas_price, self.max_gas_price)
        except Exception as e:
            logger.warning(f"Error getting gas price: {str(e)}. Using default.")
            return self.max_gas_price
    
    def check_pool_exists(self, token_a: str, token_b: str, fee: int) -> bool:
        """
        Check if a Uniswap V3 pool exists for the given token pair and fee tier.
        
        Args:
            token_a: First token address
            token_b: Second token address
            fee: Fee tier (500, 3000, 10000)
            
        Returns:
            True if pool exists, False otherwise
        """
        try:
            # Always use 3000 (0.3%) fee tier
            fee = 3000
            
            # Ensure tokens are in the correct order (lower address first)
            if int(token_a, 16) > int(token_b, 16):
                token_a, token_b = token_b, token_a
                
            # Get pool address
            pool_address = self.factory.functions.getPool(token_a, token_b, fee).call()
            
            # Check if pool exists (address is not zero)
            pool_exists = pool_address != "0x0000000000000000000000000000000000000000"
            
            if pool_exists:
                logger.info(f"Found pool at {pool_address} for {token_a}-{token_b} with fee {fee}")
            else:
                logger.warning(f"No pool found for {token_a}-{token_b} with fee {fee}")
                
            return pool_exists
        except Exception as e:
            logger.error(f"Error checking pool existence: {e}")
            return False
            
    def swap_usdc_for_eth(self, retry_count=0):
        """
        Swap a small amount of USDC for ETH to cover gas fees
        
        Returns:
            Transaction hash if successful, None if failed
        """
        if retry_count >= 2:
            logger.error("Failed to swap USDC for ETH after multiple attempts")
            return None
            
        try:
            # Get USDC contract and balance
            usdc_address = Web3.to_checksum_address("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")
            usdc_contract = self.get_token_contract(usdc_address)
            usdc_balance, usdc_decimals = self.get_token_balance(usdc_address)
            
            # Check if we have any USDC
            if usdc_balance <= 0:
                logger.warning("No USDC available to swap for ETH")
                return None
                
            # Calculate how much USDC to swap - either 0.1 USDC or 20% of balance, whichever is less
            swap_amount = min(int(0.1 * (10**usdc_decimals)), int(usdc_balance * 0.2))
            
            if swap_amount <= 0:
                logger.warning("Calculated swap amount is too small")
                return None
                
            logger.info(f"Attempting to swap {swap_amount / (10**usdc_decimals):.4f} USDC for native ETH to cover gas")
            
            # Check current ETH balance
            eth_balance_before = self.w3.eth.get_balance(self.wallet.get_address())
            
            # Check and approve USDC if needed - using a lower gas price for this transaction
            allowance = self.get_token_allowance(usdc_address, self.router_address)
            if allowance < swap_amount:
                # Use a lower gas price for the approval
                gas_price = int(self.w3.eth.gas_price * 0.8)  # 80% of current gas price
                
                # Use minimal gas for approval
                nonce = self.w3.eth.get_transaction_count(self.wallet.get_address())
                tx = usdc_contract.functions.approve(self.router_address, swap_amount * 2).build_transaction({
                    'from': self.wallet.get_address(),
                    'nonce': nonce,
                    'gas': 100000,
                    'gasPrice': gas_price
                })
                
                signed_tx = self.wallet.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx)
                
                # Wait for the approval with a short timeout
                try:
                    self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
                except Exception as e:
                    logger.warning(f"Approval transaction may not have confirmed: {e}")
            
            # Use lower gas price and gas limit
            gas_price = int(self.w3.eth.gas_price * 0.8)  # 80% of current gas price
            
            # Use a very small minAmountOut for ETH
            amount_out_min = 1  # Almost no minimum to ensure the swap succeeds
            
            # Prepare the swap transaction with minimal gas
            nonce = self.w3.eth.get_transaction_count(self.wallet.get_address())
            
            # Use V3 router for the swap - Using SwapRouter02 which supports unwrapping WETH to ETH
            # For SwapRouter02, we need to use exactInputSingle with recipient as our address
            # and a special path that includes unwrapping WETH to ETH
            
            # Get WETH address - we'll swap to WETH first and the router will unwrap it to ETH
            weth_address = self.eth_address  # WETH on Base
            
            # Special parameter to unwrap WETH to ETH - uses the exactInputSingle with unwrapWETH9 flag
            # The Base SwapRouter02 ABI doesn't include the unwrapWETH method directly, but it's
            # accessible through the exactInputSingle by setting specific parameters
            
            # Create contract with the V3 SwapRouter02 ABI that includes the unwrap method
            swap_router_abi = [
                {
                    "inputs": [
                        {
                            "components": [
                                {"internalType": "address", "name": "tokenIn", "type": "address"},
                                {"internalType": "address", "name": "tokenOut", "type": "address"},
                                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                                {"internalType": "address", "name": "recipient", "type": "address"},
                                {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                                {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                                {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                            ],
                            "internalType": "struct ISwapRouter.ExactInputSingleParams",
                            "name": "params",
                            "type": "tuple"
                        }
                    ],
                    "name": "exactInputSingle",
                    "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                    "stateMutability": "payable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amountMinimum", "type": "uint256"},
                        {"internalType": "address", "name": "recipient", "type": "address"}
                    ],
                    "name": "unwrapWETH9",
                    "outputs": [],
                    "stateMutability": "payable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amountMinimum", "type": "uint256"},
                        {"internalType": "address", "name": "recipient", "type": "address"},
                        {"internalType": "uint256", "name": "feeBips", "type": "uint256"},
                        {"internalType": "address", "name": "feeRecipient", "type": "address"}
                    ],
                    "name": "unwrapWETH9WithFee",
                    "outputs": [],
                    "stateMutability": "payable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"internalType": "address", "name": "token", "type": "address"},
                        {"internalType": "uint256", "name": "value", "type": "uint256"},
                        {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                        {"internalType": "uint8", "name": "v", "type": "uint8"},
                        {"internalType": "bytes32", "name": "r", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "s", "type": "bytes32"}
                    ],
                    "name": "selfPermit",
                    "outputs": [],
                    "stateMutability": "payable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"internalType": "address", "name": "token", "type": "address"},
                        {"internalType": "uint256", "name": "amountMinimum", "type": "uint256"},
                        {"internalType": "address", "name": "recipient", "type": "address"}
                    ],
                    "name": "sweepToken",
                    "outputs": [],
                    "stateMutability": "payable",
                    "type": "function"
                }
            ]
            
            router = self.w3.eth.contract(address=self.router_address, abi=swap_router_abi)
            
            # We need to execute two operations:
            # 1. Swap USDC to WETH
            # 2. Unwrap WETH to ETH
            
            # First, swap USDC to WETH
            deadline = int(time.time() + 60)  # 60 seconds from now
            
            # Method 1: Use multicall to do both operations in one transaction (swap and unwrap)
            # This is more complex but more efficient
            
            # On Base, the easiest approach is to:
            # 1. Swap USDC for WETH first
            tx = router.functions.exactInputSingle({
                'tokenIn': usdc_address,
                'tokenOut': weth_address,
                'fee': 3000,  # 0.3% fee
                'recipient': self.wallet.get_address(),  # First receive WETH to our address
                'deadline': deadline,
                'amountIn': swap_amount,
                'amountOutMinimum': amount_out_min,
                'sqrtPriceLimitX96': 0  # No price limit
            }).build_transaction({
                'from': self.wallet.get_address(),
                'gas': 300000,  # Reduced gas limit
                'gasPrice': gas_price,
                'nonce': nonce,
                'value': 0,
                'chainId': 8453  # Base chain ID
            })
            
            # Sign and send transaction
            signed_tx = self.wallet.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx)
            logger.info(f"USDC to WETH swap transaction sent: {self.w3.to_hex(tx_hash)}")
            
            # Wait for confirmation with timeout
            try:
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                
                if receipt.status == 1:
                    logger.info(f"USDC to WETH swap succeeded, now unwrapping WETH to ETH")
                    
                    # Get current WETH balance
                    weth_contract = self.get_token_contract(weth_address)
                    weth_balance = weth_contract.functions.balanceOf(self.wallet.get_address()).call()
                    
                    if weth_balance > 0:
                        # Now unwrap WETH to ETH - this requires using the WETH contract directly
                        weth_abi = [
                            {
                                "constant": False,
                                "inputs": [{"name": "wad", "type": "uint256"}],
                                "name": "withdraw",
                                "outputs": [],
                                "payable": False,
                                "stateMutability": "nonpayable",
                                "type": "function"
                            }
                        ]
                        
                        weth_contract = self.w3.eth.contract(address=weth_address, abi=weth_abi)
                        
                        # Build unwrap transaction
                        nonce = self.w3.eth.get_transaction_count(self.wallet.get_address())
                        unwrap_tx = weth_contract.functions.withdraw(weth_balance).build_transaction({
                            'from': self.wallet.get_address(),
                            'gas': 100000,  # Lower gas for unwrap
                            'gasPrice': gas_price,
                            'nonce': nonce,
                            'chainId': 8453  # Base chain ID
                        })
                        
                        # Sign and send transaction
                        signed_unwrap_tx = self.wallet.sign_transaction(unwrap_tx)
                        unwrap_tx_hash = self.w3.eth.send_raw_transaction(signed_unwrap_tx)
                        logger.info(f"Unwrapping WETH to ETH: {self.w3.to_hex(unwrap_tx_hash)}")
                        
                        # Wait for unwrap to complete
                        try:
                            unwrap_receipt = self.w3.eth.wait_for_transaction_receipt(unwrap_tx_hash, timeout=60)
                            
                            if unwrap_receipt.status == 1:
                                # Check if ETH balance increased
                                eth_balance_after = self.w3.eth.get_balance(self.wallet.get_address())
                                if eth_balance_after > eth_balance_before:
                                    eth_gained = eth_balance_after - eth_balance_before
                                    logger.info(f"Successfully unwrapped WETH to {self.w3.from_wei(eth_gained, 'ether')} ETH")
                                    return self.w3.to_hex(unwrap_tx_hash)
                                else:
                                    logger.warning("Unwrap succeeded but ETH balance didn't increase")
                                    return self.w3.to_hex(unwrap_tx_hash)
                            else:
                                logger.error(f"Failed to unwrap WETH to ETH")
                                return None
                        except Exception as e:
                            logger.error(f"Error unwrapping WETH: {e}")
                            return self.w3.to_hex(tx_hash)  # Return the swap tx hash at least
                    else:
                        logger.warning("No WETH received from swap")
                        # Still consider it a partial success since we got through the first transaction
                        return self.w3.to_hex(tx_hash)
                else:
                    logger.error(f"USDC to WETH swap failed. Status: {receipt.status}")
                    return None
            except Exception as e:
                logger.warning(f"Error waiting for USDC to WETH swap: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error in USDC to ETH swap: {e}")
            # Try again with slightly different parameters
            return self.swap_usdc_for_eth(retry_count + 1)
    
    def swap_tokens_for_tokens(self, token_in: str, token_out: str, amount_in: int, pool_key: dict, retry_after_eth_swap=False) -> str:
        """
        Swap tokens using Uniswap router
        
        Args:
            token_in: Address of input token
            token_out: Address of output token
            amount_in: Amount of input token to swap
            pool_key: Dictionary containing pool parameters
            retry_after_eth_swap: Whether this is a retry after swapping USDC for ETH
            
        Returns:
            Transaction hash
        """
        token_in = Web3.to_checksum_address(token_in)
        token_out = Web3.to_checksum_address(token_out)
        
        # Log transaction details
        logger.info(f"Preparing swap: {token_in} -> {token_out} for {amount_in}")
        
        # Get token names for better logging
        token_in_symbol = self.get_token_symbol(token_in)
        token_out_symbol = self.get_token_symbol(token_out)
        logger.info(f"Swapping {token_in_symbol} for {token_out_symbol}")
        
        # Make sure pool exists with fee=3000 (0.3%)
        fee = 3000
        if not self.check_pool_exists(token_in, token_out, fee):
            raise ValueError(f"No liquidity pool found for {token_in_symbol}-{token_out_symbol}")
            
        # Check allowance and approve if needed
        allowance = self.get_token_allowance(token_in, self.router_address)
        logger.info(f"Current allowance: {allowance}, Required: {amount_in}")
        
        if allowance < amount_in:
            logger.info(f"Approving {token_in_symbol} for router usage")
            approve_tx = self.approve_token(token_in, self.router_address)
            
            if approve_tx != "0x0":
                logger.info(f"Approval transaction: {approve_tx}")
                # Wait for approval to be mined
                time.sleep(5)
                
                # Verify allowance after approval
                new_allowance = self.get_token_allowance(token_in, self.router_address)
                logger.info(f"New allowance after approval: {new_allowance}")
                
                if new_allowance < amount_in:
                    raise ValueError(f"Approval failed - allowance {new_allowance} still below required {amount_in}")
        else:
            logger.info(f"{token_in_symbol} already approved for router")
            
        # Set slippage tolerance based on token being sold
        if token_in_symbol == "MYSO" and token_out_symbol == "USDC":
            # For MYSO to USDC swaps, calculate a reasonable minAmountOut considering decimal differences
            # MYSO has 18 decimals, USDC has 6 decimals - need to account for 12 decimal places difference
            decimal_difference = 12  # 18 - 6
            # Set minimum output to 0.001 USDC (1000 in USDC's 6 decimals)
            amount_out_min = 1000  # 0.001 USDC with 6 decimals
            logger.info(f"Using fixed minAmountOut: {amount_out_min} (0.001 USDC min output for MYSO sell)")
        else:
            # Standard slippage for other swaps
            amount_out_min = int(amount_in * 0.2)  # 80% slippage
            logger.info(f"Using minAmountOut: {amount_out_min} (80% slippage)")
        
        try:
            # Get the most recent nonce
            nonce = self.w3.eth.get_transaction_count(self.wallet.get_address())
            logger.info(f"Using nonce: {nonce}")
            
            # Get current gas price with 40% buffer
            gas_price = int(self.w3.eth.gas_price * 1.4)
            logger.info(f"Using gas price: {gas_price} wei")
            
            # Create proper contract with SwapRouter ABI
            router = self.w3.eth.contract(address=self.router_address, abi=SWAP_ROUTER_V3_ABI)
            
            # Build the transaction
            tx = router.functions.exactInputSingle({
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': fee,
                'recipient': self.wallet.get_address(),
                'amountIn': amount_in,
                'amountOutMinimum': amount_out_min,
                'sqrtPriceLimitX96': 0  # No price limit
            }).build_transaction({
                'from': self.wallet.get_address(),
                'gas': 500000,  # Use higher gas limit for safety
                'gasPrice': gas_price,
                'nonce': nonce,
                'value': 0,  # No ETH being sent
                'chainId': 8453  # Base chain ID
            })
            
            # Log transaction data for debugging
            logger.info(f"Transaction input data: {tx['data'][:66]}...")
            
            # Sign and send the transaction
            signed_tx = self.wallet.sign_transaction(tx)
            
            try:
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx)
                logger.info(f"Transaction sent: {self.w3.to_hex(tx_hash)}")
                
                # Wait for transaction confirmation
                logger.info("Waiting for transaction confirmation...")
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
                
                # Check transaction status
                if receipt.status == 1:
                    logger.info(f"✅ Transaction successful! Gas used: {receipt.gasUsed}")
                    return self.w3.to_hex(tx_hash)
                else:
                    logger.error(f"❌ Transaction failed on-chain. Status: {receipt.status}")
                    logger.error(f"Transaction hash: {self.w3.to_hex(tx_hash)}")
                    
                    # Try to get error reason
                    try:
                        # Replay transaction to get error
                        self.w3.eth.call({
                            'from': self.wallet.get_address(),
                            'to': self.router_address,
                            'data': tx['data'],
                            'gas': 500000,
                            'gasPrice': gas_price,
                            'value': 0,
                        }, receipt.blockNumber)
                    except Exception as e:
                        logger.error(f"Revert reason: {str(e)}")
                    
                    return self.w3.to_hex(tx_hash)
            except Exception as e:
                error_str = str(e)
                # Check for insufficient ETH error
                if "insufficient funds for gas * price + value" in error_str and not retry_after_eth_swap:
                    logger.warning(f"Insufficient ETH for gas: {error_str}")
                    
                    # Only attempt to swap for ETH if we have USDC
                    usdc_address = Web3.to_checksum_address("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")
                    usdc_balance, _ = self.get_token_balance(usdc_address)
                    
                    if usdc_balance > 0:
                        logger.info("Attempting to swap some USDC for ETH to cover gas fees")
                        eth_swap_tx = self.swap_usdc_for_eth()
                        
                        if eth_swap_tx:
                            logger.info(f"Successfully swapped USDC for ETH. Now retrying original transaction")
                            # Wait a moment for the blockchain to update
                            time.sleep(3)
                            # Retry the original swap with a fresh nonce, but prevent infinite recursion
                            return self.swap_tokens_for_tokens(token_in, token_out, amount_in, pool_key, True)
                    else:
                        logger.error("Not enough USDC to swap for ETH")
                
                # Re-raise other errors
                raise
                
        except Exception as e:
            logger.error(f"Error executing swap: {str(e)}")
            logger.exception("Detailed traceback:")
            raise
