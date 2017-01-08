import requests
import datetime
import re
import json
from text2num import text2num, NumberException


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
        get_watson_response(translated_text[0],try_num+1)
    else:
        return response.json()


def lambda_handler(event,context):
  input = event 
  answer = input["raw_response"]
  
def get_number(response):
    num_list = re.findall('\d+', response)
    if num_list:
        return ",".join(num_list)
    
    for token in response.split(' '):
        try:
          num_list = text2num(token)
          print('text2num response: {}'.format(num_list))
          return num_list
        except NumberException:
          print('number exception when converting text to num')
    if not num_list:
      try:
        translated_response = translate(response)
        for token in translated_response.split(' '):
          try:
            num_list = text2num(token)
            print('text2num response: {}'.format(num_list))
            return num_list
          except NumberException:
            print('number exception')
        else:
          raise Exception("couldn't parse number response after translation and text to num attempt")
      except:
        raise Exception("couldn't parse number response after translation and text to num attempt")

  def get_sentiment(response):
    alchemy_result = send_watson_request(response) 
    try:
      result_confidence = alchemy_result["docSentiment"]["score"]
    except KeyError:
      result_confidence = 0
    return [result_value,result_confidence]    

  def get_entities(response):
    alchemy_result = send_watson_request(response) 
    result_value = ",".join([keyword["text"] for keyword in alchemy_result["keywords"]])
    result_confidence = ",".join([keyword["relevance"] for keyword in alchemy_result["keywords"]])
    return [result_value, result_confidence]

  def get_dates(response):
    alchemy_result = send_watson_request(response) 
    result_value = ",".join([date["date"] for date in alchemy_result["dates"]])
    result_confidence = ",".join([keyword["relevance"] for keyword in alchemy_result["keywords"]])
    return [result_value, result_confidence]

    
  def get_binary(response):
    if "y" in response:
      return "yes"
    elif "n" in response:
      return "no"
    else:
      raise NameError('Bad binary response')
  
  metrics_calls = {
    1: get_number,
    2: get_binary,
    3: get_entities,
    4: get_entities,
    5: get_number,
    6: get_dates
  }
  
  metric_response = []
  
  for metric in input["question"]["metrics"]:
    metric_id = metric["metric_id"]
    result = metrics_calls[metric_id](answer)
    if len(result) > 1:
      result_value, result_confidence = result
    else:
      result_value, result_confidence = result, 0
    metric_response.append({'metric_id': metric_id, 'metric_type': metric["metric_type"], 'value': result_value, 'confidence': result_confidence})
  
  final_result = input.copy()
  final_result["question"]["metrics"] = metric_response
  return final_result

