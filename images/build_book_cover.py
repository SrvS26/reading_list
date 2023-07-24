from wand.color import Color
from wand.image import Image, GRAVITY_TYPES, COLORSPACE_TYPES
from decouple import config
import os
from uuid import uuid4
import custom_logger
import requests

database_file_path = config("DATABASE_FILE_PATH")
image_url = config("BASE_IMAGE_URL")
image_file_path = config("IMAGE_PATH")
processing_images_path = image_file_path + "processing_book_covers/"


logging, listener = custom_logger.get_logger("book_cover")


def get_image_path(conn, mapped_book_details: dict) -> str:
    """Takes a dict with ISBN10/13 and returns respective processed book cover image's file path.

    :param mapped_book_details: {"Title": "Title|"", "Subtitle": "Subtitle|"", "Authors": "Authors|"", "Category": "Category"|"", "Pages": int|None, "ISBN_10": "ISBN_10"|"", "ISBN_13": "ISBN_13"|"", "Other Identifier": "Other Identifier|"", "Summary": "Summary"|"", "Summary_extd": "Summary_extd"|"", "Published": "Published"|"", "Publisher": "Publisher"|"", "Image_url": "Image_url"|""}
    :returns: file path to processed image fetched from database table IMAGES
    """
    cursor = conn.cursor()
    image = f"""SELECT image_path from IMAGES WHERE ISBN_10 = '{mapped_book_details.get("ISBN_10")}' OR ISBN_13 = '{mapped_book_details.get("ISBN_13")}'"""
    cursor.execute(image)
    image_path = cursor.fetchone()
    conn.commit()
    return image_path


def insert_image_path(conn, mapped_book_details: dict, image_name: str) -> str:
    """Generate a file path to the image, update the database table IMAGES with ISBN 10, 13 and the path."""
    cursor = conn.cursor()
    image_path = image_url + image_name + ".jpg"
    if (mapped_book_details.get("ISBN_10") is None and mapped_book_details.get("ISBN_13") is None) or (
        mapped_book_details.get("ISBN_10") == "" or mapped_book_details.get("ISBN_13") == "" #Books that have no ISBN 10/13 were being updated with wrong images
    ):
        return image_path
    else:
        rows = f"""INSERT INTO IMAGES (ISBN_10, ISBN_13, image_path) VALUES ('{mapped_book_details.get("ISBN_10")}', '{mapped_book_details.get("ISBN_13")}', "{image_path}");"""
        cursor.execute(rows)
        conn.commit()
        return image_path


async def async_get_book_image(session, mapped_book_details: dict, cover_image_name: str) -> str:
    """Fetches book cover image and writes to a file, returns file name.

    :param mapped_book_details: {"Title": "Title|"", "Subtitle": "Subtitle|"", "Authors": "Authors|"", "Category": "Category"|"", "Pages": int|None, "ISBN_10": "ISBN_10"|"", "ISBN_13": "ISBN_13"|"", "Other Identifier": "Other Identifier|"", "Summary": "Summary"|"", "Summary_extd": "Summary_extd"|"", "Published": "Published"|"", "Publisher": "Publisher"|"", "Image_url": "Image_url"|""}
    :param cover_image_name: Name generated from Title+ISBN_10+ISBN_13 of the book or a uuid.
    :returns: file name
    """
    title = mapped_book_details["Title"]
    image_link = mapped_book_details["Image_url"]
    if image_link != "":
        r = await session.get(image_link)
        x = await r.read()
        logging.info(f"Querying for book {cover_image_name} cover")
        with open(processing_images_path + cover_image_name, "wb") as f:
            f.write(x)
        return cover_image_name
    else:
        logging.info(f"Book {title} has no image")
        return "NI.png"


def get_book_image(book_details: dict, cover_image_name: str) -> str: #Same function, for the goodreads experiment
    """Fetches book image and writes to a file, returns file name.

    :param mapped_book_details: {"Title": "Title|"", "Subtitle": "Subtitle|"", "Authors": "Authors|"", "Category": "Category"|"", "Pages": int|None, "ISBN_10": "ISBN_10"|"", "ISBN_13": "ISBN_13"|"", "Other Identifier": "Other Identifier|"", "Summary": "Summary"|"", "Summary_extd": "Summary_extd"|"", "Published": "Published"|"", "Publisher": "Publisher"|"", "Image_url": "Image_url"|""}
    :param cover_image_name: Name generated from Title+ISBN_10+ISBN_13 of the book or a uuid.
    :returns: file name
    """
    title = book_details["Title"]
    image_link = book_details["Image_url"]
    if image_link != "":
        r = requests.get(image_link)
        logging.info(f"Querying for book {cover_image_name} cover")
        with open(cover_image_name, "wb") as f:
            f.write(r.content)
        return cover_image_name
    else:
        logging.info(f"Book {title} has no image")
        return f"{image_file_path}/NI.png"


def resize_goodreads_image(image_name: str) -> str: #Same function, for the goodreads experiment
    """Resize goodreads book cover image to a uniform size to allow further processing."""
    with Image(filename=image_name) as img:
        img.resize(height=180, width=135)
        img.save(filename=f"{processing_images_path}resized_image.jpg")
    return f"{processing_images_path}resized_image.jpg"


def resize_image(cover_image_name: str) -> str:
    """Resize book cover image to a uniform size to allow further processing."""
    with Image(filename=cover_image_name) as img:
        img.resize(height=180)
        img.save(filename=f"{processing_images_path}resized_image.jpg")
    return f"{processing_images_path}resized_image.jpg"


