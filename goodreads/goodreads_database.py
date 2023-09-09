import sqlite3
from decouple import config
import logging

databaseFile = config("DATABASE_FILE_PATH")
logging.basicConfig(
    filename="goodreads_database.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level = logging.DEBUG
)

conn = sqlite3.connect(databaseFile)

def get_users():
    cursor = conn.cursor()
    fetchSpecificDeets = f"""SELECT USERS.access_token, USERS.database_id, GOODREADS.user_id, VERSIONS.version FROM USERS INNER JOIN GOODREADS ON GOODREADS.user_id = USERS.user_id INNER JOIN VERSIONS ON VERSIONS.user_id = GOODREADS.user_id WHERE GOODREADS.is_processed = 0"""
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
        version = row[3]    
        dicDeets["access_token"] = access_token
        dicDeets ["bookshelf_database_id"] = bookshelf_database_id
        dicDeets ["user_id"] = user_id 
        dicDeets["version"] = version
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
        logging.exception(f"Insert failed {e} for user: {user_id}")
    cursor_object.close()
    return         

def update_goodreads(user_id, num_books, count):
    num_books_not_added = num_books - count
    books = (num_books, num_books_not_added, 1, user_id)
    conn = sqlite3.connect(databaseFile)
    logging.debug(f"Connected to database file '{databaseFile}'")
    cursor_object = conn.cursor()
    data = f"UPDATE GOODREADS SET num_books = ?, num_books_unfilled = ?, is_processed = ? WHERE user_id = ?" 
    try:
        cursor_object.execute(data, books)
        logging.info(f"Inserted ID into table for user {user_id}")
        conn.commit()
    except Exception as e:
        logging.exception(f"Insert failed {e} for user: {user_id}")
    cursor_object.close()
    return         


def update_goodreads_books(book, image_link):
    conn = conn = sqlite3.connect(databaseFile)
    logging.debug(f"Connected to database file '{databaseFile}'")
    cursor_object = conn.cursor()
    author = ", ".join(list(map(lambda x: x["name"], book["Author"])))
    goodreads_id = book["goodreadsID"]
    if book.get("Summary Extd") is not None:
        summary = book["Summary"] + book["Summary Extd"]
    else:
        summary = book["Summary"]         
    isbn_10 = book["ISBN_10"]
    isbn_13 = book["ISBN_13"]
    title = book["Title"]
    published = book["Published"]
    publisher = book["Publisher"]
    image_url = book["Image_url"]
    genre = ", ".join(list(map(lambda x: x["name"], book["Categories"])))
    data = f"""INSERT INTO GOODREADS_BOOKS 
    (goodreads_id, ISBN_10, ISBN_13, title, author, summary, goodreads_image_link, genre, pages, published_date, published_by, image_link) 
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"""
    # ("{goodreads_id}", "{isbn_10}", "{isbn_13}", "{title}", "{author}", `{summary}`, "{image_url}", "{genre}", '{book["Pages"]}', "{published}", "{publisher}", "{image_link}")"""
    try:
        cursor_object.execute(data, (goodreads_id, isbn_10, isbn_13, title, author, summary, image_url, genre, book["Pages"], published, publisher, image_link))
        logging.info(f"Inserted book: {book['Title']} in table")
        conn.commit()
    except Exception as e:
        logging.exception(f"Insert failed for book: {book['Title']}")
    cursor_object.close()
    return        

