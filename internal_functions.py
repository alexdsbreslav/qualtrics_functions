import json
import requests
import time



# ------------------------------------------------------------------------------
# ---- Get data ----------------------------------------------------------------
# ------------------------------------------------------------------------------

def get_response_object(qualtrics_objects, export_settings):
    # ---- export the survey and provide the progress ID
    url = 'https://{}/API/v3/surveys/{}/export-responses'.format(
        qualtrics_objects['data_center'],
        qualtrics_objects['survey_id']
        )

    export_survey = requests.post(
        url,
        json = export_settings,
        headers = {
            'x-api-token':qualtrics_objects['api_token'],
            'content-type':'application/json'
            }
        ).text

    progressId = json.loads(export_survey)['result']['progressId']

    # ---- using the progress ID, get the file ID for the exported survey data
    url = 'https://{}/API/v3/surveys/{}/export-responses/{}'.format(
        qualtrics_objects['data_center'],
        qualtrics_objects['survey_id'],
        progressId
        )

    get_fileId = requests.get(
        url,
        headers={
            'x-api-token': qualtrics_objects['api_token'],
            'content-type': 'application/json'
            }
        ).text

    # ---- if the export isn't done yet, check back in 5 seconds
    while json.loads(get_fileId)['result']['status'] == 'inProgress':
        time.sleep(5)
        get_fileId = requests.get(
            url,
            headers={
                'x-api-token': qualtrics_objects['api_token'],
                'content-type': 'application/json'
                }
            ).text

    fileId = json.loads(get_fileId)['result']['fileId']

    # ---- once I have the file ID, get the exported data
    url = 'https://{}/API/v3/surveys/{}/export-responses/{}/file'.format(
        qualtrics_objects['data_center'],
        qualtrics_objects['survey_id'],
        fileId
        )

    get_export = requests.get(
        url,
        headers={
            'x-api-token':qualtrics_objects['api_token'],
            'content-type':'application/json'
            }
        )

    return get_export
