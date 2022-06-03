from random import random
import string
from uuid import UUID, uuid4
import requests
import json
import datetime
from wand.color import Color
from wand.image import Image, GRAVITY_TYPES, COLORSPACE_TYPES
import sqlite3
from decouple import config
import logging
import os

checkTime = datetime.datetime(2022, 2, 1, 0, 0, 0, 0, tzinfo=datetime.timezone.utc)
checkTimeUTC = checkTime.isoformat()
epoch_time = checkTime.timestamp()

ourList = ["Title", "Publisher", "Authors", "Summary", "Category", "Published", "ISBN_10", "Pages", "ISBN_13", "Summary_extd"]

ourDic = {"Title": "", "Publisher": "", "Authors": "", "Summary": "", "Summary_extd": "", "Category":"", "Published": "", "ISBN_10": "", "Pages": None, "ISBN_13":""}

listAccessTokens = []

databaseFile = config("DATABASE_FILE_PATH")

imageFolder = config("IMAGE_PATH")

url = config("BASE_URL")

# logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logging.basicConfig(filename='app.log', format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

conn = sqlite3.connect(databaseFile)
logging.debug(f"Connected to database '{databaseFile}'")


def getDatabaseTimestamp(databaseCheckedTime):
    cursor = conn.cursor()
    fetchSpecificDeets = f"""SELECT access_token, database_id, user_id, time_added from USERS WHERE is_validated = 1 AND time_added > {databaseCheckedTime} ORDER BY time_added DESC"""
    logging.info(f"Attempting to fetch data added to table USERS after {databaseCheckedTime}")
    cursor.execute(fetchSpecificDeets)
    records = cursor.fetchall()
    numberRecords = len(records)
    logging.info(f"Fetched {numberRecords} row/s of data added after {databaseCheckedTime} from USERS")
    conn.commit()
    cursor.close()
    return records

def removeFromUsers(revokedUsers):
    if len(revokedUsers)>0:
        cursor = conn.cursor()
        listDatabaseIDs = list(map(lambda x:(x["database_id"],), revokedUsers))
        # print (listDatabaseIDs)
        cursor.executemany("UPDATE USERS SET is_revoked = 1 WHERE database_id = ?", listDatabaseIDs)
        logging.info(f"Updated {len(revokedUsers)} number of is_revoked to 1 in USERS")
        conn.commit()
        cursor.close()
    else:
        logging.info("No users were deleted from USERS for revoking access")    
        return

def getAccessTokens(records):
    listofTokens = []
    for row in records:
        dicTokens = {}
        access_token = row[0]
        database_id = row[1]
        user_id = row[2]
        dicTokens["access_token"] = access_token
        dicTokens ["database_id"] = database_id
        dicTokens ["user_id"] = user_id
        dicTokens ["is_revoked"] = False
        listofTokens.append(dicTokens)
    logging.info(f"Processed {len(records)} number of rows of data fetched from USERS")            
    return listofTokens

def retrieveUserID (condition):
    cursor = conn.cursor()
    fetchUserID = f"""SELECT user_id from users where database_id = '{condition}'"""
    cursor.execute(fetchUserID)
    user_id = cursor.fetchall()
    conn.commit()
    return user_id        

def requiredPageDetails(databaseID, token, lastCheckedTime): #Filter can be modified to remove last checked time as it might not really be required
    url = f"https://api.notion.com/v1/databases/{databaseID}/query"
    payload = "{\"filter\": {\"and\": [{\"timestamp\": \"last_edited_time\",\"last_edited_time\": {  \"on_or_after\": \""+lastCheckedTime+"\"} },{\"or\": [{\"property\": \"Title\",\"rich_text\": {\"ends_with\": \";\"}},{\"property\": \"ISBN_10\",\"rich_text\": {\"ends_with\": \";\"}},{\"property\": \"ISBN_13\",\"rich_text\": {\"ends_with\": \";\"}}]}]}}"
    headers = {
        'Content-Type': "application/json",
        'Notion-Version': "2022-02-22",
        'Authorization': f"Bearer {token}"
        }
    logging.info("Applying filters and fetching new additions to BookShelf")    
    user_id = retrieveUserID(databaseID)
    # print (user_id)
    try:
        response = requests.request("POST", url, data=payload, headers=headers)
        # print (response)
        if response.status_code == 401:
            logging.warning(f"User {user_id} has revoked access")
            return 401
        elif response.status_code == 404:
            logging.warning(f"User {user_id} has deleted Bookshelf")
            return 404  
        elif response.status_code == 200:
            logging.info(f"Fetched new additions to BookShelf for user: {user_id}")
            parsed_response = response.json()
            # print(parsed_response)
            results = parsed_response["results"]  
            # print (results)
            return results
        else:
            logging.error(f"Failed due to status code: {response.status_code}, response: {response.json()} for user: {user_id}")     
            return None
    except Exception as e:
        logging.error(f"Failed to fetch new details from Bookshelf for user: {user_id}") 
        return None   

