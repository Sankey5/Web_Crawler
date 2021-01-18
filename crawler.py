from bs4 import BeautifulSoup   # Crawls and scrapes site content
from tld import get_fld         # Parses for domain names
import requests                 # Connects and gets content from sites
import queue                    # Queues sites/domains to search
import time                     # Times program
import re

class Scraper():
    def __init__(self, explored_domains=None):
        # -------Variables----------------------------
        self.timeout = 5                        # Used for connections functions
        self.startTime = None                   # Time that the crawler started
        self.endTime = None                     # Time the crawler finished
        # -------Used-to-scrape-----------------------
        self.domain = None                      # Top level domain of the website currently being scraped
        self.url = None                         # Current site being crawled
        self.site = None                        # Raw data from post request
        self.soup = None                        # Holds to soup object and site html
        # -------Links--------------------------------
        self.exploredDomains = explored_domains # List of explored domains
        self.unexploredDomains = queue.Queue()  # Queue of unexplored domains
        self.unexploredSites = queue.Queue()    # Queue of unexplored sites
        # -------Database-----------------------------
        self.connector = None                   # A connection to the mysqlDB
        self.cursor = None                      # Enables execution of a prepared statement

    def scrape(self, url):
        self.startTime = time.time()                        # Start timer

        starting_domain = get_domain("https://www." + url)  # Starting domain to search from.

        print(starting_domain)

        self.unexploredDomains.put(starting_domain)         # Put the starting domain in the queue

        self.explore_domains()  # Crawl the domains, look for javascript, and add more listed sites

        # print("Could not connect to a site: {}".format(self.url))
        self.endTime = time.time()                          # End timer

        print("Program took {}".format(self.endTime - self.startTime))

# ---Get-Site-Content------------------------------

    # Create a beautiful soup object
    def prepare(self, url):

        self.handshake(url)
        self.make_soup()

    # Make a request for the specified website, and get the http response code and site content
    def handshake(self, url):
        response = False    # Flag to send more requests if first one fails
        fails = 0           # Counter to set maximum amount of fails

        while not response and fails < 2:
            try:
                self.site = requests.get(url, timeout=self.timeout)
                response = True
            except:
                print("{} - There was an error connecting!\nTry again!\n".format(self.site))  # prints status code
                fails+= 1                   # If an error occurs, increment
                time.sleep(self.timeout)    # Wait to connect again

    # Create a soup object to represent the site content
    def make_soup(self):
        response = False    # Flag to send more requests if first one fails
        i = 0               # Counter to set maximum amount of fails

        while not response and i < 2:  # while loop to try creating soup
            try:
                self.soup = BeautifulSoup(self.site.content,    # creates BeautifulSoup Object from request
                                          'lxml')               # parses with lxml library (Fastest)

                response = True  # will break loop
            except:
                print("There was an error making soup!\nTry again!\n")
                i += 1
                time.sleep(self.timeout)

# ---Explore-Domains-------------------------

    # Looks through all links found and explores them
    def explore_domains(self):

        while not self.unexploredDomains.empty():
            
            self.domain = self.unexploredDomains.get()      # Get the next site

            if self.domain in self.exploredDomains:         # If site is already explored, skip it
                print("skipped")
                continue

            self.exploredDomains.append(self.domain)  # Add it to the list of explored sites

            print("-----------------------------------------")
            print("Exploring {}".format(self.domain))
            
            self.explore_sites()                        # Explores the sites in a domain

            print("Domains left - {}".format(self.unexploredDomains.qsize()))

    def crawl_sitemap(self, domain):

        self.prepare(domain)                                        # Prepare soup

        if self.soup.find("sitemapindex"):                          # Recursively call this function if multiple sitemaps exist
            for site in self.soup.find_all("loc"):
                print("Exploring - ", site.text)
                self.crawl_sitemap(site.text)
        else:                                                       # If sitemap is small, add all domains to queue
            for site in self.soup.find_all("loc"):
                if not site:                                        # If there are no sites in this sitemap, return
                    return
                if site not in list(self.unexploredSites.queue):    # If the site hasn't been explored, add it.
                    self.unexploredSites.put(site.text)

# ---Explore-Sites----------------------------
    
    def explore_sites(self):
        i = 0

        self.domain = "http://www." + self.domain + "/sitemap.xml"  # Apply necessary text for first request

        self.crawl_sitemap(self.domain)                 # Crawl the sitemap to find sites to explore
        
        while not self.unexploredSites.empty():

            self.url = self.unexploredSites.get()       # Get a site to explore

            print("--> Exploring site - {}".format(self.url))

            if i % 100 == 0:
                print("Sites remaining - {}: Domains Accumulated - {}".format(self.unexploredSites.qsize(),
                                                                             self.unexploredDomains.qsize()))
        
            self.prepare(self.url)          # Get site html

            self.checkScripts()             # Check for specified inline javascript

            self.add_links()                # Checks to site for links to external sites for scraping
            
            i += 1

    def checkScripts(self):
        """
        Looks through a web page and check for schema.org scripts.
        If a script is found, log the url that it was found on,
        and the content of the script.
        :return:
        """

        for script in self.soup.find_all("script"):             # Finds all script tags on a webpage
            #print(script.string)
            if re.search(r"schema\.org", str(script.string)):   # If a script contains the schema.org json,
                print(script.string)                            # Print the content
                break

    def add_links(self):
        """
        Looks through the current site and searches for links with domains to external sites.
        If that domain has been explored already, it will pass it. Otherwise, it
        will add it to the list of domains to crawl.
        """

        for link in self.soup.find_all("a", href=True):
            new_link = link['href']                     # Extracts the link from an anchor tag
            domain = get_domain(new_link)               # Gets a domain if it exists

            # If the link has a domain that has not been explored, add it to the unexplored list.

            if domain and domain not in self.exploredDomains and domain not in list(self.unexploredDomains.queue):
                # Used this to error check duplicate domains.
                # print("Difference - {}".format(len(list(self.unexploredDomains.queue)) - len(set(self.unexploredDomains.queue))))
                self.unexploredDomains.put(domain)

def get_domain(link):
    """
    Checks a link to see if it has a domain.
    If it has a domain, it returns it. If it does not have a domain, return nothing.
    """

    return get_fld(link, fail_silently=True)


