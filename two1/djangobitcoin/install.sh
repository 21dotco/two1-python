#!/bin/sh

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

abort () {
	echo "${RED}$1${NC}"
	exit -1;
}

# Install Dependencies
echo "Installing dependencies..."
sudo pip3 install -r requirements.txt || abort "Failed to install"
echo "${GREEN}Finished installing dependencies...${NC}"

# Compatibility Checks
echo "Checking system compatibility..."
python manage.py check --tag compatibility || abort "check failed"
echo "${GREEN}Finished installation...${NC}"
