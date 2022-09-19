import sqlite3
from decouple import config
import custom_logger

databaseFile = config("DATABASE_FILE_PATH")

logging = custom_logger.get_logger("usersDatabase")


def connectDatabase(db_file):
    conn = sqlite3.connect(db_file)
    logging.debug(f"Connected to database '{db_file}'")
    return conn


def getRecords(conn):
    cursor = conn.cursor()
    fetchSpecificDeets = f"""SELECT access_token, database_id, user_id from USERS WHERE is_validated = 1"""
    logging.info(f"Attempting to fetch data from validated users from USERS")
    cursor.execute(fetchSpecificDeets)
    records = cursor.fetchall()
    numberRecords = len(records)
    logging.info(f"Fetched {numberRecords} row/s of data from USERS")
    conn.commit()
    cursor.close()
    return records


def getValidatedTokens(records):
    listofTokens = []
    for row in records:
        dicTokens = {}
        access_token = row[0]
        database_id = row[1]
        user_id = row[2]
        dicTokens["access_token"] = access_token
        dicTokens["database_id"] = database_id
        dicTokens["user_id"] = user_id
        dicTokens["is_revoked"] = False
        listofTokens.append(dicTokens)
    logging.info(f"Processed {len(records)} number of rows of data fetched from USERS")
    return listofTokens


def removeFromUsers(revokedUsers, conn):
    if len(revokedUsers) > 0:
        cursor = conn.cursor()
        listDatabaseIDs = list(map(lambda x: (x["database_id"],), revokedUsers))
        cursor.executemany(
            "UPDATE USERS SET is_revoked = 1, is_validated = 0, database_id = '-1' WHERE database_id = ?",
            listDatabaseIDs,
        )
        logging.info(f"Updated {len(revokedUsers)} number of is_revoked to 1 in USERS")
        conn.commit()
        cursor.close()
    else:
        logging.info("No users were deleted from USERS for revoking access")
        return