def getNewTitlesOrISBN(results):   
    listOfAllTitlesOrISBN = []
    if len(results) > 0: 
        for item in results:  
            dicOfTitlesOrISBN = {}                                    
            detailsOfISBN10 = item["properties"]["ISBN_10"]["rich_text"]
            detailsOfISBN13 = item["properties"]["ISBN_13"]["rich_text"]
            detailsOfTitle = item["properties"]["Title"]["title"]   
            if len(detailsOfTitle) > 0:                                     
                for i in detailsOfTitle:                                    
                    actualTitle = i["text"]["content"]  
            else:
                actualTitle = ""        
            if len(detailsOfISBN10) > 0:
                for i in detailsOfISBN10:
                    actualISBN10 = i["text"]["content"]
            else:
                actualISBN10 = ""                
            if len(detailsOfISBN13) > 0:
                for i in detailsOfISBN13:
                    actualISBN13 = i["text"]["content"]                
            else:
                actualISBN13 = ""        
            if actualTitle != "" and actualTitle[-1] == ";":
                dicOfTitlesOrISBN["Value"] = actualTitle[:-1]
                dicOfTitlesOrISBN["Type"] = "Title"
            elif actualISBN10 != "" and actualISBN10[-1] == ";":                                                                   
                dicOfTitlesOrISBN["Value"] = actualISBN10[:-1]
                dicOfTitlesOrISBN["Type"] = "ISBN_10"            
            elif actualISBN13 != "" and actualISBN13[-1] == ";":
                dicOfTitlesOrISBN["Value"] = actualISBN13[:-1]
                dicOfTitlesOrISBN["Type"] = "ISBN_13"   
            if len(dicOfTitlesOrISBN) != 0:                        
                pageID = item["id"]                                         
                dicOfTitlesOrISBN["pageID"] = pageID 
                listOfAllTitlesOrISBN.append(dicOfTitlesOrISBN)
        logging.info("New titles/ISBN extracted from new additions to BookShelf")                                          
    else:
        logging.info("No changes in BookShelf/No new titles/ISBN found")      
    return listOfAllTitlesOrISBN

def getAllFields(results):
    allAvailableList = []
    if len(results) > 0:                                                         
        onePagePropertyDetails = results[0]                     
        requiredPropertiesGeneral = onePagePropertyDetails["properties"]    
        for item in requiredPropertiesGeneral.keys():                       
            if item in ourList:                                             
                allAvailableList.append(item)   
        logging.info("All available fields to fill in BookShelf fetched") 
    else:
        logging.info("There are no new additions or the notion database 'Bookshelf' is empty")                                       
    return allAvailableList

def getBookDetails(dicOfTitlesOrISBN):
    if dicOfTitlesOrISBN.get("Type") == "Title":
        url = "https://www.googleapis.com/books/v1/volumes?q=" + dicOfTitlesOrISBN["Value"]
    elif dicOfTitlesOrISBN.get("Type") == "ISBN_10" or dicOfTitlesOrISBN.get("Type") == "ISBN_13":
        url = "https://www.googleapis.com/books/v1/volumes?q=isbn:" + dicOfTitlesOrISBN["Value"] 
    webPageDetails = requests.get(url)     
    logging.info(f"Book details fetched from google books {url}")                                 
    webPageContent = (webPageDetails.content)
    parsedContent = json.loads(webPageContent)                              
    if parsedContent.get("totalItems", 0) > 0:
        listOfBookResults = parsedContent["items"]
        categories = getAllCategories(listOfBookResults)
        firstBookResult = listOfBookResults[0]                              
        bookDetails = firstBookResult.get("volumeInfo")
        requiredBookDetails = ["title", "authors", "publisher", "publishedDate", "description", "industryIdentifiers", "pageCount", "categories", "imageLinks"]
        dicOfRequiredBookDetails = {}
        for item in requiredBookDetails:  
            if item == "categories":
                dicOfRequiredBookDetails[item] = categories                                      
            elif item in bookDetails.keys():                                   
                dicOfRequiredBookDetails[item] = bookDetails[item]
            else:
                continue    
        return (dicOfRequiredBookDetails)                                      
    else:
        logging.info(f"No google book results were found for {dicOfTitlesOrISBN.get('Type')}: {dicOfTitlesOrISBN.get('Value')} only updating title/ISBN")
        cannotRetrieve(dicOfTitlesOrISBN)    
        return None

