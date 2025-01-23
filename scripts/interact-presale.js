const { ethers } = require("hardhat");

async function main() {
    // Contract addresses from your deployment
    const PRESALE_ADDRESS = "0xa7b9573230913218Ede3d1C94085cDc88FB535F0";
    const TOKEN_ADDRESS = "0x8a9e9Ad05010aD980a1d24b61bC2a099B13D42a2";  // proxy address
    const USDC_ADDRESS = "0x036CbD53842c5426634e7929541eC2318f3dCF7e";   // Sepolia USDC

    // Get contract instances
    const presale = await ethers.getContractAt("MySocialTokenPresale", PRESALE_ADDRESS);
    const token = await ethers.getContractAt("MySocialToken", TOKEN_ADDRESS);
    const usdc = await ethers.getContractAt("IERC20", USDC_ADDRESS);

    // Get signer
    const signer = await ethers.provider.getSigner();
    const signerAddress = await signer.getAddress();

    console.log("Using address:", signerAddress);

    // 1. Check if presale is active
    const isActive = await presale.presaleActive();
    console.log("Presale active:", isActive);
    if (!isActive) {
        console.log("Enabling presale...");
        await presale.togglePresale(true);
        console.log("Presale enabled!");
    }

    // 2. Check USDC balance
    const usdcBalance = await usdc.balanceOf(signerAddress);
    console.log("USDC Balance:", ethers.formatUnits(usdcBalance, 6), "USDC");

    // 3. Approve USDC spending (0.0001 USDC)
    const approvalAmount = ethers.parseUnits("1.25", 6); // 1.25 USDC (6 decimals)
    console.log("Approving USDC spending...");
    const approveTx = await usdc.approve(PRESALE_ADDRESS, approvalAmount);
    await approveTx.wait();
    console.log("USDC approved!");

    // Check presale supply and limits
    const remainingPresaleSupply = await presale.remainingPresaleSupply();
    const totalPresaleTokens = await presale.totalPresaleTokens();
    const maxClaimPerWallet = await presale.maxClaimPerWallet();
    const currentWalletClaims = await presale.walletClaims(signerAddress);

    console.log("Remaining presale supply:", ethers.formatUnits(remainingPresaleSupply, 18), "MYSO");
    console.log("Total presale supply:", ethers.formatUnits(totalPresaleTokens, 18), "MYSO");
    console.log("Max claim per wallet:", ethers.formatUnits(maxClaimPerWallet, 18), "MYSO");
    console.log("Current wallet MySo supply:", ethers.formatUnits(currentWalletClaims, 18), "MYSO");

    // 4. Buy tokens (10 MySo tokens)
    console.log("Buying tokens...");
    const tokenAmount = ethers.parseUnits("26", 18); // Using 18 decimals to match ERC20 standard

    // Check both supply and claim limits
    if (tokenAmount > remainingPresaleSupply) {
        console.log("Requested amount exceeds remaining presale supply");
        return;
    }

    if (tokenAmount + currentWalletClaims > maxClaimPerWallet) {
        console.log("Requested amount would exceed max claim per wallet");
        return;
    }

    // Check price before purchase
    const price = await presale.getCurrentPresalePrice(tokenAmount);
    console.log("Price for", ethers.formatUnits(tokenAmount, 18), "MYSO:", 
                ethers.formatUnits(price, 6), "USDC");

    // Check if we have enough USDC
    const usdcNeeded = price;
    if (usdcBalance < usdcNeeded) {
        console.log("Insufficient USDC. You need", ethers.formatUnits(usdcNeeded, 6), 
                   "USDC but only have", ethers.formatUnits(usdcBalance, 6), "USDC");
        return;
    }

    // Only proceed if we have enough USDC
    console.log("Buying tokens...");
    const buyTx = await presale.buyPresaleTokens(tokenAmount);
    await buyTx.wait();
    console.log("Tokens purchased!");

    // 5. Check final balances
    const mysoBalance = await token.balanceOf(signerAddress);
    const finalUsdcBalance = await usdc.balanceOf(signerAddress);
    
    console.log("\nFinal Balances:");
    console.log("MYSO:", ethers.formatUnits(mysoBalance, 18), "MYSO");
    console.log("USDC:", ethers.formatUnits(finalUsdcBalance, 6), "USDC");
}

main()
    .then(() => process.exit(0))
    .catch(error => {
        console.error(error);
        process.exit(1);
    }); 