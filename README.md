# self-hosted-mail

Personal project to implement a self hosted email within AWS using cdk.

## CDK Usage

1. install cdk tools following existing AWS instructions
2. Required parameters:
   These to be set up on AWS and passed in as context:

- `smtp_password_arn` - arn to a secrets manager smtp password
  - further notes about this upcoming. this needs to be set up per AWS instructions
- `smtp_username_arn` - arn to a secrets manager smtp username
- `elastic_ip` - ip that can be assigned to the instance
- `hostname` - domain that is owned that can be assigned to the instance

3. Optional parameters:
   These will be created if not provided. If they are created ahead of time and passed in as context, they will be used. Upon stack delete, the buckets will persist.

- `backup_s3_bucket` - backup bucket name
- `nextcloud_s3_bucket` - nextcloud bucket name

4. Run like: `cdk synth||deploy --context backup_s3_bucket=bucketname --context smtp_password_arn=arn:aws:secretsmanager:etcetc --context smtp_username_arn=arn:aws:secretsmanager:etcetc elastic_ip=123.21.13.132 domain=example.com nextcloud_s3_bucket=bucketname`

## TODO

I'm managing a project plan with github projects

1. Redo the entire original install process with cdk
2. Set up monitoring and alerting over EC2 & SES
3. Get out of SES sandbox
4. Once testing is complete, transfer my mail from it's current host to self host

## Initial Installation

I loosely followed this [guide](https://aws.amazon.com/blogs/opensource/fully-automated-deployment-of-an-open-source-mail-server-on-aws/).

#### Installation notes

1. I needed to change and add a few parameters since the cloudformation template notes seemed outdated.
2. I don't use AWS R53 with the domain I'm testing with. I needed to go to my hosting provider and set up the mail server config.
3. Cloudformation got stuck within the Creating step. However it wasn't fatal. I followed the notes in this [github issue](https://github.com/aws-samples/aws-opensource-mailserver/issues/1) to send to cloudformation a success message from the EC2 instance to ensure the install wasn't rolled back.
4. There were some interactions between some of the parameters that took a while to get right. Specifically the template works whether you are creating a new install or restoring from backup, but different parameters are needed depending upon the use case.
5. From the guide followed the instructions for setting up SSL/domain records, and SES in sandbox mode.
6. The status page for mailinabox is fantastic for figuring out configuration issues.

## Cost

1. Currently $10/month to run the EC2 server. Nothing else yet, but I'm also not really using mail capabilities.

## Why?

1. This is not for my gmail accounts. I do have issues with my custom domain emails, and would consider self-hosted-email for those accounts.
2. This is mostly for fun. I'm trying to learn more about AWS so why not use it for something real.
3. My custom domain email is either not set up, or is in a parked webhost. The webhost has horrible spam protection. I'd love to be able to manage spam myself, because anything would be an improvement.

## Code notes

- requires the black python formatter and will fail in github actions if not properly formatted
