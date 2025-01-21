// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

contract MySocialTokenProxy is ERC1967Proxy {
    constructor(
        address _implementation,
        bytes memory _data
    ) ERC1967Proxy(_implementation, _data) {}

    receive() external payable {}
} 