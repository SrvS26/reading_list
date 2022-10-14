import csv
from itertools import count
import requests
import logging
from decouple import config
import sqlite3
import app.image as image
import process_csv
import goodreads.goodreads
import notion.goodreads
import app.custom_logger
import scrape_goodreads


databaseFile = config("DATABASE_FILE_PATH")
clientID = config("NOTION_CLIENT_ID")
clientSecret = config("NOTION_CLIENT_SECRET")

logging.basicConfig(
    filename="goodreads.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level = logging.DEBUG
)

ourList = ["Title", "ISBN_10", "ISBN_13", "Rating", "Status", "Source", "Date Completed", "Date Added", "Date Started"]

conn = sqlite3.connect(databaseFile)

# def getPaid():
#     cursor = conn.cursor()
#     fetchSpecificDeets = f"""SELECT access_token, database_id, user_id from USERS WHERE Goodreads = 1"""
#     logging.info(f"Attempting to fetch data from users paid for Goodreads import from USERS")
#     cursor.execute(fetchSpecificDeets)
#     records = cursor.fetchall()
#     numberRecords = len(records)
#     logging.info(f"Fetched {numberRecords} row/s of data from USERS")
#     conn.commit()
#     cursor.close()
#     return records

# def getUserDeets(records):
#     listofDeets = []
#     for row in records:
#         dicDeets = {}
#         access_token = row[0]
#         database_id = row[1]
#         user_id = row[2]
#         dicDeets["access_token"] = access_token
#         dicDeets ["bookshelf_database_id"] = database_id
#         dicDeets ["user_id"] = user_id
#         listofDeets.append(dicDeets)
#     logging.info(f"Processed {len(records)} number of rows of data fetched from USERS")            
#     return listofDeets     

# def queryNotion(token):
#     databaseIDurl = " https://api.notion.com/v1/search"
#     params = {
#             "filter": {"value": "database", "property": "object"},
#             "query": "Goodreads",
#         }
#     try:
#         response = requests.post(
#             databaseIDurl,
#             headers={
#                 "Notion-Version": "2022-02-22",
#                     "Authorization": "Bearer " + token,
#                 },
#                 data=params,
#             )
#         if response.status_code !=200:
#             logging.error(f"Could not fetch databaseID for Goodreads database: {response.status_code}")
#             return
#         else:    
#             parsedResponse = response.json()
#             return parsedResponse
#     except Exception as e:
#         return

# def getAllFields(parsedResponse):
#     allAvailableList = []
#     if len(parsedResponse) > 0:                                                         
#         onePagePropertyDetails = parsedResponse[0]                     
#         requiredPropertiesGeneral = onePagePropertyDetails["properties"]    
#         for item in requiredPropertiesGeneral.keys():                       
#             if item in ourList:                                             
#                 allAvailableList.append(item)   
#         logging.info("All available fields to fill in BookShelf fetched") 
#     else:
#         logging.info("There are no new additions or the notion database 'Bookshelf' is empty")                                       
#     return allAvailableList     


# def deletedFields(allAvailableList):
#     finalSet = set(ourList) - set(allAvailableList)
#     return list(finalSet)

# def getDatabaseID(parsedResponse):
#     results = parsedResponse.get("results")
#     if results is not None:
#         databaseDetails = None
#         for item in results:
#             try:
#                 databaseTitle = (
#                     (item.get("title", [{}])[0]).get("text", {}).get("content")
#                 )
#             except Exception as e:
#                 logging.exception(f"Could not get database details: {e}, {parsedResponse}")
#                 databaseTitle = None
#             if databaseTitle == "Goodreads":
#                 databaseDetails = item
#                 break
#         if databaseDetails is None:
#             logging.error(f"Goodreads database not found")
#             return None
#         else:
#             database_id = databaseDetails.get("id")
#             return database_id
#     else:
#         logging.error(f"No databases found")
#         return None

