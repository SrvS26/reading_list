from distutils.debug import DEBUG
import requests
import time
import api.notion as notion
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
import json

# file_path = config("STATIC_FILE_PATH")

logging.basicConfig(
    filename="server.log",
    level= logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

errors = {
    100: "There appears to be an error. Please try again later.",
    101: "Could not find the Bookshelf database.\nPlease ensure Autofill Bookshelf was given access to the Bookshelf database.",
    102: "To use Autofill Bookshelf, please allow access.",
    103: "User not found",
    104: "You have not granted access to Autofill Bookshelf",
    105: "Incorrect License Key",
    106: "Could not verify purchase",
}

database_file = config("DATABASE_FILE_PATH")
client_id = config("NOTION_CLIENT_ID")
client_secret = config("NOTION_CLIENT_SECRET")
notion_url = config("NOTION_URL")

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


def default_headers(token: str):
    return  {
                "Notion-Version": "2022-02-22",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

def add_to_database(user_workspace_details, database_id: str):
    """To insert into database table USERS all the workspace details of a user"""
    conn = sqlite3.connect(database_file)
    logging.debug(f"Connected to database file '{database_file}'")
    cursor_object = conn.cursor()
    try:
        access_token = user_workspace_details.get("access_token", "")
        bot_id = user_workspace_details.get("bot_id", "")
        workspace_name = user_workspace_details.get("workspace_name", "")
        workspace_id = user_workspace_details.get("workspace_id", "")
        owner_type = user_workspace_details.get("owner", {}).get("type", "")
        user_id = user_workspace_details.get("owner", {}).get("user", {}).get("id", "")
        user_name = user_workspace_details.get("owner", {}).get("user", {}).get("name", "")
        user_email = (
            user_workspace_details.get("owner", {})
            .get("user", {})
            .get("person", {})
            .get("email", "")
        )
        time_added = datetime.datetime.now(datetime.timezone.utc).timestamp()
    except Exception as e:
        logging.exception(f"Exception occurred: {e}")
    data = f"""INSERT INTO USERS (access_token, database_id, bot_id, workspace_name, workspace_id, owner_type, user_id, user_name, user_email, time_added) VALUES (
        '{access_token}', '{database_id}', '{bot_id}', "{workspace_name}", '{workspace_id}', '{owner_type}', '{user_id}', '{user_name}', '{user_email}', {time_added}
    ) ON CONFLICT (user_id) DO UPDATE SET access_token = '{access_token}', database_id = '{database_id}';"""  # workspace_name has double quotes as a single quote exists in the string itself
    try:
        cursor_object.execute(data)
        logging.info(f"Inserted data into table for user {user_id}")
        conn.commit()
    except Exception as e:
        logging.exception(f"Insert failed for {user_id}: {e}")
    cursor_object.close()
    return


@app.route("/reading-list")
def get_code():
    logging.info("Querying for code")
    code = request.args.get("code", None)
    if code is not None:
        logging.info("Successfully retrieved code")
        token_url = notion_url + "oauth/token"
        params = {"grant_type": "authorization_code", "code": code}
        logging.info("Querying for access token")
        try:
            response = requests.post(
                token_url, data=params, auth=(client_id, client_secret)
            )
            if response.status_code != 200:
                logging.error(f"{response.status_code}: {response.json()}")
                return redirect(url_for("error", error=100))
            else:
                logging.info("Successfully retrieved access token using code")
        except Exception as e:
            logging.error(f"Failed due to: {e}")
            return redirect(url_for("error", error=100))
        user_workspace_details = response.json()
        access_token = user_workspace_details.get("access_token", "")
        time.sleep(10)
        params = {
            "filter": {"value": "database", "property": "object"},
            "query": "Bookshelf",
        }
        logging.info("Querying for database ID")
        user_info = {"access_token": access_token, "user_id": user_workspace_details.get("owner", {}).get("user", {}).get("id", "")}
        if user_info["access_token"] != "" and user_info["user_id"] != "":
            database_id = notion.notion_search_id("database", "Bookshelf", user_info)
            if database_id is None:
                dbId = "-1"
            else:
                dbId = database_id
            add_to_database(user_workspace_details, dbId)
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
