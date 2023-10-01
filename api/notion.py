import copy
import string
import asyncio
import requests
import json
from decouple import config
import custom_logger

notion_props_list = [
    "Title",
    "Publisher",
    "Authors",
    "Summary",
    "Category",
    "Published",
    "ISBN_10",
    "Pages",
    "ISBN_13",
    "Summary_extd",
    "Other Identifier",
]

logging = custom_logger.get_logger()

notion_url = config("NOTION_URL")


def default_headers(token: str):
    return {
        "Content-Type": "application/json",
        "Notion-Version": "2022-02-22",
        "Authorization": f"Bearer {token}",
    }


def notion_search_id(object_type: str, object_name: str, user_details: dict):
    """Takes notion object type and name and returns its unique ID|request status code|None.
    
    :param object_type: database|page
    :param object_name: name of database|page
    :param user_details: {access_token: str, user_id: str}
    :returns: requested database ID if found, None if not.
    """
    notion_search_url = notion_url + "search"
    params = {
        "filter": {"value": object_type, "property": "object"},
        "query": object_name,
    }
    logging.info(
        "Querying for object", object_type=object_type, object_name=object_name, user_id=user_details["user_id"], service="notion"
    )
    try:
        response = requests.post(
            notion_search_url,
            headers = default_headers(user_details['access_token']),
            data = json.dumps(params)
        )
        status_code = response.status_code
        if status_code == 200:
            logging.info(
                "Successfuly queried for object",
                object_type=object_type,
                object_name=object_name,
                user_id=user_details["user_id"],
                service="notion"
            )
            parsed_response = response.json()
            results = parsed_response.get("results", [])
            if len(results) > 0:
                database_id = results[0].get("id", None)
                return database_id
            else:
                logging.error(
                    "Object not found",
                    object_type=object_type,
                    object_name=object_name,
                    user_id=user_details["user_id"],
                    service="notion",
                    status_code=status_code
                )
                return None
    except Exception:
        logging.exception(
            "Query for object failed",
            object_type=object_type,
            object_name=object_name,
            user_id=user_details["user_id"],
            service="notion",
            status_code=status_code
        )
    return None


async def get_data_from_database(session, user_info_: dict, payload: str) -> dict | None | int:
    """Takes user info and returns a dict with user info and newly added book identifiers
    
    :param user_info_: {user_id: str, database_id: str, access_token: str}
    :returns: {user_id: str, database_id: str, access_token: str, is_revoked: bool, new_books: []|None}
    """
    user_info = copy.deepcopy(user_info_)
    user_id = user_info["user_id"]
    database_id = user_info["database_id"]
    url = notion_url + f"databases/{database_id}/query"
    headers = default_headers(user_info["access_token"])
    logging.info(
        "Applying filters and fetching new additions to BookShelf", user_id=user_id, service="notion"
    )
    try:
        response = await session.request(method="POST", url=url, data=payload, headers=headers, ssl=False)
        if response.status == 401:
            await logging.awarning(
                "No access to Notion page/workspace",
                user_id=user_id,
                status_code=response.status,
                service="notion"
            )
            return -1 #for these users, is_revoked will be set to True (and therefore, 1 in the database)
        elif response.status == 404:
            await logging.awarning(
                "Cannot find database",
                database_id=user_info["database_id"],
                user_id=user_id,
                status_code=response.status,
                service="notion"
            )
            return -1 #for these users, is_revoked will be set to True (and therefore, 1 in the database)
        elif response.status == 200:
            await logging.ainfo(
                "Accessed database and fetched data",
                database_id=user_info["database_id"],
                user_id=user_id,
                service="notion"
            )
            parsed_response = await response.json()
            results = parsed_response["results"]
            if len(results) > 0:
                await logging.ainfo(
                    "New books found in the Bookshelf database",
                    user_id=user_id,
                    category="ACTION",
                    database_id=user_info["database_id"],
                    service="notion"
                )
            return results
        else:
            await logging.aerror(
                "Failed to fetch data from database",
                database_id=user_info["database_id"],
                status_code=response.status,
                response=await response.content,
                user_id=user_id,
                service="notion"
            )
            return None
    except Exception:
        await logging.aexception(
            "Failed to fetch data from database",
            database_id=user_info["database_id"],
            user_id=user_id,
            service="notion"
        )
        return None


def get_available_props(user_id: str, notion_data) -> list:
    """Get a list of properties in a user's Notion database that overlap with the properties intended to be autofilled."""
    props_list = []
    if len(notion_data) > 0:
        available_props = notion_data[0]["properties"] #Each result has a list of all available properties in the database
        for item in available_props.keys():
            if item in notion_props_list:
                props_list.append(item)
        logging.info(
            "All available fields to fill in database extracted",
            user_id=user_id,
            category="ACTION",
            service="notion"
        )
    else:
        logging.info(
            "There are no new additions or the notion database 'Bookshelf' is empty",
            user_id=user_id,
            service="notion"
        )
    return props_list


