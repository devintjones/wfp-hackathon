#!/bin/bash

rm -f nlp-wfp.zip 
ln -s ../venv/lib/python2.7/site-packages/requests requests
zip -r nlp-wfp.zip main.py computer_vision.py text2num.py requests

aws lambda update-function-code --function-name NLP-WFP-PostFunction-1TLQKXKB3H2QU --zip-file fileb://$PWD/nlp-wfp.zip
