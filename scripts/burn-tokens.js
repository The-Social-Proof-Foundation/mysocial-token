const { ethers } = require("hardhat");

async function main() {
  // Configuration - update these values
  const TOKEN_ADDRESS = "0xFdD6013Bf2757018D8c087244f03e5a521B2d3B7"; // Your token proxy address
  
  // Amount of tokens to burn - adjust as needed
  const AMOUNT_TO_BURN = "218525999"; 

  // Get signer (the address calling this script)
  const [signer] = await ethers.getSigners();
  const signerAddress = await signer.getAddress();
  
  // The script will burn tokens from the signer's address
  const ADDRESS_TO_BURN_FROM = signerAddress;

  console.log("Burning tokens using Hardhat...");
  console.log(`Token Contract: ${TOKEN_ADDRESS}`);
  console.log(`Burning from: ${ADDRESS_TO_BURN_FROM} (your wallet address)`);
  console.log(`Amount: ${AMOUNT_TO_BURN} MYSO`);

  // Get token contract instance
  const token = await ethers.getContractAt("MySocialToken", TOKEN_ADDRESS);
  
  // Check if signer is owner or presale contract
  const owner = await token.owner();
  const presaleContract = await token.presaleContract();
  console.log(`Contract owner: ${owner}`);
  console.log(`Presale contract: ${presaleContract}`);
  console.log(`Is signer the owner: ${owner.toLowerCase() === signerAddress.toLowerCase()}`);
  console.log(`Is signer the presale contract: ${presaleContract.toLowerCase() === signerAddress.toLowerCase()}`);
  
  if (owner.toLowerCase() !== signerAddress.toLowerCase() && presaleContract.toLowerCase() !== signerAddress.toLowerCase()) {
    console.error("Error: You are not authorized to burn tokens (must be owner or presale contract)");
    return;
  }

  // Convert amount to wei (with 18 decimals)
  const amountInWei = ethers.parseUnits(AMOUNT_TO_BURN, 18);
  
  // Get current balance and total supply
  const currentBalance = await token.balanceOf(ADDRESS_TO_BURN_FROM);
  const totalSupply = await token.totalSupply();
  
  console.log(`Current balance of ${ADDRESS_TO_BURN_FROM}: ${ethers.formatUnits(currentBalance, 18)} MYSO`);
  console.log(`Current total supply: ${ethers.formatUnits(totalSupply, 18)} MYSO`);
  
  if (currentBalance < amountInWei) {
    console.error(`Error: Not enough tokens to burn. Available: ${ethers.formatUnits(currentBalance, 18)} MYSO`);
    return;
  }

  // Execute the burn function
  console.log(`\nBurning ${AMOUNT_TO_BURN} MYSO tokens from ${ADDRESS_TO_BURN_FROM}...`);
  const tx = await token.burnFrom(ADDRESS_TO_BURN_FROM, amountInWei);
  console.log(`Transaction hash: ${tx.hash}`);
  
  // Wait for transaction confirmation
  console.log("Waiting for confirmation...");
  const receipt = await tx.wait();
  console.log(`Transaction confirmed in block ${receipt.blockNumber}`);
  console.log("Tokens burned successfully!");
  
  // Show updated balance and supply
  const newBalance = await token.balanceOf(ADDRESS_TO_BURN_FROM);
  const newTotalSupply = await token.totalSupply();
  console.log(`\nNew balance of ${ADDRESS_TO_BURN_FROM}: ${ethers.formatUnits(newBalance, 18)} MYSO`);
  console.log(`New total supply: ${ethers.formatUnits(newTotalSupply, 18)} MYSO`);
  console.log(`Total tokens burned: ${ethers.formatUnits(totalSupply - newTotalSupply, 18)} MYSO`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  }); 