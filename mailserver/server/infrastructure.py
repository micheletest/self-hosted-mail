from aws_cdk import aws_ec2 as ec2, aws_iam as iam, aws_s3 as s3, Fn

from constructs import Construct

VPC_CIDR = "0.0.0.0/0"
# TODO: define already created elastic ip
CDK_ELASTIC_IP = ""


class MailserverInstance(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        backup_s3_bucket = self.node.get_context("backup_s3_bucket")
        smtp_username_arn = self.node.get_context("smtp_username_arn")
        smtp_password_arn = self.node.get_context("smtp_password_arn")
        elastic_ip = self.node.get_context("elastic_ip")
        hostname = self.node.get_context("hostname")

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
            self, "MailserverBackupBucket", backup_s3_bucket
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
                            smtp_username_arn,
                            smtp_password_arn,
                        ],
                    ),
                ],
            )
        )

        mappings = {"__ELASTIC_IP__": elastic_ip, "__HOSTNAME__": hostname}

        with open("./mailserver/server/user_data/user_data.sh", "r") as user_data_h:
            user_data_sub = Fn.sub(user_data_h.read(), mappings)

        ec2_instance = ec2.Instance(
            self,
            "Instance",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=linux,
            vpc=vpc,
            role=role,
            security_group=sg,
            user_data=ec2.UserData.custom(user_data_sub),
        )

        eip = ec2.CfnEIP(self, "MailserverEIP")

        ec2.CfnEIPAssociation(
            self,
            "MailserverEIPAssociation",
            instance_id=ec2_instance.instance_id,
            eip=eip.ref,
        )
