import requests
import csv
import base64
import logging
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

listToCreate = []
listToUpdate = []
listExceptions = []
listToCheckManual = []

logging.info("START TIME" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

input_file = csv.DictReader(open("INSERTME.csv", encoding='utf-8-sig'))
for row in input_file:
    PATRON_STUDENT_ID  = str(row['ID'])
    try:
        params = { 
            'varFieldTag': 'u',
            'varFieldContent': PATRON_STUDENT_ID
        }
        patrons_response = requests.get(SIERRA_API_HOST + BASE_PATRON_URI + '/find', headers = request_headers, params = params)
        if patrons_response.status_code == 200:
            if patrons_response.json()["patronType"] == 30:  
                logging.info("Found ONE w/ matching student id, update.........." + row['Name'] + "," + row['ID'])
                patronId = patrons_response.json()["id"]
                row["patronId"] = patronId
                listToUpdate.append(row)
            else:
                logging.info("Found ONE w/ matching student id, BUT PTYPE NOT 30 (upgraded card), need to create.........." + row['Name'] + "," + row['ID'])
                patronId = patrons_response.json()["id"]
                row["patronId"] = patronId 
                listExceptions.append(row)
        elif patrons_response.status_code == 409:
            logging.warning("Multiple patrons with STUDENT ID - DELETE ONE, UPDATE THE OTHER.........." + row['Name'] + "," + row['ID'])
            listToCheckManual.append(row)   
        elif patrons_response.status_code == 404:      
            logging.info("No matching student ID, create new digital record.........." + row['Name'] + "," + row['ID'])
            listToCreate.append(row)   
    except Exception as e:
        logging.warning(e)
        logging.warning("Run this patron through the script again.........." + row['Name'] + "," + row['ID'])

                
fields = ['patronId', 'ID', 'Name', 'Birthdate', 'Projected Graduation', 'WI State ID Number']

with open("needToCreate.csv", 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames = fields)  
    writer.writeheader()  
    writer.writerows(listToCreate) 

with open("needToUpdate.csv", 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames = fields)  
    writer.writeheader()  
    writer.writerows(listToUpdate) 

with open("manualCheck.csv", 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames = fields)  
    writer.writeheader()  
    writer.writerows(listToCheckManual) 

with open("exceptionsList.csv", 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames = fields)  
    writer.writeheader()  
    writer.writerows(listExceptions) 

logging.info("END TIME" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
logging.info("END OF FILE")
