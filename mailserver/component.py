from typing import Any

import aws_cdk as cdk
from constructs import Construct

from mailserver.server.infrastructure import MailserverInstance
from mailserver.object_store.infrastructure import ObjectStoreInstance


class Mailserver(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        **kwargs: Any,
    ):
        super().__init__(scope, id_, **kwargs)

        object_store = ObjectStoreInstance(self, "ObjectStoreInstance")

        self.server = MailserverInstance(
            self,
            "EC2Instance",
            self.region,
            backup_bucket=object_store.backup_mailserver_bucket,
            nextcloud_bucket=object_store.nextcloud_mailserver_bucket,
        )
