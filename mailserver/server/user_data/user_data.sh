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
# snap install duplicity --classic
# ln -s /snap/bin/duplicity /usr/bin/duplicity

# Install awscli and CloudFormation helper scripts
cd /tmp
curl "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
pip3 install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-py3-latest.tar.gz

# Storage
export STORAGE_ROOT=/home/user-data
export STORAGE_USER=user-data
