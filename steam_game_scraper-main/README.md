# Pre-requisites
- Ensure your local psql server has stopped
windows:
```
C:\Users\Administrator>net stop postgresql-x64-15
The postgresql-x64-15 - PostgreSQL Server 15 service is stopping.
The postgresql-x64-15 - PostgreSQL Server 15 service was stopped successfully.
```

- Install requirements
`pip install -r requirements.txt`

- Have docker installed

# Quick start
1. Run `docker-compose up -d` in root directory to start postgres server and webUI
2. Run `./src/main.py`
3. Go to `localhost:8080` and login with:
    * System: Postgresql
    * Server: database
    * Username: docker
    * Password: docker
    * database: exampledb
4. Check that `urls` table has been populated with the urls. You can view the response times, IP addresses and geolocation of the servers in the `url_info` table. For our data analysis, if you had selected the steam analysis mode, the data collected is stored in the `steam_game_info` and `steam_game_review` tables.

# Assignment requirements
- [x] (3 marks) Starts with the initial set of URLS in a text file/DB 
- [x] (7 marks) Coordinated access by multiple Threads to the text file/DB.
- [x] (10 marks) Adds newly found URLs to the text file/DB
    * Check urls table in `localhost:8080` after running `./src/main.py`
- [x] (5 marks) Response times to the severs, IP addresses and geolocation of the servers
are printed (either in screen or in text file/DB)
    * Printed in console and available in url_info table in `localhost:8080`
- [X] (8 marks) One page report on useful data collection/statistics (open ended
requirement)
- [x] (2 marks) Well written code with in-line comments.


# Analysis
Run code in `./src/sentiment_analysis/analyse.ipynb`

Observe word cloud and overall sentiments of steam games

Run code in `./src/popularity_analysis/analysis.ipynb`

Observe pie charts of popularity of different genres