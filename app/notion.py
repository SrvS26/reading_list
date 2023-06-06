import copy
import custom_logger
import string
import asyncio
import requests
import json
from decouple import config

notion_props = [
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

logging, listener = custom_logger.get_logger("notion")

notion_database_url = config("NOTION_DATABASE_URL")
notion_page_url = config("NOTION_PAGE_URL")
notion_search_url = config("NOTION_SEARCH_URL")


def default_headers(token: str):
    return {
        "Content-Type": "application/json",
        "Notion-Version": "2022-02-22",
        "Authorization": f"Bearer {token}",
    }


def notion_search_id(object_type: str, object_name: str, user_details: dict):
    """
    Takes notion object type and name and returns its unique ID|request status code|None.
    :param object_type: database|page
    :param object_name: name of database|page
    :param user_details: {access_token: str, user_id: str}
    :returns: requested database ID if found, None if not, status code in case of an error.
    """
    params = {
        "filter": {"value": object_type, "property": "object"},
        "query": object_name,
    }
    logging.info(f"Querying for {object_type} ID for {object_name}")
    try:
        response = requests.post(
            notion_search_url,
            headers = default_headers(user_details['access_token']),
            data = json.dumps(params)
        )
        status_code = response.status_code
        if status_code == 200:
            logging.info(f"Successfuly queried for {object_type}: {object_name} for user: {user_details['user_id']}")
            parsed_response = response.json()
            results = parsed_response.get("results", [])
            if len(results) > 0:
                database_id = results[0].get("id", None)
                return database_id
            else:
                logging.error(f"{object_type} named {object_name} was not found in user: {user_details['user_id']} workspace")
                return None
    except Exception as e:
        logging.exception(f"Query for the {object_type}: {object_name} for user: {user_details['user_id']} failed due to {e}")
    return status_code


async def get_new_books(session, user_info_: dict) -> dict:
    """
    Takes user info and returns a dict with user info and newly added book titles/ISBNs
    :param user_info_: {user_id: str, database_id: str}
    :returns: {user_id: str, database_id: str, access_token: str, is_revoked: bool, new_books: []|None}
    """
    user_info = copy.deepcopy(user_info_)
    user_id = user_info["user_id"]
    url = notion_database_url + "/" + user_info['database_id'] + "/query"
    payload = '{"filter": {"or": [{"property": "Title","rich_text": {"ends_with": ";"}},{"property": "ISBN_10","rich_text": {"ends_with": ";"}},{"property": "ISBN_13","rich_text": {"ends_with": ";"}}]}}'
    headers = default_headers(user_info["access_token"])
    logging.info(f"Applying filters and fetching new additions to BookShelf for {user_id}")
    try:
        response = await session.request(method="POST", url=url, data=payload, headers=headers, ssl=False)
        if response.status == 401:
            logging.warning(f"User {user_id} has revoked access")
            user_info["is_revoked"] = True
            user_info["new_books"] = None
            return user_info
        elif response.status == 404:
            logging.warning(f"User {user_id} has deleted Bookshelf")
            user_info["is_revoked"] = True
            user_info["new_books"] = None
            return user_info
        elif response.status == 200:
            logging.info(f"Fetched new additions to BookShelf for user: {user_id}")
            parsed_response = await response.json()
            results = parsed_response["results"]
            user_info["new_books"] = results
            return user_info
        else:
            logging.error(f"Failed due to status code: {response.status}, response: {response.content} for user: {user_id}")
            user_info["new_books"] = None
            return user_info
    except Exception as e:
        logging.error(f"Failed to fetch new details from Bookshelf for user: {user_id}, Error: {e}")
        user_info["new_books"] = None
        return user_info


def get_available_props(user_info_: dict) -> list:
    """
    Returns a list of properties in a user's Notion database that are also a part of the list of properties that will be autofilled.
    """
    user_info = copy.deepcopy(user_info_)
    results = user_info["new_books"]
    user_id = user_info["user_id"]
    props_list = []
    if len(results) > 0:
        available_props = results[0]["properties"] #Each result has a list of all available properties in the database
        for item in available_props.keys():
            if item in notion_props:
                props_list.append(item)
        logging.info(f"All available fields to fill in BookShelf fetched for user: {user_id}")
    else:
        logging.info(f"There are no new additions or the notion database 'Bookshelf' is empty for user: {user_id}")
    return props_list


def get_book_identifier(user_info_: dict) -> list:
    """
    Returns a list of new books added by a user identified by a ; at -1.
    :param user_info_: {}
    :returns: [{type: str, value: str}]
    """
    user_info = copy.deepcopy(user_info_)
    new_books = user_info["new_books"]
    user_id = user_info["user_id"]
    new_books_list = []
    if len(new_books) > 0:
        for item in new_books:
            identifier = {}
            title_ = item["properties"]["Title"]["title"]
            isbn_10_ = item["properties"]["ISBN_10"]["rich_text"]
            isbn_13_ = item["properties"]["ISBN_13"]["rich_text"]
            if len(title_) > 0:
                for i in title_:
                    title = i["text"]["content"]
            else:
                title = ""
            if len(isbn_10_) > 0:
                for i in isbn_10_:
                    isbn_10 = i["text"]["content"]
            else:
                isbn_10 = ""
            if len(isbn_13_) > 0:
                for i in isbn_13_:
                    isbn_13 = i["text"]["content"]
            else:
                isbn_13 = ""
            if title != "" and title[-1] == ";": 
                identifier["value"] = title[:-1]
                identifier["type"] = "title"
            elif isbn_10 != "" and isbn_10[-1] == ";":
                identifier["value"] = isbn_10[:-1]
                identifier["type"] = "isbn_10"
            elif isbn_13 != "" and isbn_13[-1] == ";":
                identifier["value"] = isbn_13[:-1]
                identifier["type"] = "isbn_13"
            if len(identifier) != 0:
                page_id = item["id"]
                identifier["page_id"] = page_id
                new_books_list.append(identifier)
        logging.info(f"New titles/ISBN extracted from new additions to BookShelf for user: {user_id}")
    else:
        logging.info(f"No changes in BookShelf/No new titles/ISBN found for user: {user_id}")
    return new_books_list


def missing_props(user_props: list) -> list:
    """
    Returns a list of properties the user may have deleted
    """
    missing_props = set(notion_props) - set(user_props)
    return list(missing_props)


async def update_database(session, user_info_: dict) -> dict:
    """
    Updates notion database with new book details. Returns the same dict that is passed as an argument.
    """
    user_info = copy.deepcopy(user_info_)
    user_id = user_info["user_id"]
    page_id = user_info["identifier"]["page_id"] #For one new book
    book_details = user_info["fetched_book_details"]
    url = notion_page_url + "/" + page_id
    title = string.capwords(book_details["Title"]) + book_details["Subtitle"]
    payload = {
        "cover": {
            "type": "external",
            "external": {"url": user_info["image_file_path"]},
        },
        "properties": {
            "Publisher": {
                "rich_text": [
                    {"text": {"content": book_details["Publisher"].title()}}
                ]
            },
            "Authors": {"multi_select": book_details["Authors"]},
            "Summary": {
                "rich_text": [{"text": {"content": book_details["Summary"]}}]
            },
            "Summary_extd": {
                "rich_text": [{"text": {"content": book_details["Summary_extd"]}}]
            },
            "Category": {"multi_select": book_details["Category"]},
            "Published": {
                "rich_text": [{"text": {"content": book_details["Published"]}}]
            },
            "ISBN_10": {
                "rich_text": [{"text": {"content": book_details["ISBN_10"]}}]
            },
            "ISBN_13": {
                "rich_text": [{"text": {"content": book_details["ISBN_13"]}}]
            },
            "Other Identifier": {
                "rich_text": [
                    {"text": {"content": book_details["Other Identifier"]}}
                ]
            },
            "Pages": {"number": book_details["Pages"]},
            "Title": {"title": [{"text": {"content": title}}]},
        },
    }
    for item in user_info["missing_properties"]:
        del payload["properties"][item]
    logging.info(f"Adding New book details to Bookshelf for user: {user_id}, book: {user_info['identifier']['value']}")
    # Added to solve the conflict_error, does not completely resolve it, only reduces it.
    await asyncio.sleep(1)
    r = await session.request(
        method="PATCH",
        url=url,
        json=payload,
        headers=default_headers(user_info["access_token"]),
        ssl=False,
    )
    parsed_response = await r.json()
    if r.status == 401 or r.status == 404:
        logging.warning(f"Access revoked/Database missing for {user_id}, status: {r.status}")
        user_info["is_revoked"] = True
        return user_info
    elif r.status != 200:
        logging.error(f"Could not update database with new book details for {user_id}, Title: {book_details['Title']}, ISBN_13; {book_details['ISBN_13']}: {parsed_response}")
        return user_info
    else:
        logging.info(f"Successfully updated book for user: {user_id}")
        return user_info


async def failure_update(session, user_info_: dict) -> dict:
    """
    Updates Notion database with new book identifier without the semicolon in case of failure to retrieve book details.
    """
    user_info = copy.deepcopy(user_info_)
    user_id = user_info["user_id"]
    identifiers = user_info["new_book_identifiers"]
    url = notion_page_url + "/" + {identifiers["page_id"]}
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
    )
    if r.status == 401 or r.status == 404:
        logging.warning(f"Access revoked/Database missing for user: {user_id}")
        user_info["is_revoked"] = True
        return user_info
    elif r.status == 200:
        logging.info(f"Succesfully removed ';' for user: {user_id} with value: {user_info['new_book_identifiers']['value']}")
        return user_info
    else:
        logging.error(f"Failed to update database for user: {user_id} with value: {user_info['new_book_identifiers']['value']} in cannot retrieve, status: {r.status}")
        return user_info
