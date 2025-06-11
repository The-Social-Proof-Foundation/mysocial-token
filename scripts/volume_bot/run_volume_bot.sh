#!/bin/bash
# Interactive menu for the Volume Generator Bot

# Colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Navigate to project root
cd "$(dirname "$0")/../.." || exit

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements if needed
if [ ! -f "venv/.requirements_installed" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r scripts/volume_bot/requirements.txt
    touch venv/.requirements_installed
fi

# Function to display the main menu
show_menu() {
    clear
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}       VOLUME GENERATOR BOT MENU        ${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${BLUE}1. Create Trading Wallets${NC}"
    echo -e "${BLUE}2. Fund Wallets${NC}"
    echo -e "${BLUE}3. Run Test Trade${NC}"
    echo -e "${BLUE}4. Start Continuous Trading${NC}"
    echo -e "${BLUE}5. Deactivate Wallets${NC}"
    echo -e "${BLUE}6. Edit Configuration${NC}"
    echo -e "${BLUE}7. View Wallet Information${NC}"
    echo -e "${BLUE}8. Exit${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo -e "Enter your choice [1-8]: "
}

# Function to create wallets
create_wallets() {
    echo -e "${YELLOW}How many wallets do you want to create?${NC}"
    read -r wallet_count
    
    if [[ "$wallet_count" =~ ^[0-9]+$ ]]; then
        echo -e "${GREEN}Creating $wallet_count wallets...${NC}"
        python -m scripts.volume_bot --command create-wallets --wallet-count "$wallet_count"
        echo -e "${GREEN}Wallet creation complete.${NC}"
    else
        echo -e "${YELLOW}Invalid input. Please enter a number.${NC}"
    fi
    
    read -n 1 -s -r -p "Press any key to continue..."
}

# Function to fund wallets
fund_wallets() {
    echo -e "${YELLOW}Please enter your treasury private key:${NC}"
    read -r treasury_key
    
    if [ -z "$treasury_key" ]; then
        echo -e "${YELLOW}No treasury key provided. Operation cancelled.${NC}"
        read -n 1 -s -r -p "Press any key to continue..."
        return
    fi
    
    echo -e "${YELLOW}How much ETH would you like to send to each wallet?${NC}"
    echo -e "${BLUE}(Recommended: 0.003 ETH minimum for several transactions)${NC}"
    read -r eth_amount_per_wallet
    
    # Validate input is a number
    if ! [[ "$eth_amount_per_wallet" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo -e "${YELLOW}Invalid ETH amount. Please enter a number.${NC}"
        read -n 1 -s -r -p "Press any key to continue..."
        return
    fi
    
    echo -e "${YELLOW}How much USDC would you like to send to each wallet?${NC}"
    read -r usdc_amount_per_wallet
    
    # Validate input is a number
    if ! [[ "$usdc_amount_per_wallet" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo -e "${YELLOW}Invalid USDC amount. Please enter a number.${NC}"
        read -n 1 -s -r -p "Press any key to continue..."
        return
    fi
    
    echo -e "${GREEN}Funding wallets with ${eth_amount_per_wallet} ETH and ${usdc_amount_per_wallet} USDC each...${NC}"
    python -m scripts.volume_bot --command fund-wallets --treasury-key "$treasury_key" --eth-amount "$eth_amount_per_wallet" --usdc-amount "$usdc_amount_per_wallet"
    echo -e "${GREEN}Wallet funding complete.${NC}"
    
    read -n 1 -s -r -p "Press any key to continue..."
}

# Function to run a test trade
test_trade() {
    echo -e "${GREEN}Running a test trade...${NC}"
    python -m scripts.volume_bot --command test-trade
    echo -e "${GREEN}Test trade complete.${NC}"
    
    read -n 1 -s -r -p "Press any key to continue..."
}

# Function to start continuous trading
start_trading() {
    echo -e "${YELLOW}Continuous trading will run until you press any key to stop.${NC}"
    
    echo -e "${GREEN}Starting continuous trading...${NC}"
    python -m scripts.volume_bot --command start
    
    # This will only execute if the trading stops
    echo -e "${GREEN}Trading stopped.${NC}"
    read -n 1 -s -r -p "Press any key to continue..."
}

# Function to deactivate wallets
deactivate_wallets() {
    echo -e "${YELLOW}How many wallets do you want to deactivate?${NC}"
    read -r wallet_count
    
    if [[ "$wallet_count" =~ ^[0-9]+$ ]]; then
        echo -e "${GREEN}Deactivating $wallet_count wallets...${NC}"
        python -m scripts.volume_bot --command deactivate --wallet-count "$wallet_count"
        echo -e "${GREEN}Wallet deactivation complete.${NC}"
    else
        echo -e "${YELLOW}Invalid input. Please enter a number.${NC}"
    fi
    
    read -n 1 -s -r -p "Press any key to continue..."
}

# Function to edit configuration
edit_config() {
    CONFIG_FILE="volume_generator_config.json"
    
    # Check if the config file exists, create it if not
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${YELLOW}Config file not found. Creating a default configuration...${NC}"
        python -m scripts.volume_bot --command test-trade --config "$CONFIG_FILE"
    fi
    
    # Determine which editor to use
    if command -v nano &> /dev/null; then
        EDITOR="nano"
    elif command -v vim &> /dev/null; then
        EDITOR="vim"
    elif command -v vi &> /dev/null; then
        EDITOR="vi"
    else
        echo -e "${YELLOW}No suitable text editor found (nano, vim, or vi).${NC}"
        read -n 1 -s -r -p "Press any key to continue..."
        return
    fi
    
    echo -e "${GREEN}Opening $CONFIG_FILE with $EDITOR...${NC}"
    $EDITOR "$CONFIG_FILE"
    
    echo -e "${GREEN}Configuration updated.${NC}"
    read -n 1 -s -r -p "Press any key to continue..."
}

# Function to view wallet information
view_wallet_info() {
    WALLETS_FILE="trading-wallets.json"
    
    if [ -f "$WALLETS_FILE" ]; then
        echo -e "${GREEN}Wallet information:${NC}"
        if command -v jq &> /dev/null; then
            # Pretty-print JSON if jq is available
            jq . "$WALLETS_FILE"
        else
            # Otherwise, just cat the file
            cat "$WALLETS_FILE"
        fi
    else
        echo -e "${YELLOW}No wallet information found. Create wallets first.${NC}"
    fi
    
    read -n 1 -s -r -p "Press any key to continue..."
}

# Main program loop
while true; do
    show_menu
    read -r choice
    
    case $choice in
        1) create_wallets ;;
        2) fund_wallets ;;
        3) test_trade ;;
        4) start_trading ;;
        5) deactivate_wallets ;;
        6) edit_config ;;
        7) view_wallet_info ;;
        8) 
            echo -e "${GREEN}Exiting. Goodbye!${NC}"
            deactivate
            exit 0
            ;;
        *)
            echo -e "${YELLOW}Invalid option. Please try again.${NC}"
            read -n 1 -s -r -p "Press any key to continue..."
            ;;
    esac
done 