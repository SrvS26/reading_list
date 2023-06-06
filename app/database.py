import sqlite3
from decouple import config
import custom_logger

databaseFile = config("DATABASE_FILE_PATH")

logging, listener = custom_logger.get_logger("usersDatabase")

def connect_database(db_file):
    conn = sqlite3.connect(db_file)
    logging.debug(f"Connected to database '{db_file}'")
    return conn


def fetch_records(conn, table_name: str, column_names: list, fetch_all: bool = True, condition_list = []|list) -> tuple:
    """
    Fetches data from a table in the connected database.
    :param table_name: name of the table in the database
    :param column_names: list of column names: ["Column Name", "Column Name"]
    :param all_records: default True, returns all the records that satisfy condition. Set to False if only want to return one record.
    :param condition_list: default empty string|list with dictionary with conditions: [{"condition": ["column_name", "operator", "value"]}, {"condition": ["column_name", "operator", "value"]}]
    :returns: all or one record(s) from the specified table that satisfies specified condition (if)
    """
    cursor = conn.cursor()
    if len(condition_list) > 0:
        conditions = []
        for item in condition_list:
            " ".join(item["condition"])
            conditions.append()
    else:
        condition_list = ""    
    data = f"""SELECT {column_names} from {table_name}{condition_list}"""
    cursor.execute(data)
    logging.info(f"Trying to fetch data for the columms: {column_names} from the table: {table_name}")
    if fetch_all is True:
        records = cursor.fetchall()
    else:
        records = cursor.fetchone()
    logging.info(f"""Fetched {len(records)} number of rows of records from table: {table_name}""")   
    conn.commit()
    cursor.close()
    return records


def update_table(conn, update_values:str, table_name:str,)
# Pass a value to update all.
def update_table(conn, update_values: str, table_name: str, num_iters = 0, condition = ""|None):
    cursor = conn.cursor()
    if condition != "":
        condition = " WHERE " + condition
    if num_iters == 0:
        data = f"""UPDATE {table_name} SET {update_values}{condition}"""
        cursor.execute(data)    
    else:
        cursor.executemany(f"""UPDATE {table_name} SET {update_values}{condition}""")


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


# def getRecords(conn):
#     cursor = conn.cursor()
#     fetchSpecificDeets = f"""SELECT access_token, database_id, user_id from USERS WHERE is_validated = 1"""
#     logging.info(f"Attempting to fetch data from validated users from USERS")
#     cursor.execute(fetchSpecificDeets)
#     records = cursor.fetchall()
#     numberRecords = len(records)
#     logging.info(f"Fetched {numberRecords} row/s of data from USERS")
#     conn.commit()
#     cursor.close()
#     return records



