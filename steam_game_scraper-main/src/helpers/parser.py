import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
from queries import ADD_STEAM_GAME_INFO_QUERY, ADD_STEAM_GAME_REIVEW_QUERY, FETCH_AND_MARK_SEEN_CALL, ADD_URL_QUERY, ADD_URL_INFO_QUERY, COUNT_URL_INFOS_QUERY, COUNT_GAME_INFOS_QUERY
import os
import socket
import geoip2.database
import re

# For steam- need to get dynamically loaded content
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

SAMPLE_SIZE = 100

def request_and_parse_steam():
    process_id = os.getpid()
    exitFlag = False
    # Connect to local db
    conn = psycopg2.connect(
        database="exampledb",
        user="docker",
        password="docker",
        host="localhost",
        port="5432"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    conn.autocommit = True # No need call commit()

    try:
        # Get a url from urls db
        cursor = conn.cursor()
        row = None

        while row is None:
            cursor.callproc(FETCH_AND_MARK_SEEN_CALL)
            row = cursor.fetchone()
            if row is None:
                # Wait for 1 second if no URLs to crawl
                print(f"[Process {process_id}] No URLs to crawl. Waiting for 1 second...")
                time.sleep(1)
        cur_id, url = row
        print(f"[Process {process_id}]", row)

        # Access steam game page with selenium
        driver = webdriver.Chrome() 
        driver.get(url) 
        page_source = driver.page_source
        driver.close()
        r = requests.get(url)
        if r.status_code != 200:
            # Throw exception if status code is not 200
            raise Exception(f"Status code is not 200: {r.status_code}")
        
        # Get server response time (time from sending a request to receiving the reply)
        server_response_time = r.elapsed.total_seconds()

        # Get IP address of server
        # get everything right of http://, get domain then remove port if any
        hostname = url.split("//")[-1].split("/")[0].split(":")[0]
        ip_address = socket.gethostbyname(hostname)

        # Get server region
        with geoip2.database.Reader('./geolocation_db/GeoLite2-City.mmdb') as reader:
            ip_info = reader.city(ip_address)
            if ip_info.country.iso_code is None:
                server_region = "Unknown"
            else:
                server_region = ip_info.continent.names['en'] + ", " + ip_info.country.names['en']

        print(f"[Process {process_id}] server_response_time: {server_response_time}, ip_address: {ip_address}, server_region: {server_region}") 
        # Add info to url_info table
        cursor.execute(ADD_URL_INFO_QUERY, (cur_id, server_response_time, ip_address, server_region))

        # Parse response
        soup = BeautifulSoup(page_source, 'html.parser')

        # Game Name
        game_name = soup.find('div', id='appHubAppName').string

        # Game Overall Reviews
        game_reviews = soup.find('div', id='userReviews').find_all('span')
        if (len(game_reviews) >= 5): 
            game_overall_review_rating = game_reviews[3].string
            game_overall_review_count = game_reviews[4].string.strip()
        else:
            game_overall_review_rating = game_reviews[0].string
            game_overall_review_count = game_reviews[1].string.strip()
        game_overall_review_count = re.sub(r'[^0-9]', '', game_overall_review_count)

        # Game Genres
        genres_and_manufacturer = soup.find('div', id='genresAndManufacturer')
        genres = genres_and_manufacturer.find('span').find_all('a')
        game_genres = []
        for genre in genres:
            game_genres.append(genre.string)

        # Game Developer
        game_developer = genres_and_manufacturer.find_next('div').find('a').string  

        # Game Release Date
        game_release_date = soup.find('div', class_='release_date').find('div', class_='date').string

        # Game Price (excluding DLCs)
        game_price = soup.find('div', id='game_area_purchase').find('div', class_='game_purchase_price price').string.strip()
        # If game is free, set price to 0
        if game_price.lower().__contains__('free'):
            game_price = 0
        else:
            game_price = float(game_price[2:])

        cursor.execute(ADD_STEAM_GAME_INFO_QUERY, (cur_id, game_name, game_price, game_genres, game_overall_review_rating, game_overall_review_count, game_developer, game_release_date))
        
        urls = []
        # only get steam games as urls to add, taken from the reccomended section
        recommendations_div = soup.find('div', class_='store_horizontal_autoslider_ctn')
        if recommendations_div:
            print(f"[Process {process_id}] Found recommendations div")
            # Find all the 'a' tags within this div
            game_links = recommendations_div.find_all('a')
            
            # Extract the URLs from the 'a' tags
            game_urls = [link.get('href') for link in game_links if link.get('href')]
            
            # Print the extracted URLs
            for new_url in game_urls:
                # Check that each url indeed is a steam game page
                if new_url.startswith('https://store.steampowered.com/app/'):
                    # Remove last slash contents
                    new_url = '/'.join(new_url.split('/')[:-1]) + '/'
                    urls.append(new_url)


        
        # Add all urls found into urls db
        for u in urls:
            try:
                print(f"[Process {process_id}] Inserting URL: {u}")
                cursor.execute(ADD_URL_QUERY, (u, ))
            except Exception as e:
                print(f"[Process {process_id}] Failed to insert URL {u}: {e}")
                conn.rollback()
        # Add reviews to reviews table
        game_review_parser(cur_id, url, cursor)
    except KeyboardInterrupt:
        print(f"[Process {process_id}] Program terminated by user.")
        exitFlag = True
    except Exception as e:
        print(f"[Process {process_id}] An error occurred:", e)
        conn.rollback()
    finally:
        # If there are `SAMPLE_SIZE` game infos, set exit flag to true
        cursor.execute(COUNT_GAME_INFOS_QUERY)
        count = cursor.fetchone()[0]
        if count >= SAMPLE_SIZE:
            exitFlag = True
        cursor.close()
        conn.close()
        if not exitFlag:
            return request_and_parse_steam()

def request_and_parse(skip=False):
    """
    The function `request_and_parse` sends an HTTP request to a given URL, parses the response using
    BeautifulSoup, and returns a list of URLs found in the response, optionally filtering out URLs from
    the same domain if specified.
    
    :param skip: The "skip" parameter is a boolean value that determines whether to filter out domains
    or not. If "skip" is set to True, the function will filter out domains and only retrieve unique
    domains. If "skip" is set to False, the function will not filter out domains and retrieve all URLs
    :return: a list of URLs.
    """
    process_id = os.getpid()
    exitFlag = False
    # Connect to local db
    conn = psycopg2.connect(
        database="exampledb",
        user="docker",
        password="docker",
        host="localhost",
        port="5432"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    conn.autocommit = True # No need call commit()

    try:
        # Get a url from urls db
        cursor = conn.cursor()
        row = None

        while row is None:
            cursor.callproc(FETCH_AND_MARK_SEEN_CALL)
            row = cursor.fetchone()
            if row is None:
                # Wait for 1 second if no URLs to crawl
                print(f"[Process {process_id}] No URLs to crawl. Waiting for 1 second...")
                time.sleep(1)
        cur_id, url = row
        print(f"[Process {process_id}]", row)

        # Send HTTP request to page
        r = requests.get(url)
        if r.status_code != 200:
            # Throw exception if status code is not 200
            raise Exception(f"Status code is not 200: {r.status_code}")
        
        # Get server response time (time from sending a request to receiving the reply)
        server_response_time = r.elapsed.total_seconds()

        # Get IP address of server
        # get everything right of http://, get domain then remove port if any
        hostname = url.split("//")[-1].split("/")[0].split(":")[0]
        ip_address = socket.gethostbyname(hostname)

        # Get server region
        with geoip2.database.Reader('./geolocation_db/GeoLite2-City.mmdb') as reader:
            ip_info = reader.city(ip_address)
            if ip_info.country.iso_code is None:
                server_region = "Unknown"
            else:
                server_region = ip_info.continent.names['en'] + ", " + ip_info.country.names['en']

        print(f"[Process {process_id}] server_response_time: {server_response_time}, ip_address: {ip_address}, server_region: {server_region}") 

        # Parse response
        soup = BeautifulSoup(r.text, 'html.parser')

        # Add info to url_info table
        cursor.execute(ADD_URL_INFO_QUERY, (cur_id, server_response_time, ip_address, server_region))

        # Get more urls from current page
        urls = []
        if (skip):
            # Filter out domains
            domain_set = set()
            for link in soup.find_all('a'):
                # Get href of links
                href = link.get('href')
                # Filter out hrefs that start with "/", indicating that they are for same domain
                if href and href.startswith('http'):
                    # Add domain to list of seen domains
                    domain = href.index('/', len('https://'))
                    # Only retrieve unique domains 
                    if href[:domain] not in domain_set:
                        domain_set.add(href[:domain])
                        urls.append(href)
        else: 
            # Do not filter out domains
            for link in soup.find_all('a'):
                # Get href of links
                href = link.get('href')
                if href and href.startswith('http'):
                    urls.append(href)
        print(f"[Process {process_id}] ended: ", urls)
        
        # Add all urls found into urls db
        for u in urls:
            try:
                print(f"[Process {process_id}] Inserting URL: {u}")
                cursor.execute(ADD_URL_QUERY, (u, ))
            except Exception as e:
                print(f"[Process {process_id}] Failed to insert URL {u}: {e}")
                conn.rollback()
    except KeyboardInterrupt:
        print(f"[Process {process_id}] Program terminated by user.")
        exitFlag = True
    except Exception as e:
        print(f"[Process {process_id}] An error occurred:", e)
        conn.rollback()
    finally:
        # If there are `SAMPLE_SIZE` url infos, set exit flag to true
        cursor.execute(COUNT_URL_INFOS_QUERY)
        count = cursor.fetchone()[0]
        if count >= SAMPLE_SIZE:
            exitFlag = True
        cursor.close()
        conn.close()
        if not exitFlag:
            # Sleep so site won't think we are performing DOS
            time.sleep(0.5)
            return request_and_parse(skip)

def game_review_parser(url_id, game_url, cursor):
    # Use a regular expression to find the numeric game ID in the URL
    match = re.search(r'/app/(\d+)', game_url)
    if match:
        game_id = match.group(1)
        # Construct the reviews URL
        review_url = f'https://steamcommunity.com/app/{game_id}/reviews'
        driver = webdriver.Chrome() 
        driver.get(review_url)
        # Add code to scroll to the end of reviews
        reached_end = False
        while not reached_end:
            try:
                span = driver.find_element(By.XPATH, "//span[text()='View Community Hub']")

                # Navigate to the parent button element if need permission to continue to reviews
                button = span.find_element(By.XPATH, "./ancestor::button")

                # Click the button
                button.click()
            except NoSuchElementException:
                pass
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1) # Add a delay to allow content to load

            # look for end of page
            try:
                element = driver.find_element(By.CLASS_NAME, "apphub_NoMoreContent")
                if element.is_displayed():
                    reached_end = True
                    print("Scrolled to the end of the page.")
                # else cap number of reviews at 50 per game
                else:
                    page_source_temp = driver.page_source
                    soup = BeautifulSoup(page_source_temp, 'html.parser')
                    review_divs_temp = soup.find_all('div', class_='apphub_CardTextContent')
                    if len(review_divs_temp) >= 50:
                        reached_end = True
                        print("Reached 50 reviews; stopping scrolling.")
                    else:
                        print("Element is hidden; page not scrolled to the end.")


            except NoSuchElementException:
                pass
        page_source = driver.page_source 
        driver.close()
        soup = BeautifulSoup(page_source, 'html.parser')
        # Find all divs with class=apphub_CardTextContent
        review_divs = soup.find_all('div', class_='apphub_CardTextContent')
        
        # Clean data to get each review text
        for div in review_divs:
            # Find the date_posted div and decompose it to remove from the parse tree
            date_posted_div = div.find('div', class_='date_posted')
            if date_posted_div:
                date_posted_div.decompose()
            
            # Find the early_access_review div and decompose it to remove from the parse tree
            # If not 'Early access review' will be added to the review text
            early_access_div = div.find('div', class_='early_access_review')
            if early_access_div:
                early_access_div.decompose()

            # The actual review text is what's left in the div, now without the date_posted div and 'early access review' if it was there
            review_text = div.get_text(strip=True)
            # Add review to reviews table
            cursor.execute(ADD_STEAM_GAME_REIVEW_QUERY, (url_id, review_text, review_url))
    else:
        raise ValueError("Could not extract game ID from URL")
