import aws_cdk as core
import aws_cdk.assertions as assertions

from mailserver.component import Mailserver


# example tests. To run these tests, uncomment this file along with the example
# resource in cdk/cdk_stack.py
def test_mailserver_created():
    app = core.App()
    stack = Mailserver(app, "mailserver")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::EC2::Instance", {"InstanceType": "t2.micro"})
