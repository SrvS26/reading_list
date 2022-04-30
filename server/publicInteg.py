import requests
from flask import Flask
from flask import request
from flask import render_template
from requests.auth import HTTPBasicAuth
import sqlite3
from sqlite3 import Error
import datetime
from datetime import timezone

# https://api.notion.com/v1/oauth/authorize?owner=user&client_id=1be7d857-a236-479b-904c-0162aea0b134&response_type=code


def connect(db_filemain):
    conn = None
    try:
        conn = sqlite3.connect(db_filemain)
    except Error as e:
        print (e)
    # finally:
    #     if conn:
    #         conn.close()
    return conn      

# connect("/Users/sravanthis/Documents/ReadingList/database/sqlite/db_filemain")   

# def DropTable(db_filemain):
#     conn = sqlite3.connect(db_filemain)
#     cursor_object = conn.cursor()
#     table = """DROP TABLE USERS"""
#     try:
#         cursor_object.execute(table)
#         conn.commit()
#         print ("table USERS dropped")
#     except:
#         print ("Could not drop")    
#     cursor_object.close()
#     conn.close()

# DropTable("/Users/sravanthis/Documents/ReadingList/database/sqlite/db_filemain")

def dataBase():
    conn = connect("/Users/sravanthis/Documents/ReadingList/database/sqlite/db_filemain")
    cursor_object = conn.cursor()
    table = """CREATE TABLE IF NOT EXISTS USERS (
            access_token VARCHAR(255) NOT NULL,
            database_id VARCHAR(255) NOT NULL,
            bot_id VARCHAR(255) NOT NULL,
            workspace_name VARCHAR(255) NOT NULL,
            workspace_id VARCHAR(255) NOT NULL,
            owner_type VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            user_name VARCHAR(255) NOT NULL,
            time_added FLOAT NOT NULL
            )"""
    try:        
        cursor_object.execute(table)
        conn.commit()
        print ("Table USERS created")
    except:
        print ("Could not create table USERS")
    cursor_object.close()
    conn.close()
    return

dataBase()

def addToDatabase (db_filemain, dictionary, databaseID):
    conn = sqlite3.connect(db_filemain) 
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
    );"""
    # try:
    cursor_object.execute(data)  
    conn.commit() 
    print ("Data inserted")
    # except:
    #     print ("Data could not be inserted")    
    cursor_object.close() 
    conn.close()    
    return

def getDatabaseID(dictionary):
    results = dictionary.get("results")
    databaseDetails = results[0]
    database_id = databaseDetails.get("id")
    return database_id

# def putData(db_filemain):
#     conn = sqlite3.connect(db_filemain) 
#     cursor_object = conn.cursor()    
#     data = """INSERT INTO USERS VALUES ("secret_WIAmzqw24tMdTy87rMiqzXEVUFkZ7XPYheZPAAYAqsu", 
#     "alpha", "c0060ceb-0a3f-45ed-87e1-4365ca944e22", 
#     "Sravanthi's Notion",
#     "93bfee1c-9487-4dc2-af8d-97c0055d66f6",
#     "user",
#     "bf0d816a-d155-4be4-bc24-3b7920af878d", 
#     "Sravanthi Sunkaraneni", 
#     1234.567485);"""
#     # try:  
#     cursor_object.execute(data)
#     conn.commit()
#     print ("Data inserted to Users")
#     # except:
#     #     print ("Data could not be inserted")    
#     return

# putData("/Users/sravanthis/Documents/ReadingList/database/sqlite/db_filemain")

# def response(db_filemain):
#     conn = sqlite3.connect(db_filemain) 
#     cursor_object = conn.cursor() 
#     response = """SELECT * FROM USERS"""
#     cursor_object.execute(response)
#     conn.commit()
#     c = cursor_object.fetchall()
#     return c

# r = response("/Users/sravanthis/Documents/ReadingList/database/sqlite/db_filemain") 
# print (r)


app = Flask(__name__)

@app.route("/")
def getCode():
    clientID = "1be7d857-a236-479b-904c-0162aea0b134"
    clientSecret = "secret_kJSpfcsOtrk0s2eKHVwiyiaX0RoAN75gx4CE77HyI4N"
    code = request.args.get("code", " ")
    tokenUrl = "https://api.notion.com/v1/oauth/token"
    params = {"grant_type": "authorization_code", "code": code}
    print (code)
    userDetails = requests.post(tokenUrl, 
    data=params, auth = (clientID, clientSecret))
    tokenDetails = userDetails.json()
    print (tokenDetails)
    token = tokenDetails.get("access_token")
    print (token)
    databaseIDurl = " https://api.notion.com/v1/search"
    params = {"filter" : {"value" : "database","property" : "object"}, "query" : "Book Shelf"}
    response = requests.post(databaseIDurl, headers= {"Notion-Version": "2022-02-22", "Authorization": "Bearer " + token},  data=params)
    parsedResponse = response.json()
    database_id = getDatabaseID(parsedResponse)
    print("Database ID received")
    addToDatabase("/Users/sravanthis/Documents/ReadingList/database/sqlite/db_filemain", tokenDetails, database_id) 
    print ("Details added to table USERS")
    return "You have access to the integration!"

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")    
def terms():
    return render_template("terms.html")


    

