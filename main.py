import requests
import datetime
import re
import json
from text2num import text2num
import nltk

def get_verbs(raw_string):
    url = 'http://text-processing.com/api/tag/'
    data = {'text': raw_string}
    response = requests.post(url, data=data)
    if response.status_code !=200:
        print("bad request. code: {} reason: {}".format(
            response.status_code, response.reason))
        raise Exception("text-processing.com error")
    return ','.join([token.split('/')[0] for token in response.json().get('text').split(' ') 
        if 'VB' in token.split('/')[-1]])


def translate(s):
	parameters = {
		'key':'trnsl.1.1.20170108T012202Z.fa1a8d03eb8d33be.60cd4068fa2f37d75d11fad1906531974ce3ccdf',
		'lang':'en',
		'text': s
	}
	response = requests.post(
            'https://translate.yandex.net/api/v1.5/tr.json/translate',
            data=parameters)
	return json.loads(r.text)['text']

def send_watson_request(raw_string):
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

	formatted_response = json.loads(r.text)

	if formatted_response['language'] != 'english':
		translated_text = translate(raw_string)
		get_watson_response(translated_text[0])
	else:
		return response.json


def lambda_handler(event,context):
  
  input = event 
  answer = input["raw_response"]
  
  def get_number(response):
    # num = text2num(response)
    try:
      num_list = re.findall('\d+', response)
    except:
      raise Exception
    else:
      return ",".join(num_list)
        
  def get_entities(response):
    alchemy_result = send_watson_request(response) 
    return ",".join([keyword["text"] for keyword in alchemy_result["keywords"]])
  
  def get_dates(response):
    alchemy_result = send_watson_request(response) 
    return ",".join([date["date"] for date in alchemy_result["dates"]])
    
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
    metric_response.append({'metric_id': metric_id, 'metric_type': metric["metric_type"], 'value': metrics_calls[metric_id](answer)})
  
  final_result = input.copy()
  final_result["question"]["metrics"] = metric_response
  return final_result
