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