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

    event TokensPurchased(address indexed buyer, uint256 amount, uint256 cost);
    event TokensSold(address indexed seller, uint256 amount, uint256 refund);

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
        require(totalPresaleSold + amount <= totalPresaleTokens, "Exceeds presale supply");
        require(walletClaims[msg.sender] + amount <= maxClaimPerWallet, "Exceeds claim limit");

        uint256 usdcCost = _calculatePresalePrice(amount);
        
        require(usdcToken.balanceOf(msg.sender) >= usdcCost, "Insufficient USDC balance");
        require(usdcToken.transferFrom(msg.sender, address(this), usdcCost), "USDC transfer failed");

        walletClaims[msg.sender] += amount;
        totalPresaleSold += amount;
        purchaseAmounts[msg.sender] += usdcCost;

        token.mint(msg.sender, amount);

        emit TokensPurchased(msg.sender, amount, usdcCost);
    }

    function sellPresaleTokens(uint256 amount) external nonReentrant {
        require(presaleActive, "Presale is not active");
        require(block.timestamp >= presaleStartTime, "Presale not started");
        require(block.timestamp <= presaleEndTime, "Presale ended");
        require(token.balanceOf(msg.sender) >= amount, "Insufficient tokens to sell");

        uint256 refund = purchaseAmounts[msg.sender] * amount / walletClaims[msg.sender];
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

    // ==============================
    // Safety Features
    // ==============================

    receive() external payable {
        revert("Direct ETH transfers not allowed");
    }
}