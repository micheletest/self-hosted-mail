import os
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
)

from constructs import Construct

VPC_CIDR = "0.0.0.0/0"
# TODO: fail if existing S3 bucket name isn't provided, or make it safe to rerun using removal policy
# NOTE: following are existing resources that MUST exist for this stack
CDK_BACKUP_S3_BUCKET_NAME = os.getenv("CDK_BACKUP_S3_BUCKET_NAME", "unset")
CDK_SMTP_USERNAME_SECRET_ARN = os.getenv("CDK_SMTP_USERNAME_SECRET_ARN", "")
CDK_SMTP_PASSWORD_SECRET_ARN = os.getenv("CDK_SMTP_PASSWORD_SECRET_ARN", "")
# TODO: define already created elastic ip
CDK_ELASTIC_IP = ""

with open("./mailserver/server/user_data/user_data.sh") as f:
    user_data = f.read()


class MailserverInstance(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(
            self,
            "VPC",
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC
                )
            ],
        )

        backup_bucket = s3.Bucket.from_bucket_name(
            self, "MailserverBackupBucket", CDK_BACKUP_S3_BUCKET_NAME
        )

        sg = ec2.SecurityGroup(
            self,
            id="MailserverSG",
            vpc=vpc,
            allow_all_outbound=True,
            description="Mailserver Instance Security Group",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(80),
            description="HTTP ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(443),
            description="HTTPS ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(22),
            description="SSH ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(53),
            description="DNS (TCP) ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.udp(53),
            description="DNS (UDP) ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(25),
            description="SMTP (STARTTLS) ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(143),
            description="IMAP (STARTTLS) ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(993),
            description="IMAPS ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(465),
            description="SMTPS ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(587),
            description="SMTP Submission ingress",
        )
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(VPC_CIDR),
            connection=ec2.Port.tcp(4190),
            description="Sieve Mail filtering ingress",
        )

        linux = ec2.MachineImage.generic_linux(
            {
                "us-east-1": "ami-0e783882a19958fff",
            }
        )

        role = iam.Role(
            self, "MailserverSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        role.attach_inline_policy(
            iam.Policy(
                self,
                "MailserverPolicy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["s3:*"],
                        resources=[
                            f"{backup_bucket.bucket_arn}",
                            f"{backup_bucket.bucket_arn}\*",
                        ],
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["secretsmanager:GetSecretValue"],
                        resources=[
                            CDK_SMTP_PASSWORD_SECRET_ARN,
                            CDK_SMTP_USERNAME_SECRET_ARN,
                        ],
                    ),
                ],
            )
        )

        ec2_instance = ec2.Instance(
            self,
            "Instance",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=linux,
            vpc=vpc,
            role=role,
            security_group=sg,
            user_data=ec2.UserData.custom(user_data),
        )

        eip = ec2.CfnEIP(self, "MailserverEIP")

        ec2.CfnEIPAssociation(
            self,
            "MailserverEIPAssociation",
            instance_id=ec2_instance.instance_id,
            eip=eip.ref,
        )
