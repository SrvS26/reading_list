import requests
from flask import Flask
from flask import request
from flask import render_template
from flask import redirect, url_for
from requests.auth import HTTPBasicAuth
import sqlite3
import datetime
from datetime import timezone
from decouple import config
import logging

# logging.basicConfig(filename='server.log', format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logging.basicConfig(filename='server.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

errors = {100: "There appears to be an error. Please try again later.", 101: "Could not find the Book Shelf database. Please ensure the integration was given access to the Book Shelf database." , 102 :"To use the Autofill Book Shelf integration, please allow access." , 103 : "User not found", 104: "You have not granted access to the integration", 105: "Incorrect License Key", 106: "Could not verify purchase"}

databaseFile = config("DATABASE_FILE_PATH")
clientID = config("NOTION_CLIENT_ID")
clientSecret = config("NOTION_CLIENT_SECRET")
gumroadToken = config("GUMROAD_TOKEN")

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True



def addToDatabase (dictionary, databaseID):
    conn = sqlite3.connect(databaseFile)
    logging.debug(f"Connected to database file '{databaseFile}'")
    cursor_object = conn.cursor()
    try:
        access_token = dictionary.get("access_token", "")
        bot_id = dictionary.get("bot_id", "")
        workspace_name = dictionary.get("workspace_name", "")
        workspace_id = dictionary.get("workspace_id", "")
        owner_type = dictionary.get("owner", {}).get("type", "")
        user_id = dictionary.get("owner", {}).get("user", {}).get("id", "")
        user_name = dictionary.get("owner", {}).get("user", {}).get("name", "")
        user_email = dictionary.get("owner", {}).get("user", {}).get("person", {}).get("email", "")
        time_added = datetime.datetime.now(datetime.timezone.utc).timestamp()
    except Exception as e:
        logging.exception(f"Exception occurred: {e}")   
    data = f"""INSERT INTO USERS (access_token, database_id, bot_id, workspace_name, workspace_id, owner_type, user_id, user_name, user_email, time_added) VALUES (
        '{access_token}', '{databaseID}', '{bot_id}', "{workspace_name}", '{workspace_id}', '{owner_type}', '{user_id}', '{user_name}', '{user_email}', {time_added}
    );"""    #workspace_name has double quotes as a single quote exists in the string itself
    try:
        cursor_object.execute(data)  
        logging.info(f"Inserted data into table for user {user_id}")
        conn.commit()   
    except Exception as e:
        logging.error(f"Insert failed for {user_id}: {e}")    
    cursor_object.close() 
    return

def storeLicenseKey(licenseKey):
    conn = sqlite3.connect(databaseFile)   
    cursor_object = conn.cursor()
    data = f"""INSERT INTO LICENSE_KEYS (license_key, validated) VALUES ({licenseKey}, 0);"""
    try:
        cursor_object.execute(data)
        conn.commit()
    except Exception as e:
        logging.error(f"Failed to insert license key: {e}")
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

@app.route("/gumroad")
def displayLinks():
    sale_id = request.args.get("sale_id", None)   #Handle None  To-do
    if sale_id is None:
        return "You seem to have reached this page by mistake"
    return redirect (url_for('links', sale_id = sale_id))

@app.route("/links")
def links():
    return render_template("links.html", client_id = clientID )  

@app.route("/reading-list")
def getCode():
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
                return redirect(url_for("error", error = 100))
            else:
                logging.info("Successfully retrieved access token using code")     
        except Exception as e:
            logging.error(f"Failed due to: {e}")  
            return redirect(url_for("error", error = 100))  
        tokenDetails = userDetails.json()
        token = tokenDetails.get("access_token")
        databaseIDurl = " https://api.notion.com/v1/search"
        params = {"filter" : {"value" : "database","property" : "object"}, "query" : "Book Shelf"}
        logging.info("Querying for database ID")
        try:
            response = requests.post(databaseIDurl, headers= {"Notion-Version": "2022-02-22", "Authorization": "Bearer " + token},  data=params)
            if response.status_code != 200:
                logging.error(f"Notion database retrieval failed: {response.json()}")
                return redirect(url_for("error", error= 100))
        except Exception as e:
            logging.exception(f"Notion database retrieval exception: {e}")        
        parsedResponse = response.json()
        database_id = getDatabaseID(parsedResponse)
        if database_id is None:
            return redirect(url_for("error", error = 101))
        addToDatabase(tokenDetails, database_id) 
        user_id = tokenDetails.get("owner", {}).get("user", {}).get("id")
        # workspaceName = tokenDetails.get("workspace_name")
        return redirect(url_for("user", userId = user_id))
    else:
        error = request.args.get("error")
        if error is not None:
            logging.error(f"Notion redirected with an error {error}")
            return redirect(url_for("error", error = 102))
        else:
            return redirect(url_for("error", error = 100))    

@app.route("/user/<userId>")
def user(userId):
    userId = str(userId)
    conn = sqlite3.connect(databaseFile)
    cursor = conn.cursor()
    logging.info("connected to database")
    data = f"""SELECT workspace_name FROM USERS WHERE user_id = '{userId}'"""
    try:
        cursor.execute(data)
        workspaceTuple = cursor.fetchone()
        workspaceName = workspaceTuple[0].upper()
        if len(workspaceName) != 0:
            return render_template("license.html", userId = userId, workspaceName = workspaceName)
        else:
            return redirect(url_for("error", error = 103))
    except Exception as e:
        logging.error("Could not fetch workspace name:", e)
        return redirect(url_for("error", error = 104))

@app.route("/verify/<userId>", methods = ["POST"])
def verify(userId):
    conn = sqlite3.connect(databaseFile)   
    cursor = conn.cursor()
    try:
        licenseKeyUser = request.form.get("license_key")
    except KeyError:
        return "You have not entered a License Key"
    params = {"product_permalink": "mlkqzw", "license_key" : licenseKeyUser}
    logging.info("licenkey is: ", licenseKeyUser)
    verifyLicenseUrl = "https://api.gumroad.com/v2/licenses/verify"
    verify = requests.post(verifyLicenseUrl, headers= {"Authorization": "Bearer " + gumroadToken}, data=params)
    parsed = verify.json()
    parsed =logging.info(parsed)  
    numberUses = parsed.get("uses")
    if verify.status_code == 200:
        if numberUses <= 30:
            logging.info("License key verified with Gumroad")
            data = f"""UPDATE USERS SET license_key = '{licenseKeyUser}', is_validated = 1 WHERE user_id = '{userId}'"""
            cursor.execute(data)
            conn.commit()
            return render_template ("success.html")
        elif numberUses > 1:
            data = f"""SELECT is_revoked FROM USERS WHERE user_id = '{userId}' AND license_key = '{licenseKeyUser}'"""
            cursor.execute(data)
            is_revokedList = cursor.fetchone()
            if is_revokedList is None:
                return redirect(url_for("error", error = 105))
            else:    
                is_revoked = is_revokedList[0]
                conn.commit()  
            if is_revoked == 1:
                data = f"""UPDATE USERS SET is_validated = 1, is_revoked = 0 WHERE user_id = '{userId}'"""
                cursor.execute(data)
                conn.commit()    
                return render_template("success.html")
            else:
                return redirect(url_for("error", error = 105 ))    
    else:    
        return redirect(url_for("error", error = 106))

    
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")    
def terms():
    return render_template("terms.html")

@app.route("/error/<int:error>")
def error(error):
    return render_template("error.html", error= errors[error])
