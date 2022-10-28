# Get data from the Users table, check is version is available, add to the goodreads table
import sqlite3
from colorama import Cursor
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

def get_all_users(conn):
    cursor = conn.cursor()
    data = """SELECT USERS.user_id FROM USERS INNER JOIN VERSIONS ON USERS.user_id = VERSIONS.user_id WHERE versions.version = 'V1' or versions.version = 'V2'"""
    cursor.execute(data)
    records = cursor.fetchall()
    conn.commit()
    cursor.close()
    return records

def insert_into_goodreads(conn, records):
    cursor = conn.cursor()
    data = """INSERT INTO GOODREADS (user_id) VALUES (?)"""
    cursor.executemany(data, records)
    conn.commit()
    cursor.close()
    return

records = get_all_users(conn)
insert_into_goodreads(conn, records)
