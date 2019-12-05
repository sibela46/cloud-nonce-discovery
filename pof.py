import numpy as np
import hashlib
import math
import time
import sys
import boto3
import binascii

# Create SQS client
sqs = boto3.client('sqs', region_name='us-east-1')
queue_url = 'https://sqs.us-east-1.amazonaws.com/125607959669/cloud-nonce-discovery'

block = "COMSM0010cloud"
D = 0
start = 0
step = 0

if (len(sys.argv) < 2):
    print("Please provide the number of significant zeros, the start for looping and the step number")
    exit()
if (len(sys.argv) < 3):
    print("Please provide the start for looping and the step number")
    exit()
if (len(sys.argv) < 4):
    print("Please provide the step number")
    exit()
else:
    D = int(sys.argv[1])
    start = int(sys.argv[2])
    step = int(sys.argv[3])

def convertHexToInt(hex_string):
    n = int(hex_string, 16)
    return n

def findNonce(D):
    startTime = time.time()
    for i in xrange(start, 2**32, step):
        nonce = str(i)
        hash = hashlib.sha256()
        data = block + nonce
        hash.update(data)
        hash2 = hashlib.sha256()
        hash2.update(hash.hexdigest())
        newBlock = convertHexToInt(hash2.hexdigest())
        zeros = countZeros(newBlock)
        if (zeros >= D):
            endTime = time.time()
            # writeDataToFile(str(hash2.hexdigest()), str(i), startTime, endTime) # Uncomment if you want to run locally and print results
            sendToSQS(str(hash2.hexdigest()), str(i), str(D), str(endTime-startTime))
            break
        if (i == ((2**32-start) - 1)):
            sendFailure(str(endTime-startTime))
            break
    endTime = time.time()

def countZeros(x):
    total_bits = 256
    res = 0
    while ((x & (1 << (total_bits - 1))) == 0):
        x = (x << 1)
        res += 1
    return res

def writeDataToFile(hashString, nonce, start, end):
    print("Found hash!\nThe hex for it is: " + hashString + "\nNonce is: " + nonce + "\nThis took " + str(end-start) + " seconds.")

def sendToSQS(hashString, nonce, diff, time):
    # Send message to SQS queue
    response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes={
            'Title': {
                'DataType': 'String',
                'StringValue': 'The Whistler'
            },
            'Author': {
                'DataType': 'String',
                'StringValue': 'John Grisham'
            },
            'WeeksOn': {
                'DataType': 'Number',
                'StringValue': '6'
            }
        },
        MessageBody=(
            "Found hash for difficulty " + diff + "!\nThe hex for it is: " + hashString + "\nNonce is: " + nonce + "\nI was the " + str(start+1) + " worker.\nThis took me " + time + " seconds."
        )
    )

def sendFailure(time):
    # Send message to SQS queue
    response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes={
            'Title': {
                'DataType': 'String',
                'StringValue': 'The Whistler'
            },
            'Author': {
                'DataType': 'String',
                'StringValue': 'John Grisham'
            },
            'WeeksOn': {
                'DataType': 'Number',
                'StringValue': '6'
            }
        },
        MessageBody=(
            "Failed to find nonce in my start and step (" + str(start) + ", " + str(step) + ").\nThis took me " + time + " seconds."
        )
    )

findNonce(D)
