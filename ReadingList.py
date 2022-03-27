from typing import Dict
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

ourList = ["Name", "Publisher", "Author", "Summary", "Category", "Published", "ISBN", "Pages"]

def GetWhatIsNeeded():
    url = f'https://api.notion.com/v1/databases/{databaseID}/query'
    r = requests.post(url, headers= {
        "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22"
    })
    result_dict = r.json()
    results = result_dict["results"]
    return (results)

# GetWhatIsNeeded()    

def lastEdited():
    url = f'https://api.notion.com/v1/databases/{databaseID}'
    r = requests.get(url, headers= {
        "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22"
    })
    result_dict = r.json()
    # print (result_dict)
    lastEdited = result_dict["last_edited_time"]
    lastEdited = datetime.datetime.strptime(result_dict["last_edited_time"], "%Y-%m-%dT%H:%M:%S.%f%z")
    return lastEdited


def retrieveTitle():
    url = f'https://api.notion.com/v1/databases/{databaseID}/query'
    r = requests.post(url, headers= {
        "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22"
    })
    result_dict = r.json()
    results = result_dict["results"]
    listOfTitles = []
    pageIDList = []
    dicOfTitleIDList = {}
    dicOfNewTitles = {}
    for item in results:
        detailsOfTitleList = item["properties"]["Name"]["title"]
        if len(detailsOfTitleList) != 0:
            for i in detailsOfTitleList:
                actualTitle = i["text"]["content"]
                listOfTitles.append(actualTitle)
        pageID = item["id"]
        pageIDList.append(pageID)
    for n in range (len(listOfTitles)):
        dicOfTitleIDList[listOfTitles[n]] = pageIDList [n]
    for key in dicOfTitleIDList.keys():
        if key[-1] == ";":
            dicOfNewTitles[key[:-1]] = dicOfTitleIDList[key]
    return (dicOfNewTitles)



def mapToNotion(result):
    cover = result["cover"]
    publisher = result["properties"]["Publisher"]["rich_text"]
    author = result["properties"]["Author"]["rich_text"]
    summary = result["properties"]["Summary"]["rich_text"]
    published = result["properties"]["Published"]["rich_text"]
    ISBN = result["properties"]["ISBN"]["rich_text"]
    pages = result["properties"]["Pages"]["number"]
    name = result["properties"]["Name"]["title"]
    category = result["properties"]["Category"]["rich_text"]
    return {"cover":cover,
    "Publisher": publisher,
    "Author": author,
    "Summary": summary,
    "Published" : published,
    "ISBN": ISBN,
    "Pages": pages,
    "Name": name,  
    "Category": category
    }



def getAllFields():
    url = f'https://api.notion.com/v1/databases/{databaseID}/query'
    r = requests.post(url, headers= {
        "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22"
    })
    result_dict = r.json()
    Title = result_dict["results"]
    if len(Title) != 0:
        dictofFields = mapToNotion(Title[0])           
        return (dictofFields)


def listOfFields(dictofFields): #Takes a dictionary
    return dictofFields.keys()    


def getDeets(title, pageID):
    url = "https://www.googleapis.com/books/v1/volumes?q=" + title 
    webPageDetails = requests.get(url)
    webPageContent = (webPageDetails.content)
    parsedContent = json.loads(webPageContent)
    # print(type(parsedContent), parsedContent, "getDeets")
    # keysList = list(parsedContent.keys())
    if parsedContent.get("totalItems", 0) > 0:
        requiredLists = parsedContent["items"]
        firstBook = requiredLists[0]
        # print (firstBook, type(firstBook), "getDeets")
        SomeInfo = firstBook.get("volumeInfo")
        # print (SomeInfo)
        AllWeNeedList = ["title", "authors", "publisher", "publishedDate", "description", "industryIdentifiers", "pageCount", "categories", "imageLinks"]
        AllWeNeed = {}
        for item in AllWeNeedList:
            if item in SomeInfo.keys():
                AllWeNeed[item] = SomeInfo[item]
            else:
                continue    
        return (AllWeNeed)   
    else:
        cannotRetrieve(title, pageID)    
        return None
                

# def image(AllWeNeed):
#     imageLink = AllWeNeed["imageLinks"]["thumbnail"] 
#     # imageLink = "http://books.google.com/books/content?id=bVyCd7da8OcC&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api"
#     title = AllWeNeed["title"]
#     r = requests.get(imageLink)
#     with open(title, "wb") as f:
#         f.write(r.content)    

#     background = "/Users/sravanthis/Documents/MyProjects/BackGround.jpg"
#     imageTitle = f"/Users/sravanthis/Documents/MyProjects/{title}"

