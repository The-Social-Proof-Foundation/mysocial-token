const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");

describe("Token Minting Tests", function () {
  let MySocialToken;
  let BondingCurveLib;
  let token;
  let owner;
  let addr1;
  let addr2;
  let addrs;

  beforeEach(async function () {
    // Get signers
    [owner, addr1, addr2, ...addrs] = await ethers.getSigners();
    
    // Deploy BondingCurveLib first (required by MySocialToken)
    BondingCurveLib = await ethers.getContractFactory("BondingCurveLib");
    const bondingCurveLib = await BondingCurveLib.deploy();
    await bondingCurveLib.waitForDeployment();
    
    // Deploy MySocialToken with transparent proxy
    MySocialToken = await ethers.getContractFactory("MySocialToken", {
      libraries: {
        BondingCurveLib: await bondingCurveLib.getAddress(),
      },
    });

    // Deploy token through proxy with owner as initialOwner
    token = await upgrades.deployProxy(
      MySocialToken,
      ["MySocial", "MYSO", owner.address],
      {
        initializer: 'initialize',
        unsafeAllowLinkedLibraries: true,
        silenceWarnings: true
      }
    );
    
    await token.waitForDeployment();
  });

  describe("Initial Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await token.owner()).to.equal(owner.address);
    });

    it("Should have zero initial supply", async function () {
      expect(await token.totalSupply()).to.equal(0);
    });
    
    it("Should have correct token details", async function () {
      expect(await token.name()).to.equal("MySocial");
      expect(await token.symbol()).to.equal("MYSO");
    });
  });

  describe("Minting", function () {
    it("Should allow owner to mint tokens", async function () {
      const mintAmount = ethers.parseUnits("1000000", 18); // 1M tokens
      
      // Check initial balance is zero
      expect(await token.balanceOf(owner.address)).to.equal(0);
      
      // Mint tokens to owner
      await token.connect(owner).mint(owner.address, mintAmount);
      
      // Check new balance
      expect(await token.balanceOf(owner.address)).to.equal(mintAmount);
      expect(await token.totalSupply()).to.equal(mintAmount);
    });
    
    it("Should allow minting multiple times to the same address", async function () {
      const firstMintAmount = ethers.parseUnits("1000000", 18); // 1M tokens
      const secondMintAmount = ethers.parseUnits("2000000", 18); // 2M tokens
      
      // Mint first batch
      await token.connect(owner).mint(owner.address, firstMintAmount);
      expect(await token.balanceOf(owner.address)).to.equal(firstMintAmount);
      
      // Mint second batch to same address
      await token.connect(owner).mint(owner.address, secondMintAmount);
      
      // Check total balance
      const expectedTotal = firstMintAmount + secondMintAmount;
      expect(await token.balanceOf(owner.address)).to.equal(expectedTotal);
      expect(await token.totalSupply()).to.equal(expectedTotal);
    });
    
    it("Should not allow minting beyond supply cap", async function () {
      const supplyCap = await token.getTotalSupplyCap();
      
      // Try to mint more than the cap
      await expect(
        token.connect(owner).mint(owner.address, supplyCap + BigInt(1))
      ).to.be.revertedWith("Exceeds supply cap");
      
      // Mint exactly the cap amount
      await token.connect(owner).mint(owner.address, supplyCap);
      expect(await token.totalSupply()).to.equal(supplyCap);
      
      // Try to mint 1 more token - should fail
      await expect(
        token.connect(owner).mint(owner.address, 1)
      ).to.be.revertedWith("Exceeds supply cap");
    });
    
    it("Should not allow non-owners to mint tokens", async function () {
      const mintAmount = ethers.parseUnits("1000000", 18); // 1M tokens
      
      // Try to mint as non-owner
      await expect(
        token.connect(addr1).mint(addr1.address, mintAmount)
      ).to.be.revertedWith("Unauthorized");
    });

    it("Should allow presale contract to mint tokens", async function () {
      const mintAmount = ethers.parseUnits("1000000", 18); // 1M tokens
      
      // Set addr1 as presale contract
      await token.connect(owner).setPresaleContract(addr1.address);
      
      // Mint as presale contract to addr2
      await token.connect(addr1).mint(addr2.address, mintAmount);
      expect(await token.balanceOf(addr2.address)).to.equal(mintAmount);
    });
  });

  describe("Token Distribution", function () {
    it("Should mint tokens to multiple wallets", async function () {
      const amount1 = ethers.parseUnits("1000000", 18); // 1M tokens
      const amount2 = ethers.parseUnits("2000000", 18); // 2M tokens
      const amount3 = ethers.parseUnits("3000000", 18); // 3M tokens
      
      // Mint to different addresses
      await token.connect(owner).mint(addr1.address, amount1);
      await token.connect(owner).mint(addr2.address, amount2);
      await token.connect(owner).mint(owner.address, amount3);
      
      // Check balances
      expect(await token.balanceOf(addr1.address)).to.equal(amount1);
      expect(await token.balanceOf(addr2.address)).to.equal(amount2);
      expect(await token.balanceOf(owner.address)).to.equal(amount3);
      
      // Check total supply
      const expectedTotal = amount1 + amount2 + amount3;
      expect(await token.totalSupply()).to.equal(expectedTotal);
    });
  });
}); 