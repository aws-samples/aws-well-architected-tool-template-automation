# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import boto3
import json
import logging
from decorators import catch_errors

#Setup logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'ERROR').upper()
logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger()
logger.setLevel(LOGLEVEL)

#Setup boto3 clients
wa_client = boto3.client('wellarchitected')
lambda_client = boto3.client('lambda')

@catch_errors
def lambda_handler(event, context):
    logger.debug(event)

    message = json.loads(event['Records'][0]['Sns']['Message'])
    logger.debug(message)
    shareId = message['ShareId']

    wa_acceptance = wa_client.update_share_invitation(ShareInvitationId = shareId, ShareInvitationAction='ACCEPT')
    logger.info("Accepted workload: {}".format(wa_acceptance))

    return {
        'statusCode': 200
    }