#     with Image(filename = background) as img:
#         img.composite(Image(filename = imageTitle), gravity = "center")
#         img.save(filename = "result.jpg")

#     return "/Users/sravanthis/Documents/MyProjects/result.jpg"


def getImage(AllWeNeed):
    # print (AllWeNeed, "allWeNeed")
    if AllWeNeed.get("imageLinks") != None:
        imageLink = AllWeNeed["imageLinks"]["thumbnail"] 
    # imageLink = "http://books.google.com/books/content?id=bVyCd7da8OcC&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api"
        title = AllWeNeed["title"]
    # PathTitleDict = {}
        r = requests.get(imageLink)
        with open(title, "wb") as f:       
            f.write(r.content)         
        return (f"{title}")  
    else: 
        return "/Users/sravanthis/Documents/MyProjects/NoImage.jpg"


def resizeImage(title):
    with Image(filename=title) as img:
        img.resize(height=180)
        img.save(filename="sizedImaged.jpg") 
    return ("sizedImaged.jpg")  

def getHex(title): 
    fileNaam = title   #input is filepath
    with Image(filename= fileNaam) as img: 
        img.quantize(5, "srgb", 0, True, False) 
        hist = img.histogram
        sortedDict = sorted(hist.items(), key = lambda x: x[1], reverse = True)
        # for i in sorted(hist.items(), key = lambda x: x[1], reverse = True):
        highestValue = (sortedDict[0])
        srgbHighestValue = highestValue[0]
        stringHighestValue = str(srgbHighestValue)
    #     dontWantinString = "srgb%()"
    #     finalString = ""
    #     for letter in stringHighestValue:
    #         if letter not in dontWantinString:
    #             finalString += letter
    #     RGBvalues = finalString.split(",")
    #     RGBValuesList = list(map(float, RGBvalues))
    # return (RGBValuesList)   
    return (stringHighestValue)   
     
              
def createBackground(hexCode):  #input is srgbcode
    with Color(hexCode) as bg:
        with Image(width= 500, height= 200 , background= bg) as img:
            img.save(filename = "BackGround.jpg")
        # with Image(filename="BackGround.jpg"):
            # img.gaussian_blur(sigma = 3)    
    return "BackGround.jpg"    

# def changeRGB(listRGB):
#     listofRGB = listRGB
#     r = listofRGB[0]/100
#     g = listofRGB[1]/100
#     b = listofRGB[2]/100
#     red = r*255 + ((255 - (r*255))/3)
#     green = g*255 + ((255 - (g*255))/3)
#     blue = b*255 + ((255 - (b*255))/3)
#     stringsRGB = "srgb(" + str((red/255)*100) + "%," + str((green/255)*100) + "%," + str((blue/255)*100) + "%)"
#     return (stringsRGB)
       
def addShadow(filePath, background):
    fileNaam = filePath
    with Image(filename= fileNaam) as img:
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
    
    return "/Users/sravanthis/Documents/MyProjects/BlurredBackground.jpg"
# def Blur(file):
#     with Image(filename=file) as img:
#         img.gaussian_blur(sigma = 3)
#         img.save(filename="BackGroundBlurred.jpg")   
#     return "/Users/sravanthis/Documents/MyProjects/BackGroundBlurred.jpg"    

# def createImageBackground(filePath):
#     with Image(filename = filePath) as img:
#         img.resize(500, 200)  
#         img.gaussian_blur(sigma=20)
#         img.save(filename="ResizedImage.jpg")
#     return "/Users/sravanthis/Documents/MyProjects/ResizedImage.jpg"   

def finalImage(image):
    fileNaam = image
    rightSize = resizeImage(fileNaam)
    # shadowedImage = addShadow(fileNaam)
    imageColour = getHex(fileNaam)
    background = createBackground(imageColour)
    shadowBackground = addShadow(rightSize, background)
    # blurredBackground = Blur(background)
    with Image(filename = shadowBackground) as img:
        img.composite(Image(filename = rightSize), gravity = "center")
        img.save(filename = "result.jpg")
    return "result.jpg"    


# finalImage("/Users/sravanthis/Documents/MyProjects/AtlasShrugged.jpg")
# Blur("/Users/sravanthis/Documents/MyProjects/AtlasShrugged.jpg")

def uploadImage(image):
    clientid = clientID
    path = image
    im = pyimgur.Imgur(clientid)
    uploaded_image = im.upload_image(path, title="Uploaded with PyImgur")
    return (uploaded_image.link)

