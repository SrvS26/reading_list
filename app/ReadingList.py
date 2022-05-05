import requests
import json
import datetime
import pyimgur
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

databaseFile = config("databaseFilePath")

logging.debug(f"Connecting to database '{databaseFile}'")
conn = sqlite3.connect(databaseFile)
logging.debug(f"Connected to database '{databaseFile}'")

def getDatabaseTimestamp(databaseCheckedTime):
    cursor = conn.cursor()
    fetchSpecificDeets = f"""SELECT access_token, database_id, user_id from USERS where time_added > {databaseCheckedTime}"""
    logging.info(f"Attempting to filter and fetch data added after {databaseCheckedTime}")
    cursor.execute(fetchSpecificDeets)
    records = cursor.fetchall()
    numberRecords = len(records)
    logging.info(f"Fetched {numberRecords} rows of data added after {databaseCheckedTime}")
    cursor.close()
    return records

def getAccessTokens(records):
    listofTokens = []
    if len(records) != 0:
        numRows = 0
        for row in records:
            dicTokens = {}
            access_token = row[0]
            database_id = row[1]
            user_id = row[2]
            dicTokens["access_token"] = access_token
            dicTokens ["database_id"] = database_id
            dicTokens ["user_id"] = user_id
            listofTokens.append(dicTokens)
            numRows += 1
        logging.info(f"Processed {numRows} number of rows of data")            
        return listofTokens
    else:
        return listofTokens 

def requiredPageDetails(databaseID, token, lastCheckedTime): #Filter can be modified to remove last checked time as it might not really be required
    url = f"https://api.notion.com/v1/databases/{databaseID}/query"
    payload = "{\"filter\": {\"and\": [{\"timestamp\": \"last_edited_time\",\"last_edited_time\": {  \"on_or_after\": \""+lastCheckedTime+"\"} },{\"or\": [{\"property\": \"Title\",\"rich_text\": {\"ends_with\": \";\"}},{\"property\": \"ISBN_10\",\"rich_text\": {\"ends_with\": \";\"}},{\"property\": \"ISBN_13\",\"rich_text\": {\"ends_with\": \";\"}}]}]}}"
    headers = {
        'Content-Type': "application/json",
        'Notion-Version': "2022-02-22",
        'Authorization': f"Bearer {token}"
        }
    logging.info("Fetching new details from Notion")    
    try:
        response = requests.request("POST", url, data=payload, headers=headers)
        logging.info("Fetched new details from Notion")
    except Exception as e:
        logging.exception("Failed to fetch new details from Notion")    
    parsed_response = response.json()
    results = parsed_response["results"]   
    return results

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
        logging.info("New titles/ISBN fetched from Notion")                                          
    else:
        logging.info("No changes in Notion database/No new titles/ISBN found")      
    return listOfAllTitlesOrISBN

def getAllFields(results):
    allAvailableList = []
    if len(results) > 0:                                                         
        onePagePropertyDetails = results[0]                     
        requiredPropertiesGeneral = onePagePropertyDetails["properties"]    
        for item in requiredPropertiesGeneral.keys():                       
            if item in ourList:                                             
                allAvailableList.append(item)   
        logging.info("All available fields in the Notion database fetched") 
    else:
        logging.info("There are no new additions or the notion database "Bookshelf" is empty")                                       
    return allAvailableList

def getBookDetails(dicOfTitlesOrISBN):
    if dicOfTitlesOrISBN.get("Type") == "Title":
        url = "https://www.googleapis.com/books/v1/volumes?q=" + dicOfTitlesOrISBN["Value"]
    elif dicOfTitlesOrISBN.get("Type") == "ISBN_10" or dicOfTitlesOrISBN.get("Type") == "ISBN_13":
        url = "https://www.googleapis.com/books/v1/volumes?q=isbn:" + dicOfTitlesOrISBN["Value"]     
    webPageDetails = requests.get(url)     
    logging.info(f"Book details fetched from {url}")                                 
    webPageContent = (webPageDetails.content)
    parsedContent = json.loads(webPageContent)                              
    if parsedContent.get("totalItems", 0) > 0:
        listOfBookResults = parsedContent["items"]
        firstBookResult = listOfBookResults[0]                              
        bookDetails = firstBookResult.get("volumeInfo")
        requiredBookDetails = ["title", "authors", "publisher", "publishedDate", "description", "industryIdentifiers", "pageCount", "categories", "imageLinks"]
        dicOfRequiredBookDetails = {}
        for item in requiredBookDetails:                                    
            if item in bookDetails.keys():                                   
                dicOfRequiredBookDetails[item] = bookDetails[item]
            else:
                continue    
        return (dicOfRequiredBookDetails)                                      
    else:
        logging.info(f"No results were found for {url}, only updating title/ISBN")
        cannotRetrieve(dicOfTitlesOrISBN)    
        return None

