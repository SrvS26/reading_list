import sqlite3
from sqlite3 import connect
from decouple import config
import requests

databaseFile = config("DATABASE_FILE_PATH")
gumroadToken = config("GUMROAD_TOKEN")
errors = {100:"Success" ,101: "The license key is already in use", 102: "Invalid license key"}
conn = sqlite3.connect(databaseFile)

def fetchToken():
    cursor = conn.cursor()
    data = """SELECT access_token FROM USERS WHERE is_validated = 0"""
    cursor.execute(data)
    records = cursor.fetchall()
    listTokens = []
    for item in records:
        listTokens.append(item[0])
    return listTokens    

def getRevoked():
    cursor = conn.cursor()
    data = """SELECT access_token FROM USERS WHERE is_revoked = 1"""
    cursor.execute(data)
    records = cursor.fetchall()
    listRevoked = []
    for item in records:
        listRevoked.append(item[0])
    return listRevoked   

def updateValidated(databaseId):
    cursor = conn.cursor()
    data = f"""UPDATE USERS SET is_validated = 1 WHERE database_id = '{databaseId}'"""
    cursor.execute(data)
    cursor.commit()
    return

def fetchID(token):
    databaseIDurl = "https://api.notion.com/v1/search"
    params = {"filter" : {"value" : "database","property" : "object"}, "query" : "License Key"}
    response = requests.post(databaseIDurl, headers= {"Notion-Version": "2022-02-22", "Authorization": "Bearer " + token},  data=params)
    parsedResponse = response.json()
    database = parsedResponse["results"][0]
    databaseID = database.get("id", "")
    pageID = database.get("parent", {}).get("page_id", "")
    return databaseID, pageID

def fetchLicenseKey(databaseID, token):
    url = f"https://api.notion.com/v1/databases/{databaseID}/query"    
    headers = {
        'Content-Type': "application/json",
        'Notion-Version': "2022-02-22",
        'Authorization': f"Bearer {token}"
        }
    response = requests.request("POST", url, headers=headers)
    parsedResponse = response.json()
    results = parsedResponse["results"][0]    
    licenseList = results.get("properties", {}).get("License Key", {}).get("title", [])
    licenseKey = licenseList[0].get("plain_text")
    return licenseKey

def verifyLicenseKey(licenseKey):
    url = "https://api.gumroad.com/v2/licenses/verify"
    params = {"product_permalink": "mlkqzw", "license_key" : licenseKey}
    verify = requests.post(url, headers= {"Authorization": "Bearer " + gumroadToken}, data=params)
    parsed = verify.json()
    return parsed

def verifiedResponse(response, databaseId):
    parsed = response.json()
    uses = parsed.get("uses")
    if response.status_code == 200:
        if uses == 0:
            updateValidated(databaseId)
            return 100
        else:
            return 101    
    if response.status_code != 200:
        return 102

def error(pageID, value, token):
    url = f'https://api.notion.com/v1/pages/{pageID}'
    error = errors[value]
    payload = {
                "Status" : {
                    "rich_text" : [
                        {"text" : {
                            "content" : error
                        }
                    }
                ]
            }    
        }
    r = requests.patch(url, json=payload, headers={
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
    })


while True:
    listTokens = fetchToken()
    print (listTokens)
    for token in listTokens:
        databaseID, pageID = fetchID(token)
        licenseKey = fetchLicenseKey(databaseID, token)
        response = verifyLicenseKey(licenseKey)
        value = verifiedResponse(response, databaseID)
        error (pageID, value, token)

        



