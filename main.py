import crawler
from dotenv import load_dotenv
import os

sites = ["blockonomi.com"]
explored_domains = ["instagram.com", "twitter.com", "linkedin.com", "pinterest.com",
                    "reddit.com", "discord.com", "youtube.com", "youtu.be", "facebook.com"]

# Database connection
load_dotenv()
database_connection = {"username":os.getenv("USERNAME"),
                       "password":os.getenv("PASSWORD"),
                       "host":os.getenv("HOST"),
                       "database":os.getenv("DATABASE")}

if __name__ == '__main__':
    crawl = crawler.Scraper(database_connection, explored_domains=explored_domains)

    for site in sites:
        crawl.scrape(site)
