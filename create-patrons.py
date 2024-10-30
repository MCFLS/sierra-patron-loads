import json
import requests
import csv
import base64
import psycopg2
import logging
import time
from requests import Request, Session

# -------------------------------
# Set Up Info for Sierra API Host 
# -------------------------------

SIERRA_API_HOST = 'insert-your-host-here'
BASE_PATRON_URI = '/iii/sierra-api/v6/patrons'
AUTH_URI = '/iii/sierra-api/v6/token'
SIERRA_API_KEY = 'insert-your-api-key-here'
SIERRA_API_KEY_SECRET = 'insert-your-key-secret-here'

logging.basicConfig(filename='INSERTME.log', encoding='utf-8', format='%(levelname)s:%(message)s', level=logging.INFO)

# ----------------------------------------------
# Prepare URL, custom headers, and body for auth 
# ----------------------------------------------

# Create URL for auth endpoint
auth_url = SIERRA_API_HOST + AUTH_URI

# Base64 encode the API key and secret separated by a ':' (colon)
key_secret = SIERRA_API_KEY + ':' + SIERRA_API_KEY_SECRET
data_bytes = key_secret.encode("utf-8")
base64_bytes = base64.b64encode(data_bytes)
base64_string = base64_bytes.decode('utf-8')
auth_headers = {
    'Accept': 'application/json', 
    'Authorization': 'Basic ' + base64_string,
    'Content-Type': 'application/x-www-form-urlencoded'
}

# Set grant type request for HTTP body
grant_type = 'client_credentials'  # Request a client credentials grant authorization

def getBearerToken():
    # Make the call to the Auth endpoint to get a bearer token
    auth_response = requests.post(auth_url, headers = auth_headers, data = grant_type)
    access_token = auth_response.json()['access_token']
    # Create headers for making subsequent calls to the API
    return {
        'Accept': 'application/json', 
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json', 
        'Connection':'close',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
    }

def generateUrlAndBody(action, newData):
    varFieldsToKeep = []
    body = { 
        "names": [newData['Name']],
        "patronType": 30,
        "birthDate": newData['Birthdate'],
        "expirationDate": newData['Projected Graduation'],
        "langPref": 'eng',
        "fixedFields": {
            "46": {
                "label": "RESIDENCE", # Region in TEST, Residence in PROD
                "value": '1',
            }, 
            "53": {
                "label": "PICKUP LOC", # Residence in TEST, PICKUP LOC in PROD
                "value": '1',
            }, 
            "268": {
                "label": "NOTICE PREF",
                "value": '-',
            }
        }
    }
    varFieldsToKeep.append({
        "fieldTag": 'e',
        "content": 'DO NOT DELETE - MPS LIBRARYNOW [insert date]'
    })
    varFieldsToKeep.append({
        "fieldTag": 'x',
        "content": 'DO NOT DELETE - LOADED [insert date] MPS LIBRARYNOW'
    })
    varFieldsToKeep.append({
        "fieldTag": 'u',
        "content": str(newData['ID'])
    })
    varFieldsToKeep.append({
        "fieldTag": 'g',
        "content": str(newData['WI State ID Number'])
    })
    
    message1 = "The account can be upgraded to a Regular PTYPE when full registration is completed. Update all fields as appropriate, and remove all messages when completed.  PLEASE RETAIN EXP DATE, which is based on expected graduation date. Contact Kyle Eklund at MPL if you have any questions."
    message2 = "IMPORTANT! This account uses a PTYPE limited to digital access only, meaning access to computers and to digital resources like databases and OverDrive. Sierra will prevent checkout of physical materials to this patron type."
    if action == 'post':
        body["fixedFields"]["44"] = {
            "label": "LIB OF REG",
            "value": "1"
        }
        # Sierra will not accept "2020" as a valid PIN (err mess: PIN is not valid : PIN is trivial)
        body["pin"] = newData['Birthdate'][:4]
        varFieldsToKeep.append({
            "fieldTag": 'm',
            "content": message1
        })
        varFieldsToKeep.append({
            "fieldTag": 'm',
            "content": message2
        })

    body["varFields"] = varFieldsToKeep
    return body

failedToCreateList = []

input_file = csv.DictReader(open("insertme.csv"))
request_headers = getBearerToken()
for row in input_file:
    try: 
        create_patron_url = SIERRA_API_HOST + BASE_PATRON_URI
        bodyToSend = generateUrlAndBody('post', row)
        create_patron_response = requests.post(create_patron_url, headers = request_headers, data = json.dumps(bodyToSend))
        if create_patron_response.status_code == 200:
            patronId = create_patron_response.json()["link"][-7:]
            row["patronId"] = patronId
            logging.info("Successfully created patron.........." + row['Name'] + "," + row['ID'] + ",p" + patronId)
        else: 
            logging.warning("Failed to create patron..........")
            logging.warning(create_patron_response.content)
    except Exception as e:
        logging.warning(e)
        logging.warning("Check if this patron was created.........." + row['Name'] + "," + row['ID'])
        time.sleep(5)
        
logging.info("END OF FILE")
