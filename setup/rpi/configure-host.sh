#! /bin/sh

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

abort() {
	echo "${RED}ABORT: $1${NC}"
	exit 1;
}

ask() {
	echo "${CYAN}$1${NC}"
}

inform() {
	echo "${GREEN}$1${NC}"
}

# Check for help
Host=$1
ConfigurationScriptPath=$2

# SSH Into RPI & Execute Configuration script
inform "Uploading static payload for configuration."
inform "Remove existing static files"
(ssh ${Host} "sudo rm -r ~/static")
inform "Make static payload dir."
(ssh ${Host} "mkdir ~/static") || abort "Failed to create static payload dir on target host."
inform "Upload static payload."
(scp static/* ${Host}:~/static) || abort "Failed to upload static payload to target host."

inform "Executing '${ConfigurationScriptPath}' on target host."
(ssh ${Host} "bash -s" < ${ConfigurationScriptPath}) || abort "Failed execute configuration script."

inform "Finished configuration..."