import aws_cdk as cdk

from mailserver.component import Mailserver


app = cdk.App()
Mailserver(app, "Mailserver")

app.synth()