def get_background_colour(image_name: str) -> str:
    """Get the predominant colour in the book cover image as srgb."""
    with Image(filename=image_name) as img:
        img.quantize(5, "srgb", 0, True, False)
        hist = img.histogram
        sort_hist = sorted(hist.items(), key=lambda x: x[1], reverse=True)
        highest_srgb = str(sort_hist[0][0])
    return highest_srgb


def is_background_dark(srgb: str) -> bool:
    """Check if generated background srgb value is too dark for the Notion workspace."""
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
    """Get an image of custom size and srgb for book cover background. If background is too dark, get a suitable coloured background."""
    if is_background_dark(srgb):
        hex_code = "#151514"
    else:
        hex_code = srgb  # input is srgbcode
    with Color(hex_code) as bg:
        with Image(width=500, height=200, background=bg) as img:
            img.save(filename=f"{processing_images_path}background.jpg")
    return f"{processing_images_path}background.jpg"


def add_shadow(image_name: str, background: str) -> str:
    """Add a shadow for the book cover on the background."""
    with Image(filename=f"{image_name}") as img:
        w = img.width
        h = img.height
    with Color("#000005") as bg:
        with Image(width=(w + 5), height=(h + 5), background=bg) as img:
            img.save(filename=f"{processing_images_path}shadow.jpg")
    with Image(filename=background) as img:
        img.composite(Image(filename=f"{processing_images_path}shadow.jpg"), gravity="center")
        img.save(filename=f"{processing_images_path}shadow_on_background.jpg")
    with Image(filename=f"{processing_images_path}shadow_on_background.jpg") as img:
        img.gaussian_blur(sigma=3)
        img.save(filename=f"{processing_images_path}blurred_shadow_on_background.jpg")
    return f"{processing_images_path}blurred_shadow_on_background.jpg"


def generate_cover_image (cover_image_name: str) -> str:
    """Get a fully processed book cover image ready to be uploaded to Notion"""
    path_to_image = processing_images_path + cover_image_name
    resized_image = resize_image(path_to_image)
    background_colour = get_background_colour(path_to_image)
    background = generate_background(background_colour) 
    shadow_on_background = add_shadow(resized_image, background)
    with Image(filename=shadow_on_background) as img:
        img.composite(Image(filename=resized_image), gravity="center")
        img.save(filename=f"{image_file_path}{cover_image_name}.jpg")
    logging.info("Book cover image created")
    if cover_image_name != "NI.png":
        os.remove(f"{processing_images_path}{cover_image_name}")
    return cover_image_name


async def async_upload_image(session, conn, mapped_book_details: dict) -> str:
    """Looks for image link in the IMAGES database, if link doesn't exist, generates a processed book cover and returns a path to the file.
    
    :param mapped_book_details: {"Title": "Title|"", "Subtitle": "Subtitle|"", "Authors": "Authors|"", "Category": "Category"|"", "Pages": int|None, "ISBN_10": "ISBN_10"|"", "ISBN_13": "ISBN_13"|"", "Other Identifier": "Other Identifier|"", "Summary": "Summary"|"", "Summary_extd": "Summary_extd"|"", "Published": "Published"|"", "Publisher": "Publisher"|"", "Image_url": "Image_url"|""}
    :returns: file path to existing processed image or to newly processed image
    """
    result = get_image_path(conn, mapped_book_details) #if processed image already exists in the database for the book
    if result is not None:
        return result[0]
    else:
        cover_image_name = "".join(filter(lambda x: x.isalnum(), (mapped_book_details.get("Title", "")
            + mapped_book_details.get("ISBN_10", "")
            + mapped_book_details.get("ISBN_13", ""))))
        if cover_image_name == "":
            cover_image_name = str(uuid4())
        file = await async_get_book_image(session, mapped_book_details, cover_image_name)
        generate_cover_image(file)
        image_link = insert_image_path(conn, mapped_book_details, cover_image_name)
        return image_link
    

def upload_image(conn, mapped_book_details: dict) -> str: #Same function for the Goodreads experiment
    """Looks for image link in the IMAGES database, if link doesn't exist, generates a processed book cover and returns a path to the file.
    
    :param mapped_book_details: {"Title": "Title|"", "Subtitle": "Subtitle|"", "Authors": "Authors|"", "Category": "Category"|"", "Pages": int|None, "ISBN_10": "ISBN_10"|"", "ISBN_13": "ISBN_13"|"", "Other Identifier": "Other Identifier|"", "Summary": "Summary"|"", "Summary_extd": "Summary_extd"|"", "Published": "Published"|"", "Publisher": "Publisher"|"", "Image_url": "Image_url"|""}
    :returns: file path to existing processed image or to newly processed image
    """
    result = get_image_path(conn, mapped_book_details)
    if result is not None:
        return result[0]
    else:
        cover_image_name = "".join(filter(lambda x: x.isalnum(), (mapped_book_details.get("Title", "")
            + mapped_book_details.get("ISBN_10", "")
            + mapped_book_details.get("ISBN_13", ""))))
        if cover_image_name == "":
            cover_image_name = str(uuid4())
        file = get_book_image(mapped_book_details, cover_image_name)
        generate_cover_image(cover_image_name)
        image_link = insert_image_path(conn, mapped_book_details, cover_image_name)
        return image_link
