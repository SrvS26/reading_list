import asyncio
import copy
import time
from decouple import config
import books
import database
import book_cover
import notion
from aiohttp import ClientSession
import custom_logger

notion_props_list = [
    "Title",
    "Authors",
    "Category",
    "Pages",
    "ISBN_10",
    "ISBN_13",
    "Other Identifier",
    "Summary",
    "Summary_extd",
    "Published",
    "Publisher",
]

notion_props_dict = {
    "Title": "",
    "Subtitle": "",
    "Authors": "",
    "Category": "",
    "Pages": None,
    "ISBN_10": "",
    "ISBN_13": "",
    "Other Identifier": "",
    "Summary": "",
    "Summary_extd": "",
    "Published": "",
    "Publisher": "",
    "Image_url": "",
}

database = config("DATABASE_FILE_PATH")

image = config("IMAGE_PATH")

api_key = config("BOOK_API_KEY")

logging, listener = custom_logger.get_logger("main")

conn = database.connect_database(database)


# { user_id: String
# , database_id: String
# , access_token: String
# , is_revoked: Bool
# , new_books_added: {}|None
# , new_book_identifiers: [{Type: String, Value: String, pageID: String}] | []
# , available_properties: [{}] | []
# }


async def get_new_identifiers(session, user_info = {}):
    user_info_updated = await notion.requiredPageDetails(session, user_info)
    if user_info_updated["new_books_added"] is not None:
        user_info_updated["new_book_identifiers"] = notion.getNewTitlesOrISBN(
            user_info_updated
        )
        available_properties = notion.getAllFields(user_info_updated)
        user_info_updated["missing_properties"] = notion.compareLists(
            available_properties
        )
        del user_info_updated["new_books_added"]
    return user_info_updated


def flatten_user_books(user_info_updated):
    user_info_list = []
    if user_info_updated.get("new_book_identifiers") is not None:
        for new_book in user_info_updated["new_book_identifiers"]:
            flat_dict = copy.deepcopy(user_info_updated)
            flat_dict["new_book_identifiers"] = new_book
            user_info_list.append(flat_dict)
    return user_info_list


async def get_book_details(session, conn, user_info_with_identifiers):
    user_info_with_googlebooks = await books.get_book_details(
        session, user_info_with_identifiers
    )
    if user_info_with_googlebooks["fetched_book_details"] is not None:
        mapped_google_to_notion = books.mapOneDicToAnother(
            copy.deepcopy(notion_props_dict), user_info_with_googlebooks["fetched_book_details"]
        )
        user_info_with_googlebooks["google_book_details"] = mapped_google_to_notion
        user_info_with_googlebooks["image_file_path"] = await book_cover.uploadImage(
            session, conn, mapped_google_to_notion
        )
    return user_info_with_googlebooks


async def update_notion_with_bookdetails(session, user_info_with_googlebooks):
    if user_info_with_googlebooks["google_book_details"] is not None:
        user_info_end = await notion.updateDatabase(session, user_info_with_googlebooks)
    elif user_info_with_googlebooks["google_book_details"] is None:
        user_info_end = await notion.cannotRetrieve(session, user_info_with_googlebooks)
    else:
        user_info_end = copy.deepcopy(user_info_with_googlebooks)
    if user_info_end["is_revoked"]:
        listRevoked = list(filter(lambda x: x["is_revoked"], user_info_end))
        database.removeFromUsers(listRevoked, conn)
    return None


async def run_main():
    all_users = database.getRecords(conn)
    validated_users_info = database.validated_users(all_users)
    async with ClientSession(trust_env=True) as session:
        user_info_updated = await asyncio.gather(
            *[
                get_new_identifiers(session, user_info)
                for user_info in validated_users_info
            ]
        )

    larger_list = list(map(lambda x: flatten_user_books(x), user_info_updated))

    user_info_list = [item for sublist in larger_list for item in sublist]

    async with ClientSession(trust_env=True) as session:
        user_info_with_googlebooks = await asyncio.gather(
            *[
                get_book_details(session, conn, user_info_with_identifiers)
                for user_info_with_identifiers in user_info_list
            ]
        )

    async with ClientSession(trust_env=True) as session:
        await asyncio.gather(
            *[
                update_notion_with_bookdetails(session, item)
                for item in user_info_with_googlebooks
            ]
        )


while True:
    listener.start()
    asyncio.run(run_main())
    time.sleep(5)
    listener.stop()
