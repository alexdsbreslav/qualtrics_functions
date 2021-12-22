import multiprocessing as mp
import pandas as pd
import json
from io import StringIO
from internal_functions import *
from datetime import datetime
import numpy as np

# ------------------------------------------------------------------------------
# ---- Initialize --------------------------------------------------------------
# ------------------------------------------------------------------------------

def create_qualtrics_ids(data_center, api_token):
    """qualtrics_ids = create_qualtrics_ids(data_center = ,
                                            api_token = )"""

    response = requests.get(
        'https://{}/API/v3/libraries'.format(data_center),
        headers={
            'x-api-token':api_token,
            'content-type':'application/json'
            }
        )

    if json.loads(response.text)['meta']['httpStatus'] == '200 - OK':
        qualtrics_ids = {
            'data_center': data_center,
            'api_token': api_token,
            'library': json.loads(response.text)['result']['elements'][0]['libraryId']
            }
        return qualtrics_ids

    else:
        print(response.text)
        return



# ------------------------------------------------------------------------------
# ---- Get data ----------------------------------------------------------------
# ------------------------------------------------------------------------------

def download_data(qualtrics_ids, survey):
    """data = download_data(qualtrics_ids,
                            survey = )"""

    # ---- define the qualtrics objects
    qualtrics_objects = {
        'survey_id': survey['id'],
        'data_center': qualtrics_ids['data_center'],
        'api_token': qualtrics_ids['api_token']
        }

    qualtrics_input = [
        (qualtrics_objects, {'format':'json', 'compress':False}),
        (qualtrics_objects, {
            'format':'csv','useLabels':True,
            'breakoutSets':False,
            'compress':False
            }
        )]

    # ---- set up multiprocessing pool
    pool = mp.Pool()
    result = pool.starmap(get_response_object, qualtrics_input)
    print('response objects pulled...')

    # ---- create column dictionary
    tmp = pd.read_csv(StringIO(result[1].text))
    column_dict = pd.DataFrame({
        'column_value': tmp.columns,
        'column_label': tmp.loc[0],
        'column_qid': [json.loads(tmp.loc[1, col])['ImportId'] \
                      for col in tmp.columns]
        }).reset_index(drop=True)

    print('column dictionary created...')

    # ---- create survey response dataframes
    tmp = json.loads(result[0].content)['responses']
    values = pd.DataFrame([pd.Series(tmp[i]['values'],
             name = tmp[i]['responseId']) for i in range(len(tmp))])
    labels = pd.DataFrame([pd.Series(tmp[i]['labels'],
             name = tmp[i]['responseId']) for i in range(len(tmp))])
    print('survey responses formatted...')
    return {'values': values, 'labels': labels, 'column_dict': column_dict}






























# ------------------------------------------------------------------------------
# ---- Create Survey -----------------------------------------------------------
# ------------------------------------------------------------------------------

def create_survey(qualtrics_ids, survey_name):
    """survey = create_survey(qualtrics_ids, survey_name = )"""

    if type(survey_name) is not str:
        raise TypeError('survey_name must be string')

    response = requests.post(
        'https://{}/API/v3/survey-definitions'.format(
            qualtrics_ids['data_center']
            ),
        data = json.dumps({
            'SurveyName': survey_name,
            'Language': 'EN',
            'ProjectCategory': 'CORE'
            }),
        headers={
            'x-api-token': qualtrics_ids['api_token'],
            'content-type': 'application/json'
            }
        )

    if json.loads(response.text)['meta']['httpStatus'] == '200 - OK':
        survey = {
            'name': survey_name,
            'id': json.loads(response.text)['result']['SurveyID'],
            'blocks': {
                'default': json.loads(response.text)['result']['DefaultBlockID']
                }
            }
        return survey

    else:
        print(response.text)
        return


# ------------------------------------------------------------------------------
def get_most_recent_survey(qualtrics_ids):
    """survey = get_most_recent_survey(qualtrics_ids)"""

    # ---- get list of surveys in account
    response = json.loads(requests.get(
        'https://{}/API/v3/surveys'.format(qualtrics_ids['data_center']),
        headers={
            'x-api-token': qualtrics_ids['api_token'],
            'content-type': 'application/json'
            }
        ).text)

    # ---- get the most recent survey
    modified = [datetime.strptime(
        i['lastModified'], '%Y-%m-%dT%H:%M:%SZ'
        )
        for i in response['result']['elements']]

    most_recent = response['result']['elements'][modified.index(max(modified))]

    survey = get_survey_from_id(qualtrics_ids, most_recent['id'])

    return survey



