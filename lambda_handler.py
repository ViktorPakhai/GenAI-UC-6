import os
import json
import boto3
from datetime import datetime

def get_volumes_and_snapshots(ec2):
    unattached_volumes = {}
    unencrypted_volumes = {}
    unencrypted_snapshots = {}

    # Get all volumes
    paginator_volumes = ec2.get_paginator('describe_volumes')
    for page_volumes in paginator_volumes.paginate():
        for volume in page_volumes['Volumes']:
            volume_id = volume['VolumeId']

            # Check if volume is unattached
            if len(volume['Attachments']) == 0:
                unattached_volumes[volume_id] = volume

            # Check if volume is unencrypted
            if not volume['Encrypted']:
                unencrypted_volumes[volume_id] = volume

    # Get all snapshots
    paginator_snapshots = ec2.get_paginator('describe_snapshots')
    for page_snapshots in paginator_snapshots.paginate(OwnerIds=['self']):
        for snapshot in page_snapshots['Snapshots']:
            snapshot_id = snapshot['SnapshotId']

            # Check if snapshot is unencrypted
            if not snapshot['Encrypted']:
                unencrypted_snapshots[snapshot_id] = snapshot

    return unattached_volumes, unencrypted_volumes, unencrypted_snapshots


def save_report_to_s3(report, bucket_name, report_name):
    s3 = boto3.client('s3')
    report_json = json.dumps(report, default=str)
    s3.put_object(Body=report_json, Bucket=bucket_name, Key=report_name)


def lambda_handler(event, context):
    region_name = os.environ['REGION_NAME']
    ec2 = boto3.client('ec2', region_name=region_name)

    bucket_name = os.environ['BUCKET_NAME']
    report_name = os.environ['REPORT_NAME'] + '_' + datetime.now().strftime("%Y%m%d%H%M%S") + '.json'

    unattached_volumes, unencrypted_volumes, unencrypted_snapshots = get_volumes_and_snapshots(ec2)

    # Create a report
    report = {
        'UnattachedVolumes': unattached_volumes,
        'UnencryptedVolumes': unencrypted_volumes,
        'UnencryptedSnapshots': unencrypted_snapshots
    }

    save_report_to_s3(report, bucket_name, report_name)

    print(f"Report saved to s3://{bucket_name}/{report_name}")

    return {
        'statusCode': 200,
        'body': json.dumps('Metrics collected and report saved to S3 bucket.')
    }

