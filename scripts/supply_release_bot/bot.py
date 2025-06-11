import json
import os
import logging
from web3 import Web3

from scripts.volume_bot.trader import Trader, UNISWAP_V4_ROUTER_ABI
from scripts.volume_bot.wallet import Wallet

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "mint", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
]

POOL_ABI = [
    {"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"liquidity","outputs":[{"internalType":"uint128","name":"","type":"uint128"}],"stateMutability":"view","type":"function"}
]

FACTORY_ADDRESS = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
FACTORY_ABI = [{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"}],"name":"getPool","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("supply_release")

DEFAULT_CONFIG = {
    "rpc_url": "https://mainnet.base.org",
    "token_address": "0xfdd6013bf2757018d8c087244f03e5a521b2d3b7",
    "usdc_address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "router_address": "0x2626664c2603336E57B271c5C0b26F421741e481",
    "owner_private_key": "",
    "target_price": 0.0035,
    "threshold_percent": 5,
    "release_cap": 1000000,
    "state_path": "supply_release_state.json"
}

class SupplyReleaseBot:
    def __init__(self, config_path: str):
        self.config = DEFAULT_CONFIG.copy()
        if os.path.exists(config_path):
            with open(config_path) as f:
                self.config.update(json.load(f))
        self.w3 = Web3(Web3.HTTPProvider(self.config["rpc_url"]))
        self.wallet = Wallet(private_key=self.config["owner_private_key"])
        self.trader = Trader(self.w3, self.wallet, self.config["router_address"], UNISWAP_V4_ROUTER_ABI)
        self.token = self.w3.eth.contract(address=Web3.to_checksum_address(self.config["token_address"]), abi=ERC20_ABI)
        self.usdc = self.w3.eth.contract(address=Web3.to_checksum_address(self.config["usdc_address"]), abi=ERC20_ABI)
        self.factory = self.w3.eth.contract(address=Web3.to_checksum_address(FACTORY_ADDRESS), abi=FACTORY_ABI)
        self.state_path = os.path.join(os.path.dirname(config_path), self.config.get("state_path", "supply_release_state.json"))
        self._load_state()

    @staticmethod
    def price_from_sqrtp(sqrtp: int, decimals_token0: int, decimals_token1: int, token1_is_target: bool) -> float:
        price_token1_per_token0 = (sqrtp ** 2) / 2**192 * 10 ** (decimals_token0 - decimals_token1)
        if token1_is_target:
            return 1 / price_token1_per_token0
        return price_token1_per_token0

    def _load_state(self):
        if os.path.exists(self.state_path):
            with open(self.state_path) as f:
                self.state = json.load(f)
        else:
            self.state = {"released": 0}

    def _save_state(self):
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get_pool(self):
        pool_addr = self.factory.functions.getPool(
            Web3.to_checksum_address(self.config["usdc_address"]),
            Web3.to_checksum_address(self.config["token_address"]),
            3000
        ).call()
        return self.w3.eth.contract(address=pool_addr, abi=POOL_ABI)

    def get_price(self) -> float:
        pool = self.get_pool()
        slot0 = pool.functions.slot0().call()
        token0 = pool.functions.token0().call()
        token1 = pool.functions.token1().call()
        d0 = self.w3.eth.contract(address=token0, abi=ERC20_ABI).functions.decimals().call()
        d1 = self.w3.eth.contract(address=token1, abi=ERC20_ABI).functions.decimals().call()
        sqrtp = slot0[0]
        token1_is_target = Web3.to_checksum_address(token1) == Web3.to_checksum_address(self.config["token_address"])
        return self.price_from_sqrtp(sqrtp, d0, d1, token1_is_target)

    def calculate_mint_amount(self, price: float) -> int:
        target = self.config["target_price"]
        deviation = (price - target) / target
        if deviation <= 0:
            return 0
        total_supply = self.token.functions.totalSupply().call()
        amount = int(total_supply * deviation * 0.1)
        remaining = self.config["release_cap"] - self.state.get("released", 0)
        return min(amount, remaining)

    def mint_and_sell(self, amount: int):
        if amount <= 0:
            return
        token_decimals = self.token.functions.decimals().call()
        nonce = self.w3.eth.get_transaction_count(self.wallet.get_address())
        gas_price = self.w3.eth.gas_price
        tx = self.token.functions.mint(self.wallet.get_address(), amount).build_transaction({
            'from': self.wallet.get_address(),
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': gas_price
        })
        signed = self.wallet.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        pool_key = {"fee": 3000, "tickSpacing": 60, "hooks": Web3.to_checksum_address("0x0000000000000000000000000000000000000000")}
        self.trader.swap_tokens_for_tokens(self.config["token_address"], self.config["usdc_address"], amount, pool_key)
        self.state["released"] = self.state.get("released", 0) + amount
        self._save_state()
        logger.info(f"Minted and sold {amount / (10**token_decimals)} tokens")

    def run(self):
        try:
            price = self.get_price()
            logger.info(f"Current price: {price} USDC")
            if price <= self.config["target_price"] * (1 + self.config["threshold_percent"] / 100):
                logger.info("Price within threshold - nothing to do")
                return
            if self.state.get("released", 0) >= self.config["release_cap"]:
                logger.info("Release cap reached")
                return
            amount = self.calculate_mint_amount(price)
            if amount > 0:
                self.mint_and_sell(amount)
            else:
                logger.info("Calculated mint amount is zero")
        except Exception as e:
            logger.error(f"Error in supply release bot: {e}")