def mapOneDicToAnother(ourDic, GoogleBookInfo):
    ourDic["Publisher"] = GoogleBookInfo.get("publisher", "")
    listauthors = []
    if GoogleBookInfo.get("authors") != None and len(GoogleBookInfo["authors"]) > 0:
        for item in GoogleBookInfo["authors"]:
            authors = {}
            authors["name"] = item
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
    alphabets = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    if GoogleBookInfo.get("categories") != None and len(GoogleBookInfo["categories"]) > 0:   
        for item in GoogleBookInfo["categories"]: 
            word = ""
            for i in item:
                if i in alphabets:
                    word += i
            category = {}
            category["name"] = word
            listcategory.append(category)
    ourDic["Category"] = listcategory
    logging.info("Details of book assigned to the appropriate fields")
    return ourDic

def getImage(AllWeNeed):
    title = AllWeNeed["title"]
    if AllWeNeed.get("imageLinks") != None:
        imageLink = AllWeNeed["imageLinks"]["thumbnail"] 
        r = requests.get(imageLink)
        with open(title, "wb") as f:       
            f.write(r.content)         
        return (f"{title}")  
    else:
        logging.info(f"Book {title} has no image") 
        return "NoImage.jpg"

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

def finalImage(file):
    rightSize = resizeImage(file)
    imageColour = getsRGB(file)
    background = createBackground(imageColour)
    shadowBackground = addShadow(rightSize, background)
    with Image(filename = shadowBackground) as img:
        img.composite(Image(filename = rightSize), gravity = "center")
        img.save(filename = "result.jpg")
    os.remove(file)    
    return "result.jpg"    

def getImageCover(ourDic):
    if ourDic.get("ISBN_13") != None:
        ISBN = ourDic["ISBN_13"]
    elif ourDic.get("ISBN_10") != None:
        ISBN = ourDic["ISBN_10"]
    return f"https://covers.openlibrary.org/b/isbn/{ISBN}-L.jpg"       #Returns a blank image if the book cover is not available

def uploadImage(image, ourDic):
    clientID = config("IMGURID")
    im = pyimgur.Imgur(clientID)
    try:
        uploaded_image = im.upload_image(image, title="Uploaded with PyImgur")
        return (uploaded_image.link)
    except Exception as e:
        logging.exception("Imgur failed, photo retrieved from covers.openlibrary.org")
        return getImageCover(ourDic)  

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
                        "content" : availableFields["Publisher"]
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
                            "content": availableFields ["Title"]
                        }
                    }
                ]
            }
        }    
    }
    for item in deletedProperty:
        del payload["properties"][item]     
        # print (payload)     
    logging.info("Adding New book details to Notion database")         
    r = requests.patch(url, json=payload, headers={
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
    })
    if r.status_code != 200:
        # print (r.json())
        logging.info("Could not update database with new book details, only updating title/ISBN")
        cannotRetrieve(dicOfTitlesOrISBN)
    # else:        
        # print (r.json())


while True:
    newRecords = getDatabaseTimestamp(epoch_time)
    listNewTokens = getAccessTokens(newRecords)
    listAccessTokens += listNewTokens
    for i in range (5):  #loop through Notion 5 times before looking for new access tokens
        for item in listAccessTokens:
            databaseID = item["database_id"]
            token = item["access_token"]
            try:
                results = requiredPageDetails(databaseID, token, checkTimeUTC)    
                newTitlesOrISBN = getNewTitlesOrISBN(results)
                availableFields = getAllFields(results)
                missingProperties = compareLists(availableFields)
                for item in newTitlesOrISBN:    
                    newGoogleBookDetails = getBookDetails(item)
                    if newGoogleBookDetails is not None:
                        mappedDic = mapOneDicToAnother(ourDic, newGoogleBookDetails)
                        coverImage = getImage(newGoogleBookDetails)
                        finalCoverImage = finalImage(coverImage)
                        coverImageURL = uploadImage (finalCoverImage, mappedDic)
                        updateDatabase(mappedDic, item, coverImageURL, missingProperties)   
            except Exception as e:
                print(e)    
    checkTime = datetime.datetime.now(datetime.timezone.utc)           
    checkTimeUTC = checkTime.isoformat()
    epoch_time = checkTime.timestamp()

conn.close()