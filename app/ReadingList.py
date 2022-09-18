import asyncio
import datetime, time
from decouple import config
import logging
import googlebooks
import usersDatabase
import image
import notion
import failed
from aiohttp import ClientSession

ourList = [
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
]

ourDic = {
    "Title": "",
    "Subtitle": "",
    "Publisher": "",
    "Authors": "",
    "Summary": "",
    "Summary_extd": "",
    "Category": "",
    "Published": "",
    "ISBN_10": "",
    "Pages": None,
    "ISBN_13": "",
    "Image_url": "",
}

databaseFile = config("DATABASE_FILE_PATH")

imageFolder = config("IMAGE_PATH")

google_api_key = config("GOOGLE_API_KEY")

url = config("BASE_URL")

# logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logging.basicConfig(
    filename="app.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

conn = usersDatabase.connectDatabase(databaseFile)

# { user_id: String
# , database_id: String
# , access_token: String
# , is_revoked: Bool
# , new_books_added: {}|None
# , new_book_identifiers: [{Type: String, Value: String, pageID: String}] | []
# , available_properties: [{}] | []
# }
# {user_id:1, new_book_identifiers:[{type:isbn,value:123,pageId:1},{type:title,value:hello,pageid:2}]}
# [{user_id:1,.. new_book_identifiers: {type:isbn,value:123,pageId:1}}
# , {user_id:1, new_book_identifiers: {type:title, value:hello,pageId:2}}]
# {1: [{type:title}]}
async def get_added_books_from_notion(session, user_info={}):
    user_info_updated = await notion.requiredPageDetails(session, user_info)
    if user_info_updated["new_books_added"] is not None:
        user_info_updated["new_book_identifiers"] = notion.getNewTitlesOrISBN(
            user_info_updated["new_books_added"]
        )
        available_properties = notion.getAllFields(user_info_updated["new_books_added"])
        user_info_updated["missing_properties"] = notion.compareLists(
            available_properties
        )
    return user_info_updated


def flatten_user_books(user_info_updated):
    user_info_list = []
    for new_book in user_info_updated["new_book_identifiers"]:
        flat_dict = dict()
        flat_dict = user_info_updated
        flat_dict["new_book_identifiers"] = new_book
        user_info_list.append(flat_dict)
    return user_info_list


async def get_google_book_details(session, conn, user_info_with_identifiers):
    user_info_with_googlebooks = await googlebooks.getBookDetails(
        session, user_info_with_identifiers
    )
    if user_info_with_googlebooks["google_book_details"] is not None:
        mapped_google_to_notion = googlebooks.mapOneDicToAnother(
            ourDic, user_info_with_googlebooks["google_book_details"]
        )
        user_info_with_googlebooks["google_book_details"] = mapped_google_to_notion
        user_info_with_googlebooks["image_file_path"] = await image.uploadImage(
            session, conn, mapped_google_to_notion
        )

    return user_info_with_googlebooks


async def update_notion_with_bookdetails(session, user_info_with_googlebooks):
    if (
        user_info_with_googlebooks["google_book_details"] is not None
        and user_info_with_googlebooks["new_books_added"] is not None
    ):
        user_info_end = await notion.updateDatabase(session, user_info_with_googlebooks)
    elif user_info_with_googlebooks["google_book_details"] is None:
        user_info_end = await failed.cannotRetrieve(session, user_info_with_googlebooks)
    else:
        user_info_end = user_info_with_googlebooks
    if user_info_end["is_revoked"]:
        listRevoked = list(filter(lambda x: x["is_revoked"], user_info_end))
        usersDatabase.removeFromUsers(listRevoked, conn)
    return None


all_users = usersDatabase.getRecords(conn)
validated_users_info = usersDatabase.getValidatedTokens(all_users)


async def run_main():
    async with ClientSession(trust_env=True) as session:
        # [{user_info}]
        user_info_updated = await asyncio.gather(
            *[
                get_added_books_from_notion(session, user_info)
                for user_info in validated_users_info
            ]
        )
    # user_info_updated = [5], num of books = 2
    # [
    # [{user_info},{user_info}],
    # [{user_info},{user_info}]
    # ]
    larger_list = list(map(lambda x: flatten_user_books(x), user_info_updated))
    # final = []
    # for sublist in larger_list:
    #    for item in sublist:
    #       final.append(item)
    user_info_list = [item for sublist in larger_list for item in sublist]

    async with ClientSession(trust_env=True) as session:
        user_info_with_googlebooks = await asyncio.gather(
            *[
                get_google_book_details(session, conn, user_info_with_identifiers)
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


# while True:
#     print(datetime.datetime.now())
#     newRecords = usersDatabase.getRecords(conn)
#     listAccessTokens = usersDatabase.getValidatedTokens(newRecords)
#     # async with ClientSession(trust_env=True) as session:
#     #     await asyncio.gather(
#     #         *[getBookdetails(isbn, session) for isbn in listDicIdentifier]
#     #     )
#     for i in range(
#         5
#     ):  # loop through Notion 5 times before looking for new access tokens
#         for index in range(len(listAccessTokens)):
#             listRevoked = []
#             user_info = listAccessTokens[index]
#             # databaseID = listAccessTokens[index]["database_id"]
#             # token = listAccessTokens[index]["access_token"]
#             # userID = listAccessTokens[index]["user_id"]
#             try:
#                 # results = notion.requiredPageDetails(session, user_info)
#                 if results == 401 or results == 404:
#                     listAccessTokens[index]["is_revoked"] = True
#                 elif results is not None:
#                     # newTitlesOrISBN = notion.getNewTitlesOrISBN(results)
#                     # availableFields = notion.getAllFields(results)
#                     # missingProperties = notion.compareLists(availableFields)
#                     for item in newTitlesOrISBN:
#                         # newGoogleBookDetails = googlebooks.getBookDetails(
#                         # item, user_info
#                         # )
#                         # if newGoogleBookDetails is not None:
#                         #     mappedDic = googlebooks.mapOneDicToAnother(
#                         #         ourDic, newGoogleBookDetails
#                         #     )
#                         #     filePath = image.uploadImage(mappedDic)
#                         # notion.updateDatabase(
#                             # mappedDic, item, filePath, missingProperties, user_info
#                         )
#             except Exception as e:
#                 logging.error(e)
#         # listRevoked = list(filter(lambda x: x["is_revoked"], listAccessTokens))
#         # usersDatabase.removeFromUsers(listRevoked, conn)
#         time.sleep(5)
#     print(datetime.datetime.now())

# conn.close()
