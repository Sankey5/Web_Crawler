from bs4 import BeautifulSoup           # Crawls and scrapes site content
from tld import get_fld                 # Parses for domain names
import mysql.connector                  # MySQL database to store script contents/json
from mysql.connector import errorcode   # Error codes for MySQL
import requests                         # Connects and gets content from sites
import queue                            # Queues sites/domains to search
import time                             # Times program
import re                               # Regular expressions used for searching the data in webpages

class Scraper:
    def __init__(self, database, explored_domains=None):
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
        self.match = []
        # -------Database-----------------------------
        self.database = database                # Holds the credentials for the MySQL connection
        self.connector = None                   # Holds the connection to the MySQLDB
        self.cursor = None                      # Enables execution of a prepared statement

    def scrape(self, url=None):

        self.startTime = time.time()                        # Start timer
        starting_domain = get_domain("https://www." + url)  # Starting domain to search from.

        print(starting_domain)

        self.get_unexplored_domains()                       # Get queued domains from database

        self.get_explored_domains()                         # Get completed domains from database

        if url and url not in self.exploredDomains:         # If a url is given and not already explored,
            self.unexploredDomains.put(starting_domain)     # Put the given domain in the queue

        try:
            self.explore_domains()  # Crawl the domains, look for javascript, and add more listed domains
        except KeyboardInterrupt:
            self.close_database()
        finally:
            self.endTime = time.time()                      # End timer

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

    def explore_domains(self):
        """
        Explores all of the domains in the unexplored domains queue, explores the sites
        in it's sitemap, exports the data found to the database
        :return:
        """

        while not self.unexploredDomains.empty():
            
            self.domain = self.unexploredDomains.get()      # Get the next site

            if self.domain in self.exploredDomains:         # If site is already explored, skip it
                print("skipped")
                continue

            self.exploredDomains.append(self.domain)        # Add it to the list of explored sites

            print("-----------------------------------------")
            print("Exploring {}".format(self.domain))
            
            self.explore_sites()                            # Explores the sites in a domain

            self.open_database()                            # Opens the connection to the database

            self.export_to_database()                       # Export the scraped data to the database

            self.close_database()                           # Closes the connection to the database

            print("Domains left - {}".format(self.unexploredDomains.qsize()))

    def crawl_sitemap(self, domain):
        """
        Explores the sitemap of the given domain and populates the unexplore sites queue
        :param domain:
        :return:
        """

        self.prepare(domain)                                        # Prepare soup

        if self.soup.find("sitemapindex"):                          # Recursively call this function if multiple sitemaps exist
            for site in self.soup.find_all("loc"):
                print("Exploring - ", site.text)
                self.crawl_sitemap(site.text)
        else:                                                       # If sitemap is small, add all domains to queue
            for site in self.soup.find_all("loc"):
                if site not in list(self.unexploredSites.queue) and site:    # If the site hasn't been explored, add it.
                    self.unexploredSites.put(site.text)

# ---Explore-Sites----------------------------
    
    def explore_sites(self):
        """
        Explores all sites that were found in the sitemap.xml of the next site in the
        unexplored Sites queue
        :return:
        """
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

            self.checkScripts()             # Check for specified inline javascript and add matches to the database

            self.add_links()                # Checks to site for links to external sites for scraping
            
            i += 1

    def checkScripts(self):
        """
        Looks through a web page and check for schema.org scripts.
        If a script is found, log the url that it was found on, and the content of the script.
        :return:
        """

        for script in self.soup.find_all("script"):             # Finds all script tags on a webpage
            #print(script.string)
            if re.search(r"schema\.org", str(script.string)):   # If a script contains the schema.org json,
                self.match.append({"url":self.url,              # add the url and json found to the list of
                                   "json":script.string})       # matches found.
                break

    def add_links(self):
        """
        Looks through the current site and searches for links with domains to external sites.
        If that domain has been explored already, it will pass it. Otherwise, it
        will add it to the list of domains to crawl.
        """
        unexplored_domains = []

        for link in self.soup.find_all("a", href=True):
            new_link = link['href']                     # Extracts the link from an anchor tag
            domain = get_domain(new_link)               # Gets a domain if it exists

            # If the link has a domain that has not been explored, add it to the unexplored list.
            if domain and domain not in self.exploredDomains and domain not in list(self.unexploredDomains.queue):
                # Used this to error check duplicate domains.
                # print("Difference - {}".format(len(list(self.unexploredDomains.queue)) - len(set(self.unexploredDomains.queue))))
                self.unexploredDomains.put(domain)
                unexplored_domains.append(domain)

        self.export_unexplored_domains(unexplored_domains)  # Exports domains found on that site to the database



