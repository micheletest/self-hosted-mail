from aws_cdk import aws_s3 as s3
import aws_cdk as cdk

from constructs import Construct


class ObjectStoreInstance(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        backup_s3_bucket = self.node.try_get_context("backup_s3_bucket")
        nextcloud_s3_bucket = self.node.try_get_context("nextcloud_s3_bucket")

        if backup_s3_bucket:
            backup_bucket = s3.Bucket.from_bucket_name(
                self, "MailserverBackupBucket", backup_s3_bucket
            )
        else:
            # TODO: change RemovalPolicy to RETAIN once development is stable
            backup_bucket = s3.Bucket(
                self, "MailserverBackupBucket", removal_policy=cdk.RemovalPolicy.DESTROY
            )
        if nextcloud_s3_bucket:
            nextcloud_bucket = s3.Bucket.from_bucket_name(
                self, "MailserverNextcloudBucket", nextcloud_s3_bucket
            )
        else:
            # TODO: change RemovalPolicy to RETAIN once development is stable
            nextcloud_bucket = s3.Bucket(
                self,
                "MailserverNextcloudBucket",
                removal_policy=cdk.RemovalPolicy.DESTROY,
            )

        self.backup_mailserver_bucket = backup_bucket
        self.nextcloud_mailserver_bucket = nextcloud_bucket
