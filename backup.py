import time
import json
import os
import requests
import boto3
import re
from time import gmtime, strftime
from urllib.parse import urlparse

class Atlassian:
    def __init__(self):

        if not self.check_config():
            print("Fatal: one or more configuration errors encountered")
            exit(1)
        if self.check_nothing_todo():
            exit(1)

        print('-> Starting backup; include attachments: {}'.format(os.environ['INCLUDE_ATTACHMENTS']))

        s3config = {}
        if os.environ['S3_REGION']:
            s3config["region_name"] = os.environ['S3_REGION']
        if os.environ['S3_ENDPOINT']:
            s3config["endpoint_url"] = os.environ['S3_ENDPOINT']

        self.session = requests.Session()
        self.s3 = boto3.client('s3', **s3config)
        self.session.auth = (os.environ['USER_EMAIL'], os.environ['API_TOKEN'])
        self.session.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})
        self.payload = {"cbAttachments": os.environ['INCLUDE_ATTACHMENTS'], "exportToCloud": "true"}
        self.start_confluence_backup = '{}/wiki/rest/obm/1.0/runbackup'.format(os.environ['HOST_URL'])
        self.start_jira_backup = '{}/rest/backup/1/export/runbackup'.format(os.environ['HOST_URL'])
        self.backup_status = {}
        self.wait = 30

    def check_config(self):
        config_errors=False
        # Check url
        if not "HOST_URL" in os.environ:
            print("Error: HOST_URL empty")
            config_errors=True
        else:
            url = urlparse(os.environ['HOST_URL'])
            if not url.hostname or "atlassian.net" not in url.hostname:
                print("Error: invalid HOST_URL")
                config_errors=True

        # Check email
        if not "USER_EMAIL" in os.environ or not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", os.environ['USER_EMAIL']):
            print("Error: invalid USER_EMAIL")
            config_errors=True
        
        # Check API Token
        if not "API_TOKEN" in os.environ or os.environ['API_TOKEN'] == "":
            print("Error: API_TOKEN")
            config_errors=True
        
        # Check include attachments option
        if not ("INCLUDE_ATTACHMENTS" in os.environ and 
                (os.environ['INCLUDE_ATTACHMENTS'] == "true" or os.environ['INCLUDE_ATTACHMENTS'] == "false")):
            print("Error: invalid value for INCLUDE_ATTACHMENTS option")
            config_errors=True

        # Check if S3_KEEP_LAST argument is valid
        if not "S3_KEEP_LAST" in  os.environ or not int(os.environ['S3_KEEP_LAST']) or not int(os.environ['S3_KEEP_LAST']) > 0:
            print("Error: invalid value for S3_KEEP_LAST")
            config_errors=True

        # Check if S3 Bucket name is valid
        if not "S3_BUCKET" in os.environ or not re.match(r"(?=^.{3,63}$)(?!^(\d+\.)+\d+$)(^(([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])\.)*([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])$)", os.environ['S3_BUCKET']):
            print("Error: invalid S3_BUCKET")
            config_errors=True

        if not ("BACKUP_JIRA" in os.environ and 
                (os.environ['BACKUP_JIRA'] == "true" or os.environ['BACKUP_JIRA'] == "false")):
            print("Error: invalid value for BACKUP_JIRA option")
            config_errors=True

        if not ("BACKUP_CONFLUENCE" in os.environ and 
                (os.environ['BACKUP_CONFLUENCE'] == "true" or os.environ['BACKUP_CONFLUENCE'] == "false")):
            print("Error: invalid value for BACKUP_CONFLUENCE option")
            config_errors=True

        return not config_errors

    def check_nothing_todo(self):
        if os.environ['BACKUP_CONFLUENCE'] == "false" and os.environ['BACKUP_JIRA'] == "false":
            print("Error: both BACKUP_CONFLUENCE and BACKUP_JIRA set to false - Nothing to do!")
            return True
        return False
    
    def create_confluence_backup(self):
        backup = self.session.post(self.start_confluence_backup, data=json.dumps(self.payload))
        if backup.status_code != 200:
            print("Error while starting confluence backup")
            print("Status code    : %s" % backup.status_code)
            print("Status message : %s" % backup.text)
            exit(1)
        else:
            print('-> Confluence backup process successfully started')
            confluence_backup_status = '{}/wiki/rest/obm/1.0/getprogress'.format(os.environ['HOST_URL'])
            time.sleep(self.wait)
            while 'fileName' not in self.backup_status.keys():
                self.backup_status = json.loads(self.session.get(confluence_backup_status).text)
                print('Current status: {description}'.format(description=self.backup_status['currentStatus']))
                time.sleep(self.wait)
            return '{url}/wiki/download/{file_name}'.format(
                url=os.environ['HOST_URL'], file_name=self.backup_status['fileName'])

    def create_jira_backup(self):
        backup = self.session.post(self.start_jira_backup, data=json.dumps(self.payload))
        if backup.status_code != 200:
            print("Error while starting jira backup")
            print("Status code    : %s" % backup.status_code)
            print("Status message : %s" % backup.text)
            exit(1)
        else:
            task_id = json.loads(backup.text)['taskId']
            print('-> Jira backup process successfully started: taskId={}'.format(task_id))
            jira_backup_status = '{jira_host}/rest/backup/1/export/getProgress?taskId={task_id}'.format(
                jira_host=os.environ['HOST_URL'], task_id=task_id)
            time.sleep(self.wait)
            while 'result' not in self.backup_status.keys():
                self.backup_status = json.loads(self.session.get(jira_backup_status).text)
                print('Current status: {status} - {progress}%'.format(
                    status=self.backup_status['status'], 
                    progress=self.backup_status['progress']))
                time.sleep(self.wait)
            return '{prefix}/{result_id}'.format(
                prefix=os.environ['HOST_URL'] + '/plugins/servlet', result_id=self.backup_status['result'])
    
    def s3_cleanup(self, prefix):

        print('-> Removing old backups from S3, prefix: %s' % prefix)
        objs = []
        kwargs = { 'Bucket': os.environ['S3_BUCKET'], 'Prefix': prefix }
        while True:
            resp = self.s3.list_objects_v2(**kwargs)
            for o in resp['Contents']:
                objs.append(o)
            try:
                kwargs['ContinuationToken'] = resp['NextContinuationToken']
            except KeyError:
                break

        get_last_modified = lambda obj: int(obj['LastModified'].strftime('%s'))
        keep = [s['Key'] for s in sorted(objs, key=get_last_modified, reverse=True)][:int(os.environ['S3_KEEP_LAST'])]

        for o in objs:
            if o['Key'] not in keep:
                kwargs = { 'Bucket': os.environ['S3_BUCKET'], 'Key': o['Key'] }
                self.s3.delete_object(**kwargs)

    def stream_to_s3(self, url, remote_filename):

        print('-> Streaming to S3')
        r = self.session.get(url, stream=True)

        with r as part:
            part.raw.decode_content = True
            conf = boto3.s3.transfer.TransferConfig(multipart_threshold=10000, max_concurrency=4)
            self.s3.upload_fileobj(part.raw, os.environ['S3_BUCKET'], remote_filename, Config=conf)
        return

if __name__ == '__main__':

    atlass = Atlassian()
    
    if os.environ['BACKUP_CONFLUENCE'] == "true":
        # Confluence backup
        confluence_backup_url = atlass.create_confluence_backup()
        print('-> Confluence Backup URL: {}'.format(confluence_backup_url))
        file_name = 'confluence_{timestamp}_{uuid}.zip'.format(
            timestamp=time.strftime('%Y%m%d_%H%M'), uuid=confluence_backup_url.split('/')[-1].replace('?fileId=', ''))

        atlass.stream_to_s3(confluence_backup_url, file_name)
        atlass.s3_cleanup('confluence')

    if os.environ['BACKUP_JIRA'] == "true":
        # Jira backup
        jira_backup_url = atlass.create_jira_backup()
        print('-> Jira Backup URL: {}'.format(jira_backup_url))
        file_name = 'jira_{timestamp}_{uuid}.zip'.format(
            timestamp=time.strftime('%Y%m%d_%H%M'), uuid=jira_backup_url.split('/')[-1].replace('?fileId=', ''))

        atlass.stream_to_s3(jira_backup_url, file_name)
        atlass.s3_cleanup('jira')
    