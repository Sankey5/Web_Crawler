import crawler

sites = ["blockonomi.com"]
explored_domains = ["instagram.com", "twitter.com", "linkedin.com", "pinterest.com",
                    "reddit.com", "discord.com", "youtube.com", "youtu.be", "facebook.com"]

# Database connection

if __name__ == '__main__':
    crawl = crawler.Scraper(explored_domains=explored_domains)

    for site in sites:
        crawl.scrape(site)
