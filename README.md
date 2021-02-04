[![Build status](https://img.shields.io/github/workflow/status/bitprocessor/atlassian-cloud-backup/Docker/main)](https://github.com/BitProcessor/atlassian-cloud-backup/actions?query=workflow%3ADocker)
[![License](https://img.shields.io/github/license/bitprocessor/atlassian-cloud-backup)](https://github.com/BitProcessor/atlassian-cloud-backup/blob/main/LICENSE)



# Atlassian Cloud Backup
## What is this?
This project allows you to take a backup from Atlassian Cloud Jira & Confluence and stream it to an S3 bucket.

It's based on another project that can be found here: https://github.com/datreeio/jira-backup-py

The version in this repo has been modified for the Python `boto3` library and is optimized for automated usage via a Docker container.

## Usage
### Atlassian API Token 
Start by creating an API Token for your Atlassian account: https://id.atlassian.com/manage-profile/security/api-tokens

### AWS
1. Create an S3 bucket
2. Create an IAM user on AWS with *Programmatic access*, note the Access Key ID and Secret Access Key and attach the following policy to it:
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::<s3 bucket>"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::<s3 bucket>/*"
        }
    ]
}
```
### Docker
To use the container, replace all placeholders with the actual values and run the following command:

```
docker run -it --rm \
    -e AWS_ACCESS_KEY_ID="<aws access key id>" \
    -e AWS_SECRET_ACCESS_KEY="<aws secret access key>" \
    -e S3_BUCKET="<s3 bucket>" \
    -e INCLUDE_ATTACHMENTS="true" \
    -e HOST_URL="https://<something>.atlassian.net" \
    -e USER_EMAIL="<email associated with api token>" \
    -e API_TOKEN="<atlassian api token>" \
    ghcr.io/bitprocessor/atlassian-cloud-backup:latest
```

### Kubernetes Cronjob
TODO

### Good to know
Note that both Jira & Confluence have a limit on backup frequency. 
If you run the container too often, you might end up with one or both of the following messages:

```
-> Starting backup; include attachments: true
Error while starting confluence backup
Status code    : 406
Status message : Backup frequency is limited. You can not make another backup right now. Approximate time till next allowed backup: 14h 19m
```

```
-> Starting backup; include attachments: true
Error while starting jira backup
Status code   : 412
Status message: {"error":"Backup frequency is limited. You cannot make another backup right now. Approximate time until next allowed backup: 26h 58m"}
```