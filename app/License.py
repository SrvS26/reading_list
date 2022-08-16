import json
import sqlite3
from decouple import config
import requests
import logging
import time

logging.basicConfig(
    filename="license.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)
databaseFile = config("DATABASE_FILE_PATH")
gumroadToken = config("GUMROAD_TOKEN")
gumroadProductId = config("GUMROAD_PRODUCT_ID")
errors = {
    100: "Success",
    101: "The license key is already in use",
    102: "Invalid license key",
    103: "Your access has been reinstated",
    104: "An error occurred. Please try again later",
}
conn = sqlite3.connect(databaseFile)


# fetchToken :: () -> [{"user_id"::str, "access_token"::str}]
def fetchToken():
    cursor = conn.cursor()
    data = """SELECT access_token, user_id FROM USERS WHERE is_validated = 0"""
    try:
        cursor.execute(data)
        records = cursor.fetchall()
    except Exception as e:
        logging.exception(f"Could not fetch tokens from Users: {e}")
    listTokens = []
    if len(records) > 0:
        for item in records:
            user_details = {}
            user_details["access_token"] = item[0]
            user_details["user_id"] = item[1]
            listTokens.append(user_details)
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
    data = f"""UPDATE USERS SET is_validated = 1, is_revoked = 0 WHERE user_id = '{userId}'"""
    try:
        cursor.execute(data)
    except Exception as e:
        logging.exception(f"Could not update is_validated for {userId}: {e}")
    conn.commit()
    return


def addLicenseKey(userId, licenseKey):
    cursor = conn.cursor()
    data = (
        f"""UPDATE USERS SET license_key = '{licenseKey}' WHERE user_id = '{userId}'"""
    )
    try:
        cursor.execute(data)
    except Exception as e:
        logging.exception(f"Could not update license_key for {userId}: {e}")
    conn.commit()
    return


def fetchID(userDetails):
    token = userDetails["access_token"]
    userID = userDetails["user_id"]
    databaseIDurl = "https://api.notion.com/v1/search"
    params = {
        "filter": {"value": "database", "property": "object"},
        "query": "License Key",
    }
    try:
        response = requests.post(
            databaseIDurl,
            headers={
                "Notion-Version": "2022-02-22",
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
            data=json.dumps(params),
        )
        statusCode = response.status_code
        if statusCode == 200:
            parsedResponse = response.json()
            database = parsedResponse.get("results", [])
            if len(database) > 0:
                databaseResults = database[0]
                databaseID = databaseResults.get("id", None)
                return (databaseID, userID)
            else:
                logging.error(f"License Key database not found for user: ", {userID})
                return (None, None)
        else:
            logging.error(
                f"Query for databaseID for user: {userID} failed with {statusCode}"
            )
            return (None, None)
    except Exception as e:
        logging.exception(f"Query for databaseID and userID failed: {e}")
        return (None, None)

def fetchLicenseKey(databaseID, userDetails):
    token = userDetails["access_token"]
    userID = userDetails["user_id"]
    url = f"https://api.notion.com/v1/databases/{databaseID}/query"
    payload = {"filter": {
        "property": "License Key",
        "rich_text": {"ends_with": ";"}
    }}
    headers = {
        "Content-Type": "application/json",
        "Notion-Version": "2022-02-22",
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.request("POST", url, json=payload, headers=headers)
        statusCode = response.status_code
        if statusCode == 200:
            parsedResponse = response.json()
            allResults = parsedResponse.get("results", [{}])
            if len(allResults) != 0:
                results = allResults[0]
                licenseList = (
                        results.get("properties", {}).get("License Key", {}).get("title", [])
                    )
                if len(licenseList) != 0:
                    recLicenseKey = licenseList[0].get("plain_text", None)
                        # if licenseKey[-1] == ";":
                    altLicenseKey = recLicenseKey[:-1]
                    licenseKey = ''.join(altLicenseKey.splitlines())
                    pageID = results.get("id", None)
                    return licenseKey, pageID
                else:
                    return None, None
            else:
                return None, None
        else:
            logging.error(f"Could not fetch license key for user: {userID}, error: {statusCode}")
            return None, None
    except Exception as e:
        logging.exception(f"Could not fetch license key for user: {userID}, exception: {e}")
        return None, None


def verifyLicenseKey(licenseKey, userDetails):
    userID = userDetails["user_id"]
    url = "https://api.gumroad.com/v2/licenses/verify"
    params = {"product_permalink": gumroadProductId, "license_key": licenseKey.strip()}
    try:
        verify = requests.post(url, headers={}, data=params)
        statusCode = verify.status_code
        if statusCode == 200:
            parsed = verify.json()
            return (parsed, 100)
        else:
            logging.error(
                f"Gumroad license key query failed for user: {userID}, status code: {statusCode}, license key: {licenseKey}, response: {verify.text}"
            )
            return (None, 102)
    except Exception as e:
        logging.error(f"Gumroad license key query failed for user: {userID}, {e}")
        return (None, 104)


def verifiedResponse(response, userId, licenseKey, listRevoked):
    if response.get("success") == True:
        numUses = response.get("uses", None)
        if numUses == 1:
            updateValidated(userId)
            addLicenseKey(userId, licenseKey)
            return 100
        elif numUses > 1:
            if userId in listRevoked:
                updateValidated(userId)
                addLicenseKey(userId, licenseKey)
                return 103
            else:
                return 101
        elif numUses is None:
            logging.error("No key 'uses' found")
            return 104
    else:
        return 104


def error(pageID, value, userDetails, licenseKey):
    token = userDetails["access_token"]
    userID = userDetails["user_id"]
    url = f"https://api.notion.com/v1/pages/{pageID}"
    message = errors[value]
    payload = {
        "properties": {
            "Status": {"rich_text": [{"text": {"content": message}}]},
            "License Key": {"title": [{"text": {"content": licenseKey}}]},
        }
    }
    try:
        r = requests.patch(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-02-22",
                "Content-Type": "application/json",
            },
        )
        statusCode = r.status_code
        if statusCode != 200:
            logging.error(
                f"Could not patch message to Notion database:{statusCode} for user: {userID}"
            )
            return
    except Exception as e:
        logging.exception(
            f"Could not patch message to Notion database:{e} for user: {userID}"
        )
        return


while True:
    listRevoked = getRevoked()
    listTokens = fetchToken()
    for userDetails in listTokens:
        try:
            userID = userDetails["user_id"]
            databaseID, userID = fetchID(userDetails)
            if databaseID is not None:
                licenseKey, pageID = fetchLicenseKey(databaseID, userDetails)
                if licenseKey is not None and pageID is not None:
                    response = verifyLicenseKey(licenseKey, userDetails)
                    if response[0] is not None:
                        value = verifiedResponse(
                            response[0], userID, licenseKey, listRevoked
                        )
                        error(pageID, value, userDetails, licenseKey)
                    else:
                        error(pageID, response[1], userDetails, licenseKey)
        except Exception as e:
            logging.exception(e)
    time.sleep(5)
