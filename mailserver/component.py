from typing import Any

import aws_cdk as cdk
from constructs import Construct

from mailserver.server.infrastructure import MailserverInstance


class Mailserver(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        **kwargs: Any,
    ):
        super().__init__(scope, id_, **kwargs)

        self.server = MailserverInstance(self, "EC2Instance")
