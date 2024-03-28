import psycopg2
import multiprocessing
from queries import DELETE_TABLES_QUERY, CREATE_TABLES_URLS_QUERY, CREATE_TABLES_URL_INFO_QUERY, CREATE_TABLE_STEAM_GAME_INFO_QUERY, CREATE_TABLE_STEAM_GAME_REVIEWS_QUERY, ADD_URL_QUERY, FETCH_AND_MARK_SEEN_PROCEDURE
from helpers.parser import request_and_parse, request_and_parse_steam

NUM_PROCESSES = 5

def normal_analysis():
    # Connect to local db
    conn = psycopg2.connect(
        database="exampledb",
        user="docker",
        password="docker",
        host="localhost",
        port="5432"
    )
    # Open cursor for operations
    cur = conn.cursor()

    # Drop tables if they exist
    cur.execute(DELETE_TABLES_QUERY)

    # Create or replace tables we need
    cur.execute(CREATE_TABLES_URLS_QUERY)
    cur.execute(CREATE_TABLES_URL_INFO_QUERY)

    # Add initial URLs to crawl
    initial_urls = ["https://edition.cnn.com/",
                    "https://www.bbc.com/"
                    ]
    for initial_url in initial_urls:
        cur.execute(ADD_URL_QUERY, (initial_url, ))

    # Add procdure to fetch and mark seen
    cur.execute(FETCH_AND_MARK_SEEN_PROCEDURE)
    
    conn.commit()
    cur.close()
    conn.close()
    
    while True:
        continue_flag = input("initial urls added, continue scraping? (y/n): ")
        if continue_flag == 'y':
            continue_var = True
            break
        elif continue_flag == 'n':
            continue_var = False
            break
        
    if continue_var:
        # Have n parallel processes to crawl URLs
        # Create processes
        processes = []
        for _ in range(NUM_PROCESSES):
            processes.append(multiprocessing.Process(target=request_and_parse, args=()))

        # Start processes
        for p in processes:
            p.start()

        # Wait for processes to finish
        for p in processes:
            p.join()

        print("Finished crawling URLs")
    else:
        print("program discontinued")

def steam_analysis():
    # Connect to local db
    conn = psycopg2.connect(
        database="exampledb",
        user="docker",
        password="docker",
        host="localhost",
        port="5432"
    )
    # Open cursor for operations
    cur = conn.cursor()

    # Drop tables if they exist
    cur.execute(DELETE_TABLES_QUERY)

    # Create or replace tables we need
    cur.execute(CREATE_TABLES_URLS_QUERY)
    cur.execute(CREATE_TABLES_URL_INFO_QUERY)
    cur.execute(CREATE_TABLE_STEAM_GAME_INFO_QUERY)
    cur.execute(CREATE_TABLE_STEAM_GAME_REVIEWS_QUERY)

    # Add initial URLs to crawl
    initial_urls = ["https://store.steampowered.com/app/1086940/Baldurs_Gate_3/",
                    "https://store.steampowered.com/app/578080/PUBG_BATTLEGROUNDS/",
                    "https://store.steampowered.com/app/2252570/Football_Manager_2024/",
                    "https://store.steampowered.com/app/570/Dota_2/"]
    for initial_url in initial_urls:
        cur.execute(ADD_URL_QUERY, (initial_url, ))

    # Add procdure to fetch and mark seen
    cur.execute(FETCH_AND_MARK_SEEN_PROCEDURE)
    
    conn.commit()
    cur.close()
    conn.close()

    while True:
        continue_flag = input("initial urls added, continue scraping? (y/n): ")
        if continue_flag == 'y':
            continue_var = True
            break
        elif continue_flag == 'n':
            continue_var = False
            break

    if continue_var:
        # Have n parallel processes to crawl URLs
        # Create processes
        processes = []
        for _ in range(NUM_PROCESSES):
            processes.append(multiprocessing.Process(target=request_and_parse_steam, args=()))

        # Start processes
        for p in processes:
            p.start()

        # Wait for processes to finish
        for p in processes:
            p.join()

        print("Finished crawling URLs")
    else:
        print("program discontinued")

if __name__ == '__main__':
    isSteamAnalysis = False
    steam_analysis_flag = ''
    while True:
        steam_analysis_flag = input("Steam analysis? (y/n): ")
        if steam_analysis_flag == 'y':
            isSteamAnalysis = True
            break
        elif steam_analysis_flag == 'n':
            isSteamAnalysis = False
            break
    if isSteamAnalysis:
        steam_analysis()
    else:
        normal_analysis()
