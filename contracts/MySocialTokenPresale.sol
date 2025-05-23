// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./MySocialToken.sol";
import "./BondingCurveLib.sol";
contract MySocialTokenPresale is ReentrancyGuard, Ownable {
    using BondingCurveLib for uint256;

    MySocialToken public token;
    uint256 public presaleStartTime;
    uint256 public presaleEndTime;
    uint256 public maxClaimPerWallet;
    mapping(address => uint256) public walletClaims;
    mapping(address => uint256) public purchaseAmounts;

    uint256 public totalPresaleTokens;
    uint256 public totalPresaleSold;
    bool public presaleActive = true;

    uint256 public basePrice;
    uint256 public growthRate;

    IERC20 public usdcToken;
    bool public acceptUsdc;
    uint256 public usdcDecimals;

    // Add constant for bonus percentage
    uint256 public constant BONUS_PERCENTAGE = 25;

    event TokensPurchased(address indexed buyer, uint256 amount, uint256 cost);
    event TokensSold(address indexed seller, uint256 amount, uint256 refund);

    // Add event for new presale phase
    event NewPresalePhase(
        uint256 startTime,
        uint256 endTime,
        uint256 remainingTokens,
        uint256 newGrowthRate
    );

    constructor(
        address tokenAddress,
        address _usdcAddress,
        uint256 _totalPresaleTokens,
        uint256 _maxClaimPerWallet,
        uint256 _presaleStartTime,
        uint256 _presaleEndTime,
        uint256 _basePrice,
        uint256 _growthRate
    ) Ownable(msg.sender) {
        token = MySocialToken(payable(tokenAddress));
        require(token.owner() == msg.sender, "Owner must be the same as token owner");
        require(_presaleStartTime < _presaleEndTime, "Invalid time range");
        require(_presaleEndTime > block.timestamp, "End time must be in future");
        
        totalPresaleTokens = _totalPresaleTokens;
        maxClaimPerWallet = _maxClaimPerWallet;
        presaleStartTime = _presaleStartTime;
        presaleEndTime = _presaleEndTime;
        basePrice = _basePrice;
        growthRate = _growthRate;

        usdcToken = IERC20(_usdcAddress);
        usdcDecimals = 6;
        acceptUsdc = true;
    }

    // ==============================
    // Buy / Sell Presale Tokens Functions
    // ==============================

    function _calculatePresalePrice(uint256 amount) internal view returns (uint256) {
        return BondingCurveLib.calculatePrice(
            basePrice,
            growthRate,
            totalPresaleTokens,
            totalPresaleSold,
            amount
        );
    }

    function getCurrentPresalePrice(uint256 amount) external view returns (uint256) {
        return _calculatePresalePrice(amount);
    }

    function buyPresaleTokens(uint256 amount) external nonReentrant {
        require(presaleActive, "Presale is not active");
        require(block.timestamp >= presaleStartTime, "Presale not started");
        require(block.timestamp <= presaleEndTime, "Presale ended");
        
        // Calculate total amount including bonus
        uint256 bonusAmount = (amount * BONUS_PERCENTAGE) / 100;
        uint256 totalAmount = amount + bonusAmount;
        
        require(totalPresaleSold + totalAmount <= totalPresaleTokens, "Exceeds presale supply");
        require(walletClaims[msg.sender] + totalAmount <= maxClaimPerWallet, "Exceeds claim limit");

        // Price is calculated on the base amount, not including bonus
        uint256 usdcCost = _calculatePresalePrice(amount);
        
        require(usdcToken.balanceOf(msg.sender) >= usdcCost, "Insufficient USDC balance");
        require(usdcToken.transferFrom(msg.sender, address(this), usdcCost), "USDC transfer failed");

        // Update state with total amount (including bonus)
        walletClaims[msg.sender] += totalAmount;
        totalPresaleSold += totalAmount;
        purchaseAmounts[msg.sender] += usdcCost;

        // Mint total amount including bonus
        token.mint(msg.sender, totalAmount);

        emit TokensPurchased(msg.sender, totalAmount, usdcCost);
    }

    function sellPresaleTokens(uint256 amount) external nonReentrant {
        require(presaleActive, "Presale is not active");
        require(block.timestamp >= presaleStartTime, "Presale not started");
        require(block.timestamp <= presaleEndTime, "Presale ended");
        require(token.balanceOf(msg.sender) >= amount, "Insufficient tokens to sell");

        // Check if selling all tokens
        bool sellingAll = (amount == walletClaims[msg.sender]);
        uint256 refund;

        if (sellingAll) {
            // If selling all tokens, give full refund
            refund = purchaseAmounts[msg.sender];
        } else {
            // Otherwise calculate proportional refund based on base amount
            uint256 baseAmount = (amount * 100) / (100 + BONUS_PERCENTAGE);
            refund = purchaseAmounts[msg.sender] * baseAmount / (walletClaims[msg.sender] * 100 / (100 + BONUS_PERCENTAGE));
        }

        require(refund > 0, "No refundable USDC available");

        walletClaims[msg.sender] -= amount;
        totalPresaleSold -= amount;
        purchaseAmounts[msg.sender] -= refund;

        token.burnFrom(msg.sender, amount);
        
        require(usdcToken.transfer(msg.sender, refund), "USDC transfer failed");

        emit TokensSold(msg.sender, amount, refund);
    }

    function getPresaleDuration() external view returns (uint256 start, uint256 end) {
        return (presaleStartTime, presaleEndTime);
    }

    function remainingPresaleSupply() public view returns (uint256) {
        return totalPresaleTokens - totalPresaleSold;
    }

    // ==============================
    // Admin Functions
    // ==============================

    function togglePresale() external onlyOwner {
        presaleActive = !presaleActive;
        acceptUsdc = presaleActive;
    }

    function withdrawUsdc() external onlyOwner {
        uint256 balance = usdcToken.balanceOf(address(this));
        require(balance > 0, "No USDC to withdraw");
        require(usdcToken.transfer(owner(), balance), "USDC transfer failed");
    }

    /**
     * @notice Starts a new presale phase if there are remaining tokens from previous phase
     * @param _startTime New presale start time
     * @param _endTime New presale end time
     * @param _newGrowthRate Optional new growth rate (0 to keep current rate)
     */
    function startNewPresalePhase(
        uint256 _startTime,
        uint256 _endTime,
        uint256 _newGrowthRate
    ) external onlyOwner {
        // Check if there are remaining tokens from previous phase
        uint256 remaining = remainingPresaleSupply();
        require(remaining > 0, "No tokens remaining from previous phase");
        
        // Current presale must be ended or inactive
        require(
            !presaleActive || block.timestamp > presaleEndTime,
            "Current presale still active"
        );

        // Validate time parameters
        require(_endTime > _startTime, "End time must be after start time");
        
        // Update presale parameters
        presaleStartTime = _startTime;
        presaleEndTime = _endTime;
        
        // Update growth rate if provided (non-zero)
        if (_newGrowthRate > 0) {
            growthRate = _newGrowthRate;
        }

        // Activate the presale
        presaleActive = true;
        acceptUsdc = true;

        emit NewPresalePhase(
            presaleStartTime,
            presaleEndTime,
            remaining,
            growthRate
        );
    }

    // ==============================
    // Safety Features
    // ==============================

    receive() external payable {
        revert("Direct ETH transfers not allowed");
    }

    function getRefundValue(uint256 tokenAmount) public view returns (uint256) {
        require(tokenAmount > 0, "Amount must be greater than 0");
        
        address sender = msg.sender;
        require(walletClaims[sender] > 0, "No tokens claimed");
        
        // If selling all tokens, return full purchase amount
        if (tokenAmount == walletClaims[sender]) {
            return purchaseAmounts[sender];
        }
        
        // Calculate proportional refund based on base amount (excluding bonus)
        uint256 baseAmount = (tokenAmount * 100) / (100 + BONUS_PERCENTAGE);
        uint256 refund = purchaseAmounts[sender] * baseAmount / (walletClaims[sender] * 100 / (100 + BONUS_PERCENTAGE));
        
        return refund;
    }
}