def getAllCategories (allResults):
    allCategories = []
    for i in allResults:
        categories = i.get("volumeInfo", {}).get("categories", [])
        allCategories = allCategories + categories
    finalCategories = set(allCategories)    
    return finalCategories    


def mapOneDicToAnother(ourDic, GoogleBookInfo):
    ourDic["Publisher"] = GoogleBookInfo.get("publisher", "")
    listauthors = []
    if GoogleBookInfo.get("authors") != None and len(GoogleBookInfo["authors"]) > 0:
        for item in GoogleBookInfo["authors"]:
            authors = {}
            authors["name"] = string.capwords(item)
            listauthors.append(authors)           
    ourDic["Authors"] = listauthors  
    summary = GoogleBookInfo.get("description", "")
    if len(summary) > 2000:
        summary = summary[:1997] + "..."
        summary_extd = summary[1998:]    
        ourDic["Summary_extd"] = summary_extd
    ourDic["Summary"] = summary
    ourDic["Published"] = GoogleBookInfo.get("publishedDate", "")
    if GoogleBookInfo.get("industryIdentifiers") != None:
        for element in GoogleBookInfo["industryIdentifiers"]:
            if element["type"] == "ISBN_10":
                ourDic["ISBN_10"] = element["identifier"]
            if element["type"] == "ISBN_13":
                ourDic["ISBN_13"] = element["identifier"]
    else:
        ourDic["ISBN_10"] = ""      
        ourDic["ISBN_13"] = ""
    ourDic["Pages"] = GoogleBookInfo.get("pageCount", 0)
    ourDic["Title"] = GoogleBookInfo.get("title", "")
    listcategory = []
    if GoogleBookInfo.get("categories") != None and len(GoogleBookInfo["categories"]) > 0:   
        for item in GoogleBookInfo["categories"]: 
            category = {}
            category["name"] = string.capwords(item.replace(","," "))
            listcategory.append(category)
    ourDic["Category"] = listcategory
    logging.info("Google book details matched to appropriate fields in BookShelf")
    return ourDic 

def getImageDatabase(ourDic):
    cursor = conn.cursor()
    image = f"""SELECT image_path from IMAGES WHERE ISBN_10 = '{ourDic.get("ISBN_10")}' OR ISBN_13 = '{ourDic.get("ISBN_13")}'"""
    # print(image)
    cursor.execute(image)
    imagePath = cursor.fetchone()
    conn.commit()
    # print (imagePath)
    return imagePath

def insertImage(ourDic, title):
    cursor = conn.cursor()         
    imageName = url + "/" + title + ".jpg"
    # print (imageName)
    if ourDic.get("ISBN_10") is None and ourDic.get("ISBN_13") is None: 
        return imageName        
    else:    
        rows = f"""INSERT INTO IMAGES (ISBN_10, ISBN_13, image_path) VALUES ('{ourDic.get("ISBN_10")}', '{ourDic.get("ISBN_13")}', "{imageName}");""" 
        cursor.execute(rows)
        conn.commit()
        return imageName

def getImage(AllWeNeed, finalTitle):
    title = AllWeNeed["title"]
    # print (title)
    # finalTitle = "".join(filter(lambda x:x.isalnum(), title))
    # print (finalTitle)
    if AllWeNeed.get("imageLinks") != None:
        imageLink = AllWeNeed["imageLinks"]["thumbnail"] 
        logging.info(f"Querying for book {finalTitle} cover")
        r = requests.get(imageLink)
        with open(finalTitle, "wb") as f:       
            f.write(r.content)   
        return (finalTitle)  
    else:
        logging.info(f"Book {title} has no image") 
        return "NI.jpg"

def resizeImage(title):
    with Image(filename=title) as img:
        img.resize(height=180)
        img.save(filename="resizedImaged.jpg") 
    return ("resizedImaged.jpg")  

def getsRGB(title): 
    file = title 
    with Image(filename= file) as img: 
        img.quantize(5, "srgb", 0, True, False) 
        hist = img.histogram
        sortedDict = sorted(hist.items(), key = lambda x: x[1], reverse = True)
        highestValue = (sortedDict[0])
        srgbHighestValue = highestValue[0]
        stringHighestValue = str(srgbHighestValue)
    return (stringHighestValue)   

