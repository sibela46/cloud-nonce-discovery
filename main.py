import boto3
import argparse
from collections import defaultdict
from dotenv import load_dotenv
import time
import sys
import os

class Cloud_POF(object):
    def __init__(self, sign_zeros, num_instances):
        self.D = sign_zeros
        self.Is = num_instances

        # Initialise environment variables
        load_dotenv()
        self.access_key = os.getenv("AWS_ACCESS")
        self.secret_key = os.getenv("AWS_SECRET")
        self.role_arn = os.getenv("ROLE_ARN")
        self.bucket_name = os.getenv("BUCKET_NAME")

        # Initialise services
        self.session = boto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )
        self.s3 = self.session.resource('s3')
        self.ec2 = self.session.resource('ec2', region_name='us-east-1')
        self.ec2client = boto3.client(
            'ec2', 
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name='us-east-1'
        )
        self.sqs = boto3.client('sqs')
        self.queue_url = 'https://sqs.us-east-1.amazonaws.com/125607959669/cloud-nonce-discovery'

    # Put updated script in bucket
    def putInBucket(self):
        self.s3.Object(self.bucket_name, 'pof.py').put(Body=open('./pof.py', 'rb'))

    # Clears the ec2 state by deleting all instances if there are any
    def clearEC2State(self):
        # Get information for all running and pending instances
        running_instances = self.ec2client.describe_instances(Filters=[{
            'Name': 'instance-state-name',
            'Values': ['running', 'pending']
        }])

        # Delete all currently running instances if there are any
        running_instances_length = len(running_instances['Reservations'])
        if (running_instances_length > 0):
            reservations = running_instances['Reservations']
            instances = (map(lambda reservation : reservation['Instances'], reservations))
            instances = [instance for instances in instances for instance in instances]
            ids = (map(lambda instance : instance['InstanceId'], instances))
            self.ec2.instances.filter(InstanceIds=ids).terminate()

    # Clears all the messages in the queue
    def clearMessages(self):
        # Delete all received messages from a queue
        self.sqs.purge_queue(
            QueueUrl=self.queue_url
        )

    # Creates the specified number of instances from the AMI and runs the script on all of them
    def createInstances(self):
        try:
            print("Creating " + str(self.Is) + " new instances. Press Ctrl+C to stop nonce discovery and shut down VMs.")
            for i in range(self.Is):
                user_data = '''#!/bin/bash
                exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
                pip install --user numpy boto3
                aws s3 cp s3://''' + self.bucket_name + '''/pof.py ./home/ec2-user/pof.py
                aws s3 sync /var/log/ s3://''' + self.bucket_name + '''/pof-logs/
                python ./home/ec2-user/pof.py ''' + str(self.D) + " " + str(i) + " " + str(self.Is)
                instance = self.ec2.create_instances(
                    ImageId='ami-07c54c2c2581762dc',
                    MinCount=1,
                    MaxCount=1,
                    InstanceType='t2.micro',
                    KeyName='ec2-python-launch',
                    IamInstanceProfile={
                        'Arn': self.role_arn
                    },
                    UserData=user_data
                )
        except KeyboardInterrupt:
            print("Exiting and shutting down VMs...")
            self.clearEC2State()
            exit()
        # Check if instances finished creating
        running_instances = self.ec2client.describe_instances(Filters=[{
            'Name': 'instance-state-name',
            'Values': ['running']
        }])

        running_instances_length = len(running_instances['Reservations'])
        while (running_instances_length < self.Is):
            # Some instances are still being initialised
            running_instances = self.ec2client.describe_instances(Filters=[{
                'Name': 'instance-state-name',
                'Values': ['running']
            }])
            running_instances_length = len(running_instances['Reservations'])
        print("Successfully created instances.")

    # Collects messages from the running instances and shuts them down as soon as a message is received
    def collectMessages(self):
        # Receive message from SQS queue
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            AttributeNames=[
                'SentTimestamp'
            ],
            MaxNumberOfMessages=1,
            MessageAttributeNames=[
                'All'
            ],
            WaitTimeSeconds=1
        )

        if (not('Messages' in response)):
            try:
                print("Waiting for messages to be present. Press Ctrl+C to stop nonce discovery and shut down VMs.")
                startedLoop = time.time()
                while(not('Messages' in response)):
                    response = self.sqs.receive_message(
                        QueueUrl=self.queue_url,
                        AttributeNames=[
                            'SentTimestamp'
                        ],
                        MaxNumberOfMessages=1,
                        MessageAttributeNames=[
                            'All'
                        ],
                        VisibilityTimeout=40000,
                        WaitTimeSeconds=20
                    )
                    if (time.time() - startedLoop > 5*60): # if 5 minutes pass, quit
                        print("Five minutes passed. Exiting and shutting down VMs...")
                        self.clearEC2State()
                        exit()
            except KeyboardInterrupt:
                print("Exiting and shutting down VMs...")
                self.clearEC2State()
                exit()
            messages = response['Messages']
        else:
            messages = response['Messages']

        print('Received a message!')
        for message in messages:
            print('%s' % message['Body'])

        # Shuts down all instances and deletes messages in the queue
        self.clearEC2State()

# Calculates the number of instances based on the specified time and confidence level
def getInstancesFromMetrics(difficulty, time):
    print("Note that the time you selected would be interpreted as the desired time in which nonce discovery should finish.\nThis does not include instance management time (that would take additional ~70-80 seconds).")
    multiplier = 0.45 # original multiplier for difficulty 24

    if (difficulty < 24):
        multiplier = multiplier + (24-difficulty)*2

    instances = int(round((difficulty/time) / multiplier))

    if (instances > 15):
        print("Using maximum allowed limit...")
        instances = 15
    elif (instances < 1):
        instances = 1

    return instances 

def runProgramOnCloud(difficulty, instances):
    start = time.time()
    cloud_pof = Cloud_POF(difficulty, instances)
    cloud_pof.clearMessages()
    cloud_pof.putInBucket()
    cloud_pof.createInstances()
    cloud_pof.collectMessages()
    end = time.time()
    print("Overall execution time including the starting and shutting of VMs was " + str(end-start) + " seconds.")

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='CND program'
    )
    parser.add_argument('difficulty', type=int, help='- the number of leading zeros to be found')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_a = subparsers.add_parser('yes', help='- direct specification, program will ask you for number of instances')
    parser_a.add_argument('instances', type=int)

    parser_b = subparsers.add_parser('no', help='- indirect specification, program will ask you for desired discovery time (excluding the time taken to create and shut down VMs)')
    parser_b.add_argument('time', type=float)
    
    args = parser.parse_args()

    if (hasattr(args, 'instances')):
       runProgramOnCloud(args.difficulty, args.instances)
    else:
        i = getInstancesFromMetrics(args.difficulty, args.time)
        runProgramOnCloud(args.difficulty, i)
        
if __name__ == '__main__':
    main()
    