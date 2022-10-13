import requests
import csv
from datetime import datetime, timedelta
import logging

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
        myDic["Author"] = item.get("Author","") + "," + item.get("Additional Authors", "")
        myDic["Publisher"] = item.get("Publisher", "")
        myDic["Pages"]=item.get("Number of Pages", 0)
        myDic["Published"] =item.get("Year Published", "")
        myDic["Title"] = item.get("Title", "")
        myDic["ISBN_13"] = item.get("ISBN13", '').replace('="', '').replace('"', '')
        myDic["ISBN_10"] = item.get("ISBN", '').replace('="', '').replace('"', '')
        myDic["myRating"] = item.get("My Rating", 0)
        myDic["dateStarted"] = item.get("Date Read", '')
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

# def addtrigger(bookDetails):
#     count = 0
#     triggerDetails = []
#     for item in bookDetails:
#         if item["ISBN_13"] != "":
#             item["ISBN_13"] = item["ISBN_13"] + ";"
#         elif item["ISBN_10"] != "":
#             item["ISBN_10"] = item["ISBN_10"] + ";"
#         else:
#             count += 1            
#         triggerDetails.append(item)
#     return triggerDetails, count        