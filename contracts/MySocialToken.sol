// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "./BondingCurveLib.sol";

contract MySocialToken is Initializable, ERC20Upgradeable, OwnableUpgradeable, ReentrancyGuardUpgradeable {
    using BondingCurveLib for uint256;

    uint256 public basePrice;
    uint256 public growthRate;
    uint256 public totalPresaleTokens;
    uint256 public totalPresaleSold;
    uint256 public maxClaimPerWallet;
    bool public presaleActive;
    
    address public presaleContract;
    uint256 private constant TOTAL_SUPPLY_CAP = 1_000_000_000 * 10**18; // 1 billion tokens

    mapping(address => uint256) public walletClaims;
    mapping(address => uint256) public purchaseAmounts;

    event TokensPurchased(address indexed buyer, uint256 amount, uint256 cost);
    event TokensSold(address indexed seller, uint256 amount, uint256 refund);

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(
        string memory name,
        string memory symbol,
        address initialOwner
    ) public initializer {
        __ERC20_init(name, symbol);
        __Ownable_init(initialOwner);
        __ReentrancyGuard_init();
        
        basePrice = 0.003 ether;  // Matches USDC price in deploy.js (converted to ETH)
        growthRate = 0.0145 ether; // Matches USDC growth rate in deploy.js (converted to ETH)
        totalPresaleTokens = 125_000_000 * 10**18;  // 125M tokens (100M + 25% bonus)
        maxClaimPerWallet = 18_750_000 * 10**18;    // 18.75M tokens (15M + 25% bonus)
        presaleActive = false;  // Will be activated based on timestamp checks in presale contract
    }

    // ==============================
    // Bonding Curve Price Calculation
    // ==============================

    function calculatePrice(uint256 amount) public view returns (uint256) {
        return BondingCurveLib.calculatePrice(
            basePrice,
            growthRate,
            totalPresaleTokens,
            totalPresaleSold,
            amount
        );
    }

    function getCurrentPresalePrice(uint256 amount) external view returns (uint256) {
        return calculatePrice(amount);
    }

    // ==============================
    // Core Token Functions
    // ==============================

    function getTotalSupplyCap() external pure returns (uint256) {
        return TOTAL_SUPPLY_CAP;
    }

    function mint(address to, uint256 amount) external {
        require(msg.sender == owner() || msg.sender == presaleContract, "Unauthorized");
        require(totalSupply() + amount <= TOTAL_SUPPLY_CAP, "Exceeds supply cap");
        _mint(to, amount);
    }

    function burnFrom(address from, uint256 amount) external {
        require(msg.sender == owner() || msg.sender == presaleContract, "Unauthorized");
        _burn(from, amount);
    }

    // ==============================
    // Admin Functions
    // ==============================

    function setPresaleContract(address _presaleContract) external onlyOwner {
        presaleContract = _presaleContract;
    }

    function togglePresale() external onlyOwner {
        presaleActive = !presaleActive;
    }

    // ==============================
    // Safety Features
    // ==============================

    receive() external payable {
        revert("Direct ETH transfers not allowed");
    }
}