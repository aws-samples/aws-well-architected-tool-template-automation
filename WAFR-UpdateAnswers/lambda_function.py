# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
import os
import boto3
from decorators import catch_errors


LOGLEVEL = os.environ.get('LOGLEVEL', 'ERROR').upper()
logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger()
logger.setLevel(LOGLEVEL)

# Boto3 Clients
wa_client = boto3.client('wellarchitected')


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
def getTemplateLenses(templateID):
    """ Returns lenses are active on the template """
    lens_reviews_result = wa_client.list_lens_reviews(
        WorkloadId=templateID
    )['LensReviewSummaries']

    logger.debug(lens_reviews_result)
    logger.info(f'Template {templateID} has used {len(lens_reviews_result)} lens')
    return (lens_reviews_result)


@catch_errors
def getLensAnswers(workload_id, lens):
    list_answers_result = []

    lens_name = lens['LensName']
    logger.info(f'Looking at {lens_name} answers for template {workload_id}')
    logger.debug(lens)

    #Sort out custom lenses
    lens_alias = determineCustomLens(lens)

    logger.debug(f'Using {lens_alias} as the lens alias')
    
    # Get first 50 answers for the lens
    list_answers_response = wa_client.list_answers(
        WorkloadId=workload_id, LensAlias=lens_alias, MaxResults=50
    )

    # Flatten the answer result to include LensAlias and Milestone Number
    #for answer_result in list_answers_response['AnswerSummaries']:
    #    answer_result['LensAlias'] = list_answers_response['LensAlias']

    # Find applicable answers
    res = [i for i in list_answers_response['AnswerSummaries'] if (i['IsApplicable'] == True)]
    logger.debug('Find only applicable answers')
    logger.debug(res)
    list_answers_result.extend(res)

    #Get next 50 answers for the lens if needed
    while 'NextToken' in list_answers_response:
        logger.info(f'NextToken found for workload {workload_id} in lens {lens_alias}')

        list_answers_response = wa_client.list_answers(
            WorkloadId=workload_id, LensAlias=lens_alias, NextToken=list_answers_response['NextToken'], MaxResults=50
        )

        # Find applicable answers
        res = [i for i in list_answers_response['AnswerSummaries'] if (i['IsApplicable'] == True)]
        logger.debug('Find only applicable answers')
        logger.debug(res)
        list_answers_result.extend(res)

    return (list_answers_result)


@catch_errors
def updateWorkloadOverwrite(event, templateID, lens):
    """ Overwrites any selections or notes a workload owner may have entered
    into a review with answers provided by the template.

    This is invoked with the overwrite value for the mode environment variable
    """
    # get answers for lens
    answersList = getLensAnswers(templateID, lens)

    # for each answer/question id in answers
    for question in answersList:
        logger.debug('Question data')
        logger.debug(question)

        # deal with custom lenses
        lens_alias = determineCustomLens(lens)

        # get notes for each answer
        answer = wa_client.get_answer(
          WorkloadId=templateID,
          LensAlias=lens_alias,
          QuestionId=question['QuestionId'],
          )['Answer']
        logger.debug(answer)

        # Sort out notes
        payloadNotes = ""
        if 'Notes' in answer:
            # Concatenate answer notes
            payloadNotes = "{}\nFROM CENTRAL TEAM:\n{}".format(
                payloadNotes,
                answer['Notes']
                )

        if len(payloadNotes) > 2084:
            payloadNotes = "{}... NOTES CLIPPED".format(
                payloadNotes[:2066]
                )

        # update answer with payload
        response = wa_client.update_answer(
            WorkloadId=event['WorkloadId'],
            LensAlias=lens_alias,
            QuestionId=question['QuestionId'],
            SelectedChoices=question['SelectedChoices'],
            Notes=payloadNotes,
            IsApplicable=True
            )
    return (response)


@catch_errors
def updateWorkloadAppend(event, templateID, lens):
    """ Appends both selected choices for a question as well as notes.
    If concatenated question notes are longer than the 2084 limit,
    the string is clipped

    This is invoked with the append value for the mode environment variable
    """
    # get answers for lens
    answersList = getLensAnswers(templateID, lens)

    # deal with custom lenses
    lens_alias = determineCustomLens(lens)

    # for each answer/question id in answers
    for question in answersList:
        templateAnswer = getAnswer(
            templateID,
            lens_alias,
            question['QuestionId']
            )
        workloadAnswer = getAnswer(
            event['WorkloadId'],
            lens_alias,
            question['QuestionId']
            )
        # Concatenate choices in a set
        selectedChoicesSet = set(
            templateAnswer['SelectedChoices']).union(
                set(workloadAnswer['SelectedChoices'])
            )

        # Deal with "none of these"
        # Ignore this if there's only one item selected
        if len(selectedChoicesSet) > 1:
            choice_to_remove = ""
            # See if any of the items end in 'no'
            for choice in selectedChoicesSet:
                if choice.endswith('_no'):
                    choice_to_remove = choice
            if choice_to_remove:
                selectedChoicesSet.remove(choice_to_remove)

        payloadNotes = ""
        if 'Notes' in workloadAnswer:
            payloadNotes = "{}".format(workloadAnswer['Notes'])
            #Find existing central notes and trim them
            if "FROM CENTRAL TEAM:" in payloadNotes:
                payloadNotes = payloadNotes[:payloadNotes.find(
                    "\nFROM CENTRAL TEAM:")]

        if 'Notes' in templateAnswer:
            # Concatenate answer notes
            payloadNotes = "{}\nFROM CENTRAL TEAM:\n{}".format(
                payloadNotes,
                templateAnswer['Notes']
                )

        if len(payloadNotes) > 2084:
            payloadNotes = "{}... NOTES CLIPPED".format(
                payloadNotes[:2066]
                )

        # update answer with payload
        response = wa_client.update_answer(
            WorkloadId=event['WorkloadId'],
            LensAlias=lens_alias,
            QuestionId=question['QuestionId'],
            SelectedChoices=list(selectedChoicesSet),
            Notes=payloadNotes,
            IsApplicable=True
            )
    return response


def determineCustomLens(lens):
    """ Custom Lenses don't have an alias so we need to return the Arn """
    if 'LensAlias' not in lens:
        lens_alias = lens['LensArn']
    else:
        lens_alias = lens['LensAlias']
    return lens_alias


@catch_errors
def getAnswer(workloadID, lens, question):
    """ Returns answer section for given workload, lens and question """
    logger.debug('Question data')
    logger.debug(question)
    # get notes for each answer
    answer = wa_client.get_answer(
      WorkloadId=workloadID,
      LensAlias=lens,
      QuestionId=question,
      )['Answer']
    logger.debug(answer)
    return (answer)


def getMode():
    """Using the mode environment variable
    chooses between overwrite and append.

    Accepted values are:
    overwrite
    append - default
    """
    mode = os.environ.get('MODE', 'append')
    return mode


def lambda_handler(event, context):
    logger.debug(event)
    templateIDs = getTemplateIDs()
    mode = getMode()
    logger.info("Updating templates in {} mode".format(mode))

    for templateID in templateIDs:
        lenses = getTemplateLenses(templateID)
        logger.debug(lenses)
        for lens in lenses:
            logger.debug(lens)
            if mode == "overwrite":
                update = updateWorkloadOverwrite(event, templateID, lens)
            if mode == "append":
                update = updateWorkloadAppend(event, templateID, lens)

    return update
