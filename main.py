import requests
import datetime
import re
import json
from text2num import text2num, NumberException
from computer_vision import getImageTags

class ParserException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

def translate(s):
    parameters = {
        'key':'trnsl.1.1.20170108T012202Z.fa1a8d03eb8d33be.60cd4068fa2f37d75d11fad1906531974ce3ccdf',
        'lang':'en',
        'text': s
    }
    response = requests.post(
        'https://translate.yandex.net/api/v1.5/tr.json/translate',
        data=parameters)
    if response.status_code !=200:
        msg = "bad request. code: {} reason: {}".format(
            response.status_code, response.reason)
        raise ParserException("text-processing.com error. msg: {}".format(
            msg))
    return response.json()['text'][0]


def send_watson_request(raw_string, try_num=1, max_retries=3):
    if try_num >= max_retries:
        raise ParserException("cannot translate to english. input: {}".format(
            raw_string))

    parameters = {
            'apikey':'c2370ab6d5c04452c495be090688ef5a3e0093d2',
            'outputMode':'json',
            'extract':'keywords,doc-sentiment,taxonomy,dates,entity',
            'sentiment':'0',
            'maxRetrieve':'5',
            'text':raw_string
    }

    response = requests.post(
            'https://gateway-a.watsonplatform.net/calls/text/TextGetCombinedData',
            data=parameters)
    if response.status_code != 200:
        msg = "bad request. code: {} reason: {}".format(
            response.status_code, response.reason)
        raise ParserException("IBM Watson Alchemy Error. msg: {}".format(
            msg))

    formatted_response = response.json()

    if formatted_response['language'] != 'english':
        translated_text = translate(raw_string)
        get_watson_response(translated_text,try_num+1)
    else:
        return response.json()

def get_number(response):
    num_list = re.findall('\d+', response)
    if num_list:
        return ",".join(num_list)

    def convert_string_to_num(response):
        for token in response.split(' '):
            try:
              num_list = text2num(token)
              return num_list
            except NumberException:
              print('number exception when converting text to num')
    num_list = convert_string_to_num(response)
    if num_list:
        return num_list
    translated_response = translate(response)
    num_list = convert_string_to_num(translated_response)
    if not num_list:
        raise ParserException('error parsing number metric. input: {}'.format(
            response))
    return {'value': num_list, 'confidence': None}

def get_sentiment(response):
    alchemy_result = send_watson_request(response) 
    try:
        result_sentiment = alchemy_result["docSentiment"]["score"]
    except KeyError:
        result_sentiment = 0
    return {'value': result_sentiment, 'confidence': None}    

def get_entities(response):
    alchemy_result = send_watson_request(response) 
    if len(alchemy_result["keywords"])==0:
        raise ParserException("cannot parse entities. input: {}".format(
            response))
    result_value = ",".join([keyword["text"] for keyword in alchemy_result["keywords"]])
    result_confidence = ",".join([keyword["relevance"] for keyword in alchemy_result["keywords"]])
    return {'value': result_value, 'confidence': result_confidence}

def get_dates(response):
    alchemy_result = send_watson_request(response) 
    result_value = ",".join([date["date"] for date in alchemy_result["dates"]])
    return [result_value, None]

def get_geo(response):
    alchemy_result = send_watson_request(response)
    try:
        location = alchemy_result['entities'][0]['text']
        location_type = alchemy_result['entities'][0]['type']
        return {'location': location, 'location_type': location_type}
    except IndexError:
        raise ParserException("cannot parse geo information. input: {}".format(
            response))

def get_binary(response):
    # FROM THESAURUS.COM
    yes_list = set(['yes','sure', 'affirmative','amen','fine','good','okay','true','yea','all right','aye','beyond a doubt','by all means','certainly','definitely','even so','exactly','gladly','good enough','granted','indubitably','just so','most assuredly','naturally','of course','positively','precisely','sure thing','surely','undoubtedly','unquestionably','very well','willingly','without fail','yep'])
    no_list = set(['no','negative','absolutely not','nix','by no means','never','no way','not at all','not by any means'])
    maybe_list = set(['maybe','perchance','perhaps','possibly','as it may be','can be','conceivably','could be','credible','feasible','imaginably','it could be','might be','obtainable','weather permitting'])

    cleaned_response = ' '.join([token.lower() for token in response.split()])
    
    def logic(cleaned_response):
        if cleaned_response in yes_list:
            return "YES"
        elif cleaned_response in no_list:
            return "NO"
        elif cleaned_response in maybe_list:
            return "MAYBE"
        else:
            raise ParserException('Cannot parse yes/no/maybe')
    try:
        return_val = logic(cleaned_response)
        return {'value': return_val, 'confidence': None}
    except ParserException:
        translated_response = translate(cleaned_response)
        return logic(translated_response)


def lambda_handler(event,context):
  raw_response = event["raw_response"]
  
  metrics_calls = {
    1: get_binary,
    2: get_number,
    3: get_sentiment,
    4: get_entities,
    # 4: get_dates, # unused
    # TODO test against image format provided by orchestrator
    5: getImageTags,
    6: get_geo,
  }
  
  metric_response = []
  final_result = event.copy()

  for metric in event["question"]["metrics"]:
    metric_id = metric["metric_id"]

    result = metrics_calls[metric_id](raw_response)
    
    # populate different fields for geo
    if metric_id == 6:
        final_result['respondent']['location'] = result['location']
        final_result['respondent']['location_type'] = result['location_type']

    else:
        metric_response.append({'metric_id': metric_id, 
            'metric_type': metric["metric_type"], 
            'value': result.get('value'), 
            'confidence': result.get('confidence')}) 

  final_result["question"]["metrics"] = metric_response
  return final_result

