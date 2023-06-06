from wand.color import Color
from wand.image import Image, GRAVITY_TYPES, COLORSPACE_TYPES
from decouple import config
import os
from uuid import uuid4
from app import custom_logger
import requests

database_file_path = config("DATABASE_FILE_PATH")
image_url = config("BASE_IMAGE_URL")
image_file_path = config("IMAGE_PATH")

logging, listener = custom_logger.get_logger("image")


def get_image_path(conn, book_details: dict) -> str:
    """
    Takes dict with isbn 10/13 to find and return respective book image path in the database.
    :param user_info: {}
    :returns: str
    """
    cursor = conn.cursor()
    image = f"""SELECT image_path from IMAGES WHERE ISBN_10 = '{book_details.get("ISBN_10")}' OR ISBN_13 = '{book_details.get("ISBN_13")}'"""
    cursor.execute(image)
    image_path = cursor.fetchone()
    conn.commit()
    return image_path


def insert_image_path(conn, book_details: dict, image_name: str) -> str:
    """
    Takes image name and generates an file path to the image, updates the database of books with ISBN 10, 13 and the path.
    """
    cursor = conn.cursor()
    image_path = image_url + "/" + image_name + ".jpg"
    if (book_details.get("ISBN_10") is None and book_details.get("ISBN_13") is None) or (
        book_details.get("ISBN_10") == "" or book_details.get("ISBN_13") == "" #Books that have no ISBN 10/13 were being updated with wrong images
    ):
        return image_path
    else:
        rows = f"""INSERT INTO IMAGES (ISBN_10, ISBN_13, image_path) VALUES ('{book_details.get("ISBN_10")}', '{book_details.get("ISBN_13")}', "{image_path}");"""
        cursor.execute(rows)
        conn.commit()
        return image_path


async def get_book_image(session, book_details: dict, image_name: str) -> str:
    """
    Gets the book image and writes to a file, returns file name.
    """
    title = book_details["Title"]
    image_link = book_details["Image_url"]
    if image_link != "":
        r = await session.get(image_link)
        x = await r.read()
        logging.info(f"Querying for book {image_name} cover")
        with open(image_name, "wb") as f:
            f.write(x)
        return image_name
    else:
        logging.info(f"Book {title} has no image")
        return "NI.jpg"

def get_book_image(book_details: dict, image_name: str) -> str: #Same function, for the goodreads experiment
    """
    Gets the book image and writes to a file, returns file name.
    """
    title = book_details["Title"]
    image_link = book_details["Image_url"]
    if image_link != "":
        r = requests.get(image_link)
        logging.info(f"Querying for book {image_name} cover")
        with open(image_name, "wb") as f:
            f.write(r.content)
        return image_name
    else:
        logging.info(f"Book {title} has no image")
        return "NI.jpg"

def resize_goodreads_image(image_name: str) -> str:
    """
    Resizes goodreads image to a uniform size to allow further processing.
    """
    with Image(filename=image_name) as img:
        img.resize(height=180, width=135)
        img.save(filename="resized_image.jpg")
    return "resized_image.jpg"

def resize_image(image_name: str) -> str:
    """
    Resizes images to a uniform size to allow further processing.
    """
    with Image(filename=image_name) as img:
        img.resize(height=180)
        img.save(filename="resized_image.jpg")
    return "resized_image.jpg"


def get_background_colour(image_name: str) -> str:
    """
    Returns the predominant colour in the book cover image as srgb.
    """
    with Image(filename=image_name) as img:
        img.quantize(5, "srgb", 0, True, False)
        hist = img.histogram
        sort_hist = sorted(hist.items(), key=lambda x: x[1], reverse=True)
        highest_srgb = str(sort_hist[0][0])
    return highest_srgb


