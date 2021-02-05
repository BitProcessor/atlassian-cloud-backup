[![Build status](https://img.shields.io/github/workflow/status/bitprocessor/atlassian-cloud-backup/Docker)](https://github.com/BitProcessor/atlassian-cloud-backup/actions?query=workflow%3ADocker)
[![License](https://img.shields.io/github/license/bitprocessor/atlassian-cloud-backup)](https://github.com/BitProcessor/atlassian-cloud-backup/blob/main/LICENSE)

![Atlassian Cloud Backup](images/atlassian-cloud-backup.png)

# Atlassian Cloud Backup
## What is this?
This project allows you to take a backup from Atlassian Cloud Jira & Confluence and stream it to an Amazon S3 bucket.

This fork has been modified for the `boto3` [AWS SDK for Python](https://github.com/boto/boto3)  and is optimized for automated usage via a Docker container.

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
    -e BACKUP_JIRA="true" \
    -e BACKUP_CONFLUENCE="true" \
    ghcr.io/bitprocessor/atlassian-cloud-backup:latest
```

### Kubernetes Cronjob
To use the container as a Kubernetes Cronjob, replace all placeholders with the actual values and apply the Cronjob manifest.
You'll probably want to use some form of secret encryption, but that is beyond the scope of this readme.

Note: make sure to specify the boolean values as a string, so `value: "true"` NOT `value: true`

The schedule is set to run at 02:14am, every Sunday. Change to suit your needs.

*(untested at this point, will update later)*

```
---
apiVersion: batch/v1beta1
kind: CronJob
metadata:
  name: atlassian-cloud-backup
  namespace: <namespace>
spec:
  schedule: "14 2 * * 0"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        metadata:
        spec:
          restartPolicy: Never
          containers:
          - name: atlassian-cloud-backup
            image: ghcr.io/bitprocessor/atlassian-cloud-backup:latest
            env:
            - name: AWS_ACCESS_KEY_ID
              value: <aws access key id>
            - name: AWS_SECRET_ACCESS_KEY
              value: <aws secret access key>
            - name: S3_BUCKET
              value: <s3 bucket>
            - name: INCLUDE_ATTACHMENTS
              value: "true"
            - name: HOST_URL
              value: https://<something>.atlassian.net
            - name: USER_EMAIL
              value: <email associated with api token>
            - name: API_TOKEN
              value: <atlassian api token>
            - name: BACKUP_JIRA
              value: "true"
            - name: BACKUP_CONFLUENCE
              value: "true"
            resources:
              requests:
                cpu: 50m
                memory: 64Mi
              limits:
                memory: 64Mi
```

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