import requests
from flask import Flask
from flask import request
from flask import render_template
from requests.auth import HTTPBasicAuth
import sqlite3
import datetime
from datetime import timezone
from decouple import config
import logging

logging.basicConfig(filename='server.log', format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
# logging.basicConfig(filename='server.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

# https://api.notion.com/v1/oauth/authorize?owner=user&client_id=1be7d857-a236-479b-904c-0162aea0b134&response_type=code

databaseFile = config("DATABASE_FILE_PATH")

app = Flask(__name__)



def addToDatabase (dictionary, databaseID):
    conn = sqlite3.connect(databaseFile)
    logging.debug(f"Connected to database file '{databaseFile}'")
    cursor_object = conn.cursor()
    try:
        access_token = dictionary.get("access_token")
        bot_id = dictionary.get("bot_id")
        workspace_name = dictionary.get("workspace_name")
        workspace_id = dictionary.get("workspace_id")
        owner_type = dictionary.get("owner").get("type")
        user_id = dictionary.get("owner").get("user").get("id")
        user_name = dictionary.get("owner").get("user").get("name")
        time_added = datetime.datetime.now(datetime.timezone.utc).timestamp()
    except Exception as e:
        logging.exception(f"Exception occurred: {e}")   
    data = f"""INSERT INTO USERS (access_token, database_id, bot_id, workspace_name, workspace_id, owner_type, user_id, user_name, time_added) VALUES (
        '{access_token}', '{databaseID}', '{bot_id}', "{workspace_name}", '{workspace_id}', '{owner_type}', '{user_id}', '{user_name}', {time_added}
    );"""    #workspace_name has double quotes as a single quote exists in the string itself
    try:
        cursor_object.execute(data)  
        logging.info(f"Inserted data into table for user {user_id}")
        conn.commit()   
    except Exception as e:
        logging.exception(f"Insert failed for {user_id}: {e}")    
    cursor_object.close() 
    return

def getDatabaseID(dictionary):
    results = dictionary.get("results")
    if results is not None:
        databaseDetails = None
        for item in results:
            try:
                databaseTitle = (item.get("title",[{}])[0]).get("text",{}).get("content")
            except Exception as e:
                logging.exception(f"Could not get database details: {e}, {dictionary}")
                databaseTitle = None
            if databaseTitle == "Book Shelf":
                databaseDetails = item
                break
        if databaseDetails is None:
            logging.error(f"Book Shelf not found")
            return None        
        else:    
            database_id = databaseDetails.get("id")
            return database_id
    else:
        logging.error(f"No databases found")
        return None        

@app.route("/")
def getCode():
    clientID = config("NOTION_CLIENT_ID")
    clientSecret = config("NOTION_CLIENT_SECRET")
    logging.info("Querying for code")
    code = request.args.get("code", None)
    if code is not None:
        logging.info("Successfully retrieved code")
        tokenUrl = "https://api.notion.com/v1/oauth/token"
        params = {"grant_type": "authorization_code", "code": code}
        logging.info("Querying for access token")
        try:
            userDetails = requests.post(tokenUrl, 
            data=params, auth = (clientID, clientSecret))
            if userDetails.status_code != 200:
                logging.error(f"{userDetails.status_code}: {userDetails.json()}")
                return "There appears to be an error. Please try again later."
            else:
                logging.info("Successfully retrieved access token using code")     
        except Exception as e:
            logging.exception(f"Failed due to: {e}")  
            return "There appears to be an error. Please try again later."  
        tokenDetails = userDetails.json()
        token = tokenDetails.get("access_token")
        databaseIDurl = " https://api.notion.com/v1/search"
        params = {"filter" : {"value" : "database","property" : "object"}, "query" : "Book Shelf"}
        logging.info("Querying for database ID")
        try:
            response = requests.post(databaseIDurl, headers= {"Notion-Version": "2022-02-22", "Authorization": "Bearer " + token},  data=params)
            if response.status_code != 200:
                logging.error(f"Notion database retrieval failed: {response.json()}")
                return "There appears to be an error. Please try again later."    
        except Exception as e:
            logging.exception(f"Notion database retrieval exception: {e}")        
        parsedResponse = response.json()
        database_id = getDatabaseID(parsedResponse)
        if database_id is None:
            return "Could not find the Book Shelf database. Please ensure the integration was given to the Book Shelf database"
        addToDatabase(tokenDetails, database_id) 
        return render_template("success.html")
    else:
        error = request.args.get("error")
        if error is not None:
            logging.error(f"Notion redirected with an error {error}")
            return "To access the Reading List integration, please allow access"
        else:
            return "There appears to be an error. Please try again later."    


@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")    
def terms():
    return render_template("terms.html")


    

