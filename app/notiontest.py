from datetime import datetime
from lib2to3.pgen2 import token
from urllib import response
from decouple import config
import json
import string
import aiohttp
import asyncio
import os
from aiohttp import ClientSession
import requests
import datetime
import logging
import failed

bookIdent = {'Value': 'Self Care', 'Type': 'Title', 'pageID': 'd4f6833f-91e1-4bd4-b7b1-9ef834be2708'}

logging.basicConfig(filename='app.log', format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

availableFields = {'Title': 'Self Care', 'Subtitle': ': A Novel', 'Publisher': 'Penguin', 'Authors': [{'name': 'Leigh Stein'}], 'Summary': '"Highbrow, brilliant." --The Approval Matrix, New York magazine One of Cosmopolitan\'s 12 Books You\'ll Be Dying to Read This Summer A Publishers Weekly Best Book of Summer 2020 A Vulture Best Book of Summer 2020 One of Refinery29\'s 25 Books You\'ll Want to Read This Summer An Esquire Must-Read Book of Summer 2020 A Book Riot Best Book of 2020 *so far The female cofounders of a wellness start-up struggle to find balance between being good people and doing good business, while trying to stay BFFs. Maren Gelb is on a company-imposed digital detox. She tweeted something terrible about the President\'s daughter, and as the COO of Richual, “the most inclusive online community platform for women to cultivate the practice of self-care and change the world by changing ourselves,” it\'s a PR nightmare. Not only is CEO Devin Avery counting on Maren to be fully present for their next round of funding, but indispensable employee Khadijah Walker has been keeping a secret that will reveal just how feminist Richual’s values actually are, and former Bachelorette contestant and Richual board member Evan Wiley is about to be embroiled in a sexual misconduct scandal that could destroy the company forever. Have you ever scrolled through Instagram and seen countless influencers who seem like experts at caring for themselves—from their yoga crop tops to their well-lit clean meals to their serumed skin and erudite-but-color-coded reading stack? Self Care delves into the lives and psyches of people working in the wellness industry and exposes the world behind the filter.', 'Summary_extd': '', 'Category': [{'name': 'Fiction'}], 'Published': '2020-06-30', 'ISBN_10': '0525506861', 'Pages': 256, 'ISBN_13': '9780525506867', 'Image_url': 'http://books.google.com/books/content?id=ylS9DwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api'}


ourList = ["Title", "Publisher", "Authors", "Summary", "Category", "Published", "ISBN_10", "Pages", "ISBN_13", "Summary_extd"]

listValidated = [{"token": "secret_3gzbsui1WsfopYFqG7ZPwtkws580r19nCyv9QVhk8tW", "database_id": "04cb1b93-e5eb-4bd6-982d-059d1d6d6260", "user_id": "bf0d816a-d155-4be4-bc24-3b7920af878d", "pageCoverURL": "https://seven-forward.com/images/Switch030759016X9780307590169.jpg", "page_id": "asfargfrea"}, 
{"token": "secret_tzNMHI9yXDJSbTnGsqY85X6PzGuppxmOWlDmjJjlbUa", "database_id": "f3e3bf71-7151-4c2e-bd2d-bc8ebc3b2d38", "user_id": "33db28af-ed0e-4b3b-8447-d7ac7e836c1d", "pageCoverURL": "https://seven-forward.com/images/Switch030759016X9780307590169.jpg", "page_id": "afaegrvgre"}]

async def requiredPageDetails(item, session):
    databaseID = item["database_id"]
    token = item["token"]
    user_id = item["user_id"]
    url = f"https://api.notion.com/v1/databases/{databaseID}/query"
    payload = "{\"filter\": {\"or\": [{\"property\": \"Title\",\"rich_text\": {\"ends_with\": \";\"}},{\"property\": \"ISBN_10\",\"rich_text\": {\"ends_with\": \";\"}},{\"property\": \"ISBN_13\",\"rich_text\": {\"ends_with\": \";\"}}]}}"
    headers = {
        'Content-Type': "application/json",
        'Notion-Version': "2022-02-22",
        'Authorization': f"Bearer {token}"
        }
    logging.info("Applying filters and fetching new additions to BookShelf")    
    try:
        response = await session.request("POST", url, data=payload, headers=headers, ssl=False)
        if response.status == 401:
            logging.warning(f"User {user_id} has revoked access")
            return 401
        elif response.status == 404:
            logging.warning(f"User {user_id} has deleted Bookshelf")
            return 404
        elif response.status == 200:
            logging.info(f"Fetched new additions to BookShelf for user: {user_id}")
            parsed_response = await response.json()
            results = parsed_response["results"]  
            return results
        else:
            logging.error(f"Failed due to status code: {response.status}, response: {response.json()} for user: {user_id}")     
            return None
    except Exception as e:
        logging.error(f"Failed to fetch new details from Bookshelf for user: {user_id}, Error: {e}") 
        return None

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
        logging.info("There are no new additions or the notion database 'Bookshelf' is empty") 
    print (allAvailableList)                                              
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


def compareLists(Theirs):
    finalSet = set(ourList) - set(Theirs)
    return list(finalSet)


async def updateDatabase(availableFields, dicOfTitlesOrISBN, deletedProperty, session, item):
    pageID = item["page_id"]
    userID = item["user_id"]
    token = item["token"]
    pageCoverURL = item["pageCoverURL"]
    url = f'https://api.notion.com/v1/pages/{pageID}'
    title = string.capwords(availableFields ["Title"]) + availableFields["Subtitle"]
    payload = {
        "cover" : {
            "type" : "external",
            "external" : {
                "url" : pageCoverURL
            } 
        },
        "properties" : {
            "Publisher" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Publisher"].title()
                        }
                    }
                ]
            },
            "Authors" : {
                "multi_select" :  availableFields["Authors"]
            },
            "Summary" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Summary"]
                        }
                    }
                ]
            },
            "Summary_extd" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Summary_extd"]
                        }
                    }
                ]
            },
            "Category" : {
                        "multi_select" : availableFields["Category"]
            },
            "Published" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Published"]
                        }
                    }
                ]
            },    
            "ISBN_10" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["ISBN_10"]
                        }
                    }
                ]
            },            
            "ISBN_13" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["ISBN_13"]
                        }
                    }
                ]
            },
            "Pages" : {
                "number": availableFields["Pages"]
            },
            "Title": {
                "title" : [
                    {
                        "text" : {
                            "content": title
                        }
                    }
                ]
            }
        }    
    }
    for item in deletedProperty:
        del payload["properties"][item]     
    logging.info(f"Adding New book details to Bookshelf for user: {userID}")         
    r = await session.request("PATCH", url, json=payload, ssl=False, headers={
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
    })
    if r.status == 401:
        logging.warning(f"Access has been revoked for {userID}")
    elif r.status != 200:
        logging.error(f"Could not update database with new book details for {userID}, Title: {availableFields['Title']}, ISBN_13; {availableFields['ISBN_13']}, only updating title/ISBN")
        failed.cannotRetrieve(bookIdent, token)
    else:        
        logging.info("Successfully updated")


async def run_program(item, session):
    response = await requiredPageDetails(item, session)
    allFields = getAllFields(response)
    bookIdentifiers = getNewTitlesOrISBN(response)
    missingFields = compareLists(allFields)
    databaseUpdate = await updateDatabase(availableFields, bookIdentifiers, missingFields, session, item)
    return

async def main():
    print ('--------------------------------------------------------------------')
    print(datetime.datetime.now())
    async with ClientSession(trust_env=True) as session:
        await asyncio.gather(*[run_program(item, session) for item in listValidated])
    print(datetime.datetime.now())    
    print ('--------------------------------------------------------------------')

asyncio.run(main())    