# ---Database-functions-----------------------

    def open_database(self):
        """
        Opens the connection to the database
        :return:
        """
        # Connects to the mysql database using the supplied credentials
        try:
            self.connector = mysql.connector.connect(user=self.database["username"],
                                                     password=self.database["password"],
                                                     host=self.database["host"],
                                                     database=self.database["database"])
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)


        self.cursor = self.connector.cursor(prepared=True)  # Enables the execution of a prepared statement

    def close_database(self):
        """
        Closes the connection to the database
        :return:
        """
        self.cursor.close()  # Close the connections
        self.connector.close()

    def get_unexplored_domains(self):
        """
        Gets the uncompleted domains from the database
        :return:
        """
        self.open_database()

        get_unexplored_domains = ("SELECT * FROM unexplored_domains")  # Get unexplored domains
        self.cursor.execute(get_unexplored_domains)

        for domain in self.cursor:                  # Move each query to the unexplored domains list
            self.unexploredDomains.put(domain)

        self.close_database()

    def get_explored_domains(self):
        """
        Gets the completed domains from the database
        :return:
        """
        self.open_database()

        get_explored_domains = ("SELECT * FROM explored_domains")  # Get completed domains
        self.cursor.execute(get_explored_domains)

        for domain in self.cursor:                  # Move each query to the explored domains list
            if domain not in self.exploredDomains:  # If this query is not in the given explored domains list,
                self.exploredDomains.append(domain) # Add it to the list

        self.close_database()

    def export_unexplored_domains(self, domains):
        """
        Takes a list of unexplored domains and exports them to the database
        :param domains: A list of unexplored domains
        :return:
        """

        add_domain = ("INSERT INTO unexplored_domains "      # Adding the domain to the completed domains list
                      "('domain') "
                      "VALUES "
                      "(%s)")

        self.open_database()

        for domain in domains:                              # For every unexplored domain,
            print("---->Adding domain to database: ", domain)
            self.cursor.execute(add_domain, (domain,))      # add it to the database

        self.close_database()


    def export_to_database(self):
        """
        Takes the data scraped from a domain and exports it to the MySQL database
        The database table looks like this:
            (CREATE TABLE schema_match (
                domain varchar(128) NOT NULL,
                url varchar(500) NOT NULL,
                json varchar(MAX) NOT NULL,
                PRIMARY KEY(url),
                FOREIGN KEY(domain) REFERENCES unexplored_domains(domain)) ENGINE=InnoDB)


        This function should always be prepended with the open_database()
        and close_database() functions.
        :return:
        """

        print("Transferring data to the database")

        domain = get_domain(self.domain)            # Get the told level domain

        if not domain:
            print("Not a domain")
            return

        add_match = ("INSERT INTO schema_match "    # MySQL to add a match to the database
                     "(domain, url, json)"
                     "VALUES (%s, %s, %s)")

        for i in range(len(self.match)):            # For each match found in a domain,
            match = self.match.pop(i)               # Take an item from the match list

            self.cursor.execute(add_match,          # Add the match into the database
                                (domain,
                                 match["url"],
                                 match["json"]))

        """unexplored_domains table should look like this:
                CREATE TABLE unexplored_table (
                    domain varchar(128) NOT NULL,
                    PRIMARY KEY(domain)) ENGINE=InnoDB)"""

        remove_domain = ("DELETE FROM unexplored_domains "      # Removing the domain from the queued domains list
                         "WHERE domain = %s")
        self.cursor.execute(remove_domain, (domain,))

        """explored_domains table should look like this:
            CREATE TABLE explored_table (
                domain varchar(128) NOT NULL,
                PRIMARY KEY(domain)) ENGINE=InnoDB)"""

        add_domain = ("INSERT INTO explored_domains "      # Adding the domain to the completed domains list
                      "(domain)"
                      "VALUES "
                      "(%s)")
        self.cursor.execute(add_domain, (domain,))

        self.connector.commit()                                # Make sure the data is committed to the database

def get_domain(link):
    """
    Checks a link to see if it has a domain.
    If it has a domain, it returns it. If it does not have a domain, return nothing.
    """

    return get_fld(link, fail_silently=True)


