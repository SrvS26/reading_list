from wand.color import Color
from wand.image import Image, GRAVITY_TYPES, COLORSPACE_TYPES
from decouple import config
import os
from uuid import uuid4
# import custom_logger
import requests

databaseFile = config("DATABASE_FILE_PATH")
url = config("BASE_URL")
imageFolder = config("IMAGE_PATH")

# logging, listener = custom_logger.get_logger("image")


def getImageDatabase(conn, ourDic):
    cursor = conn.cursor()
    image = f"""SELECT image_path from IMAGES WHERE ISBN_10 = '{ourDic.get("ISBN_10")}' OR ISBN_13 = '{ourDic.get("ISBN_13")}'"""
    cursor.execute(image)
    imagePath = cursor.fetchone()
    conn.commit()
    return imagePath


def insertImage(conn, ourDic, finaltitle):
    cursor = conn.cursor()
    imageName = url + "/" + finaltitle + ".jpg"
    if (ourDic.get("ISBN_10") is None and ourDic.get("ISBN_13") is None) or (
        ourDic.get("ISBN_10") == "" or ourDic.get("ISBN_13") == ""
    ):
        return imageName
    else:
        rows = f"""INSERT INTO IMAGES (ISBN_10, ISBN_13, image_path) VALUES ('{ourDic.get("ISBN_10")}', '{ourDic.get("ISBN_13")}', "{imageName}");"""
        cursor.execute(rows)
        conn.commit()
        return imageName


async def getImage(session, ourDic, finalTitle):
    title = ourDic["Title"]
    imageLink = ourDic["Image_url"]
    if imageLink != "":
        r = await session.get(imageLink)
        x = await r.read()
        # logging.info(f"Querying for book {finalTitle} cover")
        with open(finalTitle, "wb") as f:
            f.write(x)
        return finalTitle
    else:
        # logging.info(f"Book {title} has no image")
        return "NI.jpg"

def get_Image(ourDic, finalTitle):
    title = ourDic["Title"]
    imageLink = ourDic["Image_url"]
    if imageLink != "":
        r = requests.get(imageLink)
        # x = r.read()
        # logging.info(f"Querying for book {finalTitle} cover")
        with open(finalTitle, "wb") as f:
            f.write(r.content)
        return finalTitle
    else:
        # logging.info(f"Book {title} has no image")
        return "NI.jpg"

def resize_goodreads_image(title):
    with Image(filename=title) as img:
        img.resize(height=180, width=135)
        img.save(filename="resizedImaged.jpg")
    return "resizedImaged.jpg"

def resizeImage(title):
    with Image(filename=title) as img:
        img.resize(height=180)
        img.save(filename="resizedImaged.jpg")
    return "resizedImaged.jpg"


def getsRGB(title):
    file = title
    with Image(filename=file) as img:
        img.quantize(5, "srgb", 0, True, False)
        hist = img.histogram
        sortedDict = sorted(hist.items(), key=lambda x: x[1], reverse=True)
        highestValue = sortedDict[0]
        srgbHighestValue = highestValue[0]
        stringHighestValue = str(srgbHighestValue)
    return stringHighestValue


def alterIfBlack(sRGBString):
    dontWantinString = "srgb%()"
    finalString = ""
    for letter in sRGBString:
        if letter not in dontWantinString:
            finalString += letter
    RGBvalues = finalString.split(",")
    try:
        RGBValuesList = list(map(float, RGBvalues))
        r = (RGBValuesList[0] / 100) * 255
        g = (RGBValuesList[1] / 100) * 255
        b = (RGBValuesList[2] / 100) * 255
        return r <= 30 and g <= 30 and b <= 30
    except ValueError:
        return True


def createBackground(sRGBCode):
    if alterIfBlack(sRGBCode) is True:
        actualHexCode = "#151514"
    else:
        actualHexCode = sRGBCode  # input is srgbcode
    with Color(actualHexCode) as bg:
        with Image(width=500, height=200, background=bg) as img:
            img.save(filename="BackGround.jpg")
    return "BackGround.jpg"


def addShadow(filePath, background):
    file = filePath
    with Image(filename=file) as img:
        w = img.width
        h = img.height
    with Color("#000005") as bg:
        with Image(width=(w + 5), height=(h + 5), background=bg) as img:
            img.save(filename="shadow.jpg")
    shadow = "shadow.jpg"
    with Image(filename=background) as img:
        img.composite(Image(filename=shadow), gravity="center")
        img.save(filename="shadowBackground.jpg")
    shadowBackground = "shadowBackground.jpg"
    with Image(filename=shadowBackground) as img:
        img.gaussian_blur(sigma=3)
        img.save(filename="BlurredBackground.jpg")
    return "BlurredBackground.jpg"


def finalImage(file, finaltitle):
    rightSize = resizeImage(file)
    imageColour = getsRGB(file)
    background = createBackground(imageColour)
    shadowBackground = addShadow(rightSize, background)
    with Image(filename=shadowBackground) as img:
        img.composite(Image(filename=rightSize), gravity="center")
        img.save(filename=f"{imageFolder}/{finaltitle}.jpg")
    # logging.info("Book cover image created")
    if file != "NI.jpg":
        os.remove(file)
    return finaltitle


async def uploadImage(session, conn, ourDic):
    result = getImageDatabase(conn, ourDic)
    if result is not None:
        return result[0]
    else:
        title = (
            ourDic.get("Title", "")
            + ourDic.get("ISBN_10", "")
            + ourDic.get("ISBN_13", "")
        )
        finalTitle = "".join(filter(lambda x: x.isalnum(), title))
        if finalTitle == "":
            finalTitle = uuid4()
        file = await getImage(session, ourDic, finalTitle)
        finalImage(file, finalTitle)
        image_link = insertImage(conn, ourDic, finalTitle)
        return image_link

def upload_image(conn, ourDic):
    result = getImageDatabase(conn, ourDic)
    if result is not None:
        return result[0]
    else:
        title = (
            ourDic.get("Title", "")
            + ourDic.get("ISBN_10", "")
            + ourDic.get("ISBN_13", "")
        )
        finalTitle = "".join(filter(lambda x: x.isalnum(), title))
        if finalTitle == "":
            finalTitle = str(uuid4())
        file = get_Image(ourDic, finalTitle)
        rightSize = resize_goodreads_image(file)
        imageColour = getsRGB(file)
        background = createBackground(imageColour)
        shadowBackground = addShadow(rightSize, background)
        with Image(filename=shadowBackground) as img:
            img.composite(Image(filename=rightSize), gravity="center")
            img.save(filename=f"{imageFolder}/{finalTitle}.jpg")
    # logging.info("Book cover image created")
        if file != "NI.jpg":
            os.remove(file)
        image_link = insertImage(conn, ourDic, finalTitle)
        return image_link