async def update_database(session, user_info_with_books_: dict) -> dict:
    """Updates notion database with new book details. Returns the same dict that is passed as an argument.
    
    :param user_info_with_books_: {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False, "new_identifiers": {"identifier": "identifier", "page_id": "page_id"}, "missing_properties": [], "book_details": {}, "mapped_book_details": {}, "image_file_path: "image_file_path"}
    :returns user_info_with_books | None
    """
    notion_page_url = notion_url + "pages"
    user_info_with_books = copy.deepcopy(user_info_with_books_)
    user_id = user_info_with_books["user_id"]
    page_id = user_info_with_books["new_identifiers"]["page_id"] #For one new book
    mapped_book_details = user_info_with_books["mapped_book_details"]
    url = notion_page_url + "/" + page_id
    title = string.capwords(mapped_book_details["Title"]) + mapped_book_details["Subtitle"]
    payload = {
        "cover": {
            "type": "external",
            "external": {"url": user_info_with_books["image_file_path"]},
        },
        "properties": {
            "Publisher": {
                "rich_text": [
                    {"text": {"content": mapped_book_details["Publisher"].title()}}
                ]
            },
            "Authors": {"multi_select": mapped_book_details["Authors"]},
            "Summary": {
                "rich_text": [{"text": {"content": mapped_book_details["Summary"]}}]
            },
            "Summary_extd": {
                "rich_text": [{"text": {"content": mapped_book_details["Summary_extd"]}}]
            },
            "Category": {"multi_select": mapped_book_details["Category"]},
            "Published": {
                "rich_text": [{"text": {"content": mapped_book_details["Published"]}}]
            },
            "ISBN_10": {
                "rich_text": [{"text": {"content": mapped_book_details["ISBN_10"]}}]
            },
            "ISBN_13": {
                "rich_text": [{"text": {"content": mapped_book_details["ISBN_13"]}}]
            },
            "Other Identifier": {
                "rich_text": [
                    {"text": {"content": mapped_book_details["Other Identifier"]}}
                ]
            },
            "Pages": {"number": mapped_book_details["Pages"]},
            "Title": {"title": [{"text": {"content": title}}]},
        },
    }
    for item in user_info_with_books["missing_properties"]:
        del payload["properties"][item]
    await logging.ainfo(
        "Adding new book details to Bookshelf",
        book_info=user_info_with_books["new_identifiers"]["value"],
        category="ACTION",
        user_id=user_id,
        service="notion"
    )
    # Added to solve the conflict_error, does not completely resolve it, only reduces it.
    await asyncio.sleep(1)
    r = await session.request(
        method="PATCH",
        url=url,
        json=payload,
        headers=default_headers(user_info_with_books["access_token"]),
        ssl=False,
    )
    parsed_response = await r.json()
    if r.status == 401 or r.status == 404:
        await logging.awarning(
            "Access revoked or database missing", status_code=r.status, user_id=user_id, service="notion"
        )
        user_info_with_books["is_revoked"] = True
        return user_info_with_books
    elif r.status != 200:
        await logging.aerror(
            "Could not update database with new book details",
            book_title=mapped_book_details["Title"],
            book_isbn_13=mapped_book_details["ISBN_13"],
            response=parsed_response,
            user_id=user_id,
            status_code=r.status,
            service="notion"
        )
        return None #In order to do a failure update
    else:
        await logging.ainfo(
            "Successfully updated book for user", user_id=user_id, category="ACTION", service="notion"
        )
        return user_info_with_books


async def failure_update(session, user_info_: dict) -> dict:
    """Update Notion database with new book identifier without the semicolon in case of failure to retrieve book details."""
    user_info = copy.deepcopy(user_info_)
    user_id = user_info["user_id"]
    identifiers = user_info["new_identifiers"]
    url = notion_url+ f"pages/{identifiers['page_id']}"
    if identifiers["type"] == "title":
        payload = {
            "properties": {
                "Title": {"title": [{"text": {"content": identifiers["value"]}}]}
            }
        }
    elif identifiers["type"] == "isbn_10":
        payload = {
            "properties": {
                "ISBN_10": {
                    "rich_text": [{"text": {"content": identifiers["value"]}}]
                }
            }
        }
    elif identifiers["type"] == "isbn_13":
        payload = {
            "properties": {
                "ISBN_13": {
                    "rich_text": [{"text": {"content": identifiers["value"]}}]
                }
            }
        }
    r = await session.request(
        method="PATCH",
        url=url,
        json=payload,
        headers=default_headers(user_info["access_token"]),
        ssl=False
    )
    if r.status == 401 or r.status == 404:
        await logging.awarning(
            "Access revoked or database missing", user_id=user_id, status_code=r.status, service="notion"
        )
        user_info["is_revoked"] = True
        return user_info
    elif r.status == 200:
        await logging.ainfo(
            "Succesfully removed ';'",
            input=user_info["new_identifiers"]["value"],
            user_id=user_id,
            category="ACTION",
            service="notion"
        )
        return user_info
    else:
        await logging.aerror(
            "Failed to update database in cannot retrieve",
            input=user_info["new_identifiers"]["value"],
            status_code=r.status,
            user_id=user_id,
            service="notion"
        )
        return user_info
