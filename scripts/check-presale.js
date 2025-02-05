const { ethers } = require("hardhat");

async function main() {
  // The presale contract address from your deployment
  // Mainnet address: 0x8ffE0B3d3C743B5e3730693452058Ace3191a844
  const PRESALE_ADDRESS = "0x8ffE0B3d3C743B5e3730693452058Ace3191a844";
  try {
    // Get contract instance
    const presale = await ethers.getContractAt("MySocialTokenPresale", PRESALE_ADDRESS);
    
    // Get presale state
    const isActive = await presale.presaleActive();
    const startTime = await presale.presaleStartTime();
    const endTime = await presale.presaleEndTime();
    const totalSold = await presale.totalPresaleSold();
    const basePrice = await presale.basePrice();
    const growthRate = await presale.growthRate();

    // Get current time for comparison
    const currentTime = Math.floor(Date.now() / 1000);

    // Calculate actual active state
    const hasStarted = currentTime >= Number(startTime);
    const hasEnded = currentTime > Number(endTime);
    const isActuallyActive = isActive && hasStarted && !hasEnded;

    console.log("\nPresale Contract State");
    console.log("=====================");
    console.log("Address:", PRESALE_ADDRESS);
    console.log("Contract Active Flag:", isActive);
    console.log("Has Started:", hasStarted);
    console.log("Has Ended:", hasEnded);
    console.log("Can Buy Tokens:", isActuallyActive);
    console.log("Total Sold:", ethers.formatUnits(totalSold, 18), "MYSO");
    console.log("Base Price:", ethers.formatUnits(basePrice, 6), "USDC");
    console.log("Growth Rate:", ethers.formatUnits(growthRate, 6));

    console.log("\nTime Status");
    console.log("===========");
    console.log("Current Time:", new Date(currentTime * 1000).toLocaleString());
    console.log("Start Time:", new Date(Number(startTime) * 1000).toLocaleString());
    console.log("End Time:", new Date(Number(endTime) * 1000).toLocaleString());
    console.log("Time until start:", Number(startTime) - currentTime, "seconds");
    console.log("Time until end:", Number(endTime) - currentTime, "seconds");

  } catch (error) {
    console.error("Error:", error.message);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  }); 