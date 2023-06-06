import json
import sqlite3
from decouple import config
import requests
import logging
import time
from app import notion


logging.basicConfig(
    filename="license_key.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    level=logging.DEBUG,
    datefmt="%d-%b-%y %H:%M:%S",
)

database_file_path = config("DATABASE_FILE_PATH")
gumroad_token = config("GUMROAD_TOKEN")
gumroad_product_id = config("GUMROAD_PRODUCT_ID")

outcomes = {
    100: "Success",
    101: "The license key is already in use",
    102: "Invalid license key",
    103: "Your access has been reinstated",
    104: "An error occurred. Please try again later",
}

conn = sqlite3.connect(database_file_path)


def new_user_details() -> list:
    """
    Fetches the user ID and access token for new users from the USERS database to validate license.
    :returns: [{user_id: str, access_token: str}]
    """
    cursor = conn.cursor()
    data = """SELECT access_token, user_id FROM USERS WHERE is_validated = 0 and database_id != '-1'"""
    try:
        cursor.execute(data)
        records = cursor.fetchall()
    except Exception as e:
        logging.exception(f"Could not fetch new user access tokens from USERS: {e}")
    new_users = []
    logging.info(f"Fetched {len(new_users)} number of tokens from USERS")
    if len(records) > 0:
        for item in records:
            user_details = {"access_token": item[0], "user_id": item[1]}
            new_users.append(user_details)
    return new_users


def revoked_access() -> list:
    """
    Fetches the user ID for users that have revoked our access to their Notion workspace or deleted the My Bookshelf page.
    :returns: [{user_id: str}]
    """
    cursor = conn.cursor()
    data = """SELECT user_id FROM USERS WHERE is_revoked = 1"""
    try:
        cursor.execute(data)
        records = cursor.fetchall()
    except Exception as e:
        logging.exception(f"Could not fetch is_revoked from Users: {e}")
    revoked_users = []
    if len(records) > 0:
        for item in records:
            revoked_users.append(item[0])
    return revoked_users


def update_validated_status(user_id: str, license_key: str):
    """
    Updates the license key validated status and the license key in the USERS database.
    """
    cursor = conn.cursor()
    data = f"""UPDATE USERS SET is_validated = 1, is_revoked = 0, license_key = '{license_key}' WHERE user_id = '{user_id}'"""
    try:
        cursor.execute(data)
        logging.info("User status updated as validated")
    except Exception as e:
        logging.exception(f"Could not update validated status for {user_id}: {e}")
    conn.commit()
    return


# this is supposed to do the same exact thing that one of the other functions is doing to fetch the database ID, why not simply use that function?
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
            logging.info("Successfully queried for License key database")
            parsedResponse = response.json()
            database = parsedResponse.get("results", [])
            if len(database) > 0:
                databaseResults = database[0]
                databaseID = databaseResults.get("id", None)
                return (databaseID, userID)
            else:
                logging.error(f"License Key database not found for user: {userID}")
                return (None, None)
        else:
            logging.error(
                f"Query for databaseID for user: {userID} failed with {statusCode}"
            )
            return (None, None)
    except Exception as e:
        logging.exception(f"Query for databaseID and userID failed: {e}")
        return (None, None)


# This functions also, does the same as the other one, just for a different database, see if they can be clubbed into one.
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
                    logging.info(f"Received license key: {recLicenseKey} for user: {userID}")
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


def purchased_goodreads(user_id):
    cursor_object = conn.cursor()
    data = f"""INSERT INTO GOODREADS (user_id) VALUES ('{user_id}')"""
    cursor_object.execute(data)
    logging.info("Updated GOODREADS table with user details")
    conn.commit()
    cursor_object.close()
    return


# this can be done in the notion.py file. one function for all.
def error(pageID, value, userDetails, licenseKey):
    token = userDetails["access_token"]
    userID = userDetails["user_id"]
    url = f"https://api.notion.com/v1/pages/{pageID}"
    message = outcomes[value]
    if value == 102:
        message = message + ": " + licenseKey
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
    listRevoked = revoked_access()
    listTokens = new_user_details()
    for userDetails in listTokens:
        try:
            userID = userDetails["user_id"]
            database_id = notion.notion_search_id("database", "License Key", userDetails)
            databaseID, userID = fetchID(userDetails)
            if databaseID is not None:
                licenseKey, pageID = fetchLicenseKey(databaseID, userDetails)
                if licenseKey is not None and pageID is not None:
                    response = verifyLicenseKey(licenseKey, userDetails)
                    if response[0] is not None:
                        value = verifiedResponse(
                            response[0], userID, licenseKey, listRevoked
                        )
                        if getGumroadVariant(response[0]) == True:
                            logging.info("Goodreads import with autofill purchased")
                            goodreadsEntry(userID)
                        error(pageID, value, userDetails, licenseKey)
                    else:
                        error(pageID, response[1], userDetails, licenseKey)
        except Exception as e:
            logging.exception(e)
    time.sleep(5)