def alterIfBlack(sRGBString):
    dontWantinString = "srgb%()"
    finalString = ""
    for letter in sRGBString:
            if letter not in dontWantinString:
                finalString += letter
    RGBvalues = finalString.split(",")
    try:
        RGBValuesList = list(map(float, RGBvalues))
        r = (RGBValuesList[0]/100) * 255
        g = (RGBValuesList[1]/100) * 255
        b = (RGBValuesList[2]/100) * 255
        return (r  <= 30 and g <= 30 and b <= 30)     
    except ValueError:
        return True
           
def createBackground(sRGBCode):
    if alterIfBlack(sRGBCode) is True:
        actualHexCode = "#151514"
    else:
        actualHexCode = sRGBCode   #input is srgbcode
    with Color(actualHexCode) as bg:
        with Image(width= 500, height= 200 , background= bg) as img:
                img.save(filename = "BackGround.jpg")
    return "BackGround.jpg"    
      
def addShadow(filePath, background):
    file = filePath
    with Image(filename= file) as img:
        w = img.width
        h = img.height
    with Color("#000005") as bg:
        with Image(width= (w + 5), height= (h + 5) , background= bg) as img:
            img.save(filename = "shadow.jpg")
    shadow = "shadow.jpg"    
    with Image(filename = background) as img:
        img.composite(Image(filename = shadow), gravity = "center")
        img.save(filename = "shadowBackground.jpg")   
    shadowBackground =  "shadowBackground.jpg"
    with Image(filename=shadowBackground) as img:
        img.gaussian_blur(sigma=3)
        img.save(filename="BlurredBackground.jpg")              
    return "BlurredBackground.jpg"

def finalImage(file, title):
    # print(file)
    # print (os.getcwd())
    rightSize = resizeImage(file)
    # print ("Image edited as required")
    imageColour = getsRGB(file)
    background = createBackground(imageColour)
    shadowBackground = addShadow(rightSize, background)
    with Image(filename = shadowBackground) as img:
        img.composite(Image(filename = rightSize), gravity = "center")
        img.save(filename = f"{imageFolder}/{title}.jpg")
    logging.info("Book cover image created")    
    if file != "NI.jpg":
        os.remove(file)    
    return title    

def getImageCover(ourDic):
    if ourDic.get("ISBN_13") != None:
        ISBN = ourDic["ISBN_13"]
    elif ourDic.get("ISBN_10") != None:
        ISBN = ourDic["ISBN_10"]
    return f"https://covers.openlibrary.org/b/isbn/{ISBN}-L.jpg"       #Returns a blank image if the book cover is not available

# def uploadImage(image, ourDic):
#     clientID = config("IMGUR_CLIENT_ID")
#     im = pyimgur.Imgur(clientID)
#     try:
#         uploaded_image = im.upload_image(image, title="Uploaded with PyImgur")
#         logging.info("Cover image uploaded to IMGUR and link fetched")
#         return (uploaded_image.link)
#     except Exception as e:
#         logging.exception("Imgur failed, book cover retrieved from covers.openlibrary.org")
#         return getImageCover(ourDic)  

def uploadImage(ourDic, googleDetails):
    result = getImageDatabase(ourDic)
    if result is not None:
        # print (result)
        return result[0]
    else:
        title = ourDic.get("Title", "") + ourDic.get("ISBN_10", "") + ourDic.get("ISBN_13", "")
        finalTitle = "".join(filter(lambda x:x.isalnum(), title)) 
        if finalTitle == "":
            finalTitle = uuid4()    
        file = getImage(googleDetails, finalTitle)
        finalImage(file, finalTitle)
        imageLink = insertImage(ourDic, finalTitle)
        # print (imageLink)
        return imageLink


def compareLists(Theirs):
    finalSet = set(ourList) - set(Theirs)
    return list(finalSet)

def cannotRetrieve(dicOfTitlesOrISBN):
    url = f'https://api.notion.com/v1/pages/{dicOfTitlesOrISBN["pageID"]}'
    if dicOfTitlesOrISBN["Type"] == "Title":
        payload = {
        "properties" : {
            "Title": {
                "title" : [
                    {
                    "text" : {
                        "content": dicOfTitlesOrISBN["Value"]
                            }
                        }
                    ]
                }
            }
        }
    elif dicOfTitlesOrISBN["Type"] == "ISBN_10":
        payload = {
        "properties" : {
            "ISBN_10" : {
                "rich_text" : [
                    {
                        "text" : {
                        "content" : dicOfTitlesOrISBN["Value"]
                            }
                        }
                    ]
                }
            }
        }    
    elif dicOfTitlesOrISBN["Type"] == "ISBN_13":
        payload = {
        "properties" : {
            "ISBN_13" : {
                "rich_text" : [
                    {
                        "text" : {
                        "content" : dicOfTitlesOrISBN["Value"]
                            }
                        }
                    ]
                }
           }    
        }        
    r = requests.patch(url, json=payload, headers={
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
    })
    if r.status_code == 401:
        logging.warning("Access has been revoked")
    elif r.status_code == 200:
        logging.info("Succesfully removed ';'")

   
