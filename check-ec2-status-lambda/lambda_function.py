import boto3
import os
import json
import urllib.request

region = boto3.Session().region_name or 'ap-northeast-1'
ec2 = boto3.client('ec2', region_name = region)

def notify_slack(message, url):
    content = json.dumps({"text": message})
    try:
        request = urllib.request.Request(
            url,
            data=content.encode('utf-8'),
            method="POST"
        )
        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode('utf-8')
    except Exception as e:
        print(f'Slack notification error: {e}')

def check_ec2_status():
    try:
        response = ec2.describe_instances()
        instance_data = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                instance_type = instance['InstanceType']
                instance_name = ''
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                instance_data.append({
                    'InstanceId': instance_id,
                    'State': instance_state,
                    'InstanceType': instance_type,
                    'Name': instance_name
                })
        return instance_data
    except Exception as e:
        print(f"EC2 check error: {e}")
        return None

def format_ec2_status(instance_data, region):
    line = "────────────────────────────\n"
    if instance_data:
        message = line
        message += f"■ EC2 Instances Status ({region}):\n"
        message += line
        for i, instance in enumerate(instance_data):
            message += f"[{i+1}] `{instance['Name']}` (type: {instance['InstanceType']}): *{instance['State']}*\n"
        message += line
        return message
    else:
        message = line
        message += f"*No EC2 instances found in {region}.*\n"
        message += line
        return message

def lambda_handler(event, context):
    slack_url = os.environ.get('SLACK_WEBHOOK_URL')
    if not slack_url:
        print("SLACK_WEBHOOK_URL environment variable is not set. Check EC2 status only.")
        instance_data = check_ec2_status()
        message = format_ec2_status(instance_data, region)
        print(message)
        return {
            'statusCode': 200,
            'body': 'SLACK_WEBHOOK_URL is not set. Checked EC2 status.'
        }

    instance_data = check_ec2_status()
    if instance_data is None:
        error_message = f"Failed to retrieve EC2 instance status in {region}."
        print(error_message)
        notify_slack(error_message, slack_url)
        return {
            'statusCode': 500,
            'body': error_message
        }

    message = format_ec2_status(instance_data, region)
    print(message)
    notify_slack(message, slack_url)

    return {
        'statusCode': 200,
        'body': 'Successfully checked EC2 instance status and notified Slack.'
    }