def cannotRetrieve(title, pageID):
    url = f'https://api.notion.com/v1/pages/{pageID}'
    payload = {
        "properties" : {
            "Name": {
                "title" : [
                    {
                        "text" : {
                            "content": title
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

def compareLists(Ours, Theirs):
    finalSet = set(Ours) - set(Theirs)
    return list(finalSet)


def mapOneDicToAnother(availableFields, GoogleBookInfo, pageID):
    try:
        # availableFields["cover"] = GoogleBookInfo["imageLinks"]
        # print ("mapOneDicToAnother")
        availableFields["cover"] = GoogleBookInfo.get("imageLinks", "")
        availableFields["Publisher"] = GoogleBookInfo.get("publisher", "")
        if GoogleBookInfo.get("authors") != None:
            author = ""
            if len(GoogleBookInfo["authors"]) > 1:
                for element in GoogleBookInfo["authors"]:  
                    author = author + element + ", "
            else:
                for element in GoogleBookInfo["authors"]:
                    author = author + element        
        availableFields["Author"] = author    
        availableFields["Summary"] = GoogleBookInfo.get("description", "")
        availableFields["Published"] = GoogleBookInfo.get("publishedDate", "")
        if GoogleBookInfo.get("industryIdentifiers") != None:
            ISBNNum = ""
            for element in GoogleBookInfo["industryIdentifiers"]:
                ISBNNum = ISBNNum + element["type"] + element["identifier"] + ""
        else:
            ISBNNum = ""        
        availableFields["ISBN"] = ISBNNum
        availableFields["Pages"] = GoogleBookInfo.get("pageCount", 0)
        availableFields["Name"] = GoogleBookInfo.get("title", "")
        availableFields["TitleDiff"] = GoogleBookInfo.get("title", "")
        if GoogleBookInfo.get("categories") != None:
            category = ""
            for element in GoogleBookInfo["categories"]:
                category = category + element + ", "
        else:
            category = ""        
        availableFields["Category"] = category
        return availableFields
    except KeyError:
        cannotRetrieve(GoogleBookInfo["title"], pageID)
    except Exception as e:
        cannotRetrieve(GoogleBookInfo["title"], pageID)        

def updateDatabase(availableFields, pageID, pageCoverURL, deletedProperty):
    url = f'https://api.notion.com/v1/pages/{pageID}'
    payload = {
        "cover" : {
            "type" : "external",
            "external" : {
                "url" : pageCoverURL
            } 
        },
        # "icon" : {
        #     "type" : "external",
        #     "external" : {
        #         "url" : pageCoverURL
        #     }
        # },
        "properties" : {
            "Publisher" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Publisher"]
                        }
                    }
                ]
            },
            "Author" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Author"]
                        }
                    }
                ]
            },
            "Summary" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Summary"]
                        }
                    }
                ]
            },
            "Category" : {
               "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Category"]
                        }
                    }
                ]
            },
            "Published" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["Published"]
                        }
                    }
                ]
            },    
            "ISBN" : {
                "rich_text" : [
                    {"text" : {
                        "content" : availableFields["ISBN"]
                        }
                    }
                ]
            },
            "Pages" : {
                "number": availableFields["Pages"]
            },
            "Name": {
                "title" : [
                    {
                        "text" : {
                            "content": availableFields ["Name"]
                        }
                    }
                ]
            }
            # "TitleDiff": {
            #     "rich_text" : [
            #         {
            #             "equation" : {
            #                 "expression" : "\\color{e7d2bf}\\large\\text" + "{" + f"{FormattedTitle}" + "}"
            #             }, 
            #         }     
            #     ]
            # }
        }    
    }
    for item in deletedProperty:
        del payload["properties"][item]               
    r = requests.patch(url, json=payload, headers={
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json"
    })
    # if r.status() == 200
    print (r.json())



while True:
    try:
        timeEdited = lastEdited()
        if timeEdited > checkTime:
            availableFields = getAllFields()
            newTitle = retrieveTitle()
            missingProperties = compareLists(ourList, listOfFields(availableFields))
            print(missingProperties)
            for item in newTitle:    
                newtitleDeets = getDeets (item, newTitle[item])
                if newtitleDeets is not None:
                    mappedDic = mapOneDicToAnother(availableFields, newtitleDeets, newTitle[item] )
                    coverImage = getImage(newtitleDeets)
                    finalCoverImage = finalImage(coverImage)
                    coverImageURL = uploadImage (finalCoverImage)
                    updateDatabase(mappedDic, newTitle[item], coverImageURL, missingProperties)
    except Exception as e:
        print(e)




        
    
        

















