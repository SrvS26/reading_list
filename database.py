import sqlite3
from decouple import config
import custom_logger

databaseFile = config("DATABASE_FILE_PATH")

logging, listener = custom_logger.get_logger("usersDatabase")

def connect_database(db_file: str):
    """Connection to database file
    
    :param db_file: file path to database file
    """
    conn = sqlite3.connect(db_file)
    logging.debug(f"Connected to database '{db_file}'")
    return conn


def fetch_records(conn, table_name: str, column_names: list, fetch_all: bool = True, condition_list: list = []) -> tuple:
    """Fetches data from a table in the connected database.
    
    :param table_name: name of the table in the database
    :param column_names: list of column names: ["Column Name", "Column Name"]
    :param fetch_all: default True, returns all the records that satisfy condition. Set to False if only want to return one record.
    :param condition_list: default empty list or list of dictionaries with conditions: [{"condition": ["column_name", "operator", "value"]}, {"condition": ["column_name", "operator", "value"]}]
    :returns: Record(s) from the specified table that satisfies specified condition
    """
    cursor = conn.cursor()
    if len(condition_list) > 0:
        conditions = []
        for item in condition_list:
            conditions.append(" ".join(item["condition"]))
        all_conditions =  " WHERE " + ", ".join(conditions)    
    else:
        all_conditions = ""   
    data = f"""SELECT {", ".join(column_names)} from {table_name}{all_conditions}"""
    cursor.execute(data)
    logging.info(f"Trying to fetch data for the columms: {column_names} from the table: {table_name}")
    if fetch_all is True:
        records = cursor.fetchall()
    else:
        records = [cursor.fetchone()]
    logging.info(f"""Fetched {len(records)} number of rows of records from table: {table_name}""")   
    conn.commit()
    cursor.close()
    return records


def disable_users(conn, list_revoked_users: list):
    """Takes a list of dicts with the user details of users how have revoked the integrations access to their database or deleted their database and updates respective properties in their database to avoid repeated queries to their notion workspace
    
    :param list_revoked_users: {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": True, "new_identifiers": {'identifier': 'value', 'page_id': 'page_id'}, "missing_properties": []}
    """
    if len(list_revoked_users) > 0:
        cursor = conn.cursor()
        list_database_ids = list(map(lambda x: (x["database_id"],), list_revoked_users))
        cursor.executemany(
            "UPDATE USERS SET is_revoked = 1, is_validated = 0, database_id = '-1' WHERE database_id = ?",
            list_database_ids,
        )
        logging.info(f"Updated {len(list_revoked_users)} number of is_revoked to 1 in USERS")
        conn.commit()
        cursor.close()
    else:
        logging.info("No users were deleted from USERS for revoking access")
        return



