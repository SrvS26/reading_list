import requests
import time
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

logging.basicConfig(
    filename="server.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)
# logging.basicConfig(filename='server.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

errors = {
    100: "There appears to be an error. Please try again later.",
    101: "Could not find the Bookshelf database. Please ensure Autofill Bookshelf was given access to the Bookshelf database.",
    102: "To use Autofill Bookshelf, please allow access.",
    103: "User not found",
    104: "You have not granted access to Autofill Bookshelf",
    105: "Incorrect License Key",
    106: "Could not verify purchase",
}

databaseFile = config("DATABASE_FILE_PATH")
clientID = config("NOTION_CLIENT_ID")
clientSecret = config("NOTION_CLIENT_SECRET")

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


def addToDatabase(dictionary, databaseID):
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
        user_email = (
            dictionary.get("owner", {})
            .get("user", {})
            .get("person", {})
            .get("email", "")
        )
        time_added = datetime.datetime.now(datetime.timezone.utc).timestamp()
    except Exception as e:
        logging.exception(f"Exception occurred: {e}")
    data = f"""INSERT INTO USERS (access_token, database_id, bot_id, workspace_name, workspace_id, owner_type, user_id, user_name, user_email, time_added) VALUES (
        '{access_token}', '{databaseID}', '{bot_id}', "{workspace_name}", '{workspace_id}', '{owner_type}', '{user_id}', '{user_name}', '{user_email}', {time_added}
    ) ON CONFLICT (user_id) DO UPDATE SET access_token = '{access_token}', database_id = '{databaseID}';"""  # workspace_name has double quotes as a single quote exists in the string itself
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
                databaseTitle = (
                    (item.get("title", [{}])[0]).get("text", {}).get("content")
                )
            except Exception as e:
                logging.exception(f"Could not get database details: {e}, {dictionary}")
                databaseTitle = None
            if databaseTitle == "Bookshelf":
                databaseDetails = item
                break
        if databaseDetails is None:
            logging.error(f"Bookshelf not found")
            return None
        else:
            database_id = databaseDetails.get("id")
            return database_id
    else:
        logging.error(f"No databases found")
        return None


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
            userDetails = requests.post(
                tokenUrl, data=params, auth=(clientID, clientSecret)
            )
            if userDetails.status_code != 200:
                logging.error(f"{userDetails.status_code}: {userDetails.json()}")
                return redirect(url_for("error", error=100))
            else:
                logging.info("Successfully retrieved access token using code")
        except Exception as e:
            logging.error(f"Failed due to: {e}")
            return redirect(url_for("error", error=100))
        tokenDetails = userDetails.json()
        token = tokenDetails.get("access_token")
        databaseIDurl = " https://api.notion.com/v1/search"
        params = {
            "filter": {"value": "database", "property": "object"},
            "query": "Bookshelf",
        }
        logging.info("Querying for database ID")
        time.sleep(2)
        try:
            response = requests.post(
                databaseIDurl,
                headers={
                    "Notion-Version": "2022-02-22",
                    "Authorization": "Bearer " + token,
                },
                data=params,
            )
            if response.status_code != 200:
                logging.error(f"Notion database retrieval failed: {response.json()}")
                return redirect(url_for("error", error=100))
        except Exception as e:
            logging.exception(f"Notion database retrieval exception: {e}")
        parsedResponse = response.json()
        database_id = getDatabaseID(parsedResponse)
        if database_id is None:
            dbId = "-1"
        else:
            dbId = database_id
        addToDatabase(tokenDetails, dbId)
        if dbId == "-1":
            return redirect(url_for("error", error=101))
        return redirect(url_for("success"))
    else:
        error = request.args.get("error")
        if error is not None:
            logging.error(f"Notion redirected with an error {error}")
            return redirect(url_for("error", error=102))
        else:
            return redirect(url_for("error", error=100))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/error/<int:error>")
def error(error):
    return render_template("error.html", error=errors[error])
