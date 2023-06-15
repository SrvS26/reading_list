import logging
import copy

notion_props_list = [
    "Title",
    "Publisher",
    "Authors",
    "Summary",
    "Category",
    "Published",
    "ISBN_10",
    "Pages",
    "ISBN_13",
    "Summary_extd",
    "Other Identifier",
]

def validated_users(records: list) -> list:
    """Takes records retrieved from the USERS table of the database and returns a list of dictionaries with user ID, access token and Bookshelf database ID of all new users.
    
    :param records: records from a select query of the USERS database [()]
    :returns: a list of dictionaries, each with one new user's access token, user ID and Bookshelf database ID. There is also an additional key "is_revoked" with value False: [{"access_token": "access_token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False}]
    """
    validated_users_details = []
    for user in records:
        user_details = {"access_token": user[0], "user_id": user[1], "database_id": user[2], "is_revoked": False}
        validated_users_details.append(user_details)
    logging.info(f"Extracted user id, access token and database id from {len(records)} number of records fetched from USERS table")
    return validated_users_details


def get_identifiers(notion_data: list, user_id:str) -> list:
    """Takes the results from the data obtained from the Notion database Bookshelf and returns new titles/ISBNs added by the user.
    
    :param notion_data: response to a notion database query
    :returns: [{"type": "type", "value: "value", "page_id": "page_id"}]
    """
    new_identifiers_list = []
    if len(notion_data) > 0:
        for item in notion_data:
            identifier = {}
            title_ = item["properties"]["Title"]["title"]
            isbn_10_ = item["properties"]["ISBN_10"]["rich_text"]
            isbn_13_ = item["properties"]["ISBN_13"]["rich_text"]
            if len(title_) > 0:
                for i in title_:
                    title = i["text"]["content"]
            else:
                title = ""
            if len(isbn_10_) > 0:
                for i in isbn_10_:
                    isbn_10 = i["text"]["content"]
            else:
                isbn_10 = ""
            if len(isbn_13_) > 0:
                for i in isbn_13_:
                    isbn_13 = i["text"]["content"]
            else:
                isbn_13 = ""
            if title != "" and title[-1] == ";": 
                identifier["value"] = title[:-1]
                identifier["type"] = "title"
            elif isbn_10 != "" and isbn_10[-1] == ";":
                identifier["value"] = isbn_10[:-1]
                identifier["type"] = "isbn_10"
            elif isbn_13 != "" and isbn_13[-1] == ";":
                identifier["value"] = isbn_13[:-1]
                identifier["type"] = "isbn_13"
            if len(identifier) != 0:
                page_id = item["id"]
                identifier["page_id"] = page_id
                new_identifiers_list.append(identifier)
        logging.info(f"New titles/ISBN extracted from new additions to BookShelf database for user: {user_id}")
    else:
        logging.info(f"No changes in BookShelf/No new titles/ISBN found for user: {user_id}")
    return new_identifiers_list


def missing_props(user_props: list) -> list:
    """To return a list of properties the user may have deleted"""
    missing_props = set(notion_props_list) - set(user_props)
    return list(missing_props)


def flatten_user_books(user_info_with_notion: dict):
    """Takes a dict with one user's details with notion data and new identifiers and splits it into a list of duplicated dictionaries, each with the 'new_identifiers' key having a single discrete identifier dict as value.
    
    :param user_info_with_notion: {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False, "new_identifiers": [{'type': 'type', 'value': 'value', 'page_id': 'page_id'}, {'type':'type', 'value': 'value', 'page_id': 'page_id'}, {'type': 'type, 'value': 'value', 'page_id': 'page_id'}], "missing_properties": []}
    :returns: [
    {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False, "new_identifiers": {'type': 'type', 'value': 'value', 'page_id': 'page_id'}, "missing_properties": []}
    {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False, "new_identifiers": {'type': 'type', 'value': 'value', 'page_id': 'page_id'}, "missing_properties": []}
    {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False, "new_identifiers": {'type': 'type', 'value': 'value', 'page_id': 'page_id'}, "missing_properties": []}
    ]
    """
    user_info_list = []
    if user_info_with_notion.get("new_identifiers") is not None:
        for new_book in user_info_with_notion["new_identifiers"]:
            flat_dict = copy.deepcopy(user_info_with_notion)
            flat_dict["new_identifiers"] = new_book
            user_info_list.append(flat_dict)
    return user_info_list
