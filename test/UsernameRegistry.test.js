const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("UsernameRegistry", function () {
  let UsernameRegistry;
  let usernameRegistry;
  let owner;
  let addr1;
  let addr2;
  let mockToken;

  before(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    
    const MockToken = await ethers.getContractFactory("MockERC20");
    mockToken = await MockToken.deploy("MySocialToken", "MySo", 18);
    await mockToken.waitForDeployment();

    console.log("MockToken deployed at:", mockToken.target);

    UsernameRegistry = await ethers.getContractFactory("UsernameRegistry");
    usernameRegistry = await UsernameRegistry.deploy(mockToken.target);
    await usernameRegistry.waitForDeployment();

    console.log("UsernameRegistry deployed at:", usernameRegistry.target);

    await mockToken.mint(owner.address, ethers.parseEther("10"));
    await mockToken.mint(addr1.address, ethers.parseEther("10"));
    await mockToken.mint(addr2.address, ethers.parseEther("10"));
  });

  describe("Username Reservation", function () {
    it("Should allow a user to reserve an available username", async function () {
      const username = "alice123";
      await expect(usernameRegistry.connect(addr1).reserveUsername(username))
        .to.emit(usernameRegistry, "UsernameReserved")
        .withArgs(username, addr1.address);

      expect(await usernameRegistry.getUsernameOwner(username)).to.equal(addr1.address);
    });

    it("Should not allow empty usernames", async function () {
      await expect(
        usernameRegistry.connect(owner).reserveUsername("")
      ).to.be.revertedWith("Username cannot be empty");
    });

    it("Should not allow usernames longer than 32 characters", async function () {
      const longUsername = "thisusernameiswaytoolongtobevalid12345";
      await expect(
        usernameRegistry.connect(owner).reserveUsername(longUsername)
      ).to.be.revertedWith("Username too long");
    });

    it("Should not allow invalid characters in usernames", async function () {
      await expect(
        usernameRegistry.connect(owner).reserveUsername("user@name")
      ).to.be.revertedWith("Invalid username format");
    });

    it("Should not allow duplicate usernames", async function () {
      const username = "testuser";
      await usernameRegistry.connect(addr1).reserveUsername(username);
      
      await expect(
        usernameRegistry.connect(addr2).reserveUsername(username)
      ).to.be.revertedWith("Username already taken");
    });
  });

  describe("Username Release", function () {
    it("Should allow owner to release their username", async function () {
      const username = "bob123";
      await usernameRegistry.connect(addr1).reserveUsername(username);
      
      await expect(usernameRegistry.connect(addr1).releaseUsername(username))
        .to.emit(usernameRegistry, "UsernameReleased")
        .withArgs(username, addr1.address);

      expect(await usernameRegistry.getUsernameOwner(username)).to.equal(ethers.ZeroAddress);
    });

    it("Should not allow non-owners to release a username", async function () {
      const username = "charlie123";
      await usernameRegistry.connect(addr1).reserveUsername(username);
      
      await expect(
        usernameRegistry.connect(addr2).releaseUsername(username)
      ).to.be.revertedWith("Not username owner");
    });
  });

  describe("Recent Usernames", function () {
    beforeEach(async function() {
      // Deploy fresh contracts for each test
      const MockToken = await ethers.getContractFactory("MockERC20");
      mockToken = await MockToken.deploy("MySocialToken", "MySo", 18);
      await mockToken.waitForDeployment();

      UsernameRegistry = await ethers.getContractFactory("UsernameRegistry");
      usernameRegistry = await UsernameRegistry.deploy(mockToken.target);
      await usernameRegistry.waitForDeployment();

      // Mint tokens for testing
      await mockToken.mint(owner.address, ethers.parseEther("10"));
      await mockToken.mint(addr1.address, ethers.parseEther("10"));
      await mockToken.mint(addr2.address, ethers.parseEther("10"));
    });

    it("Should track recent usernames correctly", async function () {
      await usernameRegistry.connect(addr1).reserveUsername("user1");
      await usernameRegistry.connect(addr2).reserveUsername("user2");
      
      const recentUsernames = await usernameRegistry.getRecentUsernames(2);
      expect(recentUsernames.length).to.equal(2);
    });

    it("Should handle requesting more usernames than available", async function () {
      const username = "singleuser123";
      await usernameRegistry.connect(addr1).reserveUsername(username);
      
      const recentUsernames = await usernameRegistry.getRecentUsernames(5);
      expect(recentUsernames.length).to.equal(1);
      expect(recentUsernames[0]).to.equal(username);

      // Print all registered usernames
      console.log("\nRegistered usernames:");
      for (let i = 0; i < recentUsernames.length; i++) {
        console.log(`${i + 1}. ${recentUsernames[i]}`);
      }
    });

    it("Should maintain max recent usernames limit", async function () {
      this.timeout(120000);
      
      // Generate unique usernames
      for (let i = 0; i < 102; i++) {
        const username = `uniqueuser${i}`;
        await usernameRegistry.connect(addr1).reserveUsername(username);
      }
      
      const maxRecent = await usernameRegistry.MAX_RECENT_USERNAMES();
      const recentUsernames = await usernameRegistry.getRecentUsernames(200);
      expect(recentUsernames.length).to.equal(maxRecent);

      // Print all registered usernames
      console.log("\nRegistered usernames (showing last 10):");
      const lastTen = recentUsernames.slice(-10);
      for (let i = 0; i < lastTen.length; i++) {
        console.log(`${recentUsernames.length - 10 + i + 1}. ${lastTen[i]}`);
      }
    }).timeout(120000);
  });

  describe("Username Validation", function () {
    it("Should allow valid usernames", async function () {
      const validUsernames = [
        "user123",
        "USER_123",
        "abc_DEF_123",
        "a1_B2"
      ];

      for (const username of validUsernames) {
        await expect(
          usernameRegistry.connect(addr1).reserveUsername(username)
        ).to.not.be.reverted;
      }
    });

    it("Should reject invalid usernames", async function () {
      const invalidUsernames = [
        "user-123",
        "user.name",
        "user@domain",
        "user name",
        "user#123"
      ];

      for (const username of invalidUsernames) {
        await expect(
          usernameRegistry.connect(addr1).reserveUsername(username)
        ).to.be.revertedWith("Invalid username format");
      }
    });
  });

  describe("Restricted Usernames", function () {
    it("Should not allow reserving restricted usernames", async function () {
      const restrictedNames = ["admin", "owner", "system", "moderator", "mod", "support", "help"];
      
      for (const username of restrictedNames) {
        await expect(
          usernameRegistry.connect(addr1).reserveUsername(username)
        ).to.be.revertedWith("Username is restricted");
      }
    });

    it("Should correctly identify restricted usernames", async function () {
      expect(await usernameRegistry.isRestricted("admin")).to.be.true;
      expect(await usernameRegistry.isRestricted("owner")).to.be.true;
      expect(await usernameRegistry.isRestricted("randomuser123")).to.be.false;
    });
  });

  describe("Token Requirements", function () {
    it("Should not allow username reservation without holding tokens", async function () {
      const username = "test123";
      const [_, __, ___, noTokenUser] = await ethers.getSigners();
      
      await expect(
        usernameRegistry.connect(noTokenUser).reserveUsername(username)
      ).to.be.revertedWith("Must hold at least 1 MySo token");
    });

    it("Should allow username reservation with sufficient tokens", async function () {
      const username = "test123";
      await expect(
        usernameRegistry.connect(addr1).reserveUsername(username)
      ).to.not.be.reverted;
    });
  });

  describe("Username Lookup by Address", function () {
    it("Should return empty string for address with no username", async function () {
      expect(await usernameRegistry.getUsernameByAddress(addr2.address)).to.equal("");
    });

    it("Should return correct username for address", async function () {
      const username = "testuser123";
      await usernameRegistry.connect(addr1).reserveUsername(username);
      
      expect(await usernameRegistry.getUsernameByAddress(addr1.address)).to.equal(username);
    });

    it("Should handle username changes for an address", async function () {
      const username1 = "firstuser";
      const username2 = "seconduser";
      
      // Reserve first username
      await usernameRegistry.connect(addr1).reserveUsername(username1);
      expect(await usernameRegistry.getUsernameByAddress(addr1.address)).to.equal(username1);
      
      // Change to second username
      await usernameRegistry.connect(addr1).reserveUsername(username2);
      expect(await usernameRegistry.getUsernameByAddress(addr1.address)).to.equal(username2);
    });

    it("Should clear username when released", async function () {
      const username = "tempuser";
      await usernameRegistry.connect(addr1).reserveUsername(username);
      await usernameRegistry.connect(addr1).releaseUsername(username);
      
      expect(await usernameRegistry.getUsernameByAddress(addr1.address)).to.equal("");
    });
  });
}); 