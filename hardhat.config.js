require("@nomicfoundation/hardhat-toolbox");
require("@openzeppelin/hardhat-upgrades");
require("@nomicfoundation/hardhat-verify");
require('dotenv').config();

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
      
      // Convert parameters to BigInt
      const startTime = BigInt(taskArgs.start);
      const endTime = BigInt(taskArgs.end);
      const growthRate = hre.ethers.parseUnits(taskArgs.growth, 6); // Convert to 6 decimals for USDC
      
      console.log("Starting new presale phase with parameters:");
      console.log("Start time:", new Date(Number(startTime) * 1000).toISOString());
      console.log("End time:", new Date(Number(endTime) * 1000).toISOString());
      console.log("Growth rate:", hre.ethers.formatUnits(growthRate, 6), "USDC");
      
      // Get current time for validation
      const currentTime = BigInt(Math.floor(Date.now() / 1000));
      
      // Validate parameters
      if (startTime <= currentTime) {
        throw new Error("Start time must be in the future");
      }
      if (endTime <= startTime) {
        throw new Error("End time must be after start time");
      }
      
      const tx = await presale.startNewPresalePhase(
        startTime,
        endTime,
        growthRate
      );
      
      console.log("Transaction hash:", tx.hash);
      console.log("Waiting for confirmation...");
      await tx.wait();
      console.log("New presale phase started successfully!");
      
    } catch (error) {
      console.error("Error:", error.message);
      if (error.data) {
        console.error("Error data:", error.data);
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