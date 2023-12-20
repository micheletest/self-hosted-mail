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

# ---------------- CONFIG
# Installer behaviour
export NONINTERACTIVE=true
export SKIP_NETWORK_CHECKS=true
# Storage
export STORAGE_ROOT=/home/user-data
export STORAGE_USER=user-data
# Network and DNS
export PRIVATE_IP=$(ec2metadata --local-ipv4)
export PUBLIC_IPV6=""
export PRIVATE_IPV6=""
export MTA_STS_MODE=enforce
export PRIMARY_HOSTNAME="${InstanceDns}.${MailInABoxDomain}"
if [[ -z "${InstanceEIP}" ]]; then
export PUBLIC_IP=$(ec2metadata --public-ipv4)
else
export PUBLIC_IP="${InstanceEIP}"
fi
# Setup Admin Account.
export EMAIL_ADDR="admin@${MailInABoxDomain}"
# If no admin password is specified generate a random one. In that case, we upload this randomly genereated PW to SSM if it's a fresh install
if [[ -z "${MailInABoxAdminPassword}" ]]; then
export EMAIL_PW=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 16 ; echo '')
if [[ -z "${RestorePrefix}" ]]; then
    aws ssm put-parameter \
        --overwrite \
        --name "/MailInABoxAdminPassword" \
        --type SecureString \
        --value "$EMAIL_PW"
fi
else
export EMAIL_PW=${MailInABoxAdminPassword}
fi
# Nextcloud config variables are picked up by the Mail-in-a-Box Setup script
export NEXTCLOUD_S3_BUCKET=${NextCloudS3Bucket}
export NEXTCLOUD_S3_REGION=$(aws s3api get-bucket-location --bucket $NEXTCLOUD_S3_BUCKET --query 'LocationConstraint' --output 'text')
[[ $NEXTCLOUD_S3_REGION == "None" ]]  && NEXTCLOUD_S3_REGION=us-east-1 
# Setup SMTP Relay if configured. Variables are picked up by the Mail-in-a-Box Setup script 
if [[ "${SesRelay}" == "true" ]]; then
export SMTP_RELAY_ENDPOINT="email-smtp.${AWS::Region}.amazonaws.com"
export SMTP_RELAY_PORT=587
export SMTP_RELAY_USER=$(aws ssm get-parameter --name "/smtp-username-${AWS::StackName}" --with-decryption --query Parameter.Value --output text)
export SMTP_RELAY_PASSWORD=$(aws ssm get-parameter --name "/smtp-password-${AWS::StackName}" --with-decryption --query Parameter.Value --output text)
fi

# ---------------- PRE INSTALL
useradd -m $STORAGE_USER
mkdir -p $STORAGE_ROOT
git clone ${MailInABoxCloneUrl} /opt/mailinabox
export TAG=${MailInABoxVersion}
cd /opt/mailinabox && git checkout $TAG

# ---------------- RESTORE
if [[ -n "${RestorePrefix}" ]]; then
# Restore files from S3 Backup
export S3_URL="s3://${BackupS3Bucket}/${RestorePrefix}"
# If we have a RestoreKey passed, use it, otherwise try to load from SSM Parameter.
if [[ -n "${RestoreKey}" ]]; then
    export PASSPHRASE_FULL="${RestoreKey}"
elif [[ -n "${RestoreKeySsmParameterName}" ]]; then
    PASSPHRASE_FULL=$(aws ssm get-parameter --name "/${RestoreKeySsmParameterName}" --with-decryption --query Parameter.Value --output text)
else
    echo "Either 'RestoreKey' or 'RestoreKeySsmParameterName' need to be passed if you want to restore from a Prefix!"
    exit -1
fi
# Only the first line of the passphrase is actually used: https://github.com/mail-in-a-box/mailinabox/issues/2209
# We save and pass the full passphrase, with space delimiters
export PASSPHRASE=$(echo $PASSPHRASE_FULL | awk '{print $1}')
duplicity restore --force $S3_URL $STORAGE_ROOT
# Continue using the secret key for subsequent backups
mkdir -p $STORAGE_ROOT/backup
echo $PASSPHRASE_FULL | tr ' ' '\n'  > $STORAGE_ROOT/backup/secret_key.txt
fi

# ---------------- INSTALL
cd /opt/mailinabox/ && setup/start.sh

# ---------------- POST INSTALL
# Configure networking according to https://aws.amazon.com/premiumsupport/knowledge-center/ec2-static-dns-ubuntu-debian/
INTERFACE=$(ip route list | grep default | grep -E  'dev (\w+)' -o | awk '{print $2}')
cat <<EOT > /etc/netplan/99-custom-dns.yaml
network:
version: 2
ethernets:
    $INTERFACE:         
        nameservers:
        addresses: [127.0.0.1]
        dhcp4-overrides:
        use-dns: false
EOT
netplan apply

# Configure Backups, create a new backup folder for instance and trigger an initial backup
export RESTORE_S3_REGION=$(aws s3api get-bucket-location --bucket ${BackupS3Bucket} --query 'LocationConstraint' --output 'text')
[[ $RESTORE_S3_REGION == "None" ]]  && RESTORE_S3_REGION=us-east-1 
export INSTANCE_ID=$(ec2metadata --instance-id)
echo "Mail-in-a-box ($TAG) backups for instance $INSTANCE_ID created on $(date -Im) " > /tmp/README.txt
aws s3 cp /tmp/README.txt s3://${BackupS3Bucket}/$INSTANCE_ID/README.txt
mkdir -p $STORAGE_ROOT/backup
cat <<EOT > $STORAGE_ROOT/backup/custom.yaml
min_age_in_days: 7
target: s3://s3.$RESTORE_S3_REGION.amazonaws.com/${BackupS3Bucket}/$INSTANCE_ID
target_user: ""
target_pass: ""
EOT
# Save 'RestoreKey' or 'RestoreKeySsmParameterName' that were passed locally or upload newly created in case this is a new install
if [[ -z "${RestorePrefix}" ]]; then
if [[ -n "${RestoreKey}" ]]; then
    echo "${RestoreKey}" | tr ' ' '\n'  > $STORAGE_ROOT/backup/secret_key.txt
elif [[ -n "${RestoreKeySsmParameterName}" ]]; then
    # check if SSM Parameter exists. If yes retrieve and use it going forward. If not, save the freshly generated key to SSM
    restore_key_param_exists="$(aws ssm describe-parameters --filters "Key=Name,Values=/${RestoreKeySsmParameterName}" --query Parameters --output text )"
    if [[ -n "$restore_key_param_exists" ]]; then
    aws ssm get-parameter --name "/${RestoreKeySsmParameterName}" --with-decryption --query Parameter.Value --output text | tr ' ' '\n'  > $STORAGE_ROOT/backup/secret_key.txt
    else
    aws ssm put-parameter \
        --overwrite \
        --name "/${RestoreKeySsmParameterName}" \
        --type SecureString \
        --value "$(cat $STORAGE_ROOT/backup/secret_key.txt |tr '\n' ' ' )"
    fi
fi
fi

# Create Initial Backup
/opt/mailinabox/management/backup.py

# Clear logs for key contents
rm /var/lib/cloud/instances/$INSTANCE_ID/scripts/part-00* \
    /var/lib/cloud/instances/$INSTANCE_ID/user-data.txt* \
    /var/lib/cloud/instances/$INSTANCE_ID/obj.pkl

# Signal Success to CloudFormation
/usr/local/bin/cfn-signal --success true --stack ${AWS::StackId} --resource EC2Instance --region ${AWS::Region}
# Reboot
reboot