def updateDatabase(availableFields, dicOfTitlesOrISBN, pageCoverURL, deletedProperty):
    pageID = dicOfTitlesOrISBN["pageID"]
    url = f'https://api.notion.com/v1/pages/{pageID}'
    payload = {
        "cover" : {
            "type" : "external",
            "external" : {
                "url" : pageCoverURL
            } 
        },
        "properties" : {
            "Publisher" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Publisher"].title()
                        }
                    }
                ]
            },
            "Authors" : {
                "multi_select" :  availableFields["Authors"]
            },
            "Summary" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Summary"]
                        }
                    }
                ]
            },
            "Summary_extd" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Summary_extd"]
                        }
                    }
                ]
            },
            "Category" : {
                        "multi_select" : availableFields["Category"]
            },
            "Published" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Published"]
                        }
                    }
                ]
            },    
            "ISBN_10" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["ISBN_10"]
                        }
                    }
                ]
            },            
            "ISBN_13" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["ISBN_13"]
                        }
                    }
                ]
            },
            "Pages" : {
                "number": availableFields["Pages"]
            },
            "Title": {
                "title" : [
                    {
                        "text" : {
                            "content": string.capwords(availableFields ["Title"])
                        }
                    }
                ]
            }
        }    
    }
    for item in deletedProperty:
        del payload["properties"][item]     
        # print (payload)     
    logging.info("Adding New book details to Bookshelf")         
    r = requests.patch(url, json=payload, headers={
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
    })
    if r.status_code == 401:
        logging.warning("Access has been revoked")
    elif r.status_code != 200:
        # print (r.json())
        logging.error("Could not update database with new book details, only updating title/ISBN", r.json())
        cannotRetrieve(dicOfTitlesOrISBN)
        # print (r.json())
    else:        
        logging.info("Successfully updated")

while True:
    newRecords = getDatabaseTimestamp(epoch_time)
    # checkTime = datetime.datetime.now(datetime.timezone.utc)  
    if len(newRecords) > 0:  
        (var1, var2, var3, epoch_time) = newRecords[0]
    listNewTokens = getAccessTokens(newRecords)
    # print (listNewTokens)
    listAccessTokens += listNewTokens
    for i in range (5):  #loop through Notion 5 times before looking for new access tokens
        for index in range(len(listAccessTokens)):
            listRevoked = []
            databaseID = listAccessTokens[index]["database_id"]
            # print (databaseID)
            token = listAccessTokens[index]["access_token"]
            try:
                results = requiredPageDetails(databaseID, token, checkTimeUTC)  
                # print (results) 
                if results == 401 or results == 404:
                    listAccessTokens[index]["is_revoked"] = True
                elif results is not None: 
                    newTitlesOrISBN = getNewTitlesOrISBN(results)
                    availableFields = getAllFields(results)
                    # print (availableFields)
                    missingProperties = compareLists(availableFields)
                    for item in newTitlesOrISBN:    
                        newGoogleBookDetails = getBookDetails(item)
                        if newGoogleBookDetails is not None:
                            mappedDic = mapOneDicToAnother(ourDic, newGoogleBookDetails)
                            # print (mappedDic)
                            # coverImage = getImage(newGoogleBookDetails)
                            filePath = uploadImage(mappedDic, newGoogleBookDetails)
                            # print (filePath)
                            # finalCoverImage = finalImage(coverImage)
                            # coverImageURL = uploadImage (finalCoverImage, mappedDic)
                            updateDatabase(mappedDic, item, filePath, missingProperties)               
            except Exception as e:
                logging.error(e) 
        # print (listAccessTokens)         
        listRevoked = list(filter(lambda x: x["is_revoked"], listAccessTokens))
        # print (listRevoked)
        removeFromUsers(listRevoked)
        listAccessTokens = list(filter(lambda x: x["is_revoked"] is False, listAccessTokens))
    checkTime = datetime.datetime.now(datetime.timezone.utc)           
    checkTimeUTC = checkTime.isoformat()
    # epoch_time = checkTime.timestamp()

conn.close()