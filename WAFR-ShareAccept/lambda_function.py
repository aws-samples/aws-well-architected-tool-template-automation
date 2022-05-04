# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import boto3
import json
import logging
import os
from decorators import catch_errors

# Setup logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'ERROR').upper()
logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger()
logger.setLevel(LOGLEVEL)

# Setup boto3 clients
wa_client = boto3.client('wellarchitected')
lambda_client = boto3.client('lambda')


@catch_errors
def invokeWAFRShareTemplate(workloadAccountId, workloadSNSTopic):
    # Call Lambda to share the templates back to the workload account
    payload = {
        'AccountId': workloadAccountId,
        'SNSTopic': workloadSNSTopic
    }
    response = lambda_client.invoke(
        FunctionName=os.environ['SHARE_TEMPLATE_FUNCTION'],
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(payload)
    )
    return (response)


@catch_errors
def invokeWAFRUpdateAnswers(workloadId):
    # Invoke Lambda to update shared workload answers
    # Construct Payload
    payload = {'WorkloadId': workloadId}
    response = lambda_client.invoke(
        FunctionName=os.environ["UPDATE_FUNCTION"],
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(payload)
    )
    return (response)


@catch_errors
def acceptShare(shareId):
    wa_acceptance = wa_client.update_share_invitation(ShareInvitationId=shareId, ShareInvitationAction='ACCEPT')
    logger.info("Accepted workload: {}".format(wa_acceptance))
    return (wa_acceptance)


def lambda_handler(event, context):
    logger.debug(event)

    message = json.loads(event['Records'][0]['Sns']['Message'])
    logger.debug(message)
    workloadId = message['WorkloadId']
    shareId = message['ShareId']
    workloadAccountId = message['WorkloadAccountId']
    workloadSNSTopic = message['InboundShareTopic']

    acceptShare(shareId)

    invokeWAFRUpdateAnswers(workloadId)
    invokeWAFRShareTemplate(workloadAccountId, workloadSNSTopic)

    return {
        'statusCode': 200
    }