# def updateDatabase(database_id, user_id):
#     conn = sqlite3.connect(databaseFile)
#     logging.debug(f"Connected to database file '{databaseFile}'")
#     cursor_object = conn.cursor()
#     data = f"UPDATE USERS SET Goodreads_id = {database_id} WHERE user_id = {user_id}" 
#     try:
#         cursor_object.execute(data)
#         logging.info(f"Inserted ID into table for user {user_id}")
#         conn.commit()
#     except Exception as e:
#         logging.exception(f"Insert failed for {user_id}: {e}")
#     cursor_object.close()
#     return         

# def getFileResults(databaseID, userID, token):
#     url = f"https://api.notion.com/v1/databases/{databaseID}/query"
#     payload = "{\"filter\": {\"property\": \"Name\",\"rich_text\": {\"ends_with\": \";\"}}}"
#     headers = {
#         'Content-Type': "application/json",
#         'Notion-Version': "2022-02-22",
#         'Authorization': f"Bearer {token}"
#         }
#     logging.info("Checking for Goodreads trigger")    
#     try:
#         response = requests.request("POST", url, data=payload, headers=headers)
#         if response.status_code == 200:
#             parsed_response = response.json()
#             results = parsed_response["results"]  
#             return results
#         else:
#             logging.error(f"Failed due to status code: {response.status_code}, response: {response.json()} for user: {userID}")     
#             return
#     except Exception as e:
#         logging.error(f"Failed to check for trigger for user: {userID}") 
#         return                  

# def getURL(results):
#     finalResults = results[0]
#     urlDeets = finalResults.get("properties", {}).get("files",[])
#     url = urlDeets[0].get("url", None)
#     return url


# def extractCSV(url):
#     data = requests.get(url)
#     lines = data.text.splitlines()
#     listDictCSV = list(csv.DictReader(lines))
#     return listDictCSV

# def mapDic(listDictCSV):
#     bookDetails = []
#     for item in listDictCSV:
#         myDic = {}
#         myDic["Title"] = item.get("Title", "")
#         myDic["ISBN_13"] = item.get("ISBN13", '').replace('="', '').replace('"', '')
#         myDic["ISBN_10"] = item.get("ISBN", '').replace('=""', '').replace('"', '')
#         myDic["myRating"] = item.get("My Rating", 0)
#         myDic["dateStarted"] = item.get("Date Read", '')
#         myDic["status"] = item.get("Exclusive Shelf", '')
#         myDic["myReview"] = item.get("My Review", '')
#         myDic["myNotes"] = item.get("Private Notes", '')
#         bookDetails.append(myDic)
#     return bookDetails


# def addtrigger(bookDetails):
#     triggerDetails = []
#     for item in bookDetails:
#         if item["ISBN_13"] != "":
#             item["ISBN_13"] = item["ISBN_13"] + ";"
#         elif item["ISBN_10"] != "":
#             item["ISBN_10"] = item["ISBN_10"] + ";"
#         elif item["Title"] != "":
#             item["Title"] = item["Title"] + ";"        
#         triggerDetails.append(item)
#     return triggerDetails        


