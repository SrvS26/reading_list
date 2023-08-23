import asyncio
import copy
import time
from decouple import config
import book_sources.source_01
import database.records as records
import images.build_book_cover
import api.notion as notion
import app.process_data
import aiohttp
from aiohttp import ClientSession
import custom_logger
import os
import math

payload_new_identifiers = '{"filter": {"or": [{"property": "Title","rich_text": {"ends_with": ";"}},{"property": "ISBN_10","rich_text": {"ends_with": ";"}},{"property": "ISBN_13","rich_text": {"ends_with": ";"}}]}}'

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

database_file = config("DATABASE_FILE_PATH")

image_file = config("IMAGE_PATH")

api_key = config("BOOK_API_KEY")

logging, listener = custom_logger.get_logger("main")

conn = records.connect_database(database_file)

processing_image_path = config("IMAGE_PATH") + "processing_book_covers"

temp_user = config("TEMP_USER")


if not os.path.exists(processing_image_path):
    os.mkdir(processing_image_path)

async def on_request_start(session, context, params):
    logging, listener = custom_logger.get_logger("aiohttp.client")
    logging.debug(f'Starting request <{params}>')

async def on_response_chunk_received(session, context, params):
    logging, listener = custom_logger.get_logger("aiohttp.client")
    logging.debug(f'Received response')

def get_all_validated():
    validated_users = records.fetch_records(conn, "USERS", ["access_token", "user_id", "database_id"], True, [{"condition":["is_validated", "=", "1"]}, {"condition":["user_id", "=", f"'{temp_user}'"]}])
    validated_users_details = app.process_data.validated_users(validated_users)
    num_users = math.ceil(len(validated_users_details)/3)
    return ([validated_users_details[x:x+num_users] for x in range(0, len(validated_users_details), num_users)])



async def get_new_identifiers(session, user_info: dict) -> dict:
    """Takes a dict with user details and returns it updated with new identifiers (if any) added to the user's database and missing properties in the user's database.

    :param user_info: {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False}
    :returns: {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False, "new_identifiers": [], "missing_properties": []}
    """
    notion_data = await notion.get_data_from_database(session, user_info, payload_new_identifiers)
    if notion_data == -1:
        user_info["is_revoked"] = True
    elif notion_data is not None:
        user_info['new_identifiers'] = app.process_data.get_identifiers(notion_data, user_info['user_id'])
        user_info['missing_properties'] = app.process_data.missing_props(notion.get_available_props(user_info['user_id'], notion_data))
    return user_info


async def get_book_details(session, conn, user_info_with_identifiers):
    """Takes a dict with user details and book identifiers and returns updated dict with book metadata and processed book cover image
    
    :param user_info_with_identifiers: {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False, "new_identifiers": {}, "missing_properties": []}
    :returns: {"access_token": "access token", "user_id": "user_id", "database_id": "database_id", "is_revoked": False, "new_identifiers": {}, "missing_properties": [], "book_details": {}, "mapped_book_details": {}, "image_file_path: "image_file_path"}
    """
    book_details = await book_sources.source_01.get_book_details(session, user_info_with_identifiers)
    user_info_with_identifiers["book_details"] = book_details
    if book_details is not None:
        mapped_books_details = book_sources.source_01.map_dict(copy.deepcopy(notion_props_dict), book_details)
        user_info_with_identifiers["mapped_book_details"] = mapped_books_details
        user_info_with_identifiers["image_file_path"] = await images.build_book_cover.async_upload_image(
            session, conn, mapped_books_details
        )
    user_info_with_books = user_info_with_identifiers    
    return user_info_with_books


async def update_notion(session, user_info_with_books):
    if user_info_with_books["book_details"] is not None:
        user_info_end = await notion.update_database(session, user_info_with_books)
    elif user_info_with_books["book_details"] is None:
        user_info_end = await notion.failure_update(session, user_info_with_books)
    else:
        user_info_end = copy.deepcopy(user_info_with_books)
    if user_info_end["is_revoked"]:
        list_revoked_users = list(filter(lambda x: x["is_revoked"], user_info_end))
        records.disable_users(conn, list_revoked_users)
    return None


async def run_main(validated_users_details):
    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    trace_config.on_response_chunk_received.append(on_response_chunk_received)
    # validated_users = records.fetch_records(conn, "USERS", ["access_token", "user_id", "database_id"], True, [{"condition":["is_validated", "=", "1"]}, {"condition":["user_id", "=", f"'{temp_user}'"]}])
    # validated_users_details = app.process_data.validated_users(validated_users)
    async with ClientSession(trust_env=True, trace_configs=[trace_config]) as session:
        user_info_with_notion = await asyncio.gather(
            *[
                get_new_identifiers(session, user_info)
                for user_info in validated_users_details
            ]
        )
    larger_list = list(map(lambda x: app.process_data.flatten_user_books(x), user_info_with_notion))
    user_info_list = [item for sublist in larger_list for item in sublist]
    async with ClientSession(trust_env=True) as session:
        user_info_with_books = await asyncio.gather(
            *[
                get_book_details(session, conn, user_info_with_identifiers)
                for user_info_with_identifiers in user_info_list
            ]
        )

    async with ClientSession(trust_env=True) as session:
        await asyncio.gather(
            *[
                update_notion(session, item)
                for item in user_info_with_books
            ]
        )

while True:
    listener.start()
    for sublist in get_all_validated():
        print(sublist)
        asyncio.run(run_main(sublist))
        time.sleep(2)
    listener.stop()
