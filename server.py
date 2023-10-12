import requests
import time
import api.notion as notion
from flask import Flask, flash, jsonify, send_from_directory
from flask import request
from flask import render_template
from flask import redirect, url_for
import sqlite3
import datetime
from decouple import config
from werkzeug.utils import secure_filename
import logging
import os
from images import build_book_cover
from uuid import uuid4
from wand.image import Image
import custom_logger
from markupsafe import Markup
import random


logging = custom_logger.get_logger()

errors = {
    100: "There appears to be an error. Please try again later.",
    101: "Could not find the Bookshelf database.<br> Please ensure Autofill Bookshelf was given access to the Bookshelf database.",
    102: "To use Autofill Bookshelf, please allow access.",
    103: "User not found",
    104: "You have not granted access to Autofill Bookshelf",
    105: "Incorrect License Key",
    106: "Could not verify purchase",
    107: "Your License Key does not exist",
    108: "Your License Key is already in use"
}

database_file = config("DATABASE_FILE_PATH")
client_id = config("NOTION_CLIENT_ID")
client_secret = config("NOTION_CLIENT_SECRET")
notion_url = config("NOTION_URL")
allowed_extensions = {'jpg', 'jpeg', 'png'}
notion_covers_unprocessed = config("BOOK_COVERS")
notion_covers_processed = config("PROCESSED_BOOK_COVERS")
secret_key = config("SECRET_KEY")

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
Flask.secret_key = secret_key


