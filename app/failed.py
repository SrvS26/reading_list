import requests
import logging
logging.basicConfig(filename='app.log', format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

def cannotRetrieve(dicOfTitlesOrISBN, token):
    url = f'https://api.notion.com/v1/pages/{dicOfTitlesOrISBN["pageID"]}'
    if dicOfTitlesOrISBN["Type"] == "Title":
        payload = {
        "properties" : {
            "Title": {
                "title" : [
                    {
                    "text" : {
                        "content": dicOfTitlesOrISBN["Value"]
                            }
                        }
                    ]
                }
            }
        }
    elif dicOfTitlesOrISBN["Type"] == "ISBN_10":
        payload = {
        "properties" : {
            "ISBN_10" : {
                "rich_text" : [
                    {
                        "text" : {
                        "content" : dicOfTitlesOrISBN["Value"]
                            }
                        }
                    ]
                }
            }
        }    
    elif dicOfTitlesOrISBN["Type"] == "ISBN_13":
        payload = {
        "properties" : {
            "ISBN_13" : {
                "rich_text" : [
                    {
                        "text" : {
                        "content" : dicOfTitlesOrISBN["Value"]
                            }
                        }
                    ]
                }
           }    
        }        
    r = requests.patch(url, json=payload, headers={
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
    })
    if r.status_code == 401:
        logging.warning("Access has been revoked")
    elif r.status_code == 200:
        logging.info("Succesfully removed ';'")