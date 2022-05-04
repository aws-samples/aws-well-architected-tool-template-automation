# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import boto3
import logging
import os
from decorators import catch_errors

# Configure logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'ERROR').upper()
logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger()
logger.setLevel(LOGLEVEL)

# Setup boto3 Clients
wa_client = boto3.client('wellarchitected')

@catch_errors
def getWorkloadIDs():
    workloads = wa_client.list_workloads()
    workloadIDs = []

    for workload in workloads['WorkloadSummaries']:
        workloadIDs.append({
            "WorkloadName": workload["WorkloadName"],
            "WorkloadId": workload["WorkloadId"]
        })

    #Strip template ID
    workloadIDs = stripCentralTemplate(workloadIDs)
    workloadObject = {'Workloads': workloadIDs}
    logger.debug(workloadObject)
    logger.info('Found {} Well-Architected workloads.'.format(len(workloadIDs)))
    return (workloadObject)


def stripCentralTemplate(workloadIDs):
    logger.debug(workloadIDs)
    templatePrefix = os.environ.get('TEMPLATE_PREFIX', 'CentralTemplate')
    res = [i for i in workloadIDs if not (i['WorkloadName'] == templatePrefix)]
    return (res)


def lambda_handler(event, context):
    return (getWorkloadIDs())
