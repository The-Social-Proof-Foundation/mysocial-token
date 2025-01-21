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
    
    // Change the recentUsernames array to store structs with both hash and name
    struct RecentUsername {
        bytes32 hash;
        string name;
    }
    
    // Update the storage variable
    RecentUsername[] public recentUsernames;
    uint256 public constant MAX_RECENT_USERNAMES = 100;
    
    // Add restricted usernames set
    mapping(string => bool) private restrictedUsernames;
    
    // Add reverse mapping from address to username hash
    mapping(address => bytes32) public addressToUsername;
    
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
        
        // Clear any previous username for this address
        bytes32 previousUsernameHash = addressToUsername[msg.sender];
        if (previousUsernameHash != bytes32(0)) {
            delete usernames[previousUsernameHash];
        }

        // Store username data
        usernames[usernameHash] = UsernameData({
            owner: msg.sender,
            timestamp: block.timestamp
        });
        
        // Update reverse mapping
        addressToUsername[msg.sender] = usernameHash;

        // Add to recent usernames
        if (recentUsernames.length >= MAX_RECENT_USERNAMES) {
            // Remove oldest username
            for (uint i = 0; i < recentUsernames.length - 1; i++) {
                recentUsernames[i] = recentUsernames[i + 1];
            }
            recentUsernames.pop();
        }
        recentUsernames.push(RecentUsername({
            hash: usernameHash,
            name: username
        }));

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
        delete addressToUsername[msg.sender];

        // Remove from recent usernames if present
        for (uint i = 0; i < recentUsernames.length; i++) {
            if (recentUsernames[i].hash == usernameHash) {
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
     * @return string[] Array of username strings
     */
    function getRecentUsernames(uint256 count) public view returns (string[] memory) {
        uint256 actualCount = count > recentUsernames.length ? recentUsernames.length : count;
        string[] memory result = new string[](actualCount);
        
        for(uint i = 0; i < actualCount; i++) {
            result[i] = recentUsernames[recentUsernames.length - 1 - i].name;
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

    /**
     * @dev Gets the username associated with an address
     * @param user The address to look up
     * @return username The username string, or empty string if no username is set
     */
    function getUsernameByAddress(address user) external view returns (string memory) {
        bytes32 usernameHash = addressToUsername[user];
        if (usernameHash == bytes32(0)) {
            return "";
        }
        
        // Find the username string from recentUsernames
        for (uint i = 0; i < recentUsernames.length; i++) {
            if (recentUsernames[i].hash == usernameHash) {
                return recentUsernames[i].name;
            }
        }
        
        return ""; // Return empty string if username not found in recent list
    }
}