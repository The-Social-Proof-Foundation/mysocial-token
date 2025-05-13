require("@nomicfoundation/hardhat-toolbox");
require("@openzeppelin/hardhat-upgrades");
require("@nomicfoundation/hardhat-verify");
require('dotenv').config();
const { types } = require("hardhat/config");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.28",
    settings: {
      viaIR: true,
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    hardhat: {
      forking: {
        url: `https://eth-mainnet.alchemyapi.io/v2/${process.env.ALCHEMY_API_KEY}`,
        blockNumber: 21672445  // Use a fixed recent block number
      }
    },
    sepolia: {
      url: process.env.BASE_TESTNET_RPC,
      accounts: [process.env.PRIVATE_KEY],
      chainId: 84532,
      verify: {
        etherscan: {
          apiUrl: "https://api-sepolia.basescan.org"
        }
      }
    },
    base: {
      url: process.env.BASE_MAINNET_RPC,
      accounts: [process.env.PRIVATE_KEY],
      chainId: 8453,
      verify: {
        etherscan: {
          apiUrl: "https://api.basescan.org"
        }
      }
    }
  },
  upgrades: {
    silenceWarnings: true,
    unsafeAllow: ['external-library-linking']
  },
  etherscan: {
    apiKey: {
      baseSepolia: process.env.BASESCAN_API_KEY,
      base: process.env.BASESCAN_API_KEY
    },
    customChains: [
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://api-sepolia.basescan.org/api",
          browserURL: "https://sepolia.basescan.org"
        }
      },
      {
        network: "base",
        chainId: 8453,
        urls: {
          apiURL: "https://api.basescan.org/api",
          browserURL: "https://basescan.org"
        }
      }
    ]
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};

task("start-presale-phase", "Starts a new presale phase")
  .addParam("contract", "The presale contract address")
  .addParam("start", "Start time in unix timestamp")
  .addParam("end", "End time in unix timestamp")
  .addParam("growth", "New growth rate in USDC (6 decimals)")
  .setAction(async (taskArgs, hre) => {
    try {
      const presale = await hre.ethers.getContractAt("MySocialTokenPresale", taskArgs.contract);
      
      // First check remaining supply
      const remaining = await presale.remainingPresaleSupply();
      console.log("\nRemaining supply:", hre.ethers.formatUnits(remaining, 18), "MYSO");
      if (remaining <= 0) {
        throw new Error("No tokens remaining from previous phase");
      }

      // Check current state
      const isActive = await presale.presaleActive();
      const currentEndTime = await presale.presaleEndTime();
      const currentTime = Math.floor(Date.now() / 1000);
      console.log("\nCurrent state:");
      console.log("Active:", isActive);
      console.log("Current time > end time:", currentTime > Number(currentEndTime));
      
      // Convert parameters
      const startTime = BigInt(taskArgs.start);
      const endTime = BigInt(taskArgs.end);
      const growthRate = hre.ethers.parseUnits(taskArgs.growth, 6); // Convert to 6 decimals for USDC
      
      console.log("\nStarting new presale phase with parameters:");
      console.log("Start time:", new Date(Number(startTime) * 1000).toLocaleString());
      console.log("End time:", new Date(Number(endTime) * 1000).toLocaleString());
      console.log("Growth rate:", hre.ethers.formatUnits(growthRate, 6), "USDC");
      
      // Send transaction with timeout
      console.log("\nSending transaction...");
      const tx = await presale.startNewPresalePhase(
        startTime,
        endTime,
        growthRate,
        { gasLimit: 500000 } // Add explicit gas limit
      );
      
      console.log("Transaction hash:", tx.hash);
      console.log("Waiting for confirmation...");
      
      // Add timeout to wait
      const receipt = await Promise.race([
        tx.wait(),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error("Transaction timeout after 60 seconds")), 60000)
        )
      ]);
      
      console.log("Transaction confirmed in block:", receipt.blockNumber);
      
    } catch (error) {
      console.error("\nError occurred:");
      if (error.message) console.error("Message:", error.message);
      if (error.data) {
        console.error("Error data:", error.data);
        try {
          // Try to decode the error
          const iface = new hre.ethers.Interface([
            "error NoTokensRemaining()",
            "error PresaleStillActive()",
            "error InvalidTimeRange()"
          ]);
          const decoded = iface.parseError(error.data);
          console.error("Decoded error:", decoded.name);
        } catch (e) {
          console.error("Raw error data:", error.data);
        }
      }
      process.exit(1);
    }
  });

task("get-timestamp", "Converts a date to unix timestamp")
  .addParam("date", "Date in YYYY-MM-DD format")
  .addOptionalParam("time", "Time in HH:MM format (24h)", "00:00")
  .setAction(async (taskArgs) => {
    const date = new Date(`${taskArgs.date}T${taskArgs.time}:00Z`);
    const timestamp = Math.floor(date.getTime() / 1000);
    console.log(`Date: ${date.toISOString()}`);
    console.log(`Timestamp: ${timestamp}`);
  });

