import os
from aws_cdk import aws_ec2 as ec2, aws_iam as iam, aws_s3 as s3, aws_ssm as ssm

from constructs import Construct

VPC_CIDR = "0.0.0.0/0"
# TODO: fail if existing S3 bucket name isn't provided, or make it safe to rerun using removal policy
CDK_BACKUP_S3_BUCKET_NAME = os.getenv("CDK_BACKUP_S3_BUCKET_NAME", "")
CDK_SMTP_USER_NAME = os.getenv("CDK_SMTP_USER_NAME", "")
CDK_SMTP_PASSWORD = os.getenv("CDK_SMTP_PASSWORD", "")
# TODO: define already created elastic ip
CDK_ELASTIC_IP = ""


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

        smtp_user_name = ssm.StringParameter(
            self,
            "SMTPUserName",
            parameter_name="/mailserver/smtp-user-name",
            string_value=CDK_SMTP_USER_NAME,
            type=ssm.ParameterType.SECURE_STRING,
        )

        smtp_password = ssm.StringParameter(
            self,
            "SMTPPassword",
            parameter_name="/mailserver/smtp-password",
            string_value=CDK_SMTP_PASSWORD,
            type=ssm.ParameterType.SECURE_STRING,
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

        amzn_linux = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE,
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
                        actions=["ssm:GetParameter"],
                        resources=[
                            f"{smtp_user_name.parameter_arn}",
                            f"{smtp_password.parameter_arn}",
                        ],
                    ),
                ],
            )
        )

        ec2_instance = ec2.Instance(
            self,
            "Instance",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=amzn_linux,
            vpc=vpc,
            role=role,
            security_group=sg,
        )

        eip = ec2.CfnEIP(self, "MailserverEIP")

        ec2.CfnEIPAssociation(
            self,
            "MailserverEIPAssociation",
            instance_id=ec2_instance.instance_id,
            eip=eip.ref,
        )