# def updateDatabase(triggerDetails, databaseID, token, finalSet):
#     url = f'https://api.notion.com/v1/pages'
#     payload = {
# 	    "parent": {
# 				"type": "database_id",
# 				"database_id": f"{databaseID}"
# 			    },
# 	    "properties": {
# 			"Title": {
# 				"title": [
# 					{
# 					"text": {
# 						"content": triggerDetails["Title"]
# 						}
# 					}
# 				]
# 			},
# 			"Status": {
# 				"status": {
# 					"name": triggerDetails["status"]
# 				}
# 			},
# 			"Source": {
# 				"type": "select",
# 				"select": {
# 					"name": "Goodreads"
# 				}
# 			},
# 			"Rating": {
# 				"type": "select",
# 				"select": {
# 					"name": "⭐" * triggerDetails["myRating"]
# 				}
# 	        },
# 			"ISBN_13": {
# 				"type": "rich_text",
# 				"rich_text": [
# 						{
# 						"type": "text",
# 						"text": {
# 							"content": triggerDetails["ISBN_13"]
# 						},
# 						"plain_text": triggerDetails["ISBN_13"]
# 					}
# 				]
# 			},
# 			"ISBN_13": {
# 				"type": "rich_text",
# 				"rich_text": [
# 						{
# 						"type": "text",
# 						"text": {
# 							"content": triggerDetails["ISBN_10"]
# 						},
# 						"plain_text": triggerDetails["ISBN_10"]
#     				}
# 				]
# 			}
# 		},
# 	    "children": [
# 		    {
# 			    "type": "heading_1",
# 			    "heading_1": {
# 				    "rich_text": [{
# 					    "type": "text",
# 					    "text": {
# 						    "content": "My Review"
# 					}
# 			}],
# 				"color": "default",
# 			}
# 		},
# 		{"type": "paragraph",
# 		"paragraph": {
# 			"rich_text": [{
# 				"type": "text",
# 				"text": {
# 					"content": triggerDetails["myReview"]
# 				}
# 			}],
# 			"color": "default"
# 		}
# 		},
# 		{"type": "heading_1",
# 			"heading_1": {
# 				"rich_text": [{
# 					"type": "text",
# 					"text": {
# 						"content": "My Notes"
# 					}
# 				}],
# 				"color": "default",
# 			}
# 		},
# 		{
#             "type": "paragraph",
# 		    "paragraph": {
# 			"rich_text": [{
# 				"type": "text",
# 				"text": {
# 					"content": triggerDetails["myNotes"]
# 				}
# 			}],
# 			    "color": "default"
# 		}
# 		}
# 		],
# 			"icon": {
# 			"type": "external",
# 			"external": {
# 				"url": "https://www.notion.so/icons/book-closed_gray.svg"
# 				}
# 			}
#         }
#     headers = {
#         "Content-Type": "application/json",
#         "Accept": "application/json",
#         "Notion-Version": "2022-06-28",
#         "Authorization": f"Bearer {token}"
#     }
#     for item in finalSet:
#         del payload["properties"][item]   
#     response = requests.request("POST", url, json=payload, headers=headers)
#     return


while True:
    paid_user_details = goodreads.goodreads.get_users()
    paid_users = goodreads.goodreads.get_user_details(paid_user_details)
    for item in paid_users:
        user_id = item.get("user_id")
        bookshelf_database_id = item.get("bookshelf_database_id")
        access_token = item.get("access_token")
        goodreads_id_data = notion.goodreads.get_goodreads_data(access_token)
        available_fields = notion.goodreads.get_available_fields(goodreads_id_data)
        missing_fields = notion.goodreads.missing_fields(available_fields)
        goodreads_database_id = notion.goodreads.get_goodreads_id(goodreads_id_data)
        if goodreads_database_id is not None:
            item["goodreads_database_id"] = notion.goodreads.get_goodreads_id(goodreads_id_data)
            goodreads.goodreads.update_goodreads_id(item["goodreads_database_id"], item["user_id"])
            csv_file_results = notion.goodreads.get_csvfile_results(item["goodreads_database_id"],item["user_id"], item["access_token"])
            if csv_file_results is not None:
                csv_file, page_id = notion.goodreads.get_csvfile(csv_file_results)
                extracted_data, num_books = process_csv.extract_csv(csv_file)
                if extracted_data is not None:
                    mapped_dic = process_csv.map_csv_to_notion_fields(extracted_data)
                    count = 0                    
                    for item in mapped_dic:
                        books_not_added=[]
                        book = scrape_goodreads.add_to_dic(item)
                        # file = book["Image_url"]
                        image_link = image.upload_Image(conn, book)
                        status = notion.goodreads.updateDatabaseNew(book, bookshelf_database_id, access_token, missing_fields, image_link)
                        if status == 200:
                            count+=1
                        else:
                            books_not_added.append(status)         
                    notion.goodreads.status(user_id, access_token, page_id, num_books, count, books_not_added)
                    goodreads.goodreads.update_goodreads(user_id, num_books, count)


        
        