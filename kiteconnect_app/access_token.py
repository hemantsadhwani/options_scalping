from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pyotp import TOTP
import time

def autologin():
    token_path = "./key_secrets/api_key.txt"
    key_secret = open(token_path, 'r').read().split()
    kite = KiteConnect(api_key=key_secret[0])

    # Initialize the ChromeDriver service automatically
    service = Service(ChromeDriverManager().install()) # <-- This is the magic line
    options = webdriver.ChromeOptions()
    # Comment out headless mode for debugging
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=service, options=options)

    # Open the Kite login URL
    driver.get(kite.login_url())
    driver.implicitly_wait(10)

    # Enter username and password
    username = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//input[@type="text" or @id="userid"]'))
    )
    password = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//input[@type="password" or @id="password"]'))
    )
    username.send_keys(key_secret[2])
    password.send_keys(key_secret[3])

    # Click the login button
    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@type="submit"]'))
    )
    login_button.click()

    # Wait for the TOTP PIN field
    try:
        pin = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="number" and @id="userid"]'))
        )
    except Exception as e:
        print("Error locating TOTP PIN field:", e)
        print(driver.page_source)  # Debugging: Print the page source
        driver.quit()
        return

    # Generate the TOTP token
    totp = TOTP(key_secret[4])
    token = totp.now()
    print("Generated TOTP:", token)
    pin.send_keys(token)

    # REMOVE the lines that look for and click the submit button.
    # The form likely auto-submits after the TOTP is entered.
    
    # Immediately start waiting for the redirect URL that contains the request_token.
    # This is the correct next step after sending the TOTP.
    print("TOTP entered. Waiting for redirect...")
    WebDriverWait(driver, 15).until(EC.url_contains("request_token="))
    
    redirect_url = driver.current_url
    print("Current URL after redirect:", redirect_url)

    # A more robust way to parse the request token from the URL
    request_token = redirect_url.split('request_token=')[1].split('&')[0]
    print("request_token :", request_token)

    # Save the request token to a file
    with open('./key_secrets/request_token.txt', 'w') as the_file:
        the_file.write(request_token)

    # Quit the driver
    driver.quit()

if __name__ == '__main__':
    autologin()

    # generating and storing access token - valid till 6 am the next day
    request_token = open("./key_secrets/request_token.txt", 'r').read()
    
    key_secret = open("./key_secrets/api_key.txt", 'r').read().split()
    kite = KiteConnect(api_key=key_secret[0])
    data = kite.generate_session(request_token, api_secret=key_secret[1])

    with open('./key_secrets/access_token.txt', 'w') as file:
        file.write(data["access_token"])
