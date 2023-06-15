import logging
import requests
from decouple import config

verify_url = config("GUMROAD_VERIFY_URL")
gumroad_token = config("GUMROAD_TOKEN")
gumroad_product_id = config("GUMROAD_PRODUCT_ID")

logging.basicConfig(
    filename="gumroad.log",
    format="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    level=logging.DEBUG,
    datefmt="%d-%b-%y %H:%M:%S",
)


def verify_license(license_key: str, user_details: dict) -> tuple:
    """Verifies user license key with Gumroad and returns (response,response code)|(None, response code)
    

    """
    params = {"product_permalink": gumroad_product_id, "license_key": license_key.strip()}
    try:
        response = requests.post(verify_url, headers={}, data=params)
        status_code = response.status_code
        if status_code == 200:
            logging.info("Successfully verified license key with Gumroad")
            parsed_response = response.json()
            return (parsed_response, 100)
        else:
            logging.error(f"Gumroad license key query failed for user: {user_details['user_id']}, status code: {status_code}, license key: {license_key}, response: {response.text}")
            return (None, 102)
    except Exception as e:
        logging.error(f"Gumroad license key query failed for user: {user_details['user_id']}, {e}")
        return (None, 104)
    
# Can user ID and license key be in a dictionary?
def gumroad_response(response, user_id: str, license_key: str, revoked_users: list) -> int:
    """
    Checks Gumroad response to check is license key is successfully validated and ensures that the license is key is being used only by one user.
    """
    if response.get("success") == True:
        logging.info("License key successfully validated")
        num_uses = response.get("uses", None)
        if num_uses == 1:
            license_key_verification.update_validated_status(user_id, license_key)
            return 100
        elif num_uses > 1:
            if user_id in revoked_users:
                license_key_verification.update_validated_status(user_id, license_key)
                return 103
            else:
                return 101
        elif num_uses is None:
            logging.error("No key 'uses' found in the Gumroad response for license key query")
            return 104
    else:
        return 104


def get_gumroad_variant(response) -> bool:
    """
    Checks if user has purchased the product with/without additional goodreads import feature
    """
    tier = response.get("purchase").get("variants")
    return tier == "(Auto-fill Feature with Goodreads Import)"     

