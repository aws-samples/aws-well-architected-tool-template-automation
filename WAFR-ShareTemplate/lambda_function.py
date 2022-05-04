# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import boto3
import os
import logging
from decorators import catch_errors

LOGLEVEL = os.environ.get('LOGLEVEL', 'ERROR').upper()
logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger()
logger.setLevel(LOGLEVEL)

wa_client = boto3.client('wellarchitected')
sns_client = boto3.client('sns')


@catch_errors
def getTemplateIDs():
    """ Returns a list of template ID's from central account """
    templateWorkloads = wa_client.list_workloads(
        WorkloadNamePrefix=os.environ.get("TEMPLATE_PREFIX", "CentralTemplate")
        )
    templateIDs = []

    for workload in templateWorkloads['WorkloadSummaries']:
        templateIDs.append(workload['WorkloadId'])

    return (templateIDs)


@catch_errors
def lambda_handler(event, context):
    logger.debug(event)
    templateIDs = getTemplateIDs()

    for templateID in templateIDs:

        # Check it hasn't already been shared with the destination account
        listshares = wa_client.list_workload_shares(
            WorkloadId = templateID,
            SharedWithPrefix = event['AccountId']
        )

        # Share it if not already shared
        if not 'WorkloadShareSummaries' in listshares or len(listshares['WorkloadShareSummaries']) == 0:
            share_response = wa_client.create_workload_share(
                WorkloadId = templateID,
                SharedWith= event['AccountId'],
                PermissionType='READONLY'
            )

            # Publish message to SNS topic in destination account to trigger share acceptance
            share_id = share_response["ShareId"]
            sns_message = {
                "ShareId": share_id,
            }
            sns_response = sns_client.publish(
                TopicArn= event['SNSTopic'],
                Message=json.dumps(sns_message)
            )

            logger.info("Workload account: share response: {}".format(share_response))
            logger.info("SNS response: {}".format(sns_response))
            logger.info("Share ID: {}".format(share_id))
            logger.info("Message: {}".format(json.dumps(sns_message)))

        return {
        'statusCode': 200,
    }
