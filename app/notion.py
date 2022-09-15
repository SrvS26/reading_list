import logging
import requests
import string
import failed
ourList = ["Title", "Publisher", "Authors", "Summary", "Category", "Published", "ISBN_10", "Pages", "ISBN_13", "Summary_extd"]

def requiredPageDetails(databaseID, user_id, token):
    url = f"https://api.notion.com/v1/databases/{databaseID}/query"
    payload = "{\"filter\": {\"or\": [{\"property\": \"Title\",\"rich_text\": {\"ends_with\": \";\"}},{\"property\": \"ISBN_10\",\"rich_text\": {\"ends_with\": \";\"}},{\"property\": \"ISBN_13\",\"rich_text\": {\"ends_with\": \";\"}}]}}"
    headers = {
        'Content-Type': "application/json",
        'Notion-Version': "2022-02-22",
        'Authorization': f"Bearer {token}"
        }
    logging.info("Applying filters and fetching new additions to BookShelf")    
    try:
        response = requests.request("POST", url, data=payload, headers=headers)
        if response.status_code == 401:
            logging.warning(f"User {user_id} has revoked access")
            return 401
        elif response.status_code == 404:
            logging.warning(f"User {user_id} has deleted Bookshelf")
            return 404
        elif response.status_code == 200:
            logging.info(f"Fetched new additions to BookShelf for user: {user_id}")
            parsed_response = response.json()
            results = parsed_response["results"]  
            return results
        else:
            logging.error(f"Failed due to status code: {response.status_code}, response: {response.json()} for user: {user_id}")     
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


def updateDatabase(availableFields, dicOfTitlesOrISBN, pageCoverURL, deletedProperty, userID, token):
    pageID = dicOfTitlesOrISBN["pageID"]
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
    r = requests.patch(url, json=payload, headers={
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
    })
    if r.status_code == 401:
        logging.warning(f"Access has been revoked for {userID}")
    elif r.status_code != 200:
        logging.error(f"Could not update database with new book details for {userID}, Title: {availableFields['Title']}, ISBN_13; {availableFields['ISBN_13']}, only updating title/ISBN: {r.json()}")
        failed.cannotRetrieve(dicOfTitlesOrISBN, token)
    else:        
        logging.info("Successfully updated")