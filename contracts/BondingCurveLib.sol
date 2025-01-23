// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

library BondingCurveLib {
    // Constants for price calculation
    uint256 constant PRECISION = 1e6;  // 6 decimals to match USDC
    uint256 constant TOKEN_DECIMALS = 1e18;  // 18 decimals for token
    uint256 constant DECIMAL_ADJUSTMENT = 1e12; // Difference between 18 and 6 decimals
    
    function calculatePrice(
        uint256 basePrice,      // $0.003 (3000)
        uint256 growthRate,
        uint256 totalPresaleTokens,
        uint256 currentSold,
        uint256 amount
    ) public pure returns (uint256) {
        require(currentSold + amount <= totalPresaleTokens, "Exceeds presale cap");
        
        // Convert 18 decimal values to 6 decimals for calculation
        uint256 adjustedCurrentSold = currentSold / DECIMAL_ADJUSTMENT;
        uint256 adjustedAmount = amount / DECIMAL_ADJUSTMENT;
        uint256 adjustedTotal = totalPresaleTokens / DECIMAL_ADJUSTMENT;

        // Calculate the percentage through the sale for this batch
        uint256 startPercent = (adjustedCurrentSold * PRECISION) / adjustedTotal;
        uint256 endPercent = ((adjustedCurrentSold + adjustedAmount) * PRECISION) / adjustedTotal;
        uint256 avgPercent = (startPercent + endPercent) / 2;

        // Calculate current price: basePrice + (growthRate * percentComplete)
        uint256 currentPrice = basePrice + ((growthRate * avgPercent) / PRECISION);
        
        // Calculate total cost
        return (currentPrice * adjustedAmount) / PRECISION;
    }

    function log2(uint256 x) internal pure returns (uint256) {
        if (x == 0) return 0;
        if (x == 1) return 0;
        
        uint256 result = 0;
        uint256 value = x;
        
        while (value >= 2) {
            value = value >> 1;
            result++;
        }
        
        return result * PRECISION;  // Scale up by PRECISION for better accuracy
    }
}