import requests
import csv
from datetime import datetime, timedelta
import logging
import scrape_goodreads

logging.basicConfig(
    filename="goodreads.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level = logging.DEBUG
)


def extract_csv(url):
    if url is not None:
        data = requests.get(url)
        lines = data.text.splitlines()
        listDictCSV = list(csv.DictReader(lines))
        num_books = len(listDictCSV)
        return listDictCSV, num_books
    else:
        return None, None    

def map_csv_to_notion_fields(listDictCSV):
    bookDetails = []
    for item in listDictCSV:
        myDic = {}
        myDic["goodreadsID"] = item.get("Book Id", "")
        authorsList = []
        author = {}
        author["name"] = item.get("Author","")
        authorsList.append(author)
        myDic["Author"] = authorsList
        myDic["Publisher"] = item.get("Publisher", "")
        if item["Number of Pages"] != "":
            myDic["Pages"] = int(item.get("Number of Pages", 0))
        else:
            myDic["Pages"] = None    
        myDic["Published"] =item.get("Year Published", "")
        myDic["Title"] = item.get("Title", "")
        myDic["ISBN_13"] = item.get("ISBN13", '').replace('="', '').replace('"', '')
        myDic["ISBN_10"] = item.get("ISBN", '').replace('="', '').replace('"', '')
        myDic["myRating"] = item.get("My Rating", 0)
        if item.get("Exclusive Shelf") == "read":
            myDic["status"] = "Done"
        elif item.get("Exclusive Shelf") == "to-read":
            myDic["status"] = "To Read"   
        elif item.get("Exclusive Shelf") == "currently-reading":
            myDic["status"] = "Reading"
        else:
            myDic["status"] = ""    
        myDic["myReview"] = item.get("My Review", '')
        myDic["myNotes"] = item.get("Private Notes", '')
        myDic["Date Added"] = ""
        myDic["Date Completed"] = ""
        myDic["Date Started"] = ""
        if item.get("Date Read", "") != "":
            try:
                date_object = datetime.strptime(item.get("Date Read"), '%Y/%M/%d').date()
                myDic["Date Completed"] = date_object.isoformat()
                startDate = date_object-timedelta(days=7)
                myDic["Date Started"] = startDate.isoformat()
            except ValueError:
                myDic["Date Completed"] = ""      
        if item.get("Date Added", "") != "":
            try:
                date_object = datetime.strptime(item.get("Date Added"), '%Y/%M/%d').date()
                myDic["Date Added"] = date_object.isoformat()
            except ValueError:
                myDic["Date Added"] = ""
        bookDetails.append(myDic)
    return bookDetails

def divide_into_sets(listCSV):
    book_list = []
    mapped_list = map_csv_to_notion_fields(listCSV)
    num_in_set = 25
    quo = int((len(mapped_list))/num_in_set)
    mod = (len(mapped_list))%num_in_set
    for i in range(quo):
        start = i * num_in_set
        end = start + num_in_set
        one_set = mapped_list[start:end]
        book_list.append(one_set)
    if mod != 0:
        start = quo * num_in_set
        last_set = mapped_list[start:]
        book_list.append(last_set)
    return book_list         
