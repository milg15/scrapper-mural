from dotenv import load_dotenv
import requests
import time
import json
import os

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
def config_browser_local():
    from selenium import webdriver  # Import from selenium
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options

    options = Options() 
    options.add_argument("window-size=1400,600")
    options.add_argument('log-level=3')
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.headless = True
    driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options)
    return driver

def config_browser_server():
    from selenium import webdriver

    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)

# Now you can start using Selenium

def split_url(url):
    #the url has to be the visitor link and most allow anyone to see the link.
    details = url.split('/m/')[1].split('/')
    #return error here if i can't get the data.
    return (details[0] , details[1])

from faunadb import query as q
from faunadb.objects import Ref
from faunadb.client import FaunaClient
def get_token_from_db(): 
    secret = os.environ.get("FAUNADB_SECRET")
    #os.getenv('FAUNADB_SECRET')
    client = FaunaClient(secret=secret)

    data = client.query(
        q.paginate(
            q.match(
                q.index("token_by_date")
            )
        )
    )['data']

    token = data[-1][1]
    return f"Bearer {token}"

def add_new_token_to_db(token):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    secret = os.environ.get("FAUNADB_SECRET")
    #os.getenv('FAUNADB_SECRET')
    client = FaunaClient(secret=secret)
    client.query(
        q.create(
            q.collection("token"),
            {"data": {"token": token.replace('Bearer ', ''), "creation": now}}
        )
    )

    print ("Added token to db")

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
    valid_notes = {"notes": []}
    for key in notes:
        note = notes[key]
        if ('murally.widget.TextWidget' in note['type']):
            properties = note['properties']
            if (len(properties['text'])>0):
                valid_notes['notes'].append({
                    "backgroundColor": properties['backgroundColor'], 
                    "text": properties['text']
                })
    return valid_notes

def get_info(token, mural_user, mural_id):
    notes = get_mural_information(token, mural_user, mural_id)
    if (len(notes)>0):
        return generate_csv(notes)
    return False

def main(url):
    mural_user, mural_id = split_url(url)
    token = get_token_from_db()

    data = get_info(token, mural_user, mural_id)
    if (data):
        return data
    else:
        driver = config_browser()
        token = get_token(url, driver)
        data = get_info(token, mural_user, mural_id)
        if (data):
            add_new_token_to_db(token)
            return data    
        else: 
            return "ERROR! Enviar notificacion a host."
    
import flask
from flask import request, jsonify

app = flask.Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "<h1>Distant Reading Archive</h1><p>This site is a prototype API for distant reading of science fiction novels!</p>"

@app.route('/api/v1/notes', methods=['GET'])
def api_notes():
    if 'url' in request.args:
        url = request.args['url']
        return main(url)
    else:
        return "Error: No url provided. Please specify an url."

app.run()