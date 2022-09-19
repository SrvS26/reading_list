import copy
from turtle import title
import requests
import custom_logger
import json
from decouple import config
import string


logging = custom_logger.get_logger("googlebooks")

google_api_key = config("GOOGLE_API_KEY")


async def getBookDetails(session, user_info_with_identifiers_):
    user_info_with_identifiers = copy.deepcopy(user_info_with_identifiers_)
    dicIdentifier = user_info_with_identifiers["new_book_identifiers"]
    user_id = user_info_with_identifiers["user_id"]
    if dicIdentifier.get("Type") == "Title":
        url = f"https://www.googleapis.com/books/v1/volumes?key={google_api_key}&q={dicIdentifier['Value']}"
    elif (
        dicIdentifier.get("Type") == "ISBN_10" or dicIdentifier.get("Type") == "ISBN_13"
    ):
        url = f"https://www.googleapis.com/books/v1/volumes?key={google_api_key}&q=isbn:{dicIdentifier['Value']}"
    webPage = await session.request(method="GET", url=url, ssl=False)
    if webPage.status != 200:
        logging.error(
            f"Failed request to fetch book details, Book: {dicIdentifier['Value']} for user: {user_id} with {webPage.status}"
        )
        user_info_with_identifiers["google_book_details"] = None
        return user_info_with_identifiers
        # failed.cannotRetrieve(dicIdentifier, token) TODO: call this in notion update in the end
    else:
        logging.info(
            f"Book details fetched for book: {dicIdentifier['Value']} for user: {user_id}"
        )
    parsedContent = await webPage.json()
    if parsedContent.get("totalItems", 0) > 0:
        listOfBookResults = parsedContent["items"]
        categories = getAllCategories(listOfBookResults)
        firstBookResult = listOfBookResults[0]
        bookDetails = firstBookResult.get("volumeInfo")
        requiredBookDetails = [
            "title",
            "subtitle",
            "authors",
            "publisher",
            "publishedDate",
            "description",
            "industryIdentifiers",
            "pageCount",
            "categories",
            "imageLinks",
        ]
        dicOfRequiredBookDetails = {}
        for item in requiredBookDetails:
            if item == "categories":
                dicOfRequiredBookDetails[item] = categories
            elif item in bookDetails.keys():
                dicOfRequiredBookDetails[item] = bookDetails[item]
            else:
                continue
        user_info_with_identifiers["google_book_details"] = dicOfRequiredBookDetails
        return user_info_with_identifiers
    else:
        logging.warning(
            f"No google book results were found for {dicIdentifier.get('Type')}: {dicIdentifier.get('Value')} only updating title/ISBN"
        )
        user_info_with_identifiers["google_book_details"] = None
        # failed.cannotRetrieve(dicIdentifier, token) TODO: call this in the end notion update
        return user_info_with_identifiers


def mapOneDicToAnother(ourDic, GoogleBookInfo):
    ourDic["Publisher"] = GoogleBookInfo.get("publisher", "")
    listauthors = []
    if GoogleBookInfo.get("authors") != None and len(GoogleBookInfo["authors"]) > 0:
        for item in GoogleBookInfo["authors"]:
            authors = {}
            authors["name"] = string.capwords(item).replace(",", "")
            listauthors.append(authors)
    ourDic["Authors"] = listauthors
    summary = GoogleBookInfo.get("description", "")
    if len(summary) > 2000:
        summary = summary[:1997] + "..."
        summary_extd = summary[1998:]
        ourDic["Summary_extd"] = summary_extd
    ourDic["Summary"] = summary
    ourDic["Published"] = GoogleBookInfo.get("publishedDate", "")
    if GoogleBookInfo.get("industryIdentifiers") != None:
        for element in GoogleBookInfo["industryIdentifiers"]:
            if element["type"] in ["ISBN_10", "ISBN_13"]:
                if element["type"] == "ISBN_10":
                    ourDic["ISBN_10"] = element["identifier"]
                if element["type"] == "ISBN_13":
                    ourDic["ISBN_13"] = element["identifier"]
            else:
                ourDic["ISBN_10"] = ""
                ourDic["ISBN_13"] = ""
    else:
        ourDic["ISBN_10"] = ""
        ourDic["ISBN_13"] = ""
    ourDic["Pages"] = GoogleBookInfo.get("pageCount", 0)
    ourDic["Title"] = GoogleBookInfo.get("title", "")
    subTitle = GoogleBookInfo.get("subtitle", "")
    if subTitle != "":
        ourDic["Subtitle"] = f": {subTitle}"
    listcategory = []
    if (
        GoogleBookInfo.get("categories") != None
        and len(GoogleBookInfo["categories"]) > 0
    ):
        for item in GoogleBookInfo["categories"]:
            category = {}
            category["name"] = string.capwords(item.replace(",", " "))
            listcategory.append(category)
    ourDic["Category"] = listcategory
    if GoogleBookInfo.get("imageLinks") != None:
        imageLink = GoogleBookInfo["imageLinks"]["thumbnail"]
        ourDic["Image_url"] = imageLink
    logging.info("Google book details matched to appropriate fields in BookShelf")
    return ourDic


def getAllCategories(allResults):
    allCategories = []
    for i in allResults:
        categories = i.get("volumeInfo", {}).get("categories", [])
        allCategories = allCategories + categories
    finalCategories = set(allCategories)
    return finalCategories
