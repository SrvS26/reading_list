import json
import sqlite3
from decouple import config
import requests
import logging
import time
import database.database as database
import notion.notion as notion


verify_url = config("GUMROAD_VERIFY_URL")
gumroad_token = config("GUMROAD_TOKEN")
gumroad_product_id = config("GUMROAD_PRODUCT_ID")

logging.basicConfig(
    filename="license_key_verification.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    level=logging.DEBUG,
    datefmt="%d-%b-%y %H:%M:%S",
)

database_file_path = config("DATABASE_FILE_PATH")

outcomes = {
    100: "Success",
    101: "The license key is already in use",
    102: "Invalid license key",
    103: "Your access has been reinstated",
    104: "An error occurred. Please try again later",
}

conn = sqlite3.connect(database_file_path)


def new_user_details() -> list:
    """Fetches the user ID and access token for new users from the USERS database to validate license.

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
    """Fetches the user ID for users that have revoked access to their Notion workspace or deleted the My Bookshelf page/Bookshelf database.
    
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
    """To update the license key validated status and the license key in the USERS database."""
    cursor = conn.cursor()
    data = f"""UPDATE USERS SET is_validated = 1, is_revoked = 0, license_key = '{license_key}' WHERE user_id = '{user_id}'"""
    try:
        cursor.execute(data)
        logging.info("User status updated as validated")
    except Exception as e:
        logging.exception(f"Could not update validated status for {user_id}: {e}")
    conn.commit()
    return



def get_license_key(database_id: str, user_info) -> tuple:
    """Takes user details and gets the license key they enter in their Notion "License Key" database

    :param user_info: {"access_token": "access_token", "user_id": "user_id"}
    :returns: ("license key", "page_id")|(None, None)
    """
    access_token = user_info["access_token"]
    user_id = user_info["user_id"]
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {"filter": {
        "property": "License Key",
        "rich_text": {"ends_with": ";"}
    }}
    headers = notion.default_headers(access_token)
    try:
        response = requests.request("POST", url, json=payload, headers=headers)
        status_code = response.status_code
        if status_code == 200:
            parsed_response = response.json()
            all_results = parsed_response.get("results", [{}])
            if len(all_results) != 0:
                results = all_results[0]
                license_key_ = (
                        results.get("properties", {}).get("License Key", {}).get("title", [])
                    )
                if len(license_key_) != 0:
                    license_key_text = license_key_[0].get("plain_text", None)
                    logging.info(f"Received license key: {license_key_text} for user: {user_id}")
                    license_key = ''.join(license_key_text[:-1].splitlines())
                    page_id = results.get("id", None)
                    return license_key, page_id
                else:
                    return None, None
            else:
                return None, None
        else:
            logging.error(f"Could not fetch license key for user: {user_id}, error: {status_code}")
            return None, None
    except Exception as e:
        logging.exception(f"Could not fetch license key for user: {user_id}, exception: {e}")
        return None, None


def purchased_goodreads(user_id: str): #For Goodreads experiment
    """To add user details to GOODREADS table if user has purchased the goodreads import feature"""
    cursor_object = conn.cursor()
    data = f"""INSERT INTO GOODREADS (user_id) VALUES ('{user_id}')"""
    cursor_object.execute(data)
    logging.info("Updated GOODREADS table with user details")
    conn.commit()
    cursor_object.close()
    return


def update_page(page_id: str, value: int, user_info: dict, license_key: str):
    """To update status of license key on the user's Notion "License Key" database"""
    access_token = user_info["access_token"]
    userID = user_info["user_id"]
    url = f"https://api.notion.com/v1/pages/{page_id}"
    message = outcomes[value]
    if value == 102:
        message = message + ": " + license_key
    headers = notion.default_headers(access_token)
    payload = {
        "properties": {
            "Status": {"rich_text": [{"text": {"content": message}}]},
            "License Key": {"title": [{"text": {"content": license_key}}]},
        }
    }
    try:
        r = requests.patch(
            url,
            json=payload,
            headers=headers,
        )
        status_code = r.status_code
        if status_code != 200:
            logging.error(
                f"Could not patch message to Notion database:{status_code} for user: {userID}"
            )
            return
    except Exception as e:
        logging.exception(
            f"Could not patch message to Notion database:{e} for user: {userID}"
        )
        return

def verify_license(license_key: str, user_details: dict) -> tuple:
    """Verifies user license key with Gumroad and returns reponse and response code.
    
    :param user_info: {"access_token": "access_token", "user_id": "user_id"}
    :returns: (response, response code)|(None, response code)
    """
    params = {"product_permalink": gumroad_product_id, "license_key": license_key.strip()}
    try:
        response = requests.post(verify_url, headers={}, data=params)
        status_code = response.status_code
        if status_code == 200:
            logging.info("Successfully verified license key with Gumroad")
            parsed_response = response.json()
            return (parsed_response, 100)
        else:
            logging.error(f"Gumroad license key query failed for user: {user_details['user_id']}, status code: {status_code}, license key: {license_key}, response: {response.text}")
            return (None, 102)
    except Exception as e:
        logging.error(f"Gumroad license key query failed for user: {user_details['user_id']}, {e}")
        return (None, 104)
    

def gumroad_response(response, user_id: str, license_key: str, revoked_users: list) -> int:
    """To check if license key is successfully validated and to ensure that the license is key is being used only by one user."""
    if response.get("success") == True:
        logging.info("License key successfully validated")
        num_uses = response.get("uses", None)
        if num_uses == 1:
            update_validated_status(user_id, license_key)
            return 100
        elif num_uses > 1:
            if user_id in revoked_users:
                update_validated_status(user_id, license_key)
                return 103
            else:
                return 101
        elif num_uses is None:
            logging.error("No key 'uses' found in the Gumroad response for license key query")
            return 104
    else:
        return 104


def get_gumroad_variant(response) -> bool:
    """To checks if user has purchased the product with/without additional goodreads import feature"""
    tier = response.get("purchase").get("variants")
    return tier == "(Auto-fill Feature with Goodreads Import)"     


while True:
    revoked_users = revoked_access()
    user_details_list = new_user_details()
    for user_info in user_details_list:
        try:
            user_id = user_info["user_id"]
            database_id = notion.notion_search_id("database", "License Key", user_info)
            if database_id is not None:
                license_key, page_id = get_license_key(database_id, user_info)
                if license_key is not None and page_id is not None:
                    response = verify_license(license_key, user_info)
                    if response[0] is not None:
                        value = gumroad_response(response[0], user_id, license_key, revoked_users)
                        if get_gumroad_variant(response[0]) == True:
                            logging.info("Goodreads import with autofill purchased")
                        update_page(page_id, value, user_info, license_key)
                    else:
                        update_page(page_id, response[1], user_info, license_key)
        except Exception as e:
            logging.exception(e)
    time.sleep(5)