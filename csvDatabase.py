import csv
from itertools import count
import requests
import logging
from decouple import config
import sqlite3
import process_csv
import goodreads.goodreads
import notion.goodreads
import scrape_goodreads
from app import image

databaseFile = config("DATABASE_FILE_PATH")
clientID = config("NOTION_CLIENT_ID")
clientSecret = config("NOTION_CLIENT_SECRET")

logging.basicConfig(
    filename="goodreads.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level = logging.DEBUG
)

ourList = {"V1": ["Title", "ISBN_10", "ISBN_13", "Rating", "Status", "Source", "Date Completed", "Date Started", "Authors", "Summary", "Summary_extd", "Category", "Pages", "Publisher", "Source", "Date Added", "Rating"],
            "V2": ["Title", "ISBN_10", "ISBN_13", "Rating", "Status", "Source", "Dates", "Authors", "Summary", "Summary_extd", "Category", "Pages", "Publisher", "Source", "Date Added", "Rating"],
            "Unknown": None}

conn = sqlite3.connect(databaseFile)

while True:
    paid_user_details = goodreads.goodreads.get_users()
    paid_users = goodreads.goodreads.get_user_details(paid_user_details)
    for item in paid_users:
        user_id = item.get("user_id")
        bookshelf_database_id = item.get("bookshelf_database_id")
        access_token = item.get("access_token")
        version = item.get("version")
        if version != "Unknown":
            goodreads_id_data = notion.goodreads.get_goodreads_data(access_token)
            available_fields = notion.goodreads.get_available_fields(goodreads_id_data, version)
            missing_fields = notion.goodreads.missing_fields(available_fields, version)
            goodreads_database_id = notion.goodreads.get_goodreads_id(goodreads_id_data)
            if goodreads_database_id is not None:
                item["goodreads_database_id"] = notion.goodreads.get_goodreads_id(goodreads_id_data)
                goodreads.goodreads.update_goodreads_id(item["goodreads_database_id"], item["user_id"])
                csv_file_results = notion.goodreads.get_csvfile_results(item["goodreads_database_id"],item["user_id"], item["access_token"])
                if csv_file_results is not None:
                    csv_file, page_id = notion.goodreads.get_csvfile(csv_file_results)
                    extracted_data, num_books = process_csv.extract_csv(csv_file)
                    if extracted_data is not None:
                        mapped_dic = process_csv.map_csv_to_notion_fields(extracted_data)
                        count = 0                    
                        for item in mapped_dic:
                            print (item)
                            books_not_added=[]
                            book = scrape_goodreads.add_to_dic(item)
                            if book is not None:
                                image_link = image.upload_image(conn, book)
                                status = notion.goodreads.updateDatabase(book, bookshelf_database_id, access_token, missing_fields, image_link, version)
                                if status == 200:
                                    count+=1
                                else:
                                    books_not_added.append(status)
                                goodreads.goodreads.update_goodreads_books(book, image_link)             
                        notion.goodreads.status(user_id, access_token, page_id, num_books, count, books_not_added)
                        goodreads.goodreads.update_goodreads(user_id, num_books, count)


        
        