from itertools import count
from xml.dom import NoModificationAllowedErr
import requests
import logging
from decouple import config

clientID = config("NOTION_CLIENT_ID")
clientSecret = config("NOTION_CLIENT_SECRET")
logging.basicConfig(
    filename="goodreads.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level = logging.DEBUG
)

ourList = ["Title", "ISBN_10", "ISBN_13", "Rating", "Status", "Source"]


def get_goodreads_data(token):
    databaseIDurl = " https://api.notion.com/v1/search"
    params = {
            "filter": {"value": "database", "property": "object"}
        }
    try:
        response = requests.post(
            databaseIDurl,
            headers={
                "Notion-Version": "2022-02-22",
                    "Authorization": "Bearer " + token,
                },
                data=params
            )
        if response.status_code !=200:
            logging.error(f"Could not fetch databaseID for Goodreads database: {response.status_code}")
            return
        else:    
            parsedResponse = response.json()
            return parsedResponse
    except Exception as e:
        return


def get_goodreads_id(parsedResponse):
    results = parsedResponse.get("results")
    if results is not None:
        databaseDetails = None
        for item in results:
            try:
                databaseTitle = (
                    (item.get("title", [{}])[0]).get("text", {}).get("content")
                )
            except Exception as e:
                logging.exception(f"Could not get database details: {e}, {parsedResponse}")
                databaseTitle = None
            if databaseTitle == "Goodreads":
                databaseDetails = item
                break
        if databaseDetails is None:
            logging.error(f"Goodreads database not found")
            return None
        else:
            database_id = databaseDetails.get("id")
            return database_id
    else:
        logging.error(f"No databases found")
        return None        


def get_available_fields(parsedResponse):
    allAvailableList = []
    results = parsedResponse.get("results")
    if results is not None:    
        for item in results:
            try:
                databaseTitle = (
                    (item.get("title", [{}])[0]).get("text", {}).get("content")
                )
            except Exception as e:
                logging.exception(f"Could not get database details: {e}, {parsedResponse}")
                return None
            if databaseTitle == "Bookshelf":
                databaseDetails = item                   
                requiredPropertiesGeneral = databaseDetails["properties"]    
                for item in requiredPropertiesGeneral.keys():                       
                    if item in ourList:                                             
                        allAvailableList.append(item)   
                        logging.info("All available fields to fill in BookShelf fetched")                                     
    return allAvailableList     


def missing_fields(allAvailableList):
    finalSet = set(ourList) - set(allAvailableList)
    return list(finalSet)


def get_csvfile_results(databaseID, userID, token):
    url = f"https://api.notion.com/v1/databases/{databaseID}/query"
    payload = "{\"filter\": {\"property\": \"Name\",\"rich_text\": {\"ends_with\": \";\"}}}"
    headers = {
        'Content-Type': "application/json",
        'Notion-Version': "2022-02-22",
        'Authorization': f"Bearer {token}"
        }
    logging.info("Checking for Goodreads trigger")    
    try:
        response = requests.request("POST", url, data=payload, headers=headers)
        if response.status_code == 200:
            parsed_response = response.json()
            results = parsed_response["results"]  
            logging.info(f"Successfully found trigger, {results}")
            return results
        else:
            logging.error(f"Failed due to status code: {response.status_code}, response: {response.json()} for user: {userID}")     
            return
    except Exception as e:
        logging.error(f"Failed to check for trigger for user: {userID}") 
        return                  


def get_csvfile(results):
    finalResults = results[0]
    urlDeets = finalResults.get("properties", {}).get("File",{}).get("files", [])
    page_id = finalResults.get("id", None)
    if len(urlDeets) != 0:
        url = urlDeets[0].get("file", {}).get("url", None)
        return url, page_id
    else:
        return None, None    

