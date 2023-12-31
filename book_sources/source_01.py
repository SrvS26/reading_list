import copy
import string

from decouple import config
import custom_logger

logging = custom_logger.get_logger()

api_key = config("BOOK_API_KEY")
base_url = config("BASE_URL_BOOK")


async def get_book_details(session, user_info_with_identifiers_: dict, with_key = True, retries: int = 5) -> dict:
    """Takes a dict with user info and book identifier and returns the dict updated with fetched book metadata.

    param user_info_with_identifiers_: {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False, "new_identifiers": {'identifier': 'value', 'page_id': 'page_id'}, "missing_properties": []}
    param with_key: Default True. Useful if rate limited, attempts to query without API key.
    param retries: Number of retries if rate-limited.
    returns: {"title": "title",
            "subtitle": "subtitle",
            "authors": "authors",
            "publisher": "publisher",
            "publishedDate": "publishedDate",
            "description": "description",
            "industryIdentifiers": "industryIdentifiers",
            "pageCount": "pageCount",
            "categories": "categories",
            "imageLinks": "imageLinks"}
    """
    user_info_with_identifiers = copy.deepcopy(user_info_with_identifiers_)
    user_id = user_info_with_identifiers["user_id"]
    identifier = user_info_with_identifiers["new_identifiers"]
    if with_key:
        query_param = f"&key={api_key}"
    else: # when rate limited
        await logging.awarning(
            "Retrying fetching book details without API key",
            user_id=user_id,
            book_info=identifier["value"],
            book_source=1
        )
        query_param = ""
    if retries > 0:
        if identifier.get("type") == "title":
            url = base_url + "?q=" + identifier['value'] + query_param
        elif (
            identifier.get("type") == "isbn_10"
            or identifier.get("type") == "isbn_13"
        ):
            url = base_url + "?q=isbn:" + identifier['value'] + query_param
        web_page = await session.request(method="GET", url=url, ssl=False)
        if web_page.status == 429:
            await logging.aerror(
                "Rate limited by provider",
                book_type=identifier.get("type"),
                book_info=identifier["value"],
                user_id=user_id,
                status_code=web_page.status,
                with_key=with_key,
                book_source=1
            )
            return await get_book_details(
                session,
                copy.deepcopy(user_info_with_identifiers_),
                with_key = False,
                retries = retries - 1,
            )
        elif web_page.status != 200:
            await logging.aerror(
                "Failed request to fetch book details", book_info=identifier['value'], user_id= user_id, status_code=web_page.status, book_source=1
            )
            return None
        else:
            await logging.ainfo(
                "Book details fetched", book_info=identifier['value'], user_id= user_id, with_key=with_key, category="ACTION", book_source=1
            )
        parsed_content = await web_page.json()
    else:
        logging.error(
            "Exhausted retries for book", book_info=identifier['value'], user_id= user_id, book_source=1
        )
        parsed_content = {}
    if parsed_content.get("totalItems", 0) > 0:
        results_list = parsed_content["items"]
        categories_list = all_categories(results_list)
        first_book_details = results_list[0].get("volumeInfo") #To obtain book details of the first, most relevant result
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
        book_details = {}
        for item in required_details:
            if item == "categories":
                book_details[item] = categories_list
            elif item in first_book_details.keys():
                book_details[item] = first_book_details[item]
            else:
                continue
        return book_details
    else:
        await logging.awarning(
            "No book results found, only updating title/ISBN", book_type=identifier.get('type'), book_info=identifier.get('value'), book_source=1
        )
        return None


def map_dict(notion_props: dict, book_details: dict) -> dict:
    """Maps book details to respective notion properties.

    param notion_props: Dict with notion properties that will be autofilled
    param book_details: Dict with book details fetched from source
    returns: Dict with book details mapped to notion properties
    {"Title": "Title|"",
    "Subtitle": "Subtitle|"",
    "Authors": "Authors|"",
    "Category": "Category"|"",
    "Pages": int|None,
    "ISBN_10": "ISBN_10"|"",
    "ISBN_13": "ISBN_13"|"",
    "Other Identifier": "Other Identifier|"",
    "Summary": "Summary"|"",
    "Summary_extd": "Summary_extd"|"",
    "Published": "Published"|"",
    "Publisher": "Publisher"|"",
    "Image_url": "Image_url"|"",
    }
    """
    notion_props["Publisher"] = book_details.get("publisher", "")
    authors_list = []
    if book_details.get("authors") is not None and len(book_details) != 0:
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
    if book_details.get("categories") != None and len(book_details["categories"]) > 0:
        for item in book_details["categories"]:
            category = {"name": string.capwords(item.replace(",", " "))}
            category_list.append(category)
    notion_props["Category"] = category_list #List of dictionaries for multiselect property in Notion
    if book_details.get("imageLinks") != None:
        imageLink = book_details["imageLinks"]["thumbnail"]
        notion_props["Image_url"] = imageLink
    logging.info("Book details matched to appropriate fields in BookShelf", book_source=1)
    return notion_props


def all_categories(all_results: list) -> list:
    """Get a list of book categories (or genre) from all results of one book title/identifier"""
    all_categories = []
    for book in all_results:
        categories = book.get("volumeInfo", {}).get("categories", [])
        all_categories += categories
    categories_set = set(all_categories)
    return categories_set
