#!/usr/bin/env python
# coding: utf-8

# ### This scraper focuses on the feeds section of the page supplied and gathers user enegagement data by focuing on profiles who liked a particular post.
# #### Info Scraped:
#     1). Name
#     2). Linkedin Profile link
#     3). Professional eadline/ Role 
#     4). Count ( Count of user interactions)
# 


# All Necessary imports
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import re as re
import time
import pandas as pd
from selenium.common.exceptions import NoSuchElementException
import configparser
import os

#Read config file
config = configparser.ConfigParser()
config.read('conf/conf.ini')

# Get the default section
conf_default = config['DEFAULT']
email = conf_default['email']
password = conf_default['password']
inst = conf_default['inst']
output_file = conf_default['output_file']
max_scroll_count = int(conf_default['max_scroll_count'])

# The login function takes in the users credentials and logs into linkedin
def login(driver, email=None, password=None, timeout=10):
    driver.get("https://www.linkedin.com/login")
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(email)
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password + Keys.RETURN)
    
    if driver.current_url == 'https://www.linkedin.com/checkpoint/lg/login-submit':
        remember_prompt = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, 'remember-me-prompt__form-primary')))
        remember_prompt.submit()

    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CLASS_NAME, "global-nav__primary-link")))


driver = webdriver.Chrome()
login(driver, email, password)


# Go to feeds page of the institution provided
driver.get(inst)
wait = WebDriverWait(driver, 10)
wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "social-details-social-counts__reactions-count")))


scroll_count=0
while True:
        try:
            show_more_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".scaffold-finite-scroll__load-button .artdeco-button__text")))
            actions = ActionChains(driver)
            actions.move_to_element(show_more_button).perform()
            scroll_count+=1
            time.sleep(10)  # this is essential as the page at times takes time to load
            if scroll_count>=max_scroll_count:
                break
        except Exception as e:
            print("No more results to show or encountered an error:", e)
            break  
# Find all like buttons
like_buttons = driver.find_elements(By.CLASS_NAME, "social-details-social-counts__reactions-count")


# Main scraper logic
data_collected=[]
for button in like_buttons:
    driver.execute_script("arguments[0].scrollIntoView();", button)
    driver.execute_script("window.scrollBy(0, -150);") # Scroll & Adjust .. seems needed to adjust focus

    
    button.click() #open modal
    wait.until(EC.visibility_of_element_located((By.ID, "artdeco-modal-outlet")))

    while True:
        try:
            show_more_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".scaffold-finite-scroll__load-button .artdeco-button__text")))
            actions = ActionChains(driver)
            actions.move_to_element(show_more_button).perform()
            time.sleep(4)  # this is essential as the page at times takes time to load
        except Exception as e:
            print("No more results to show or encountered an error:", e)
            break  

    #Extract names, LinkedIn profile links and Roles... just named the third column roles as it seems to be a summary or headline
    profiles = driver.find_elements(By.CLASS_NAME, "social-details-reactors-tab-body-list-item")
    for profile in profiles:
        try:
            name_element = profile.find_element(By.CSS_SELECTOR, "span[dir='ltr']")
            name = name_element.text if name_element else "Name not found"
        except NoSuchElementException:
            name = "Name not found"
            continue
        link = profile.find_element(By.CSS_SELECTOR, "a").get_attribute('href')
        # Extracting the role or professional headline
        role_element = profile.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__caption")
        role = role_element.text
        row={"Name":name,"Link":link,"Role":role}
        data_collected.append(row)

    # Close the modal before proceeding to the next like button
    close_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".artdeco-modal__dismiss")))
    close_button.click()

    # Wait for the modal to close
    wait.until(EC.invisibility_of_element_located((By.ID, "artdeco-modal-outlet")))


# Creates a dataframe out of the data collected
df=pd.DataFrame(data_collected)
#df.head(20)

#deduplication
df_deduped = df.drop_duplicates('Link').reset_index(drop=True)
df_deduped['count'] = df.groupby('Link').size().values


# #### Sort the profiles based on engagement count
df_deduped.sort_values('count', ascending=False, inplace=True)
df_deduped.count()

# Create 'data' directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

# Write to csv
df_deduped.to_csv("data/"+output_file, index=False, encoding='utf-8')
