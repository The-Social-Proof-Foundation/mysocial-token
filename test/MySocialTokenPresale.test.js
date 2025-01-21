const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");
const { time, loadFixture } = require("@nomicfoundation/hardhat-toolbox/network-helpers");

describe("MySocialTokenPresale", function () {
  async function deployPresaleFixture() {
    const [owner, buyer1, buyer2] = await ethers.getSigners();

    // Deploy BondingCurveLib
    const BondingCurveLib = await ethers.getContractFactory("BondingCurveLib");
    const bondingCurveLib = await BondingCurveLib.deploy();

    // Deploy MySocialToken
    const MySocialToken = await ethers.getContractFactory("MySocialToken", {
      libraries: {
        BondingCurveLib: bondingCurveLib.target
      }
    });

    const token = await upgrades.deployProxy(
      MySocialToken,
      ["MySocial", "MYSO", owner.address],
      {
        initializer: 'initialize',
        unsafeAllowLinkedLibraries: true
      }
    );

    // Deploy mock USDC
    const MockUSDC = await ethers.getContractFactory("MockERC20");
    const usdc = await MockUSDC.deploy("USD Coin", "USDC", 6);

    // Setup presale parameters
    const totalPresaleTokens = ethers.parseUnits("125000000", 18); // 125M tokens (100M + 25% bonus)
    const maxClaimPerWallet = ethers.parseUnits("18750000", 18);   // 18.75M tokens (15M + 25% bonus)
    const presaleStartTime = await time.latest() + 3600;
    const presaleEndTime = presaleStartTime + 7 * 24 * 3600;
    const basePrice = ethers.parseUnits("0.003", 6);  // Start at $0.003
    const growthRate = ethers.parseUnits("0.0145", 6); // Growth rate for $500k target

    // Deploy Presale contract
    const MySocialTokenPresale = await ethers.getContractFactory("MySocialTokenPresale", {
      libraries: {
        BondingCurveLib: bondingCurveLib.target
      }
    });

    const presale = await MySocialTokenPresale.deploy(
      token.target,
      usdc.target,
      totalPresaleTokens,
      maxClaimPerWallet,
      presaleStartTime,
      presaleEndTime,
      basePrice,
      growthRate
    );

    // Set presale contract in token
    await token.setPresaleContract(presale.target);

    // Mint some USDC to buyers for testing
    const usdcAmount = ethers.parseUnits("10000", 6); // 10,000 USDC
    await usdc.mint(buyer1.address, usdcAmount);
    await usdc.mint(buyer2.address, usdcAmount);

    return {
      token,
      presale,
      usdc,
      owner,
      buyer1,
      buyer2,
      totalPresaleTokens,
      maxClaimPerWallet,
      presaleStartTime,
      presaleEndTime,
      basePrice,
      growthRate
    };
  }

  describe("Deployment", function () {
    it("Should set the correct initial values", async function () {
      const { presale, token, usdc, owner, totalPresaleTokens, maxClaimPerWallet, 
        presaleStartTime, presaleEndTime, basePrice, growthRate } = await loadFixture(deployPresaleFixture);

      expect(await presale.owner()).to.equal(owner.address);
      expect(await presale.token()).to.equal(token.target);
      expect(await presale.usdcToken()).to.equal(usdc.target);
      expect(await presale.totalPresaleTokens()).to.equal(totalPresaleTokens);
      expect(await presale.maxClaimPerWallet()).to.equal(maxClaimPerWallet);
      expect(await presale.presaleStartTime()).to.equal(presaleStartTime);
      expect(await presale.presaleEndTime()).to.equal(presaleEndTime);
      expect(await presale.basePrice()).to.equal(basePrice);
      expect(await presale.growthRate()).to.equal(growthRate);
      expect(await presale.presaleActive()).to.be.true;
    });
  });

  describe("Price Calculation", function () {
    it("Should start at exactly base price for first token", async function () {
      const { presale, basePrice } = await loadFixture(deployPresaleFixture);
      
      const oneToken = ethers.parseUnits("1", 18);
      const price = await presale.getCurrentPresalePrice(oneToken);
      
      expect(price).to.equal(ethers.parseUnits("0.003", 6));
    });

    it("Should calculate correct price for various amounts", async function () {
      const { presale } = await loadFixture(deployPresaleFixture);
      
      // Test key amounts
      const amounts = [
        ethers.parseUnits("1", 18),      // 1 token
        ethers.parseUnits("1000000", 18), // 1M tokens
        ethers.parseUnits("10000000", 18) // 10M tokens
      ];

      console.log("\nPrice Points:");
      for (const amount of amounts) {
        const price = await presale.getCurrentPresalePrice(amount);
        console.log(
          `${ethers.formatUnits(amount, 18)} MYSO:`,
          `${ethers.formatUnits(price * BigInt(1e18) / amount, 6)} USDC per token`
        );
      }
    });

    it("Should reach target raise amount for total supply", async function () {
      const { presale } = await loadFixture(deployPresaleFixture);
      
      // Calculate total raise by breaking it into chunks like real purchases
      const purchaseSizes = [
        ethers.parseUnits("10000000", 18),  // First 10M base tokens
        ethers.parseUnits("25000000", 18),  // Next 25M base tokens
        ethers.parseUnits("50000000", 18),  // Next 50M base tokens
        ethers.parseUnits("100000000", 18)  // All 100M base tokens (becomes 125M with bonus)
      ];
      
      let runningTotal = BigInt(0);
      let totalRaise = BigInt(0);

      for (const targetAmount of purchaseSizes) {
        const increment = targetAmount - runningTotal;
        const price = await presale.getCurrentPresalePrice(increment);
        totalRaise += price;
        runningTotal = targetAmount;
      }
      
      console.log("Total raise for all tokens:", ethers.formatUnits(totalRaise, 6), "USDC");
      
      const targetRaise = ethers.parseUnits("500000", 6); // $500k
      const tolerance = ethers.parseUnits("50000", 6); // $50k tolerance
      
      expect(totalRaise).to.be.closeTo(targetRaise, tolerance);
    });

    it("Should show price progression for total supply purchase", async function () {
      const { presale, totalPresaleTokens } = await loadFixture(deployPresaleFixture);
      
      // Test purchases in 20M token increments
      const increment = totalPresaleTokens / BigInt(5);
      let totalRaised = BigInt(0);
      
      console.log("\nPresale Overview:");
      console.log("Total Supply:", ethers.formatUnits(totalPresaleTokens, 18), "MYSO");
      console.log("Batch Size:", ethers.formatUnits(increment, 18), "MYSO");

      for (let i = 1; i <= 5; i++) {
        const purchaseAmount = increment;
        const price = await presale.getCurrentPresalePrice(purchaseAmount);
        totalRaised += price;
      }

      console.log("\nFinal Metrics:");
      console.log("Total USDC to Raise: $" + ethers.formatUnits(totalRaised, 6));
      console.log("Average Price per Token: $" + ethers.formatUnits(totalRaised * BigInt(1e18) / totalPresaleTokens, 6));
      
      expect(totalRaised).to.be.gt(0);
    });
  });

  describe("Token Purchase", function () {
    it("Should calculate price in USDC", async function () {
      const { presale } = await loadFixture(deployPresaleFixture);
      
      const purchaseAmount = ethers.parseUnits("1000", 18);
      const price = await presale.getCurrentPresalePrice(purchaseAmount);
      
      // Price should be within expected range
      expect(price).to.be.gt(0);
      
      // Check if price is within expected USDC range ($0.003 - $0.007 per token)
      const minExpectedUsdc = ethers.parseUnits("3", 3); // $0.003 in USDC
      const maxExpectedUsdc = ethers.parseUnits("7", 3); // $0.007 in USDC
      
      // Calculate price per token (adjusting for 18 decimals)
      const pricePerToken = (price * BigInt(1e18)) / purchaseAmount;
      
      expect(pricePerToken).to.be.gte(minExpectedUsdc);
      expect(pricePerToken).to.be.lte(maxExpectedUsdc);
    });

    it("Should allow USDC purchases during presale", async function () {
      const { presale, usdc, token, buyer1, presaleStartTime } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleStartTime);

      const baseAmount = ethers.parseUnits("10", 18);
      const expectedBonus = baseAmount * BigInt(25) / BigInt(100);
      const totalAmount = baseAmount + expectedBonus;
      const usdcPrice = await presale.getCurrentPresalePrice(baseAmount);
      
      await usdc.connect(buyer1).approve(presale.target, usdcPrice);
      await presale.connect(buyer1).buyPresaleTokens(baseAmount);

      // Verify the purchase includes bonus
      const tokenBalance = await token.balanceOf(buyer1.address);
      expect(tokenBalance).to.equal(totalAmount);
    });

    it("Should calculate correct price for large purchases", async function () {
      const { presale } = await loadFixture(deployPresaleFixture);
      
      // Test with 1M tokens (18 decimals)
      const purchaseAmount = ethers.parseUnits("1000000", 18);
      const usdcPrice = await presale.getCurrentPresalePrice(purchaseAmount);
      
      console.log("\nLarge Purchase Test:");
      console.log("Purchase amount (tokens):", ethers.formatUnits(purchaseAmount, 18));
      console.log("Total USDC price:", ethers.formatUnits(usdcPrice, 6));
      console.log("Average price per token:", ethers.formatUnits(usdcPrice * BigInt(1e18) / purchaseAmount, 6));

      // Test with 10M tokens
      const largerAmount = ethers.parseUnits("10000000", 18);
      const largerPrice = await presale.getCurrentPresalePrice(largerAmount);
      
      console.log("\nVery Large Purchase Test:");
      console.log("Purchase amount (tokens):", ethers.formatUnits(largerAmount, 18));
      console.log("Total USDC price:", ethers.formatUnits(largerPrice, 6));
      console.log("Average price per token:", ethers.formatUnits(largerPrice * BigInt(1e18) / largerAmount, 6));

      expect(largerPrice).to.be.gt(0);
      expect(usdcPrice).to.be.gt(0);
    });

    it("Should enforce max claim per wallet", async function () {
      const { presale, buyer1, presaleStartTime, maxClaimPerWallet } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleStartTime);

      const price = await presale.getCurrentPresalePrice(maxClaimPerWallet);
      
      await expect(
        presale.connect(buyer1).buyPresaleTokens(maxClaimPerWallet + BigInt(1))
      ).to.be.revertedWith("Exceeds claim limit");
    });

    it("Should show detailed breakdown of total raise for 125M tokens", async function () {
      const { presale, totalPresaleTokens } = await loadFixture(deployPresaleFixture);
      
      // Test purchases in chunks
      const purchaseSizes = [
        ethers.parseUnits("10000000", 18),  // First 10M base tokens
        ethers.parseUnits("25000000", 18),  // Next 25M base tokens
        ethers.parseUnits("50000000", 18),  // Next 50M base tokens
        ethers.parseUnits("100000000", 18)  // All 100M base tokens
      ];

      let runningTotal = BigInt(0);
      let totalRaise = BigInt(0);

      for (const targetAmount of purchaseSizes) {
        const increment = targetAmount - runningTotal;
        const price = await presale.getCurrentPresalePrice(increment);
        totalRaise += price;
        runningTotal = targetAmount;
        
        const withBonus = targetAmount + (targetAmount * BigInt(25) / BigInt(100));
        
        console.log(`\nBase Purchase: ${ethers.formatUnits(targetAmount, 18)} MYSO`);
        console.log(`With 25% Bonus: ${ethers.formatUnits(withBonus, 18)} MYSO`);
        console.log(`Increment Cost: $${ethers.formatUnits(price, 6)}`);
        console.log(`Total USDC Cost: $${ethers.formatUnits(totalRaise, 6)}`);
      }

      // Verify total raise is around $500k
      const expectedRaise = ethers.parseUnits("500000", 6);
      const tolerance = ethers.parseUnits("50000", 6);
      expect(totalRaise).to.be.closeTo(expectedRaise, tolerance);
    });
  });

  describe("Token Sale", function () {
    it("Should allow token sales during presale", async function () {
      const { presale, usdc, token, buyer1, presaleStartTime } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleStartTime);

      // First buy tokens
      const baseAmount = ethers.parseUnits("10", 18);
      const bonusAmount = baseAmount * BigInt(25) / BigInt(100);
      const totalAmount = baseAmount + bonusAmount;
      const usdcCost = await presale.getCurrentPresalePrice(baseAmount);
      
      await usdc.connect(buyer1).approve(presale.target, usdcCost);
      await presale.connect(buyer1).buyPresaleTokens(baseAmount);

      // Record initial USDC balance
      const initialUsdcBalance = await usdc.balanceOf(buyer1.address);

      // Approve total amount (including bonus) for selling
      await token.connect(buyer1).approve(presale.target, totalAmount);

      // Then sell tokens (including bonus)
      await presale.connect(buyer1).sellPresaleTokens(totalAmount);

      // When selling all tokens (including bonus), should get full refund
      // The refund should be based on the base amount's price
      const usdcBalanceAfter = await usdc.balanceOf(buyer1.address);
      expect(usdcBalanceAfter - initialUsdcBalance).to.equal(usdcCost);

      // Verify tokens were burned
      const finalTokenBalance = await token.balanceOf(buyer1.address);
      expect(finalTokenBalance).to.equal(0);
    });

    it("Should handle selling bonus tokens correctly", async function () {
      const { presale, usdc, token, buyer1, presaleStartTime } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleStartTime);

      // First buy tokens
      const baseAmount = ethers.parseUnits("1000", 18);
      const bonusAmount = baseAmount * BigInt(25) / BigInt(100);
      const totalAmount = baseAmount + bonusAmount;
      const usdcCost = await presale.getCurrentPresalePrice(baseAmount);
      
      await usdc.connect(buyer1).approve(presale.target, usdcCost);
      await presale.connect(buyer1).buyPresaleTokens(baseAmount);

      // Record USDC balance before selling
      const usdcBalanceBefore = await usdc.balanceOf(buyer1.address);

      // Approve and sell all tokens (including bonus)
      await token.connect(buyer1).approve(presale.target, totalAmount);
      await presale.connect(buyer1).sellPresaleTokens(totalAmount);

      // When selling all tokens (including bonus), should get full refund
      // The refund should be based on the base amount's price
      const usdcBalanceAfter = await usdc.balanceOf(buyer1.address);
      expect(usdcBalanceAfter - usdcBalanceBefore).to.equal(usdcCost);

      // Verify all tokens were burned
      const finalTokenBalance = await token.balanceOf(buyer1.address);
      expect(finalTokenBalance).to.equal(0);
    });
  });

  describe("Admin Functions", function () {
    it("Should allow owner to toggle presale", async function () {
      const { presale, owner } = await loadFixture(deployPresaleFixture);
      
      await presale.connect(owner).togglePresale();
      expect(await presale.presaleActive()).to.be.false;
      
      await presale.connect(owner).togglePresale();
      expect(await presale.presaleActive()).to.be.true;
    });

    it("Should allow owner to withdraw USDC", async function () {
      const { presale, usdc, token, owner, buyer1, presaleStartTime } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleStartTime);

      // First make a purchase with a significant amount
      const purchaseAmount = ethers.parseUnits("1000000", 18); // 1M tokens
      const usdcPrice = await presale.getCurrentPresalePrice(purchaseAmount);
      
      await usdc.connect(buyer1).approve(presale.target, usdcPrice);
      await presale.connect(buyer1).buyPresaleTokens(purchaseAmount);

      // Then withdraw
      const initialBalance = await usdc.balanceOf(owner.address);
      await presale.connect(owner).withdrawUsdc();
      const finalBalance = await usdc.balanceOf(owner.address);
      
      expect(finalBalance - initialBalance).to.equal(usdcPrice);
    });
  });

  describe("Safety Features", function () {
    it("Should reject direct ETH transfers", async function () {
      const { presale, buyer1 } = await loadFixture(deployPresaleFixture);
      
      await expect(
        buyer1.sendTransaction({
          to: presale.target,
          value: ethers.parseEther("1")
        })
      ).to.be.revertedWith("Direct ETH transfers not allowed");
    });

    it("Should prevent purchases before presale starts", async function () {
      const { presale, buyer1 } = await loadFixture(deployPresaleFixture);
      
      const purchaseAmount = ethers.parseUnits("10", 6);
      const price = await presale.getCurrentPresalePrice(purchaseAmount);

      await expect(
        presale.connect(buyer1).buyPresaleTokens(purchaseAmount)
      ).to.be.revertedWith("Presale not started");
    });

    it("Should prevent purchases after presale ends", async function () {
      const { presale, buyer1, presaleEndTime } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleEndTime + 1);

      const purchaseAmount = ethers.parseUnits("10", 6);
      const price = await presale.getCurrentPresalePrice(purchaseAmount);

      await expect(
        presale.connect(buyer1).buyPresaleTokens(purchaseAmount)
      ).to.be.revertedWith("Presale ended");
    });
  });

  describe("Token Purchase with Bonus", function () {
    it("Should give 25% bonus tokens on purchase", async function () {
      const { presale, usdc, token, buyer1, presaleStartTime } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleStartTime);

      // Purchase 1000 base tokens
      const baseAmount = ethers.parseUnits("1000", 18);
      const expectedBonus = baseAmount * BigInt(25) / BigInt(100); // 25% bonus
      const totalExpectedAmount = baseAmount + expectedBonus;
      
      const usdcPrice = await presale.getCurrentPresalePrice(baseAmount);
      
      await usdc.connect(buyer1).approve(presale.target, usdcPrice);
      
      // Buy tokens and verify the event includes the total amount (base + bonus)
      await expect(presale.connect(buyer1).buyPresaleTokens(baseAmount))
        .to.emit(presale, "TokensPurchased")
        .withArgs(buyer1.address, totalExpectedAmount, usdcPrice);

      // Verify final token balance includes bonus
      const finalBalance = await token.balanceOf(buyer1.address);
      expect(finalBalance).to.equal(totalExpectedAmount);
      
      // Verify wallet claims tracking includes bonus
      const walletClaims = await presale.walletClaims(buyer1.address);
      expect(walletClaims).to.equal(totalExpectedAmount);
    });

    it("Should enforce limits including bonus amounts", async function () {
      const { presale, usdc, buyer1, presaleStartTime, maxClaimPerWallet } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleStartTime);

      // Calculate max base amount that would exceed limit with bonus
      const baseAmount = (maxClaimPerWallet * BigInt(100)) / BigInt(125);
      const slightlyOver = baseAmount + BigInt(1);
      
      const usdcPrice = await presale.getCurrentPresalePrice(slightlyOver);
      await usdc.connect(buyer1).approve(presale.target, usdcPrice);

      // Should revert because base + bonus would exceed maxClaimPerWallet
      await expect(
        presale.connect(buyer1).buyPresaleTokens(slightlyOver)
      ).to.be.revertedWith("Exceeds claim limit");
    });

    it("Should maintain correct total supply accounting with bonus", async function () {
      const { presale, usdc, buyer1, buyer2, presaleStartTime } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleStartTime);

      // Get 10 buyers
      const [_, __, ___, ...additionalBuyers] = await ethers.getSigners();
      const buyers = [buyer1, buyer2, ...additionalBuyers.slice(0, 8)]; // Total 10 buyers

      // Each buyer buys 10M base tokens (becomes 12.5M with bonus)
      // 10 buyers * 10M = 100M base tokens (125M total with bonus)
      const purchaseAmount = ethers.parseUnits("10000000", 18); // 10M tokens each

      // Buy tokens with each buyer
      for (const buyer of buyers) {
        // Mint USDC for the buyer
        await usdc.mint(buyer.address, ethers.parseUnits("1000000", 6)); // 1M USDC

        // Calculate price and buy tokens
        const usdcPrice = await presale.getCurrentPresalePrice(purchaseAmount);
        await usdc.connect(buyer).approve(presale.target, usdcPrice);
        await presale.connect(buyer).buyPresaleTokens(purchaseAmount);
      }

      // Verify total supply (should be 125M)
      const totalSold = await presale.totalPresaleSold();
      expect(totalSold).to.equal(ethers.parseUnits("125000000", 18));
    });
  });
}); 