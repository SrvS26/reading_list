import json
import sqlite3
from decouple import config
import requests
import logging

logging.basicConfig(filename='license.log', format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
databaseFile = config("DATABASE_FILE_PATH")
gumroadToken = config("GUMROAD_TOKEN")
errors = {100:"Success" ,101: "The license key is already in use", 102: "Invalid license key", 103: "Your access has been reinstated", 104: "An error occurred. Please try again later"}
conn = sqlite3.connect(databaseFile)

def fetchToken():
    cursor = conn.cursor()
    data = """SELECT access_token FROM USERS WHERE is_validated = 0"""
    try:
        cursor.execute(data)
        records = cursor.fetchall()
    except Exception as e:
        logging.exception(f"Could not fetch tokens from Users: {e}")    
    listTokens = []
    if len(records) > 0:
        for item in records:
            listTokens.append(item[0])
    return listTokens    

def getRevoked():
    cursor = conn.cursor()
    data = """SELECT user_id FROM USERS WHERE is_revoked = 1"""
    try:
        cursor.execute(data)
        records = cursor.fetchall()
    except Exception as e:
        logging.exception(f"Could not fetch is_revoked from Users: {e}")    
    listRevoked = []
    if len(records) > 0:
        for item in records:
            listRevoked.append(item[0])
    return listRevoked   

def updateValidated(userId):
    cursor = conn.cursor()
    data = f"""UPDATE USERS SET is_validated = 1 WHERE user_id = '{userId}'"""
    try:
        cursor.execute(data)
    except Exception as e:
        logging.exception(f"Could not update is_validated for {userId}: {e}")
    conn.commit()
    return

def updateRevoked(userId):
    cursor = conn.cursor()
    data = f"""UPDATE USERS SET is_revoked = 0 WHERE user_id = '{userId}'"""
    try:
        cursor.execute(data)
    except Exception as e:
        logging.exception (f"Could not update is_revoked for {userId}: {e}")    
    conn.commit()
    return

def addLicenseKey(userId, licenseKey):
    cursor = conn.cursor()
    data = f"""UPDATE USERS SET license_key = '{licenseKey}' WHERE user_id = '{userId}'"""
    try:
        cursor.execute(data)
    except Exception as e:   
        logging.exception (f"Could not update license_key for {userId}: {e}") 
    conn.commit()
    return    

def fetchID(token):
    databaseIDurl = "https://api.notion.com/v1/search"
    params = {"filter" : {"value" : "database","property" : "object"}, "query" : "License Key"}
    try:
        response = requests.post(databaseIDurl, headers= {"Notion-Version": "2022-02-22", "Authorization": "Bearer " + token, "Content-Type": "application/json"},  data=json.dumps(params))
        statusCode = response.status_code
        if statusCode == 200:
            parsedResponse = response.json()
            database = parsedResponse.get("results",[{}])[0]
            databaseID = database.get("id", None)
            userID = database.get("created_by", {}).get("id", None)
            return (databaseID, userID)
        else:
            logging.error(f"Query for databaseID and userID failed: {statusCode}")
            return (None, None)
    except Exception as e:
        logging.exception(f"Query for databaseID and userID failed: {e}")
        return (None, None)

def fetchLicenseKey(databaseID, token):
    url = f"https://api.notion.com/v1/databases/{databaseID}/query"    
    headers = {
        'Content-Type': "application/json",
        'Notion-Version': "2022-02-22",
        'Authorization': f"Bearer {token}"
        }
    try:    
        response = requests.request("POST", url, headers=headers)
        statusCode = response.status_code
        if statusCode == 200:
            parsedResponse = response.json()
            results = parsedResponse.get("results",[{}])[0]    
            licenseList = results.get("properties", {}).get("License Key", {}).get("title", [])
            if len(licenseList)>0:
                licenseKey = licenseList[0].get("plain_text", None)
                pageID = results.get("id", None)
                return licenseKey, pageID
            else:
                return None, None
        else:
            logging.error(f"Could not fetch license key: {statusCode}")    
            return None, None       
    except Exception as e:
        logging.exception(f"Could not fetch license key:{e}")
        return None, None

def verifyLicenseKey(licenseKey):
    url = "https://api.gumroad.com/v2/licenses/verify"
    params = {"product_permalink": "mlkqzw", "license_key" : licenseKey}
    try:
        verify = requests.post(url, headers= {"Authorization": "Bearer " + gumroadToken}, data=params)
        statusCode = verify.status_code
        if statusCode == 200:
            parsed = verify.json()
            return (parsed, 100)
        else:
            logging.error(f"Gumroad license key query failed: {statusCode}, license key: {licenseKey}, response: {verify.text}")
            return (None, 102)
    except Exception as e:
        logging.error(f"Gumroad license key query failed: {e}")
        return (None, 104)

def verifiedResponse(response, userId, licenseKey):
    if response.get("success") == True:
        numUses = response.get("uses", None)
        if numUses < 1:
            updateValidated(userId)
            addLicenseKey(userId, licenseKey)
            return 100
        elif numUses > 1:
            if userId in listRevoked:
                updateValidated(userId)
                updateRevoked(userId)
                addLicenseKey(userId, licenseKey)
                return 103
            else:
                return 101    
        elif numUses is None:
            logging.error("No key 'uses' found")
            return 104
    else:
        return 104    

def error(pageID, value, token):
    url = f'https://api.notion.com/v1/pages/{pageID}'
    message = errors[value]
    payload = {
                "properties": {
                "Status" : {
                    "rich_text" : [
                        {"text" : {
                            "content" : message
                        }
                    }
                ]
            }    
        }
    }
    try:
        r = requests.patch(url, json=payload, headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-02-22",
        "Content-Type": "application/json"
        })
        statusCode = r.status_code
        if statusCode != 200:
            logging.error(f"Could not patch message to Notion database:{statusCode}")
            return    
    except Exception as e:
        logging.exception(f"Could not patch message to Notion database:{e}")
        return

while True:
    listRevoked = getRevoked()
    listTokens = fetchToken()
    for token in listTokens:
        try: 
            databaseID, userID = fetchID(token)
            if databaseID is not None and userID is not None:
                licenseKey, pageID = fetchLicenseKey(databaseID, token)
                if licenseKey is not None and pageID is not None:
                    response = verifyLicenseKey(licenseKey)
                    if response[0] is not None:
                        value = verifiedResponse(response[0], userID, licenseKey)
                        error (pageID, value, token)
                    else:
                        error (pageID, response[1], token)    
        except Exception as e:
            logging.exception(e)                
    listTokens = []
    listRevoked = []

        



