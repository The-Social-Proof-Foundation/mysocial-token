// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract UsernameRegistry is Ownable {
    IERC20 public mySoToken;

    // Struct to store username data
    struct UsernameData {
        address owner;
        uint256 timestamp;
    }

    // Mapping from username hash to username data
    mapping(bytes32 => UsernameData) public usernames;
    
    // Array to store recent username hashes
    bytes32[] public recentUsernames;
    uint256 public constant MAX_RECENT_USERNAMES = 100;
    
    // Add restricted usernames set
    mapping(string => bool) private restrictedUsernames;
    
    // Events
    event UsernameReserved(string username, address indexed owner);
    event UsernameReleased(string username, address indexed previousOwner);

    constructor(address _mySoToken) Ownable(msg.sender) {
        mySoToken = IERC20(_mySoToken);
        // Initialize restricted usernames
        restrictedUsernames["admin"] = true;
        restrictedUsernames["owner"] = true;
        restrictedUsernames["system"] = true;
        restrictedUsernames["moderator"] = true;
        restrictedUsernames["mod"] = true;
        restrictedUsernames["support"] = true;
        restrictedUsernames["help"] = true;
    }

    /**
     * @dev Reserves a username for the caller
     * @param username The username to reserve
     */
    function reserveUsername(string calldata username) external {
        require(mySoToken.balanceOf(msg.sender) >= 1e18, "Must hold at least 1 MySo token");
        require(bytes(username).length > 0, "Username cannot be empty");
        require(bytes(username).length <= 32, "Username too long");
        require(_isValidUsername(username), "Invalid username format");
        require(!restrictedUsernames[username], "Username is restricted");
        
        bytes32 usernameHash = keccak256(bytes(username));
        require(usernames[usernameHash].owner == address(0), "Username already taken");

        // Store username data
        usernames[usernameHash] = UsernameData({
            owner: msg.sender,
            timestamp: block.timestamp
        });

        // Add to recent usernames
        if (recentUsernames.length >= MAX_RECENT_USERNAMES) {
            // Remove oldest username
            for (uint i = 0; i < recentUsernames.length - 1; i++) {
                recentUsernames[i] = recentUsernames[i + 1];
            }
            recentUsernames.pop();
        }
        recentUsernames.push(usernameHash);

        emit UsernameReserved(username, msg.sender);
    }

    /**
     * @dev Releases a username
     * @param username The username to release
     */
    function releaseUsername(string calldata username) external {
        bytes32 usernameHash = keccak256(bytes(username));
        require(usernames[usernameHash].owner == msg.sender, "Not username owner");

        address previousOwner = usernames[usernameHash].owner;
        delete usernames[usernameHash];

        // Remove from recent usernames if present
        for (uint i = 0; i < recentUsernames.length; i++) {
            if (recentUsernames[i] == usernameHash) {
                // Shift remaining elements left
                for (uint j = i; j < recentUsernames.length - 1; j++) {
                    recentUsernames[j] = recentUsernames[j + 1];
                }
                recentUsernames.pop();
                break;
            }
        }

        emit UsernameReleased(username, previousOwner);
    }

    /**
     * @dev Gets the owner of a username
     * @param username The username to look up
     * @return owner The address of the username owner
     */
    function getUsernameOwner(string calldata username) external view returns (address owner) {
        bytes32 usernameHash = keccak256(bytes(username));
        return usernames[usernameHash].owner;
    }

    /**
     * @dev Gets the list of recent usernames
     * @param count The number of recent usernames to return
     * @return bytes32[] Array of username hashes
     */
    function getRecentUsernames(uint256 count) external view returns (bytes32[] memory) {
        uint256 resultCount = count > recentUsernames.length ? recentUsernames.length : count;
        bytes32[] memory result = new bytes32[](resultCount);
        
        for (uint256 i = 0; i < resultCount; i++) {
            result[i] = recentUsernames[recentUsernames.length - 1 - i];
        }
        
        return result;
    }

    /**
     * @dev Validates username format (alphanumeric and underscores only)
     * @param username The username to validate
     * @return bool Whether the username is valid
     */
    function _isValidUsername(string memory username) internal pure returns (bool) {
        bytes memory b = bytes(username);
        for (uint i = 0; i < b.length; i++) {
            bytes1 char = b[i];
            
            if (!(
                (char >= 0x30 && char <= 0x39) || // 0-9
                (char >= 0x41 && char <= 0x5A) || // A-Z
                (char >= 0x61 && char <= 0x7A) || // a-z
                char == 0x5F                       // _
            )) {
                return false;
            }
        }
        return true;
    }

    /**
     * @dev Checks if a username is restricted
     * @param username The username to check
     * @return bool Whether the username is restricted
     */
    function isRestricted(string calldata username) external view returns (bool) {
        return restrictedUsernames[username];
    }
}