task("toggle-presale", "Toggles the presale state")
  .addParam("contract", "The presale contract address")
  .setAction(async (taskArgs, hre) => {
    try {
      const presale = await hre.ethers.getContractAt("MySocialTokenPresale", taskArgs.contract);
      const [signer] = await hre.ethers.getSigners();
      
      // Get current state and ownership info
      const currentState = await presale.presaleActive();
      const owner = await presale.owner();
      const signerAddress = await signer.getAddress();
      
      console.log("\nContract Info:");
      console.log("Owner:", owner);
      console.log("Signer:", signerAddress);
      console.log("Is Owner:", owner.toLowerCase() === signerAddress.toLowerCase());
      console.log("Current presale state:", currentState);
      
      // Toggle presale
      console.log("\nToggling presale state...");
      const tx = await presale.togglePresale();
      console.log("Transaction hash:", tx.hash);
      
      console.log("Waiting for confirmation...");
      const receipt = await tx.wait();
      console.log("Gas used:", receipt.gasUsed.toString());
      
      // Verify new state
      const newState = await presale.presaleActive();
      console.log("\nPresale state updated:");
      console.log("Previous state:", currentState);
      console.log("New state:", newState);
      
      if (currentState === newState) {
        console.log("\nWARNING: State did not change!");
        console.log("This might be because:");
        console.log("1. Transaction reverted silently");
        console.log("2. Contract has additional conditions preventing toggle");
        console.log("3. Another transaction changed state in between");
      }
      
    } catch (error) {
      console.error("\nError:", error.message);
      if (error.data) {
        console.error("Error data:", error.data);
      }
      process.exit(1);
    }
  });

task("withdraw-usdc", "Withdraws USDC from the presale contract")
  .addParam("contract", "The presale contract address")
  .addOptionalParam("nonce", "Custom nonce for the transaction")
  .setAction(async (taskArgs, hre) => {
    const { ethers } = hre;
    const presale = await ethers.getContractAt("MySocialTokenPresale", taskArgs.contract);
    
    // Get contract info
    const owner = await presale.owner();
    const signer = await ethers.provider.getSigner();
    const signerAddress = await signer.getAddress();
    
    console.log("\nContract Info:");
    console.log("Owner:", owner);
    console.log("Signer:", signerAddress);
    console.log("Is Owner:", owner.toLowerCase() === signerAddress.toLowerCase());
    
    // Prepare transaction options
    const txOptions = {};
    if (taskArgs.nonce) {
      txOptions.nonce = parseInt(taskArgs.nonce);
    }
    
    console.log("\nWithdrawing USDC...");
    const tx = await presale.withdrawUsdc(txOptions);
    console.log("Transaction hash:", tx.hash);
    console.log("Waiting for confirmation...");
    await tx.wait();
    console.log("USDC withdrawn successfully!");
  });

// Import the volume generator bot functions
const volumeGeneratorBot = require('./scripts/volume-generator-bot');

// Volume generator bot tasks
task("create-wallets", "Create trading bot wallets")
  .setAction(async (taskArgs, hre) => {
    await volumeGeneratorBot.createWallets(hre.ethers.provider);
  });

task("fund-wallets", "Fund bot wallets with ETH and USDC")
  .setAction(async (taskArgs, hre) => {
    await volumeGeneratorBot.fundWallets(hre.ethers.provider);
  });

task("test-trade", "Test a single trade with the volume bot")
  .setAction(async (taskArgs, hre) => {
    await volumeGeneratorBot.testTrade(hre.ethers.provider);
  });

task("start-bot", "Start the automated trading bot")
  .setAction(async (taskArgs, hre) => {
    await volumeGeneratorBot.startBot(hre.ethers.provider);
  });

task("deactivate-wallets", "Deactivate a number of trading bot wallets")
  .addParam("count", "Number of wallets to deactivate", 1, types.int)
  .setAction(async (taskArgs, hre) => {
    await volumeGeneratorBot.deactivateWallets(taskArgs.count);
  });

// Main combined task for the volume generator bot
task("volume-generator", "Run the volume generator bot with specified commands")
  .addPositionalParam("command", "Command to run: create-wallets, fund-wallets, test-trade, start, deactivate")
  .addOptionalPositionalParam("count", "Number of wallets to process (for deactivate command)", 1, types.int)
  .setAction(async (taskArgs, hre) => {
    // Set environment variables for the script
    process.env.BOT_COMMAND = taskArgs.command;
    process.env.WALLET_COUNT = taskArgs.count.toString();
    
    // Run the main function from the bot script
    await volumeGeneratorBot.main();
  });