# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import boto3
import os
import logging
from decorators import catch_errors

#Setup logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'ERROR').upper()
logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger()
logger.setLevel(LOGLEVEL)

#boto3 clients
wa_client = boto3.client('wellarchitected')
sts_client = boto3.client('sts')
sns_client = boto3.client('sns')


@catch_errors
def publishSNSMessage(WorkloadAccountId, WorkloadId, shareResponse):
    sns_message = {
        "WorkloadId": WorkloadId,
        "ShareId": shareResponse["ShareId"],
        "WorkloadAccountId": WorkloadAccountId,
        "InboundShareTopic": os.environ['INCOMING_SHARE_TOPIC_ARN']
    }
    sns_response = sns_client.publish(
        TopicArn=os.environ["NEW_WORKLOAD_TOPIC_ARN"],
        Message=json.dumps(sns_message)
    )
    logger.debug("SNS response: {}".format(sns_response))
    logger.debug("Message: {}".format(json.dumps(sns_message)))
    return sns_response


@catch_errors
def createWorkloadShare(workloadID, shareAccountID, permission):
    share_response = wa_client.create_workload_share(
        WorkloadId=workloadID,
        SharedWith=shareAccountID,
        PermissionType=permission
    )
    logger.debug("Share response: {}".format(share_response))
    logger.debug("Share ID: {}".format(share_response["ShareId"]))
    return share_response


@catch_errors
def listWorkloadShares(WorkloadId, sharePrefix):
    listShares = wa_client.list_workload_shares(
        WorkloadId=WorkloadId,
        SharedWithPrefix=sharePrefix
    )
    return listShares


@catch_errors
def getWorkloadAccountID():
    WorkloadAccountId = sts_client.get_caller_identity()['Account']
    return WorkloadAccountId


def lambda_handler(event, context):
    logger.debug(event)

    # Check it hasn't already been shared with the destination account
    # And share it if not already shared
    listShares = listWorkloadShares(event["WorkloadId"], os.environ['TEMPLATE_ACCOUNT_ID'])
    workloadAccountID = getWorkloadAccountID()

    if 'WorkloadShareSummaries' not in listShares or len(listShares['WorkloadShareSummaries']) == 0:
        #Publish SNS Message
        shareResponse = createWorkloadShare(event["WorkloadId"], os.environ["TEMPLATE_ACCOUNT_ID"], 'CONTRIBUTOR')
        publishSNSMessage(workloadAccountID, event["WorkloadId"], shareResponse)

    # Share with AWS Account Team if specified:
    if os.environ["AWSTeamAccountID"]:
        # Check it hasn't already been shared with the destination account
        # And share it if not already shared
        listShares = listWorkloadShares(event["WorkloadId"], os.environ['AWSTeamAccountID'])

        if 'WorkloadShareSummaries' not in listShares or len(listShares['WorkloadShareSummaries']) == 0:
            shareResponse = createWorkloadShare(event["WorkloadId"], os.environ["AWSTeamAccountID"], 'READONLY')
            logger.info("aws team: share response: {}".format(shareResponse))

    return {
        'statusCode': 200,
    }