import requests
import json
import datetime
import pyimgur
from wand.color import Color
from wand.image import Image, GRAVITY_TYPES, COLORSPACE_TYPES

token = "secret_hei5HWtvc97doM7BWwhJBzDppzm9nN9dkaOHevQol2q"

databaseID = "2a4fdc20740b4f41a87463da37806ece"

checkTime = datetime.datetime(2022, 2, 1, 0, 0, 0, 0, tzinfo=datetime.timezone.utc)

clientID = "185188df22248e6"

ourList = ["Title", "Publisher", "Authors", "Summary", "Category", "Published", "ISBN_10", "Pages", "ISBN_13", "Summary_extd"]

ourDic = {"Title": "", "Publisher": "", "Authors": "", "Summary": "", "Summary_extd": "", "Category":"", "Published": "", "ISBN_10": "", "Pages": None, "ISBN_13":""}



#Returns last edited time

def getlastEdited():  
    url = f'https://api.notion.com/v1/databases/{databaseID}'
    r = requests.get(url, headers= {
        "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22"
    })
    result_dict = r.json()
    lastEdited = result_dict["last_edited_time"]
    lastEdited = datetime.datetime.strptime(result_dict["last_edited_time"], "%Y-%m-%dT%H:%M:%S.%f%z")
    return lastEdited

# lastEditedTime = getlastEdited() 

#Returns a list of dictionaries, each dictionary contains details of one page in the database 

def getPagePropertyDetails(): 
    url = f'https://api.notion.com/v1/databases/{databaseID}/query'
    r = requests.post(url, headers= {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-02-22"
    })
    result_dict = r.json()
    results = result_dict["results"]
    return (results)

# print (getPagePropertyDetails())
# results = getPagePropertyDetails()
# def main():
# databaseId = ""
# token = ""
# dbResults = fetchDatabaseProperties(databaseId, token) -> DatabasePropertyResults
# toBeFilled = 

#Returns a dictionary of title name as key (string) and page ID as value (string)
# () -> {value: title/isbn10, pageId: pageId, type: "title"/"ISBN"}
# dict[title]
# [{title: fountainhead, pageId:1},{title:atlas shrugged,pageId: 2},{pageId:3, title:harry potter}]
# dict["title"] == "FountainHead": dict["pageId"]

# for i in listOfTitles:
#     if i["title"] == "Fountainhead":
#         return i["pageId"]

def getNewTitlesOrISBN():   
    listOfAllTitlesOrISBN = []
    results = getPagePropertyDetails()
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
    return listOfAllTitlesOrISBN
                                                                                
# getNewTitlesOrISBN(results)
# returns all the fields available for filling in the database

def getAllFields():
    allAvailableList = []
    pagePropertyDetails = getPagePropertyDetails()
    if len(pagePropertyDetails) > 0:                                        #Ensures that the database is not empty                  
        onePagePropertyDetails = pagePropertyDetails[0]                     #Chooses the first dictionary of page details
        requiredPropertiesGeneral = onePagePropertyDetails["properties"]    
        for item in requiredPropertiesGeneral.keys():                       
            if item in ourList:                                             #Compares with outList to decide which to keep and which to disregard
                allAvailableList.append(item)                               #Creates a final list of available fields
    return allAvailableList



#takes title name and pageID
#returns a dictionary with details of the book

def getBookDetails(dicOfTitlesOrISBN):
    if dicOfTitlesOrISBN.get("Type") == "Title":
        url = "https://www.googleapis.com/books/v1/volumes?q=" + dicOfTitlesOrISBN["Value"]
    elif dicOfTitlesOrISBN.get("Type") == "ISBN_10" or dicOfTitlesOrISBN.get("Type") == "ISBN_13":
        url = "https://www.googleapis.com/books/v1/volumes?q=isbn:" + dicOfTitlesOrISBN["Value"]     
    webPageDetails = requests.get(url)                                      
    webPageContent = (webPageDetails.content)
    parsedContent = json.loads(webPageContent)                              
    if parsedContent.get("totalItems", 0) > 0:
        listOfBookResults = parsedContent["items"]                          #List of all book results
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
    return ourDic




#takes dictionary of book details
#returns downloaded image or a placeholder image if image is not available

def getImage(AllWeNeed):
    if AllWeNeed.get("imageLinks") != None:
        imageLink = AllWeNeed["imageLinks"]["thumbnail"] 
        title = AllWeNeed["title"]
        r = requests.get(imageLink)
        with open(title, "wb") as f:       
            f.write(r.content)         
        return (f"{title}")  
    else: 
        return "NoImage.jpg"



def resizeImage(title):
    with Image(filename=title) as img:
        img.resize(height=180)
        img.save(filename="resizedImaged.jpg") 
    return ("resizedImaged.jpg")  




def getsRGB(title): 
    file = title   #input is filepath
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



def finalImage(image):
    file = image
    rightSize = resizeImage(file)
    imageColour = getsRGB(file)
    background = createBackground(imageColour)
    shadowBackground = addShadow(rightSize, background)
    with Image(filename = shadowBackground) as img:
        img.composite(Image(filename = rightSize), gravity = "center")
        img.save(filename = "result.jpg")
    return "result.jpg"    


def getImageCover(ourDic):
    if ourDic.get("ISBN_13") != None:
        ISBN = ourDic["ISBN_13"]
    elif ourDic.get("ISBN_10") != None:
        ISBN = ourDic["ISBN_10"]
    return f"https://covers.openlibrary.org/b/isbn/{ISBN}-L.jpg"        



def uploadImage(image, ourDic):
    clientid = clientID
    path = image
    im = pyimgur.Imgur(clientid)
    try:
        uploaded_image = im.upload_image(path, title="Uploaded with PyImgur")
        return (uploaded_image.link)
    except Exception as e:
        # return "https://cdn.99images.com/photos/wallpapers/creative-graphics/black%20android-iphone-desktop-hd-backgrounds-wallpapers-1080p-4k-j7bml.jpg"
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
    r = requests.patch(url, json=payload, headers={
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
    })
    if r.status_code != 200:
        print (r.json())
        cannotRetrieve(dicOfTitlesOrISBN)
    else:        
        print (r.json())




while True:
    try:
        timeEdited = getlastEdited()
        if timeEdited > checkTime:
            newTitlesOrISBN = getNewTitlesOrISBN()
            availableFields = getAllFields()
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

 