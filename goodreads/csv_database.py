import csv
from itertools import count
import requests
import logging
from decouple import config
import sqlite3
import app.process_csv as process_csv
import app.goodreads_database
import app.goodreads
import scrape_goodreads
from app import image
import time

databaseFile = config("DATABASE_FILE_PATH")
clientID = config("NOTION_CLIENT_ID")
clientSecret = config("NOTION_CLIENT_SECRET")

logging.basicConfig(
    filename="csv_database.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level = logging.DEBUG
)

ourList = ["Title", "ISBN_10", "ISBN_13", "Rating", "Status", "Source", "Dates", "Date Completed", "Date Started", "Authors", "Summary", "Summary_extd", "Category", "Pages", "Publisher", "Source", "Date Added", "Rating"]

conn = sqlite3.connect(databaseFile)

while True:
    paid_user_details = app.goodreads_database.get_users()
    paid_users = app.goodreads_database.get_user_details(paid_user_details)
    for item in paid_users:
        user_id = item.get("user_id")
        bookshelf_database_id = item.get("bookshelf_database_id")
        access_token = item.get("access_token")
        version = item.get("version")
        if version != "Unknown":
            goodreads_id_data = app.goodreads.get_goodreads_data(access_token)
            available_fields = app.goodreads.get_available_fields(goodreads_id_data)
            missing_fields = app.goodreads.missing_fields(available_fields)
            goodreads_database_id = app.goodreads.get_goodreads_id(goodreads_id_data)
            if goodreads_database_id is not None:
                item["goodreads_database_id"] = app.goodreads.get_goodreads_id(goodreads_id_data)
                app.goodreads_database.update_goodreads_id(item["goodreads_database_id"], item["user_id"])
                csv_file_results = app.goodreads.get_csvfile_results(item["goodreads_database_id"],item["user_id"], item["access_token"])
                if csv_file_results is not None:
                    csv_file, page_id = app.goodreads.get_csvfile(csv_file_results)
                    extracted_data, num_books = process_csv.extract_csv(csv_file)
                    if extracted_data is not None:
                        mapped_list = process_csv.divide_into_sets(extracted_data)
                        count = 0
                        books_not_added=[]
                        for set in mapped_list:                 
                            final_book = []
                            for item in set:
                                book_with_scraped_info = scrape_goodreads.add_to_dic(item)
                                final_book.append(book_with_scraped_info)
                            for book in final_book:    
                                if book is not None:
                                    image_link = image.upload_image(conn, book)
                                    status = app.goodreads.updateDatabase(book, bookshelf_database_id, access_token, missing_fields, image_link, version)
                                    if status == 200:
                                        count+=1
                                    else:
                                        books_not_added.append(status)
                                    app.goodreads_database.update_goodreads_books(book, image_link)
                            time.sleep(5)                 
                        app.goodreads.status(user_id, access_token, page_id, num_books, count, books_not_added)
                        app.goodreads_database.update_goodreads(user_id, num_books, count)


        
        