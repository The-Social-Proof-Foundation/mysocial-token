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
    const totalPresaleTokens = ethers.parseUnits("100000000", 18); // 100M tokens
    const maxClaimPerWallet = ethers.parseUnits("15000000", 18);   // 15M tokens
    const presaleStartTime = await time.latest() + 3600;
    const presaleEndTime = presaleStartTime + 7 * 24 * 3600;
    const basePrice = ethers.parseUnits("0.003", 6);  // Start at $0.003
    const growthRate = ethers.parseUnits("0.011111", 6); // Will give us max increase of $0.004

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
      const { presale, totalPresaleTokens } = await loadFixture(deployPresaleFixture);
      
      // Calculate total raise by breaking it into chunks like real purchases
      const purchaseSizes = [
        ethers.parseUnits("10000000", 18),  // First 10M tokens
        ethers.parseUnits("20000000", 18),  // First 20M tokens
        ethers.parseUnits("50000000", 18),  // First 50M tokens
        totalPresaleTokens                   // All 100M tokens
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
      const tolerance = ethers.parseUnits("150000", 6); // $150k tolerance
      
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

      const purchaseAmount = ethers.parseUnits("10", 18);
      const usdcPrice = await presale.getCurrentPresalePrice(purchaseAmount);
      
      await usdc.connect(buyer1).approve(presale.target, usdcPrice);
      await presale.connect(buyer1).buyPresaleTokens(purchaseAmount);

      // Verify the purchase
      const tokenBalance = await token.balanceOf(buyer1.address);
      expect(tokenBalance).to.equal(purchaseAmount);
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

    it("Should show detailed breakdown of total raise for 100M tokens", async function () {
      const { presale, totalPresaleTokens } = await loadFixture(deployPresaleFixture);
      
      // Calculate prices for cumulative purchases to show real progression
      const purchaseSizes = [
        ethers.parseUnits("10000000", 18),  // First 10M tokens
        ethers.parseUnits("20000000", 18),  // First 20M tokens
        ethers.parseUnits("50000000", 18),  // First 50M tokens
        totalPresaleTokens                   // All 100M tokens
      ];

      console.log("\n=== Total Raise Analysis for 100M Tokens ===");
      
      let runningTotal = BigInt(0);
      let totalRaise = BigInt(0);

      for (const targetAmount of purchaseSizes) {
        // Calculate price for the increment since last purchase
        const increment = targetAmount - runningTotal;
        const price = await presale.getCurrentPresalePrice(increment);
        totalRaise += price;
        runningTotal = targetAmount;
        
        const averagePrice = (totalRaise * BigInt(1e18)) / targetAmount;
        
        console.log(`\nCumulative Purchase: ${ethers.formatUnits(targetAmount, 18)} MYSO tokens`);
        console.log(`Total USDC Cost So Far: $${ethers.formatUnits(totalRaise, 6)}`);
        console.log(`Average Price Per Token: $${ethers.formatUnits(averagePrice, 6)}`);
        console.log(`Last Batch Price Per Token: $${ethers.formatUnits((price * BigInt(1e18)) / increment, 6)}`);
      }

      console.log("\n=== Final Totals ===");
      console.log(`Total Tokens: ${ethers.formatUnits(totalPresaleTokens, 18)} MYSO`);
      console.log(`Total Raise: $${ethers.formatUnits(totalRaise, 6)} USDC`);
      console.log(`Final Average Price Per Token: $${ethers.formatUnits((totalRaise * BigInt(1e18)) / totalPresaleTokens, 6)}`);

      // Verify the total raise is within expected range (around $500k)
      const expectedRaise = ethers.parseUnits("500000", 6); // $500k
      const tolerance = ethers.parseUnits("10000", 6);      // $10k tolerance
      
      expect(totalRaise).to.be.closeTo(expectedRaise, tolerance);
    });
  });

  describe("Token Sale", function () {
    it("Should allow token sales during presale", async function () {
      const { presale, usdc, token, buyer1, presaleStartTime } = await loadFixture(deployPresaleFixture);
      
      await time.increaseTo(presaleStartTime);

      // First buy tokens
      const purchaseAmount = ethers.parseUnits("10", 18);
      const usdcPrice = await presale.getCurrentPresalePrice(purchaseAmount);
      
      await usdc.connect(buyer1).approve(presale.target, usdcPrice);
      await presale.connect(buyer1).buyPresaleTokens(purchaseAmount);

      // Approve tokens for selling
      await token.connect(buyer1).approve(presale.target, purchaseAmount);

      // Then sell tokens
      await expect(presale.connect(buyer1).sellPresaleTokens(purchaseAmount))
        .to.emit(presale, "TokensSold")
        .withArgs(buyer1.address, purchaseAmount, usdcPrice);
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
}); 