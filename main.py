import requests
import datetime
import re
import json
from text2num import text2num, NumberException
from computer_vision import getImageTags

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
        print("bad request. code: {} reason: {}".format(
            response.status_code, response.reason))
        raise Exception("text-processing.com error")
    return response.json()['text'][0]


def send_watson_request(raw_string, try_num=1, max_retries=3):
    if try_num >= max_retries:
        raise Exception("cannot translate to english")

    parameters = {
            'apikey':'c2370ab6d5c04452c495be090688ef5a3e0093d2',
            'outputMode':'json',
            'extract':'keywords,doc-sentiment,taxonomy,dates',
            'sentiment':'0',
            'maxRetrieve':'5',
            'text':raw_string
    }

    response = requests.post(
            'https://gateway-a.watsonplatform.net/calls/text/TextGetCombinedData',
            data=parameters)
    if response.status_code != 200:
        raise Exception("IBM Watson API Error")

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
    if not num_list:
        translated_response = translate(response)
        print(translated_response)
        num_list = convert_string_to_num(translated_response)
        raise Exception('error parsing number metric')
  
def get_sentiment(response):
    alchemy_result = send_watson_request(response) 
    try:
        result_sentiment = alchemy_result["docSentiment"]["score"]
    except KeyError:
        result_sentiment = 0
    return [result_sentiment, None]    

def get_entities(response):
    alchemy_result = send_watson_request(response) 
    result_value = ",".join([keyword["text"] for keyword in alchemy_result["keywords"]])
    result_confidence = ",".join([keyword["relevance"] for keyword in alchemy_result["keywords"]])
    return [result_value, result_confidence]

def get_dates(response):
    alchemy_result = send_watson_request(response) 
    result_value = ",".join([date["date"] for date in alchemy_result["dates"]])
    return [result_value, None]


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
            raise NameError('Bad binary response')
    try:
        return_val = logic(cleaned_response)
        return return_val
    except NameError:
        translated_response = translate(cleaned_response)
        return logic(translated_response)


def lambda_handler(event,context):
  raw_response = event["raw_response"]
  
  metrics_calls = {
    1: get_number,
    2: get_binary,
    3: get_entities,
    4: get_dates,
    5: get_sentiment,
    6: getImageTags
  }
  
  metric_response = []
  
  for metric in event["question"]["metrics"]:
    metric_id = metric["metric_id"]
    print('metric_id: {}'.format(metric_id))
    result = metrics_calls[metric_id](raw_response)
    if result:
      result_value, result_confidence = result
    else:
      result_value, result_confidence = result, 0
    metric_response.append({'metric_id': metric_id, 'metric_type': metric["metric_type"], 'value': result_value, 'confidence': result_confidence})
  
  final_result = event.copy()
  final_result["question"]["metrics"] = metric_response
  return final_result

