# MySocial Token (MySo)

Smart contracts for the MySocial Token (MySo) - the native token powering the MySocial Blockchain.

## Overview

This repository contains the core smart contracts for:

- MySocial Token (MySo) - ERC20 token with bonding curve mechanics
- Token Presale Contract - Handles token distribution during presale phase
- Username Registry - On-chain username registration for MySocial Identity
- Bonding Curve Library - Price calculation logic for token economics

Try running some of the following tasks:

```shell
npx hardhat help
npx hardhat test
REPORT_GAS=true npx hardhat test
npx hardhat node
npx hardhat run scripts/deploy.js --network sepolia
npx hardhat run --network sepolia scripts/get-address.js
npx hardhat run scripts/check-presale.js --network sepolia
npx hardhat get-timestamp --date 2025-02-06 --time 18:00
npx hardhat start-presale-phase \                         
  --network sepolia \
  --contract 0xa7b9573230913218Ede3d1C94085cDc88FB535F0 \
  --start 1738864800 \
  --end 1739469600 \
  --growth 0.0145
npx hardhat toggle-presale \                           
  --network sepolia \
  --contract 0xa7b9573230913218Ede3d1C94085cDc88FB535F0
```

## Technical Stack

Built using:
- Solidity ^0.8.28
- OpenZeppelin Contracts v5.2.0
- OpenZeppelin Contracts Upgradeable v5.2.0
- Hardhat Development Environment v2.22.18

### Development Dependencies

- @nomicfoundation/hardhat-toolbox v5.0.0
- @nomicfoundation/hardhat-verify v2.0.0  
- @openzeppelin/hardhat-upgrades v3.0.0

## License

ISC License