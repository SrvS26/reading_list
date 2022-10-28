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

ourListV2 = ["Title", "ISBN_10", "ISBN_13", "Rating", "Status", "Source", "Dates", "Authors", "Summary", "Summary_extd", "Category", "Pages", "Publisher", "Source", "Date Added", "Rating"]
ourListV1 = ["Title", "ISBN_10", "ISBN_13", "Rating", "Status", "Source", "Date Completed", "Date Started", "Authors", "Summary", "Summary_extd", "Category", "Pages", "Publisher", "Source", "Date Added", "Rating"]


def get_goodreads_data(token):
	url = "https://api.notion.com/v1/search"

	payload = {"filter": {
			"value": "database",
			"property": "object"
		}}
	headers = {
		"Content-Type": "application/json",
		"Notion-Version": "2022-02-22",
		"Authorization": f"Bearer {token}"
	}
	response = requests.request("POST", url, json=payload, headers=headers)
	if response.status_code !=200:
		logging.error(f"Could not fetch databaseID for Imports database: {response.status_code}")
		return
	else:    
		parsedResponse = response.json()
		return parsedResponse

    # databaseIDurl = "https://api.notion.com/v1/search"
    # params = {
	# "filter" : {
	# 	"value" : "database",
	# 	"property" : "object"
	# 			}
	# 		}
    # try:
    #     response = requests.post(
    #         databaseIDurl,
    #         headers={
    #             "Notion-Version": "2022-06-28",
    #                 "Authorization": "Bearer " + token,
	# 				"Content-Type": "application/json"
    #             },
    #             data=params
    #         )
    #     if response.status_code !=200:
    #         logging.error(f"Could not fetch databaseID for Goodreads database: {response.status_code}")
    #         return
    #     else:    
    #         parsedResponse = response.json()
    #         return parsedResponse
    # except Exception as e:
    #     return

def get_goodreads_id(parsedResponse):
	if parsedResponse is not None:
		results = parsedResponse.get("results")
		if results is not None and len(results) != 0:
			databaseDetails = None
			for item in results:
				databaseTitle = (
						(item.get("title", [{}])[0]).get("text", {}).get("content")
					)
				if databaseTitle == "Imports":
					databaseDetails = item
					break
			if databaseDetails is None:
				logging.error(f"Imports database not found")
				return None
			else:
				database_id = databaseDetails.get("id")
				return database_id
		else:
			logging.error(f"No databases found")
			return None        


def get_available_fields(parsedResponse, version):
	if version == "V1":
		ourList = ourListV1
	else:
		ourList = ourListV2
	allAvailableList = []
	if parsedResponse is not None:
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


def missing_fields(allAvailableList, version):
	if version == "V1":
		ourList = ourListV1
	else:
		ourList = ourListV2
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
	if results is not None and len(results) != 0:
		finalResults = results[0]
		urlDeets = finalResults.get("properties", {}).get("File",{}).get("files", [])
		page_id = finalResults.get("id", None)
		if len(urlDeets) != 0:
			url = urlDeets[0].get("file", {}).get("url", None)
			return url, page_id
		else:
			return None, None    
	else:
		return None, None

def updateDatabase(triggerDetails, databaseID, token, finalSet, image_link, version):
	url = f'https://api.notion.com/v1/pages'
	title = triggerDetails["Title"]
	if version == "V1":
		type = "select"
	elif version == "V2":
		type = "status"
	else:
		logging.error("No version details available")
	payload = {
		"cover" : {
			"type": "external",
			"external" : {"url": image_link},
		},
		"parent": {
				"type": "database_id",
				"database_id": databaseID
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
			"Authors": {"multi_select": triggerDetails["Author"]},
            "Summary": {
                "rich_text": [{"text": {"content": triggerDetails["Summary"]}}]
            },
            "Summary_extd": {
                "rich_text": [{"text": {"content": triggerDetails["SummaryExtd"]}}]
            },
			"Category": {"multi_select": triggerDetails["Categories"]},
            "Published": {
                "rich_text": [{"text": {"content": triggerDetails["Published"]}}]
            },
			"Pages": {"number": triggerDetails["Pages"]},
			"Status": {
				"type": f"{type}",
				f"{type}": {
					"name": triggerDetails["status"]
				}
			},
			"Publisher": {
                "rich_text": [
                    {"text": {"content": triggerDetails["Publisher"]}}
                ]
            },
			"Source": {
				"type": "select",
				"select": {
					"name": "Goodreads"
				}
			},
			"Dates": {
				"type": "date",
				"date": {
					"start": triggerDetails["Date Started"],
					"end": triggerDetails["Date Completed"]
				}
			},
			"Date Added": {
				"type": "date",
				"date": {
					"start": triggerDetails["Date Added"]
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
	if triggerDetails["Date Added"] == "":
		del payload["properties"]["Date Added"]
	if triggerDetails["Date Completed"] == "":
		del payload["properties"]["Dates"]	  
	for item in finalSet:
		del payload["properties"][item] 
	if int(triggerDetails["myRating"]) == 0:
		del payload["properties"]["Rating"]
	try:	    
		response = requests.request("POST", url, json=payload, headers=headers)
		status = response.status_code
		if status == 200:
			logging.info(f"Page created for book {title}")
			return status
		else:
			logging.error(f"Page creation failed for book {title} with status code: {status} with message: {response.json()}")
			return title
	except Exception as e:
		logging.error(f"Update failed: {e}")
		return


def status(user_id, access_token, page_id, num_books, count, books_not_added):
	books_missed = ", ".join(books_not_added)
	url = f"https://api.notion.com/v1/pages/{page_id}"
	message = f"Number of books in file: {num_books}\nNumber of books added: {count}\nBooks not added: {books_missed}"
	payload = {
        "properties": {
			"Name": {
				"title": [
					{
					"text": {
						"content": "Goodreads"
						}
					}
				]
			},	
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
                f"Could not patch message to Notion database:{statusCode} for user: {user_id}, {r.json()}"
        	)
			return
	except Exception as e:
		logging.exception(
			f"Could not patch message to Notion database:{e} for user: {user_id}"
		)
		return	