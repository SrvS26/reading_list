import logging

def validated_users(records) -> list:
    """
    Takes records retrieved from the USERS table of the database and returns a list of dictionaries with user ID, access token and Bookshelf database ID of all new users.
    :param records: records from a database SELECT query
    :returns: a list of dictionaries. Each dict has one new users user ID, access token and Bookshelf database ID
    """
    users_list = []
    for record in records:
        user_details = {"user_id": record[2], "access_token": record[0], "database_id": record[1], "is_revoked": False}
        users_list.append(user_details)
    logging.info(f"Extracted user id, access token and database id from {len(records)} number of records fetched from USERS table")
    return users_list

