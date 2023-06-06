import copy
import string

import custom_logger
from decouple import config

logging, listener = custom_logger.get_logger("books")

api_key = config("BOOK_API_KEY")
base_url = config("BASE_URL_BOOK")


async def get_book_details(
    session, user_info_with_identifiers_: dict, with_key = True, retries: int = 5
) -> dict:
    """
    Takes a dict with user info and book identifier and returns a dict with user information, 
    book identifier and book details.
    """
    user_info_with_identifiers = copy.deepcopy(user_info_with_identifiers_)
    user_id = user_info_with_identifiers["user_id"]
    identifier = user_info_with_identifiers["new_book_identifiers"]
    if with_key:
        query_param = f"&key={api_key}"
    else: # when rate limited
        logging.warning(
            f"Retrying fetching book details without API key for user: {user_id} for book: {identifier['value']}"
        )
        query_param = ""
    if retries > 0:
        if identifier.get("type") == "Title":
            url = base_url + "?q=" + identifier['value'] + query_param
        elif (
            identifier.get("type") == "ISBN_10"
            or identifier.get("type") == "ISBN_13"
        ):
            url = base_url + "?q=isbn:" + identifier['value'] + query_param
        web_page = await session.request(method="GET", url=url, ssl=False)
        if web_page.status == 429:
            logging.error(
                f"Rate limited, Book: {identifier['value']} for user: {user_id} with {web_page.status} with key: {with_key}"
            )
            return await get_book_details(
                session,
                copy.deepcopy(user_info_with_identifiers_),
                with_key = False,
                retries = retries - 1,
            )
        elif web_page.status != 200:
            logging.error(
                f"Failed request to fetch book details, Book: {identifier['value']} for user: {user_id} with {web_page.status}"
            )
            user_info_with_identifiers["fetched_book_details"] = None
            return user_info_with_identifiers
        else:
            logging.info(
                f"Book details fetched for book: {identifier['value']} for user: {user_id} with key: {with_key}"
            )
        parsed_content = await web_page.json()
    else:
        logging.error(
            f"Exhausted retries for book: {identifier['value']} for user: {user_id}"
        )
        parsed_content = {}
    if parsed_content.get("totalItems", 0) > 0:
        results_list = parsed_content["items"]
        categories_list = all_categories(results_list)
        book_details = results_list[0].get("volumeInfo") #To obtain book details of the first, most relevant result
        required_details = [
            "title",
            "subtitle",
            "authors",
            "publisher",
            "publishedDate",
            "description",
            "industryIdentifiers",
            "pageCount",
            "categories",
            "imageLinks",
        ]
        required_details_dict = {}
        for item in required_details:
            if item == "categories":
                required_details_dict[item] = categories_list
            elif item in book_details.keys():
                required_details_dict[item] = book_details[item]
            else:
                continue
        user_info_with_identifiers["fetched_book_details"] = required_details_dict
        return user_info_with_identifiers
    else:
        logging.warning(
            f"No book results were found for {identifier.get('type')}: {identifier.get('value')} only updating title/ISBN"
        )
        user_info_with_identifiers["fetched_book_details"] = None
        return user_info_with_identifiers


def map_dict(notion_props: dict, book_details: dict) -> dict:
    """
    Maps book details to respective notion properties.
    """
    notion_props["Publisher"] = book_details.get("publisher", "")
    authors_list = []
    if book_details.get("authors", 0) > 0:
        for item in book_details["authors"]:
            authors = {"name": string.capwords(item).replace(",", "")}
            authors_list.append(authors)
    notion_props["Authors"] = authors_list #List of dictionaries for multiselect property in Notion
    summary = book_details.get("description", "")
    #Character limit for Text property in Notion
    if len(summary) > 2000:
        summary = summary[:1997] + "..."
        notion_props["Summary_extd"] = summary[1998:]
    notion_props["Summary"] = summary
    notion_props["Published"] = book_details.get("publishedDate", "")
    if book_details.get("industryIdentifiers") != None:
        for element in book_details["industryIdentifiers"]:
            if element["type"] in ["ISBN_10", "ISBN_13"]:
                if element["type"] == "ISBN_10":
                    notion_props["ISBN_10"] = element["identifier"]
                if element["type"] == "ISBN_13":
                    notion_props["ISBN_13"] = element["identifier"]
            elif element["type"] == "OTHER":
                notion_props["Other Identifier"] = element["identifier"]
            else:
                notion_props["ISBN_10"] = ""
                notion_props["ISBN_13"] = ""
    else:
        notion_props["ISBN_10"] = ""
        notion_props["ISBN_13"] = ""
    notion_props["Pages"] = book_details.get("pageCount", 0)
    notion_props["Title"] = book_details.get("title", "")
    subtitle = book_details.get("subtitle", "")
    if subtitle != "":
        notion_props["Subtitle"] = f": {subtitle}"
    category_list = []
    if book_details.get("categories", 0) > 0:
        for item in book_details["categories"]:
            category = {"name": string.capwords(item.replace(",", " "))}
            category_list.append(category)
    notion_props["Category"] = category_list #List of dictionaries for multiselect property in Notion
    if book_details.get("imageLinks") != None:
        imageLink = book_details["imageLinks"]["thumbnail"]
        notion_props["Image_url"] = imageLink
    logging.info("Book details matched to appropriate fields in BookShelf")
    return notion_props


def all_categories(all_results: list) -> list:
    """
    Returns a list of book categories (or genre) from all results of one book title/identifier
    """
    all_categories = []
    for book in all_results:
        categories = book.get("volumeInfo", {}).get("categories", [])
        all_categories += categories
    categories_set = set(all_categories)
    return categories_set