def default_headers(token: str):
    return  {
                "Notion-Version": "2022-02-22",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

def add_to_database(user_workspace_details):
    """To insert into database table USERS all the workspace details of a user"""
    conn = sqlite3.connect(database_file)
    logging.debug("Connected to database file", db_file=database_file)
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
        database_id = random.randint(111, 999)
    except Exception:
        logging.exception("Exception occurred while adding to database", user_id=user_workspace_details.get("owner", {}).get("user", {}).get("id", ""))
    data = f"""INSERT INTO USERS (access_token, database_id, bot_id, workspace_name, workspace_id, owner_type, user_id, user_name, user_email, time_added) VALUES (
        '{access_token}', '{database_id}', '{bot_id}', "{workspace_name}", '{workspace_id}', '{owner_type}', '{user_id}', '{user_name}', '{user_email}', {time_added}
    ) ON CONFLICT (user_id) DO UPDATE SET access_token = '{access_token}';"""  # workspace_name has double quotes as a single quote exists in the string itself
    try:
        cursor_object.execute(data)
        logging.info("Inserted data into table", user_id=user_id)
        conn.commit()
    except Exception as e:
        logging.exception("Insert failed", user_id=user_id)
    cursor_object.close()
    return


def allowed_file(filename):
    return "." in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def process_image(filename):
    """Get a fully processed book cover image ready to be uploaded to Notion"""
    path_to_image = notion_covers_unprocessed + filename
    final_sizes = build_book_cover.calculate_size(path_to_image)
    if final_sizes["is_book_large"]:
        with Image(filename=path_to_image) as img:
            resized_image = img.resize(height=final_sizes["height"], width=final_sizes["width"])
            background_colour = build_book_cover.get_background_colour(path_to_image)
            background = build_book_cover.generate_background(background_colour) 
            shadow_on_background = build_book_cover.add_shadow(path_to_image, background, final_sizes["height"], final_sizes["width"])
            with Image(filename=shadow_on_background) as img2:
                img2.composite(img, gravity="center")
                img2.save(filename=f"{notion_covers_processed}{filename}")
    else: 
        with Image(filename=path_to_image) as img:
            image_height, image_width = img.height, img.width
            background_colour = build_book_cover.get_background_colour(path_to_image)
            background = build_book_cover.generate_background(background_colour, (image_height+20)) 
            shadow_on_background = build_book_cover.add_shadow(path_to_image, background, image_height, image_width)
            with Image(filename=shadow_on_background) as img:
                img.composite(Image(filename=path_to_image), gravity="center")
                img.save(filename=f"{notion_covers_processed}{filename}")
    logging.info("ACTION: Book cover image created")
    return filename


def add_dbID_license(dbID, license_key, user_id):
    conn = sqlite3.connect(database_file)
    logging.debug("Connected to database file", db_file=database_file)
    cursor_object = conn.cursor()
    data = f"""UPDATE USERS SET database_id = '{dbID}', license_key = '{license_key}', is_validated = 1, is_revoked = 0 WHERE user_id = '{user_id}'"""
    cursor_object.execute(data)
    conn.commit()
    return


def update_license_status(license_key):
    conn = sqlite3.connect(database_file)
    cursor_object = conn.cursor()
    data = f"""UPDATE GUMROAD SET is_used = 1 WHERE license_key = '{license_key}'"""
    cursor_object.execute(data)
    conn.commit()
    return


def verify_license(license_key):
    license = {"is_valid": None, "never_used": None}
    conn = sqlite3.connect(database_file)
    logging.debug("Connected to database file", db_file=database_file)
    cursor_object = conn.cursor()
    license_key_sql = (license_key,)
    license_exists = f"""SELECT EXISTS(SELECT * FROM GUMROAD WHERE license_key = ?)"""
    license_used = f"""SELECT is_used FROM GUMROAD WHERE license_key = ?"""
    cursor_object.execute(license_exists, license_key_sql)
    is_valid = cursor_object.fetchone()
    if is_valid[0] == 1: #simplify this if possible
        license["is_valid"] = True
        cursor_object.execute(license_used, license_key_sql)
        never_used = cursor_object.fetchone()
        if never_used[0] == 0:
            license["never_used"] = True
    return license


@app.route("/reading-list")
def get_code():
    logging.debug("Querying for code from Notion")
    code = request.args.get("code", None)
    if code is not None:
        token_url = notion_url + "oauth/token"
        params = {"grant_type": "authorization_code", "code": code}
        logging.info("Querying for access token")
        try:
            response = requests.post(
                token_url, data=params, auth=(client_id, client_secret)
            )
            if response.status_code != 200:
                logging.error("Error from Notion", status_code=response.status_code, response=response.json(), service="notion")
                return redirect(url_for("error", error=100))
            else:
                logging.info("Successfully retrieved access token using code", service="notion")
        except Exception:
            logging.error("Failed to fetch access token", service="notion")
            return redirect(url_for("error", error=100))
        user_workspace_details = response.json()
        user_id = user_workspace_details.get("owner", {}).get("user", {}).get("id", "")
        add_to_database(user_workspace_details)
        return redirect(url_for("get_license", user_id=user_id))
    else:
        error = request.args.get("error")
        if error is not None:
            logging.error("Notion redirected with an error", data=error, service="notion")
            return redirect(url_for("error", error=102))
        else:
            return redirect(url_for("error", error=100))


@app.route("/get-license/<user_id>")
def get_license(user_id):
    return render_template("license-key.html", user_id=user_id)


@app.route("/license/<user_id>", methods=["POST"])
def license(user_id):
    license_key = request.form.get("license-key")
    conn = sqlite3.connect(database_file)
    cursor_object = conn.cursor()
    data = f"""SELECT access_token, is_revoked FROM USERS WHERE user_id = '{user_id}'"""
    cursor_object.execute(data)
    records = cursor_object.fetchone()
    access_token, is_revoked = records[0], records[1]
    user_info = {"access_token": access_token, "user_id": user_id}
    license = verify_license(license_key)
    if (license["is_valid"] == True and license["never_used"] == True) or (license["is_valid"] == True and license["never_used"] == None and is_revoked == 1):
        if user_info["access_token"] != "" and user_info["user_id"] != "":
            database_id = notion.notion_search_id("database", "Bookshelf", user_info)
            if database_id is not None:
                dbId = database_id
                add_dbID_license(dbId, license_key, user_id)
                update_license_status(license_key)
            if dbId is None:
                return redirect(url_for("error", error=101))
            return redirect(url_for("success", database_id=database_id))
    if license["is_valid"] == None:
        return redirect(url_for("error", error=107))
    if license["never_used"] == None:
        return redirect(url_for('error', error=108))


def create_db_link(database_id):
    db_link = "https://www.notion.so/" + database_id.replace("-", "")
    return db_link


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/success/<database_id>")
def success(database_id):
    db_link = create_db_link(database_id)
    return render_template("success.html", db_link=db_link)


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/error/<int:error>")
def error(error):
    return render_template("error.html", error=Markup(errors[error]))


def unique_name(filename: str) -> str:
    return str(uuid4()) + filename


@app.route("/upload-file", defaults={"name": None}, methods=["GET"])
@app.route("/upload-file/<name>")
def upload_file(name):
    if request.method == "GET":
        if name is None:
            return render_template("upload_file.html")
        else:
            return redirect(url_for("download_file", name=name))
    else:
        return redirect(url_for("download-notioncover", _methods="POST"))


@app.route("/download-notioncover", methods=["POST"])
def download_notioncover():
    if request.method == "POST":
        if 'file' not in request.files:
            flash('No file part')
            return render_template("layout.html")
        file = request.files['file']
        if file.filename == '':
            flash("No selected file")
            return render_template("layout.html")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = unique_name(filename)
            file.save(os.path.join(notion_covers_unprocessed, unique_filename))
            process_image(unique_filename)
            return redirect(url_for("upload_file", name=unique_filename))
        else:
            flash("Please choose a different file format")
            return render_template("layout.html")
    else:
        flash('No file has been uploaded')
        return render_template("layout.html")


@app.route("/uploads/<name>")
def download_file(name):
    file_path = os.path.join(notion_covers_processed, name)
    return render_template("download.html", file_path = file_path, filename = name)


@app.route("/download-image/<filename>")
def download_image(filename):
    file_path = os.path.join(notion_covers_processed, filename)
    return send_from_directory(notion_covers_processed, filename, as_attachment=True)


@app.route("/gumroad", methods=["POST"])
def add_purchase():
    conn = sqlite3.connect(database_file)
    cursor_object = conn.cursor()
    form = request.form
    if form.get("test") != "true":
        list_params = [form.get("sale_id"), form.get("sale_timestamp"), form.get("order_number"), form.get("product_id"), form.get("permalink"), form.get("product_permalink"), form.get("product_name"), form.get("short_product_id"), form.get("email"), form.get("full_name"), form.get("subscription_id"), form.get("ip_country"), form.get("referrer"), form.get("price"), form.get("variants"), form.get("is_recurring_charge"), form.get("license_key"), form.get("affiliate"), form.get("affiliate_credit_amount_cents"), form.get("refunded"), form.get("discover_fee_charged"), form.get("gumroad_fee")]
        data = """INSERT INTO GUMROAD(sale_id, sale_timestamp, order_number, product_id, permalink, product_permalink, product_name, short_product_id, email, full_name, subscription_id, ip_country, referrer, price, variants, is_recurring_charge, license_key, affiliate, affiliate_credit, refunded, discover_fee_charged, gumroad_fee)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cursor_object.execute(data, list_params)
        conn.commit()
    return jsonify({"message": "Data received"}), 200
