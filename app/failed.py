import requests
import logging
import asyncio

from app.notion import default_headers

logging.basicConfig(
    filename="app.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


def cannotRetrieve(session, user_info):
    user_id = user_info["user_id"]
    dicOfTitlesOrISBN = user_info["new_book_identifiers"]
    url = f'https://api.notion.com/v1/pages/{dicOfTitlesOrISBN["pageID"]}'
    if dicOfTitlesOrISBN["Type"] == "Title":
        payload = {
            "properties": {
                "Title": {"title": [{"text": {"content": dicOfTitlesOrISBN["Value"]}}]}
            }
        }
    elif dicOfTitlesOrISBN["Type"] == "ISBN_10":
        payload = {
            "properties": {
                "ISBN_10": {
                    "rich_text": [{"text": {"content": dicOfTitlesOrISBN["Value"]}}]
                }
            }
        }
    elif dicOfTitlesOrISBN["Type"] == "ISBN_13":
        payload = {
            "properties": {
                "ISBN_13": {
                    "rich_text": [{"text": {"content": dicOfTitlesOrISBN["Value"]}}]
                }
            }
        }
    r = session.request(
        method="PATCH",
        url=url,
        json=payload,
        headers=default_headers(user_info["access_token"]),
    )
    if r.status == 401 or r.status == 404:
        logging.warning(f"Access revoked/Database missing for user: {user_id}")
        user_info["is_revoked"] = True
        return user_info
    elif r.status == 200:
        logging.info(
            f"Succesfully removed ';' for user: {user_id} with value: {user_info['new_book_identifiers']['Value']}"
        )
        return user_info
    else:
        logging.error(
            f"Failed to update database for user: {user_id} with value: {user_info['new_book_identifiers']['Value']} in cannot retrieve, status: {r.status}"
        )
        return user_info
