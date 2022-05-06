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

logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

# https://api.notion.com/v1/oauth/authorize?owner=user&client_id=1be7d857-a236-479b-904c-0162aea0b134&response_type=code

databaseFile = config("databaseFilePath")


def addToDatabase (dictionary, databaseID):
    logging.debug(f"Connecting to database file '{databaseFile}")
    conn= sqlite3.connect(databaseFile)
    logging.debug(f"Connected to database file '{databaseFile}")
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
        logging.exception(f"Could not retrieve access token and other data from response to query")   
    data = f"""INSERT INTO USERS (access_token, database_id, bot_id, workspace_name, workspace_id, owner_type, user_id, user_name, time_added) VALUES (
        '{access_token}', '{databaseID}', '{bot_id}', "{workspace_name}", '{workspace_id}', '{owner_type}', '{user_id}', '{user_name}', {time_added}
    );"""    #workspace_name has double quotes as a single quote exists in the string itself
    try:
        logging.info(f"Inserted data into table for user {user_id}")
        cursor_object.execute(data)  
    except Exception as e:
        logging.exception(f"Failed to insert data into table USERS for user {user_id}")    
    conn.commit() 
    cursor_object.close() 
    return

def getDatabaseID(dictionary):
    results = dictionary.get("results")
    databaseDetails = results[0]
    database_id = databaseDetails.get("id")
    return database_id


app = Flask(__name__)

@app.route("/")
def getCode():
    clientID = config("NOTIONID")
    clientSecret = config("NOTIONSECRET")
    logging.info("Querying for code")
    code = request.args.get("code", " ")
    if code != " ":
        logging.info("Successfully retrieved code")
        tokenUrl = "https://api.notion.com/v1/oauth/token"
        params = {"grant_type": "authorization_code", "code": code}
        logging.info("Querying for access token")
        try:
            userDetails = requests.post(tokenUrl, 
            data=params, auth = (clientID, clientSecret))
            logging.info("Successfully retrieved access token using code")
        except Exception as e:
            logging.exception("Failed to retrieve access token using code")    
        tokenDetails = userDetails.json()
        token = tokenDetails.get("access_token")
        databaseIDurl = " https://api.notion.com/v1/search"
        params = {"filter" : {"value" : "database","property" : "object"}, "query" : "Book Shelf"}
        logging.info("Querying for database ID")
        try:
            response = requests.post(databaseIDurl, headers= {"Notion-Version": "2022-02-22", "Authorization": "Bearer " + token},  data=params)
            logging.info("Database ID retrieved")
        except Exception as e:
            logging.exception("Could not retrieve database ID")        
        parsedResponse = response.json()
        database_id = getDatabaseID(parsedResponse)
        addToDatabase(tokenDetails, database_id) 
        return render_template("success.html")
    else:
        if request.args.get("error") is not None:
            return "Access Denied"
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


    