# ------------------------------------------------------------------------------
def get_survey_from_id(qualtrics_ids, survey_id):
    """survey = get_survey_from_id(qualtrics_ids, survey_id=)"""
    # ---- get the names and IDs of the blocks
    response = json.loads(requests.get(
        'https://{}/API/v3//surveys/{}'.format(
            qualtrics_ids['data_center'], survey_id
            ),
        headers={
            'x-api-token': qualtrics_ids['api_token'],
            'content-type': 'application/json'
            }
        ).text)

    if not response['meta']['httpStatus'] == '200 - OK':
        print(response.text)
        return

    blocks = response['result']['blocks']

    keys = [key for key in blocks.keys()]

    survey = {
        'name': response['result']['name'],
        'id': survey_id,
        'blocks': dict(zip(
            ['default' if blocks[key]['description'] == 'Default Question Block'
            else blocks[key]['description'] for key in blocks.keys()],
            blocks.keys()
            ))
        }

    print('retrieved "{}" (id = {})'.format(survey['name'], survey['id']))
    return survey




# ------------------------------------------------------------------------------
def delete_survey(qualtrics_ids, survey):
    """delete_survey(qualtrics_ids, survey = )"""

    response = requests.delete(
        'https://{}/API/v3/survey-definitions/{}'.format(
            qualtrics_ids['data_center'], survey['id']
            ),
        headers={
            'x-api-token': qualtrics_ids['api_token'],
            'content-type': 'application/json'
            }
        )

    if json.loads(response.text)['meta']['httpStatus'] == '200 - OK':
        print('survey {} deleted'.format(survey['id']))
        return

    else:
        print(response.text)
        return

# ------------------------------------------------------------------------------
def add_block_to_survey(qualtrics_ids, block_name, survey):
    """add_block_to_survey(qualtrics_ids, block_name = , survey = )"""

    if type(block_name) is not str:
        raise TypeError('block_name must be string')

    response = requests.post(
        'https://{}/API/v3/survey-definitions/{}/blocks'.format(
            qualtrics_ids['data_center'], survey['id']
            ),
            data = json.dumps({'Type': 'Standard', 'Description': block_name}),
            headers={
                'x-api-token': qualtrics_ids['api_token'],
                'content-type': 'application/json'
                }
            )

    if json.loads(response.text)['meta']['httpStatus'] == '200 - OK':
        survey['blocks'].update(
            {block_name: json.loads(response.text)['result']['BlockID']}
            )
        print('{} added to {}'.format(block_name, survey['name']))
        return

    else:
        print(response.text)
        return



# ------------------------------------------------------------------------------
def add_embedded_data_fields_from_table(qualtrics_ids, dataframe, survey):
    """add_embedded_data_fields_from_table(qualtrics_ids,
        dataframe = ,
        survey = )"""

    if type(dataframe) is not type(pd.DataFrame()):
        raise TypeError('dataframe must be a pandas DataFrame.')

    if type(survey) is not dict:
        raise TypeError('survey must be an entire survey dictionary.')

    # ---- reformat user data headers into embedded data fields json
    data_headers = {
        'embeddedDataFields': [{'key': col,
        'type': {str:'text', np.int64: 'number', float: 'number', int: 'number'}[
            type(dataframe[col].iloc[0])]} for col in dataframe.columns
            ]
        }

    response = requests.post(
        'https://{}/API/v3/surveys/{}/embeddeddatafields'.format(
            qualtrics_ids['data_center'], survey['id']
            ),
        data=json.dumps(data_headers),
        headers={
            'x-api-token': qualtrics_ids['api_token'],
            'content-type': 'application/json'
            }
        )

    if json.loads(response.text)['meta']['httpStatus'] == '200 - OK':
        print('Embedded data fields added to {}'.format(survey['name']))
        return

    else:
        print(response.text)

    return



# ------------------------------------------------------------------------------
def post_questions_to_survey(qualtrics_ids,survey,question,block_id=None):
    """post_questions_to_survey(qualtrics_ids,
        survey = ,
        question = ,
        block_id = None)"""

    if block_id is None:
        block_id = survey['blocks']['default']

    response = requests.post(
        'https://{}/API/v3/survey-definitions/{}/questions?blockId={}'.format(
            qualtrics_ids['data_center'],
            survey['id'],
            block_id
            ),
        data=json.dumps(question),
        headers={
        'x-api-token': qualtrics_ids['api_token'],
        'content-type': 'application/json'
        }
    )

    if json.loads(response.text)['meta']['httpStatus'] == '200 - OK':
        print('{} posted to {} (id = {})'.format(
            question['QuestionID'], survey['name'], survey['id']
            ))
        return

    else:
        print(response.text)

    return



