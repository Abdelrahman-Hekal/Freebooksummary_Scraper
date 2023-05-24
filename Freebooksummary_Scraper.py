from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
import pandas as pd
import time
import csv
import sys
import numpy as np

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_page_load_timeout(60)
    driver.maximize_window()

    return driver

def scrape_freebooksummary(path):

    start = time.time()
    print('-'*75)
    print('Scraping freebooksummary.com ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'freebooksummary_data.xlsx'
        # getting the books under each category
        links = []
        nbooks, npages = 0, 0
        homepage = 'https://freebooksummary.com/our-library/page/'
        while True:
            npages += 1
            url = homepage + str(npages)
            driver.get(url)
            # scraping books urls
            titles = wait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.layout-content__inner-item")))
            for title in titles:
                try:
                    nbooks += 1
                    print(f'Scraping the url for book {nbooks}')
                    link = title.get_attribute('href')
                    links.append(link)
                except Exception as err:
                    print('The below error occurred during the scraping from freebooksummary.com, retrying ..')
                    print('-'*50)
                    print(err)
                    continue

            # checking the next page
            try:
                button = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.next.page-numbers")))
            except:
                break
                    
        # saving the links to a csv file
        print('-'*75)
        print('Exporting links to a csv file ....')
        with open('freebooksummary_links.csv', 'w', newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Link'])
            for row in links:
                writer.writerow([row])

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        name = path.split('\\')[-1][:-4]
        name = name + '_data.xlsx'
    else:
        df_links = pd.read_csv('freebooksummary_links.csv')

    links = df_links['Link'].values.tolist()

    try:
        data = pd.read_excel(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass

    # scraping books details
    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        try:
            if link in scraped: continue
            driver.get(link)           
            details = {}
            print(f'Scraping the info for book {i+1}\{n}')

            # title and title link
            title_link, title = '', ''              
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).get_attribute('textContent').replace('\n', '').strip().title() 
            except:
                print(f'Warning: failed to scrape the title for book: {link}')               
                
            details['Title'] = title
            details['Title Link'] = title_link               
            
            # summary
            summary = ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//div[@id='content-description']")))
                summary = div.get_attribute('textContent').replace("Show More", "").strip()
            except:
                pass          
                
            details['Summary'] = summary      
            
            # Author and author link
            author, author_link = '', ''
            try:
                trs = wait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "tr")))
                for tr in trs:
                    text = tr.get_attribute('textContent').replace('\n', '').strip()
                    if 'Author' in text[:6]:
                        author = text[6:].strip().title()
                        span = wait(tr, 2).until(EC.presence_of_element_located((By.TAG_NAME, "span")))
                        author_link = span.get_attribute("data-link")
                        if 'http' not in author_link:
                            author_link = 'https://freebooksummary.com' + author_link
                        break
            except:
                print(f'Warning: failed to scrape the author for book: {link}')           
                
            details['Author'] = author            
            details['Author Link'] = author_link                                      
            # other info
            genre, date, lang, loc, ISBN, ISBN13 = '', '', '', '', '', ''
            try:
                trs = wait(driver, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "tr")))
                for tr in trs:
                    text = tr.get_attribute('textContent').replace('\n', '').strip()
                    if 'Genre' in text[:5]:
                        genre = text[5:].strip()         
                    elif 'Published' in text[:9]:
                        date = text[9:].strip()  
                    elif 'Language' in text[:8]:
                        lang = text[8:].strip()
                    elif 'Setting' in text[:7]:
                        loc = text[7:].strip()   
                    elif 'ISBN' in text[:4]:
                        info = text[7:].strip()
                        # check for ISBN13
                        if info.find('ISBN13') == -1:
                            ISBN = info.strip()
                        else:
                            ISBN13 = info.split(':')[-1].strip()    
                            ISBN = info.split('(')[0].strip()    
            except:
                pass
                    
            details['Genre'] = genre
            details['Publication Date'] = date
            details['Language'] = lang
            details['Location'] = loc
            details['ISBN'] = ISBN
            details['ISBN-13'] = ISBN13[:-1]

            # appending the output to the datafame        
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except:
            pass

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'freebooksummary.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_freebooksummary(path)

