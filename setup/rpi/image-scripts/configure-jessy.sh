#! bin/sh
# Note: This executes directly on the RPI, we cant source local resources.

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

abort() {
	echo -e "${RED}ABORT: $1${NC}"
	exit 1;
}

ask() {
	echo -e "${CYAN}$1${NC}"
}

inform() {
	echo -e "${GREEN}$1${NC}"
}

### Branding ###
inform "Start branding..."

# Set SSH Banner
inform "Configuring SSH banner..."
sudo cp ~/static/motd /etc/motd

### Dependency Installation ### 
inform "Start dependency installation..."

# Update apt
inform "Updating apt..."
sudo rm -f /etc/apt/sources.list.d/unstable.list
(sudo apt-get update &&  sudo apt-get -y upgrade) || abort 'Failed to update apt.'

# Install zerotier
(sudo apt-get install -y zerotier) || abort 'Failed to install zerotier'

# Install Python Dependencies
inform "Installing python dependencies..."
(sudo apt-get install -y python-qt4 python-pip) || abort 'Failed to install python-pip'
wget 'https://bootstrap.pypa.io/get-pip.py' || abort 'Failed to get pip install script.'

# Install Virtual environment for python
inform "Installing virtual environment."
sudo pip install virtualenv || abort 'Failed to install virtualenv'

# Install Electrum Globally for python 2.7
inform "Installing electrum."
sudo pip-2.7 install http://download.electrum.org/download/Electrum-2.4.tar.gz || abort 'Failed to install electrum globally.'

# Start Electrum Daemon on each boot
inform "Restarting electrum daemon."
electrum daemon stop
electrum daemon start || abort 'Failed to start the electrum daemon'

# Setup Electrum config file
inform "Setting inital electum config."
electrum setconfig two1 true

# Install Python 3.4
inform "Installing python 3.4"
echo 'deb http://ftp.debian.org/debian sid main' | sudo tee /etc/apt/sources.list.d/unstable.list
sudo apt-get update || abort 'Failed to update apt.'
(sudo apt-get install -y --force-yes python3.4 python3.4-dev ) || abort 'Failed to install python3.4'
sudo python3.4 get-pip.py || abort 'Failed to install python 3.4 pip'

# libxml, this step takes about 5 minutes
inform "Installing libxml: ~5min"
(sudo apt-get install -y --force-yes libxml2 libxslt-dev) || abort 'Failed to install libxml2 or libxslt-dev.'

# scipy, few hours
inform "Installing scipy: few hours..."
(sudo apt-get install -y --force-yes libblas-dev liblapack-dev gfortran) || abort 'Failed to install libxml2 or libxslt-dev.'
pip install scipy -v || abort 'Failed to install scipy'

# cython, 30 minutes
inform "Installing cython: 30 min"
pip install cython -v || abort 'Failed to install cython'

# Remove unstable
inform "Removing unstable"
sudo rm -f /etc/apt/sources.list.d/unstable.list
sudo apt-get update || abort 'Failed to update installs'
inform "Finished installing dependencies..."