def is_background_dark(srgb: str) -> bool:
    """
    Checks if generated background srgb value is too dark for the Notion workspace.
    """
    remove_characters = "srgb%()"
    srgb_value = ""
    for letter in srgb:
        if letter not in remove_characters:
            srgb_value += letter
    formatted_srgb = srgb_value.split(",")
    try:
        RGBValuesList = list(map(float, formatted_srgb))
        r = (RGBValuesList[0] / 100) * 255
        g = (RGBValuesList[1] / 100) * 255
        b = (RGBValuesList[2] / 100) * 255
        return r <= 30 and g <= 30 and b <= 30
    except ValueError:
        return True


def generate_background(srgb: str) -> str:
    """
    Generates an image of custom size and srgb for book cover background.
    """
    if is_background_dark(srgb) is True:
        hex_code = "#151514"
    else:
        hex_code = srgb  # input is srgbcode
    with Color(hex_code) as bg:
        with Image(width=500, height=200, background=bg) as img:
            img.save(filename="background.jpg")
    return "background.jpg"


def add_shadow(image_name: str, background: str) -> str:
    """
    Adds a shadow for the book cover on the background.
    """
    with Image(filename=image_name) as img:
        w = img.width
        h = img.height
    with Color("#000005") as bg:
        with Image(width=(w + 5), height=(h + 5), background=bg) as img:
            img.save(filename="shadow.jpg")
    with Image(filename=background) as img:
        img.composite(Image(filename="shadow.jpg"), gravity="center")
        img.save(filename="shadow_on_background.jpg")
    with Image(filename="shadow_on_background.jpg") as img:
        img.gaussian_blur(sigma=3)
        img.save(filename="blurred_on_background.jpg")
    return "blurred_on_background.jpg"

def notion_cover_image(resized_book_cover: str, shadow_on_background: str, notion_cover_name: str) -> str:
    with Image(filename=shadow_on_background) as img:
        img.composite(Image(filename=resized_book_cover), gravity="center")
        img.save(filename=f"{image_file_path}/{notion_cover_name}.jpg")
    logging.info("Book cover image created")
    if resized_book_cover != "NI.jpg":
        os.remove(resized_book_cover)
    return


def generate_unique_name(book_details: dict) -> str:
    name = (
            book_details.get("Title", "")
            + book_details.get("ISBN_10", "")
            + book_details.get("ISBN_13", "")
        )
    unique_name = "".join(filter(lambda x: x.isalnum(), name))
    if unique_name == "":
        unique_name = str(uuid4())
    return unique_name    


def generate_cover_image (image_name: str, final_image_name: str) -> str:
    resized_image = resize_image(image_name)
    background_colour = get_background_colour(image_name)
    background = generate_background(background_colour) 
    shadow_on_background = add_shadow(resized_image, background)
    with Image(filename=shadow_on_background) as img:
        img.composite(Image(filename=resized_image), gravity="center")
        img.save(filename=f"{image_file_path}/{final_image_name}.jpg")
    logging.info("Book cover image created")
    if image_name != "NI.jpg":
        os.remove(image_name)
    return final_image_name


async def uploadImage(session, conn, ourDic):
    result = get_image_path(conn, ourDic)
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
        file = await get_book_image(session, ourDic, finalTitle)
        processed_image(file, finalTitle)
        image_link = insert_image_path(conn, ourDic, finalTitle)
        return image_link

def upload_image(conn, ourDic):
    result = get_image_path(conn, ourDic)
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
        file = get_book_image(ourDic, finalTitle)
        rightSize = resize_goodreads_image(file)
        imageColour = get_background_colour(file)
        background = generate_background(imageColour)
        shadowBackground = add_shadow(rightSize, background)
        with Image(filename=shadowBackground) as img:
            img.composite(Image(filename=rightSize), gravity="center")
            img.save(filename=f"{image_file_path}/{finalTitle}.jpg")
        logging.info("Book cover image created")
        if file != "NI.jpg":
            os.remove(file)
        image_link = insert_image_path(conn, ourDic, finalTitle)
        return image_link