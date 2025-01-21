const { ethers } = require("hardhat");
const { run, upgrades } = require("hardhat");
const { parseEther } = require("ethers");

async function main() {
  // Deploy BondingCurveLib first
  const BondingCurveLib = await ethers.getContractFactory("BondingCurveLib");
  const bondingCurveLib = await BondingCurveLib.deploy();
  await bondingCurveLib.waitForDeployment();
  console.log("BondingCurveLib deployed to:", await bondingCurveLib.target);

  // Wait for a few blocks before verification
  await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds

  // Verify BondingCurveLib
  try {
    await run("verify:verify", {
      address: await bondingCurveLib.target,
      constructorArguments: []
    });
    console.log("BondingCurveLib verified on Basescan");
  } catch (error) {
    console.log("Error verifying BondingCurveLib:", error);
  }

  // Deploy MySocialToken with UUPS proxy
  const MySocialToken = await ethers.getContractFactory("MySocialToken", {
    libraries: {
      BondingCurveLib: bondingCurveLib.target,
    },
  });

  const signer = await ethers.provider.getSigner();
  const signerAddress = await signer.address;

  const token = await upgrades.deployProxy(MySocialToken, 
    ["MySocial", "MySo", signerAddress],
    { 
      initializer: 'initialize',
      unsafeAllowLinkedLibraries: true
    }
  );
  await token.waitForDeployment();
  console.log("MySocial Token proxy deployed to:", await token.getAddress());

  // Get implementation address for proxy
  const implementationAddress = await upgrades.erc1967.getImplementationAddress(await token.getAddress());
  
  // Verify MySocialToken implementation
  try {
    await run("verify:verify", {
      address: implementationAddress,
      constructorArguments: [],
      libraries: {
        BondingCurveLib: bondingCurveLib.target
      }
    });
    console.log("MySocialToken implementation verified on Basescan");
  } catch (error) {
    console.log("Error verifying MySocialToken implementation:", error);
  }

  // Deploy UsernameRegistry
  const UsernameRegistry = await ethers.getContractFactory("UsernameRegistry");
  const usernameRegistry = await UsernameRegistry.deploy(await token.getAddress());
  await usernameRegistry.waitForDeployment();
  console.log("UsernameRegistry deployed to:", await usernameRegistry.getAddress());

  // Verify UsernameRegistry
  try {
    await run("verify:verify", {
      address: await usernameRegistry.getAddress(),
      constructorArguments: [await token.getAddress()]
    });
    console.log("UsernameRegistry verified on Etherscan");
  } catch (error) {
    console.log("Error verifying UsernameRegistry:", error);
  }

  // Get proxy address for verification
  const proxyAddress = await token.getAddress();
  
  // Verify proxy contract
  try {
    await run("verify:verify", {
      address: proxyAddress,
      constructorArguments: []
    });
    console.log("MySocialToken proxy verified on Etherscan");
  } catch (error) {
    console.log("Error verifying MySocialToken proxy:", error);
  }

  // Deploy Presale contract
  const MySocialTokenPresale = await ethers.getContractFactory("MySocialTokenPresale", {
    libraries: {
      BondingCurveLib: bondingCurveLib.target,
    },
  });
  const presale = await MySocialTokenPresale.deploy(
    await token.getAddress(),
    "0x036CbD53842c5426634e7929541eC2318f3dCF7e", // USDC address on Base testnet
    ethers.parseUnits("100000000", 18), // 100M tokens with 18 decimals
    ethers.parseUnits("15000000", 18),   // 15M tokens with 18 decimals
    new Date('2025-01-20T18:00:00Z').getTime() / 1000,
    new Date('2025-01-20T18:00:00Z').getTime() / 1000 + 7 * 24 * 60 * 60,
    ethers.parseUnits("0.003", 6),   // basePrice in USDC (6 decimals)
    BigInt(400)   // growthRate = 0.0004 with 6 decimals = 400
  );
  await presale.waitForDeployment();
  console.log("Presale deployed to:", await presale.getAddress());

  // Verify Presale contract
  try {
    await run("verify:verify", {
      address: await presale.getAddress(),
      constructorArguments: [
        await token.getAddress(),
        "0x8A04d904055528a69f3E4594DDA308A31aeb8457", // USDC address
        ethers.parseUnits("100000000", 18), // 100M tokens with 18 decimals
        ethers.parseUnits("15000000", 18),   // 15M tokens with 18 decimals
        new Date('2025-01-23T18:00:00Z').getTime() / 1000,
        new Date('2025-01-23T18:00:00Z').getTime() / 1000 + 7 * 24 * 60 * 60,
        ethers.parseUnits("0.003", 6),   // basePrice in USDC (6 decimals)
        BigInt(400)   // growthRate = 0.0004 with 6 decimals = 400
      ],
      libraries: {
        BondingCurveLib: bondingCurveLib.target
      }
    });
    console.log("Presale contract verified on Basescan");
  } catch (error) {
    console.log("Error verifying Presale contract:", error);
  }

  // Set presale contract in token
  await token.setPresaleContract(await presale.getAddress());
  console.log("Presale contract set in token");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
});