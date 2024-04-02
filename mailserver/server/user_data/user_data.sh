#!/bin/bash -xe
ELASTIC_IP="${__ELASTIC_IP__}"
HOSTNAME="box.${__HOSTNAME__}"
NEXTCLOUD_BUCKET="${__NEXTCLOUD_BUCKET__}"
REGION="${__REGION__}"

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
export PUBLIC_IP=${!ELASTIC_IP}
export PUBLIC_IPV6=auto
export PRIMARY_HOSTNAME=${!HOSTNAME}
export SKIP_NETWORK_CHECKS=1
export NEXTCLOUD_S3_BUCKET=${!NEXTCLOUD_BUCKET}
export NEXTCLOUD_S3_REGION=${!REGION}

curl -s https://mailinabox.email/setup.sh | sudo -E bash
