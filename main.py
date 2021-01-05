from selenium import webdriver  # Import from selenium
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import os
import time
import requests
import json

class SessionStorage:
    def __init__(self, driver) :
        self.driver = driver

    def keys(self) :
        return self.driver.execute_script( \
            "let ls = window.sessionStorage, keys = []; " \
            "for (var i = 0; i < ls.length; ++i) " \
            "  keys[i] = ls.key(i); " \
            "return keys; ")

    def get(self, key):
        return self.driver.execute_script("return window.sessionStorage.getItem(arguments[0]);", key)

    def __getitem__(self, key) :
        value = self.get(key)
        if value is None :
          raise KeyError(key)
        return value

"""
Create a new instance of the Chromium driver
"""
def config_browser():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
    return driver

def split_url(url):
    #the url has to be the visitor link and most allow anyone to see the link.
    details = url.split('/m/')[1].split('/')
    #return error here if i can't get the data.
    return (details[0] , details[1])

def get_token(url, driver):
    # Go to the Mural home page.
    driver.get(url)
    time.sleep(1)

    token = ''
    storage = SessionStorage(driver)
    for key in storage.keys():
        if ('token' in key):
            token = storage[key].replace('"', '')
    driver.close()

    return f"Bearer {token}"

def get_mural_information(token, user, id):
    url = f"https://app.mural.co/api/murals/{user}/{id}"
    headers =  {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:71.0) Gecko/20100101 Firefox/71.0", "Authorization": token}

    session = requests.session()
    dirty = session.get(url, headers=headers).text

    if 'Not Found' in dirty: 
        print("There was an error connecting. Check Info")
        print(dirty)
        return []
    else:
        clean = json.loads(dirty)
        return clean['widgets']
        
def generate_csv(notes):
    for key in notes:
        note = notes[key]
        if ('murally.widget.TextWidget' in note['type']):
            properties = note['properties']
            if (len(properties['text'])>0):
                print (key, properties['backgroundColor'], properties['text'])
    return "CSV_FILE"

def get_info(token, mural_user, mural_id):
    notes = get_mural_information(token, mural_user, mural_id)
    if (len(notes)>0):
        generate_csv(notes)
        return True
    return False

def main(url):
    mural_user, mural_id = split_url(url)
    token = "1"

    if (get_info(token, mural_user, mural_id)):
        print("Works")
    else:
        driver = config_browser()
        token = get_token(url, driver)
        if (get_info(token, mural_user, mural_id)):
            print ("Save new token in database")
        else: 
            print ("ERROR! Enviar notificacion a host.")

if __name__ == '__main__':
    #Todo save the token in a database if the token doesn't work create a new one.
    url = 'https://app.mural.co/t/jbrock5296/m/jbrock5296/1605660756092/11f05c8e617c26182856f1dd6c6b240928b8cd7c'
    main(url)
    