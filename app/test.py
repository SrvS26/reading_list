import requests
import json


def getAllCategories(allResults):
    allCategories = []
    for i in allResults:
        categories = i.get("volumeInfo", {}).get("categories", [])
        allCategories = allCategories + categories
    finalCategories = set(allCategories)
    return finalCategories


def getBookDetails(dicOfTitlesOrISBN):
    url = "https://www.googleapis.com/books/v1/volumes?q=" + dicOfTitlesOrISBN
    webPageDetails = requests.get(url)
    webPageContent = webPageDetails.content
    parsedContent = json.loads(webPageContent)
    print(parsedContent.get("totalItems"))
    if parsedContent.get("totalItems", 0) > 0:
        listOfBookResults = parsedContent["items"]
        categories = getAllCategories(listOfBookResults)
        firstBookResult = listOfBookResults[0]
        bookDetails = firstBookResult.get("volumeInfo")
        requiredBookDetails = [
            "title",
            "authors",
            "publisher",
            "publishedDate",
            "description",
            "industryIdentifiers",
            "pageCount",
            "categories",
            "imageLinks",
        ]
        # print(bookDetails)
        dicOfRequiredBookDetails = {}
        for item in requiredBookDetails:
            if item == "categories":
                dicOfRequiredBookDetails[item] = categories
            elif item in bookDetails.keys():
                dicOfRequiredBookDetails[item] = bookDetails[item]
            else:
                continue
        return dicOfRequiredBookDetails
    else:
        # logging.info(
        #     f"No google book results were found for {dicOfTitlesOrISBN.get('Type')}: {dicOfTitlesOrISBN.get('Value')} only updating title/ISBN"
        # )
        # cannotRetrieve(dicOfTitlesOrISBN)
        return None


print(getBookDetails("learning how to learn"))
