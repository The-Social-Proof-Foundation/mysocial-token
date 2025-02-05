async function main() {
  const [signer] = await ethers.getSigners();
  console.log("Your wallet address:", await signer.address);
  
  // Get balance
  const balance = await ethers.provider.getBalance(signer.address);
  console.log("Balance:", ethers.formatEther(balance), "ETH");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  }); 