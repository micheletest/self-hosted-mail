#!/bin/bash -xe
apt-get update
apt-get upgrade -o DPkg::Lock::Timeout=120 -y  

# Pre-Install. Arm64 is not supported by the duplicity ppa used by MIAB, so to get the correct version
# (1.0.1 at the time of creation) we use pip install (and install the required dependencies)
apt-get install -o DPkg::Lock::Timeout=120 -y \
librsync-dev \
python3-setuptools \
python3-pip \
python3-boto3 \
unzip \
intltool \
python-is-python3
pip3 install duplicity==1.0.1

# Configuration for mailinabox non-interactive
export STORAGE_ROOT=/home/user-data
export STORAGE_USER=user-data
export NONINTERACTIVE=1
export PUBLIC_IP=auto
export PUBLIC_IPV6=auto
export PRIMARY_HOSTNAME=auto
export SKIP_NETWORK_CHECKS=1

curl -s https://mailinabox.email/setup.sh | sudo -E bash
