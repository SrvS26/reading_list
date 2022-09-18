import logging
import requests
import string
import failed
from aiohttp import ClientSession

ourList = [
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
]


def default_headers(token):
    return {
        "Content-Type": "application/json",
        "Notion-Version": "2022-02-22",
        "Authorization": f"Bearer {token}",
    }


# TODO: Fix the type of `user_info`
# [{user_id: String, database_id: String, access_token: String, is_revoked: Bool, results: {}|None}]
async def requiredPageDetails(session, user_info={}):
    user_id = user_info["user_id"]
    url = f"https://api.notion.com/v1/databases/{user_info['database_id']}/query"
    payload = '{"filter": {"or": [{"property": "Title","rich_text": {"ends_with": ";"}},{"property": "ISBN_10","rich_text": {"ends_with": ";"}},{"property": "ISBN_13","rich_text": {"ends_with": ";"}}]}}'
    headers = default_headers({user_info["access_token"]})
    logging.info("Applying filters and fetching new additions to BookShelf")
    try:
        response = await session.request(
            method="POST", url=url, data=payload, headers=headers, ssl=False
        )
        if response.status == 401:
            logging.warning(f"User {user_id} has revoked access")
            user_info["is_revoked"] = True
            user_info["new_books_adeed"] = None
            return user_info
        elif response.status == 404:
            logging.warning(f"User {user_id} has deleted Bookshelf")
            user_info["is_revoked"] = True
            user_info["new_books_added"] = None
            return user_info
        elif response.status == 200:
            logging.info(f"Fetched new additions to BookShelf for user: {user_id}")
            parsed_response = await response.json()
            results = parsed_response["results"]
            user_info["new_books_added"] = results
            return user_info
        else:
            logging.error(
                f"Failed due to status code: {response.status}, response: {parsed_response} for user: {user_id}"
            )
            user_info["new_books_added"] = None
            return user_info
    except Exception as e:
        logging.error(
            f"Failed to fetch new details from Bookshelf for user: {user_id}, Error: {e}"
        )
        user_info["new_books_added"] = None
        return user_info


def getAllFields(results):
    allAvailableList = []
    if len(results) > 0:
        onePagePropertyDetails = results[0]
        requiredPropertiesGeneral = onePagePropertyDetails["properties"]
        for item in requiredPropertiesGeneral.keys():
            if item in ourList:
                allAvailableList.append(item)
        logging.info("All available fields to fill in BookShelf fetched")
    else:
        logging.info(
            "There are no new additions or the notion database 'Bookshelf' is empty"
        )
    return allAvailableList


def getNewTitlesOrISBN(results):
    listOfAllTitlesOrISBN = []
    if len(results) > 0:
        for item in results:
            dicOfTitlesOrISBN = {}
            detailsOfISBN10 = item["properties"]["ISBN_10"]["rich_text"]
            detailsOfISBN13 = item["properties"]["ISBN_13"]["rich_text"]
            detailsOfTitle = item["properties"]["Title"]["title"]
            if len(detailsOfTitle) > 0:
                for i in detailsOfTitle:
                    actualTitle = i["text"]["content"]
            else:
                actualTitle = ""
            if len(detailsOfISBN10) > 0:
                for i in detailsOfISBN10:
                    actualISBN10 = i["text"]["content"]
            else:
                actualISBN10 = ""
            if len(detailsOfISBN13) > 0:
                for i in detailsOfISBN13:
                    actualISBN13 = i["text"]["content"]
            else:
                actualISBN13 = ""
            if actualTitle != "" and actualTitle[-1] == ";":
                dicOfTitlesOrISBN["Value"] = actualTitle[:-1]
                dicOfTitlesOrISBN["Type"] = "Title"
            elif actualISBN10 != "" and actualISBN10[-1] == ";":
                dicOfTitlesOrISBN["Value"] = actualISBN10[:-1]
                dicOfTitlesOrISBN["Type"] = "ISBN_10"
            elif actualISBN13 != "" and actualISBN13[-1] == ";":
                dicOfTitlesOrISBN["Value"] = actualISBN13[:-1]
                dicOfTitlesOrISBN["Type"] = "ISBN_13"
            if len(dicOfTitlesOrISBN) != 0:
                pageID = item["id"]
                dicOfTitlesOrISBN["pageID"] = pageID
                listOfAllTitlesOrISBN.append(dicOfTitlesOrISBN)
        logging.info("New titles/ISBN extracted from new additions to BookShelf")
    else:
        logging.info("No changes in BookShelf/No new titles/ISBN found")
    return listOfAllTitlesOrISBN


def compareLists(theirs):
    finalSet = set(ourList) - set(theirs)
    return list(finalSet)


async def updateDatabase(session, user_info):
    user_id = user_info["user_id"]
    pageID = user_info["new_book_identifiers"]["pageID"]
    availableFields = user_info["google_book_details"]
    url = f"https://api.notion.com/v1/pages/{pageID}"
    title = string.capwords(availableFields["Title"]) + availableFields["Subtitle"]
    payload = {
        "cover": {
            "type": "external",
            "external": {"url": user_info["image_file_path"]},
        },
        "properties": {
            "Publisher": {
                "rich_text": [
                    {"text": {"content": availableFields["Publisher"].title()}}
                ]
            },
            "Authors": {"multi_select": availableFields["Authors"]},
            "Summary": {
                "rich_text": [{"text": {"content": availableFields["Summary"]}}]
            },
            "Summary_extd": {
                "rich_text": [{"text": {"content": availableFields["Summary_extd"]}}]
            },
            "Category": {"multi_select": availableFields["Category"]},
            "Published": {
                "rich_text": [{"text": {"content": availableFields["Published"]}}]
            },
            "ISBN_10": {
                "rich_text": [{"text": {"content": availableFields["ISBN_10"]}}]
            },
            "ISBN_13": {
                "rich_text": [{"text": {"content": availableFields["ISBN_13"]}}]
            },
            "Pages": {"number": availableFields["Pages"]},
            "Title": {"title": [{"text": {"content": title}}]},
        },
    }
    for item in user_info["missing_properties"]:
        del payload["properties"][item]
    logging.info(f"Adding New book details to Bookshelf for user: {user_id}")
    r = await session.request(
        method="PATCH",
        url=url,
        json=payload,
        headers=default_headers({user_info["access_token"]}),
        ssl=False,
    )
    if r.status == 401 or r.status == 404:
        logging.warning(
            f"Access revoked/Database missing for {user_id}, status: {r.status}"
        )
        user_info["is_revoked"] = True
        return user_info
    elif r.status != 200:
        logging.error(
            f"Could not update database with new book details for {user_id}, Title: {availableFields['Title']}, ISBN_13; {availableFields['ISBN_13']}, only updating title/ISBN: {r.json()}"
        )
        return user_info
        # failed.cannotRetrieve(dicOfTitlesOrISBN, user_info) TODO: call cannot retrieve in the end for all failure cases
    else:
        logging.info("Successfully updated")
        return user_info
