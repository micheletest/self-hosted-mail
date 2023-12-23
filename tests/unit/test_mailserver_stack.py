import json

import aws_cdk as cdk
import aws_cdk.assertions as assertions

from mailserver.component import Mailserver


with open("tests/unit/test_context.json") as tc:
    context = json.load(tc)["context"]


def test_mailserver_created():
    app = cdk.App(context=context)
    stack = Mailserver(app, "mailserver")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::EC2::Instance", {"InstanceType": "t2.micro"})
    template.resource_count_is("AWS::EC2::EIPAssociation", 1)
    template.has_resource_properties(
        "AWS::EC2::SecurityGroup",
        {"GroupDescription": "Mailserver Instance Security Group"},
    )
