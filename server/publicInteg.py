import requests
from flask import Flask
from flask import request
from flask import render_template
from requests.auth import HTTPBasicAuth
import sqlite3
import datetime
from datetime import timezone
from decouple import config

# https://api.notion.com/v1/oauth/authorize?owner=user&client_id=1be7d857-a236-479b-904c-0162aea0b134&response_type=code

conn= sqlite3.connect("/Users/sravanthis/Documents/ReadingList/notionReadingList")

def addToDatabase (dictionary, databaseID):
    cursor_object = conn.cursor()
    access_token = dictionary.get("access_token")
    bot_id = dictionary.get("bot_id")
    workspace_name = dictionary.get("workspace_name")
    workspace_id = dictionary.get("workspace_id")
    owner_type = dictionary.get("owner").get("type")
    user_id = dictionary.get("owner").get("user").get("id")
    user_name = dictionary.get("owner").get("user").get("name")
    time_added = datetime.datetime.now(datetime.timezone.utc).timestamp()
    data = f"""INSERT INTO USERS (access_token, database_id, bot_id, workspace_name, workspace_id, owner_type, user_id, user_name, time_added) VALUES (
        '{access_token}', '{databaseID}', '{bot_id}', "{workspace_name}", '{workspace_id}', '{owner_type}', '{user_id}', '{user_name}', {time_added}
    );"""    #workspace_name has double quotes as a single quote exists in the string itself
    cursor_object.execute(data)  
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
    code = request.args.get("code", " ")
    tokenUrl = "https://api.notion.com/v1/oauth/token"
    params = {"grant_type": "authorization_code", "code": code}
    userDetails = requests.post(tokenUrl, 
    data=params, auth = (clientID, clientSecret))
    tokenDetails = userDetails.json()
    token = tokenDetails.get("access_token")
    databaseIDurl = " https://api.notion.com/v1/search"
    params = {"filter" : {"value" : "database","property" : "object"}, "query" : "Book Shelf"}
    response = requests.post(databaseIDurl, headers= {"Notion-Version": "2022-02-22", "Authorization": "Bearer " + token},  data=params)
    parsedResponse = response.json()
    database_id = getDatabaseID(parsedResponse)
    addToDatabase("/Users/sravanthis/Documents/ReadingList/notionReadingList.db", tokenDetails, database_id) 
    return render_template("success.html")

@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")    
def terms():
    return render_template("terms.html")


    

