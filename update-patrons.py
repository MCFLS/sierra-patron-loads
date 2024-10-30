import json
import requests
import csv
import base64
import psycopg2
import logging
import time
import datetime
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

# Make the call to the Auth endpoint to get a bearer token
auth_response = requests.post(auth_url, headers = auth_headers, data = grant_type)

access_token = auth_response.json()['access_token']

# Create headers for making subsequent calls to the API
request_headers = {
    'Accept': 'application/json', 
    'Authorization': 'Bearer ' + access_token,
    'Content-Type': 'application/json', 
    'Connection':'close',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
}

def generateUrlAndBody(action, newData, id=None, oldData=None):
    varFieldsToKeep = []
    # keep all other variable fields that are not the below
    for k in oldData['varFields']:
        # only remove campaign, Wisconsin State ID, name
        if k["fieldTag"] not in ['e', 'g', 'n']:
            varFieldsToKeep.append(k)
    
    oldData["birthDate"] = str(newData['Birthdate'])
    oldData["expirationDate"] = str(newData['Projected Graduation'])
    oldData["names"] = [newData['Name']]
    oldData.pop("fixedFields")
    oldData.pop("id")
    
    varFieldsToKeep.append({
        "fieldTag": 'e',
        "content": 'DO NOT DELETE - MPS LIBRARYNOW [insert date]'
    })
    varFieldsToKeep.append({
        "fieldTag": 'u',
        "content": str(newData['ID'])
    })
    varFieldsToKeep.append({
        "fieldTag": 'g',
        "content": str(newData['WI State ID Number'])
    })
    oldData["varFields"] = varFieldsToKeep
    
    return oldData

toCreate = []
failedToUpdateList = []
logging.info("START TIME" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

input_file = csv.DictReader(open("insertfile.csv"))
for row in input_file:
    PATRON_ID  = str(row['patronId'])
    params = { 
        'fields': ['varFields', 'fixedFields']
    }
    try:
        patrons_response = requests.get(SIERRA_API_HOST + BASE_PATRON_URI + '/' + PATRON_ID, headers = request_headers, params = params)
        if patrons_response.status_code == 200:
            # update the record with WI State ID / school ID and expiration date and campaign field
            existingSchoolId = ''
            existingCampaign = ''
            for field in patrons_response.json()['varFields']:
                if field['fieldTag'] == 'u':
                    existingSchoolId = field['content']
                if field['fieldTag'] == 'e':
                    existingCampaign = field['content']
            # if idempotent response required
            if existingSchoolId == str(row['ID']) and existingCampaign == 'DO NOT DELETE - MPS LIBRARYNOW [insert date]':
                logging.info("Patron already updated no need for changes.........." + row['Name'] + "," + row['ID'] + ",.p" + row["patronId"]+"a")
            else:
                bodyToSend = generateUrlAndBody('put', row, PATRON_ID, patrons_response.json())
                update_patron_response = requests.put(SIERRA_API_HOST + BASE_PATRON_URI + "/" + PATRON_ID, headers = request_headers, data = json.dumps(bodyToSend))
                if update_patron_response.status_code == 204:
                    logging.info("Successfully updated patron.........." + row['Name'] + "," + row['ID'] + ",.p" + row["patronId"]+"a")
                else:
                    logging.warning("Failed to update patron.........." + row['Name'] + "," + row['ID'] + ",.p" + row["patronId"]+"a")
                    logging.warning(update_patron_response.content)
                    failedToUpdateList.append(row)
    except Exception as e:
        logging.warning(e)
        logging.warning("Check what happened with this patron.........." + row['Name'] + "," + row['ID'] + ",.p" + row["patronId"]+"a")
        failedToUpdateList.append(row)


fields = ['patronId','ID','Name','Birthdate','Projected Graduation','WI State ID Number']

with open("failedToUpdateRedo.csv", 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames = fields)  
    writer.writeheader()
    writer.writerows(failedToUpdateList) 

logging.info(failedToUpdateList)
logging.info("END TIME" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
logging.info("END OF FILE")
