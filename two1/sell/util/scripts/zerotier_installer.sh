#!/bin/sh
# Install ZeroTier and jq

wget -O zerotier-one https://s3-us-west-1.amazonaws.com/21-zerotier/zerotier-one-v6
chmod a+x zerotier-one

wget -O jq https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux32
chmod a+x jq

sudo ./zerotier-one -d
ln -s zerotier-one zerotier-cli
sudo ./zerotier-cli listnetworks

exit 0