def updateDatabaseOld(triggerDetails, databaseID, token, finalSet):
    url = f'https://api.notion.com/v1/pages'
    title = triggerDetails["Title"]
    payload = {
	    "parent": {
				"type": "database_id",
				"database_id": f"{databaseID}"
			    },
	    "properties": {
			"Title": {
				"title": [
					{
					"text": {
						"content": triggerDetails["Title"]
						}
					}
				]
			},
			"Status": {
                "type": "select",
				"select": {
					"name": triggerDetails["status"]
				}
			},
			"Source": {
				"type": "select",
				"select": {
					"name": "Goodreads"
				}
			},
			"Rating": {
				"type": "select",
				"select": {
					"name": "⭐" * int(triggerDetails["myRating"])
				}
	        },
			"ISBN_13": {
				"type": "rich_text",
				"rich_text": [
						{
						"type": "text",
						"text": {
							"content": triggerDetails["ISBN_13"]
						},
						"plain_text": triggerDetails["ISBN_13"]
					}
				]
			},
			"ISBN_10": {
				"type": "rich_text",
				"rich_text": [
						{
						"type": "text",
						"text": {
							"content": triggerDetails["ISBN_10"]
						},
						"plain_text": triggerDetails["ISBN_10"]
    				}
				]
			}
		},
	    "children": [
		    {
			    "type": "heading_1",
			    "heading_1": {
				    "rich_text": [{
					    "type": "text",
					    "text": {
						    "content": "My Review"
					}
			}],
				"color": "default",
			}
		},
		{"type": "paragraph",
		"paragraph": {
			"rich_text": [{
				"type": "text",
				"text": {
					"content": triggerDetails["myReview"]
				}
			}],
			"color": "default"
		}
		},
		{"type": "heading_1",
			"heading_1": {
				"rich_text": [{
					"type": "text",
					"text": {
						"content": "My Notes"
					}
				}],
				"color": "default",
			}
		},
		{
            "type": "paragraph",
		    "paragraph": {
			"rich_text": [{
				"type": "text",
				"text": {
					"content": triggerDetails["myNotes"]
				}
			}],
			    "color": "default"
		}
		}
		],
			"icon": {
			"type": "external",
			"external": {
				"url": "https://www.notion.so/icons/book-closed_gray.svg"
				}
			}
        }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Authorization": f"Bearer {token}"
    }
    for item in finalSet:
        del payload["properties"][item] 
    if int(triggerDetails["myRating"]) == 0:
        del payload["properties"]["Rating"]    
    response = requests.request("POST", url, json=payload, headers=headers)
    status = response.status_code
    if status == 200:
        logging.info(f"Page created for book {title}")
    else:
        logging.error(f"Page creation failed for book {title} with status code: {status} with message: {response.json()}")
    return            

def updateDatabaseNew(triggerDetails, databaseID, token, finalSet):
    url = f'https://api.notion.com/v1/pages'
    title = triggerDetails["Title"]
    payload = {
	    "parent": {
				"type": "database_id",
				"database_id": f"{databaseID}"
			    },
	    "properties": {
			"Title": {
				"title": [
					{
					"text": {
						"content": triggerDetails["Title"]
						}
					}
				]
			},
			"Status": {
                "type": "status",
				"status": {
					"name": triggerDetails["status"]
				}
			},
			"Source": {
				"type": "select",
				"select": {
					"name": "Goodreads"
				}
			},
			"Rating": {
				"type": "select",
				"select": {
					"name": "⭐" * int(triggerDetails["myRating"])
				}
	        },
			"ISBN_13": {
				"type": "rich_text",
				"rich_text": [
						{
						"type": "text",
						"text": {
							"content": triggerDetails["ISBN_13"]
						},
						"plain_text": triggerDetails["ISBN_13"]
					}
				]
			},
			"ISBN_10": {
				"type": "rich_text",
				"rich_text": [
						{
						"type": "text",
						"text": {
							"content": triggerDetails["ISBN_10"]
						},
						"plain_text": triggerDetails["ISBN_10"]
    				}
				]
			}
		},
	    "children": [
		    {
			    "type": "heading_1",
			    "heading_1": {
				    "rich_text": [{
					    "type": "text",
					    "text": {
						    "content": "My Review"
					}
			}],
				"color": "default",
			}
		},
		{"type": "paragraph",
		"paragraph": {
			"rich_text": [{
				"type": "text",
				"text": {
					"content": triggerDetails["myReview"]
				}
			}],
			"color": "default"
		}
		},
		{"type": "heading_1",
			"heading_1": {
				"rich_text": [{
					"type": "text",
					"text": {
						"content": "My Notes"
					}
				}],
				"color": "default",
			}
		},
		{
            "type": "paragraph",
		    "paragraph": {
			"rich_text": [{
				"type": "text",
				"text": {
					"content": triggerDetails["myNotes"]
				}
			}],
			    "color": "default"
		}
		}
		],
			"icon": {
			"type": "external",
			"external": {
				"url": "https://www.notion.so/icons/book-closed_gray.svg"
				}
			}
        }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Authorization": f"Bearer {token}"
    }
    for item in finalSet:
        del payload["properties"][item] 
    if int(triggerDetails["myRating"]) == 0:
        del payload["properties"]["Rating"]    
    response = requests.request("POST", url, json=payload, headers=headers)
    status = response.status_code
    if status == 200:
        logging.info(f"Page created for book {title}")
    else:
        logging.error(f"Page creation failed for book {title} with status code: {status} with message: {response.json()}")
    return     



def status(user_id, access_token, page_id, num_books, count):
    num = num_books - count
    url = f"https://api.notion.com/v1/pages/{page_id}"
    message = f"Number of books fetched: {num_books}\nNumber of books autofilled: {num}"
    payload = {
        "properties": {
            "Status": {"rich_text": [{"text": {"content": message}}]}
        }
    }
    try:
        r = requests.patch(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Notion-Version": "2022-02-22",
                "Content-Type": "application/json",
            },
        )
        statusCode = r.status_code
        if statusCode != 200:
            logging.error(
                f"Could not patch message to Notion database:{statusCode} for user: {user_id}"
            )
            return
    except Exception as e:
        logging.exception(
            f"Could not patch message to Notion database:{e} for user: {user_id}"
        )
        return	