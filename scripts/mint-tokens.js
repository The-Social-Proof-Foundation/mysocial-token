const { ethers } = require("hardhat");

async function main() {
  // Configuration - update these values
  const TOKEN_ADDRESS = "0xFdD6013Bf2757018D8c087244f03e5a521B2d3B7"; // Your token proxy address
  
  // Amount of tokens to mint - adjust as needed
  const AMOUNT_TO_MINT = "2"; 

  // Get signer (the address calling this script)
  const signer = await ethers.provider.getSigner();
  const signerAddress = await signer.getAddress();
  
  // The script will mint tokens to the signer's address
  const RECIPIENT_ADDRESS = signerAddress;

  console.log("Minting tokens using Hardhat...");
  console.log(`Token Contract: ${TOKEN_ADDRESS}`);
  console.log(`Recipient: ${RECIPIENT_ADDRESS} (your wallet address)`);
  console.log(`Amount: ${AMOUNT_TO_MINT} MYSO`);

  // Get token contract instance
  const token = await ethers.getContractAt("MySocialToken", TOKEN_ADDRESS);
  
  // Check if signer is owner
  const owner = await token.owner();
  console.log(`Contract owner: ${owner}`);
  console.log(`Is signer the owner: ${owner.toLowerCase() === signerAddress.toLowerCase()}`);
  
  if (owner.toLowerCase() !== signerAddress.toLowerCase()) {
    console.error("Error: You are not the owner of this contract");
    return;
  }

  // Convert amount to wei (with 18 decimals)
  const amountInWei = ethers.parseUnits(AMOUNT_TO_MINT, 18);
  
  // Get current total supply
  const totalSupply = await token.totalSupply();
  const supplyCap = await token.getTotalSupplyCap();
  
  console.log(`Current supply: ${ethers.formatUnits(totalSupply, 18)} MYSO`);
  console.log(`Supply cap: ${ethers.formatUnits(supplyCap, 18)} MYSO`);
  
  if (totalSupply + amountInWei > supplyCap) {
    console.error(`Error: Minting ${AMOUNT_TO_MINT} tokens would exceed the total supply cap`);
    return;
  }

  // Execute the mint function
  console.log(`\nMinting ${AMOUNT_TO_MINT} MYSO tokens to ${RECIPIENT_ADDRESS}...`);
  const tx = await token.mint(RECIPIENT_ADDRESS, amountInWei);
  console.log(`Transaction hash: ${tx.hash}`);
  
  // Wait for transaction confirmation
  console.log("Waiting for confirmation...");
  const receipt = await tx.wait();
  console.log(`Transaction confirmed in block ${receipt.blockNumber}`);
  console.log("Tokens minted successfully!");
  
  // Show updated balance
  const balance = await token.balanceOf(RECIPIENT_ADDRESS);
  console.log(`\nNew balance of ${RECIPIENT_ADDRESS}: ${ethers.formatUnits(balance, 18)} MYSO`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  }); 