# ------------------------------------------------------------------------------
# ---- Create Questions --------------------------------------------------------
# ------------------------------------------------------------------------------
def create_multiple_choice(question_number, question_text, question_description, values, labels, display_text, force_response, multiple_answer, align):
    '''q = create_multiple_choice(question_number = ,
                                  question_text = markdown(''' '''),
                                  question_description = ,
                                  values = [], #None if items are categorical
                                  labels = [],
                                  display_text = [],
                                  force_response = False,
                                  multiple_answer = False,
                                  align = 'vertical') # vertical, horizontal, column, dropdown

        *Adding "Please Specify" to an item in display_text will turn on text entry.'''

    # ---- check input types
    if type(question_number) is not int:
        raise TypeError('question_number is currently a {}; it must be int'.format(type(question_number)))

    if type(question_text) is not str:
        raise TypeError('question_text is currently a {}; it must be str'.format(type(question_text)))

    if type(question_description) is not str:
        raise TypeError('question_description is currently a {}; it must be str'.format(type(question_description)))

    if values is None:
        values = [i+1 for i in range(len(labels))]
        if not len(labels) == len(display_text):
            raise Exception('labels and display_text must have the same number of items; they currently have {} and {} items each.'.format(len(labels), len(display_text)))
    else:
        if not len(values) == len(labels) == len(display_text):
            raise Exception('values, labels, and display_text must have the same number of items; they currently have {}, {}, and {} items each.'.format(len(values), len(labels), len(display_text)))

    if type(values) is not list:
        raise TypeError('values is currently a {}; it must be list'.format(type(values)))

    if any([type(i) is not int for i in values]):
        raise TypeError('all items in values must be int')

    if type(labels) is not list:
        raise TypeError('labels is currently a {}; it must be list'.format(type(labels)))

    if any([type(i) is not str for i in labels]):
        raise TypeError('all items in labels must be str')

    if type(display_text) is not list:
        raise TypeError('display_text is currently a {}; it must be list'.format(type(display_text)))

    if any([type(i) is not str for i in display_text]):
        raise TypeError('all items in display_text must be str')

    if multiple_answer and align == 'dropdown':
        raise TypeError('dropdowns only work for single answer; multiple_answer must be set to False to use this setting.')

    if align not in ['vertical', 'horizontal', 'column', 'dropdown']:
        raise TypeError('align is not defined correctly.')

    if multiple_answer:
        selector = {'vertical': 'MAVR', 'horizontal': 'MAHR', 'column': 'MACOL'}[align]
    else:
        selector = {'vertical': 'SAVR', 'horizontal': 'SAHR', 'column': 'SACOL', 'dropdown': 'DL'}[align]

    # ---- create question
    question = {'QuestionID': 'QID{}'.format(question_number),
                'DataExportTag': 'Q{}'.format(question_number),
                'QuestionText': question_text,
                'QuestionDescription': question_description,
                'QuestionType': 'MC',
                'Selector': selector,
                'Choices': dict(zip(values, [{'Display': i} for i in display_text])),
                'ChoiceOrder': values,
                'VariableNaming': dict(zip(values,labels)),
                'Language': [],
                'Configuration': {'QuestionDescriptionOption': 'SpecifyLabel'}}

    if force_response:
        question.update({
            'Validation': {'Settings': {'ForceResponse': 'ON',
                                        'ForceResponseType': 'ON',
                                        'Type': 'None'
                                        }}
            })

    # ---- update display_text to include text entry if any of the questions have 'specify' in them
    display_text_with_specify = [list(question['Choices'].keys())[i] for i in [display_text.index(i) for i in [i for i in display_text if 'specify' in str.lower(i)]]]
    if display_text_with_specify:
        for key in display_text_with_specify:
            question['Choices'][key].update({'TextEntry': 'true'})

    return question



# ------------------------------------------------------------------------------
def create_text_block(question_number, question_text, question_description):
    '''t = create_text_block(question_number = ,
                             question_text = markdown(''' '''),
                             question_description = )'''

    # ---- check input types
    if type(question_number) is not int:
        raise TypeError('question_number is currently a {}; it must be int'.format(type(question_number)))

    if type(question_text) is not str:
        raise TypeError('question_text is currently a {}; it must be str'.format(type(question_text)))

    if type(question_description) is not str:
        raise TypeError('question_description is currently a {}; it must be str'.format(type(question_description)))

    # ---- create question
    question = {'QuestionID': 'QID{}'.format(question_number),
                'DataExportTag': 'Q{}'.format(question_number),
                'QuestionText': question_text,
                'QuestionDescription': question_description,
                'QuestionType': 'DB',
                'Selector': 'TB',
                'Configuration': {'QuestionDescriptionOption': 'SpecifyLabel'},
                'Language': []}
    return question



# ------------------------------------------------------------------------------
def create_text_entry(question_number, question_text, question_description, force_response):
    '''q = create_text_entry(question_number = ,
                             question_text = markdown(''' '''),
                             question_description = ,
                             force_response = False)'''

    # ---- check input types
    if type(question_number) is not int:
        raise TypeError('question_number is currently a {}; it must be int'.format(type(question_number)))

    if type(question_text) is not str:
        raise TypeError('question_text is currently a {}; it must be str'.format(type(question_text)))

    if type(question_description) is not str:
        raise TypeError('question_description is currently a {}; it must be str'.format(type(question_description)))

    # ---- create question
    question = {'QuestionID': 'QID{}'.format(question_number),
                'DataExportTag': 'Q{}'.format(question_number),
                'QuestionText': question_text,
                'QuestionDescription': question_description,
                'QuestionType': 'TE',
                'Selector': 'SL',
                'Configuration': {'QuestionDescriptionOption': 'SpecifyLabel'},
                'Language': []}

    if force_response:
        question.update({
            'Validation': {'Settings': {'ForceResponse': 'ON',
                                        'ForceResponseType': 'ON',
                                        'Type': 'None'
                                        }}
            })


    return question
