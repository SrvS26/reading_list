import sqlite3
from decouple import config
import logging

databaseFile = config("DATABASE_FILE_PATH")
logging.basicConfig(
    filename="goodreads.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level = logging.DEBUG
)

conn = sqlite3.connect(databaseFile)

def get_users():
    cursor = conn.cursor()
    fetchSpecificDeets = f"""SELECT USERS.access_token, USERS.database_id, GOODREADS.user_id from GOODREADS INNER JOIN USERS WHERE USERS.user_id = GOODREADS.user_id and GOODREADS.is_processed = 0"""
    logging.info(f"Attempting to fetch data from users paid for Goodreads import from GOODREADS")
    cursor.execute(fetchSpecificDeets)
    records = cursor.fetchall()
    numberRecords = len(records)
    logging.info(f"Fetched {numberRecords} row/s of data from GOODREADS")
    conn.commit()
    cursor.close()
    return records

def get_user_details(records):
    listofDeets = []
    for row in records:
        dicDeets = {}
        access_token = row[0]
        bookshelf_database_id = row[1]
        user_id = row[2]
        dicDeets["access_token"] = access_token
        dicDeets ["bookshelf_database_id"] = bookshelf_database_id
        dicDeets ["user_id"] = user_id 
        listofDeets.append(dicDeets)
    logging.info(f"Processed {len(records)} number of rows of data fetched from GOODREADS")            
    return listofDeets    

def update_goodreads_id(database_id, user_id):
    conn = sqlite3.connect(databaseFile)
    logging.debug(f"Connected to database file '{databaseFile}'")
    cursor_object = conn.cursor()
    data = f"UPDATE GOODREADS SET database_id = '{database_id}' WHERE user_id = '{user_id}'" 
    try:
        cursor_object.execute(data)
        logging.info(f"Inserted ID into table for user {user_id}")
        conn.commit()
    except Exception as e:
        logging.exception(f"Insert failed for {user_id}: {e}")
    cursor_object.close()
    return         

def update_goodreads(user_id, num_books, count):
    num_books_not_added = num_books - count
    conn = sqlite3.connect(databaseFile)
    logging.debug(f"Connected to database file '{databaseFile}'")
    cursor_object = conn.cursor()
    data = f"UPDATE GOODREADS SET num_books = '{num_books}', num_books_unfilled = '{num_books_not_added}', is_processed = 1 WHERE user_id = '{user_id}'" 
    try:
        cursor_object.execute(data)
        logging.info(f"Inserted ID into table for user {user_id}")
        conn.commit()
    except Exception as e:
        logging.exception(f"Insert failed for {user_id}: {e}")
    cursor_object.close()
    return         
