import httplib, urllib, base64, json

def getImageTags(photo_file):
    headers = {
        # Request headers
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': 'fe1ddf67faa347b1847318f516e6065f',
    }

    params = urllib.urlencode({
    })

    with open(photo_file, 'rb') as image:
        image_data = image.read()

    try:
        conn = httplib.HTTPSConnection('api.projectoxford.ai')
        conn.request("POST", "/vision/v1.0/tag?%s" % params, image_data, headers)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        conn.close()
        return data['tags']
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))
