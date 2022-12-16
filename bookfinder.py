#!/usr/bin/env python3


# ##############################################################################
#                               Dependencies
# ##############################################################################


# time              Used to sleep in between book searches
# pandas            For dataframes
# urllib            Only used to construct the "final" URL
# selenium          Automated web scrapping is done with Selenium
# fake_useragent    Provides fake "User Agents" (1)

# (1): Field that the browser provides to the webpage which contains info such
#      as the OS and web browser used among others. Eg:
#
# Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0

import time
import pandas as pd
import urllib
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from fake_useragent import UserAgent


# ##############################################################################
#                                   Constants
# ##############################################################################


# DRIVER_PATH
#   Path in which the web browser engine (in this case "geckodriver") is
#   located.
#
# LOG_FILE
#   Path in which the log file generated by geckodriver will be stored.
#
# BOOK_LIST
#   Path in which the book list "excel" file is located.
#
# EXPORT_FILE
#   Path of the output csv file resulting from the web scrapping.
#
# SITE
#   Base URL.

DRIVER_PATH = '</home/example/web_driver_path/geckodriver>'         # TODO: fill
LOG_FILE = '</home/example/.cache/geckodriver/geckodriver.log>'     # TODO: fill
BOOK_LIST = '</home/example/path_to_file/book_list.ods>'            # TODO: fill
EXPORT_FILE = '</home/example/path_to_file/temp_book_list.csv>'     # TODO: fill
SITE = 'https://www.bookfinder.com/search/'

# Sleep time (403 prevention) [s]
t = 1

# Applied shipping taxes by BookFinder on BearBookSales [$]
shipping = 2.99


# ##############################################################################
#                                  Functions
# ##############################################################################


# Creates a Selenium session with the following:
#   - Headless: that is, you do not see the browser but it's there (magic).
#   - User Agent is overridden by a random one (helps to scrap in some scenarios).
#   - Log file is redirected to the specified path.
#
# INPUT:
#   driver_path:
#       String. Path of the web engine.
#   user_agent:
#       String. User Agent.
#   log_file:
#       String. By default '=LOG_FILE'. Path of the log file.
#
# OUTPUT:
#   Object. Web browser session.
#
# Minor details:
#   The commented out line is the one that makes the browser headless.
#
#   My advice is to try the script "with head" first, so that you can make sure
#   it works as intended and once you are certain remove the pound/hashtag '#'
#   sign and run it headless.

def headless_browser(driver_path, user_agent, log_file=LOG_FILE):
    fireFoxOptions = webdriver.FirefoxOptions()
    # fireFoxOptions.headless = True
    fireFoxOptions.set_preference("general.useragent.override", user_agent)
    s = Service(driver_path, log_path=log_file)

    return webdriver.Firefox(options=fireFoxOptions, service=s)


# ##############################################################################
#                                   Variables
# ##############################################################################


# Fields used to build the "final" URL of the book.
# Only the ISBN is modified, the rest are kept intact.
values = {'author': '',
          'title': '',
          'lang': '',
          'isbn': '',
          'submitBtn': 'Search',
          'new_used': '*',
          'destination': '<COUNTRY CODE>',      # TODO: fill (eg. gb)
          'currency': '<CURRENCY>',             # TODO: fill (eg. GBP)
          'mode': 'basic',
          'st': 'sr',
          'ac': 'qr', }

# Random User Agent
user_agent = UserAgent().random

# Set headless webdriver
driver = headless_browser(DRIVER_PATH, user_agent)

# Import book list (dropna is for the extra emtpy rows)
df = pd.read_excel(BOOK_LIST, engine='odf').dropna()

# Transforms the dataframe into a list of dictionaries:
#
#   [ { 'ISBN': 'XXXXXXXXXX', 'Author': '...', 'Title': '...', ... }, < row 0
#     { <next book> },                                                < row 1
#      ...                                                              ...
#     { <last book> } ]                                               < row N-1
#
# Convert to dict
df_dict = df.to_dict('records')

# Additional dataframe for Bear Book (Bear Book Sales, a seller)
df_bb = pd.DataFrame()

# Flag used for printing the output csv file header (temp_book_list.csv)
first_row = True


# ##############################################################################
#                                       Loop
# ##############################################################################


# Iterate through each row (each book)
for row in df_dict:
    # Builds the webpage URL based on ISBN search
    values['isbn'] = row['ISBN']
    data = urllib.parse.urlencode(values)
    url = '?'.join([SITE, data])

    # It can fail.
    # For example, there may be some books where one of the two columns
    # (new/used) is missing and fails to grab both prices.
    try:
        # Get webpage content:
        # Calls the web driver to go to the specified webpage and gets the html
        # content.
        driver.get(url)
        content = driver.page_source

        # Scrap html for tables (new/used):
        # Returns a list of dataframes, that is why the name df_list.
        df_list = pd.read_html(content)

        # Get book prices (both new and used and picks the lowest)
        #
        # TODO: change if needed.
        #   - If your browser/system settings uses comma as decimal separator it
        #     replaces the comma with a dot.
        #   - If not, you can remove the .replace(',', '.')
        prices = [float(df_list[i]['Price'][0][1:].replace(',', '.')) for i in [2, 3]]
        lowest_price = round(min(prices), 2)

        # Search for 'Bear Book' in 'Bookseller' df:
        # If there is a seller named 'Bear Book' it returns a non-empty df.
        df_bb = df_list[3][df_list[3]['Bookseller'].str.contains('Bear Book', regex=True)]

    except Exception:
        # If it fails waits an extra 8 seconds
        time.sleep(8)
        pass

    else:
        # If Book Finder was present
        if not(df_bb.empty):
            # Grab prices
            # TODO: change if needed. Same as the previous one.
            bb_price = df_bb.iloc[0]['Price'][1:].replace(',', '.')

            # Subtract shipping costs
            bb_price = round(float(bb_price) - shipping, 2)

            # Compare if Bear Book minus the shipping is lower than the cheapest
            # book listed
            if bb_price < lowest_price:
                lowest_price = bb_price

        # price_diff
        #   Price difference between:
        #       - Reference price "AMZN" in the "excel" file 'book_list.ods'
        #       - And the "current BookFndr price" obtained from the scrapping.
        #
        # percent_diff
        #   Percent-wise difference of the reference price "AMZN" and the
        #   current one.
        #
        # percent_inc
        #   Difference in percentages between the reference "percent_diff" (the
        #   one in 'book_list.ods') and the current calculated "percent_diff".
        #
        #   That is:
        #       If the book in 'book_list.ods' has a $10 price in "AMZN" and $8
        #       in "BookFndr" (cheapest known price from a previous scrapping)
        #       that is a "percent_diff" of 20%.
        #
        #       Now, if the script finds it even cheaper, eg, for $5 (50%
        #       "percent_diff"), the "percentage increase" (how much has
        #       increased the discount) would be 50% - 20% = 30%.
        #
        #       That is, this book would be 30% cheaper for me to buy at this
        #       newly found price compared to the previous cheapest scrapped
        #       price.
        #
        #       The opposite can occur with books that once where cheap and now
        #       their prices have soared (negative "percent_inc").

        price_diff = round(row['AMZN'] - lowest_price, 2)
        percent_diff = round(1 - lowest_price / row['AMZN'], 2)
        percent_inc = round(percent_diff - row['Percentage'], 2)

        # Book filter conditions:
        # Later used for sorting the books in the output csv file.
        conditions = [(lowest_price < row['BookFndr']),
                      (lowest_price <= 10),
                      (percent_diff >= 40),
                      ((lowest_price <= 1.1 * row['BookFndr']) & (lowest_price <= 12)), ]

        row['BookFndr'] = lowest_price
        row['Price diff'] = price_diff
        row['Percentage'] = percent_diff
        row['% increase'] = percent_inc

        # NH (New High) is set to 'True' if the first condition is met.
        # If not, looks if any other condition is met 'any()'. In that case, it
        # sets it to 'False'.
        # And if no condition is met, it leaves it unset/empty.
        #
        # Basically this new field helps sorting the books in the output csv.

        row['NH'] = True if conditions[0] else False if any(conditions) else ""

        # Convert dict to df and append to csv
        df_export = pd.DataFrame(row, index=[0])

        # Exports row by row to the 'temp_book_list.csv'
        if first_row == True:
            df_export.to_csv(EXPORT_FILE, mode='w', index=False, header=True)
            first_row = False
        else:
            df_export.to_csv(EXPORT_FILE, mode='a', index=False, header=False)

    time.sleep(t)

# ##############################################################################
#                               End of loop
# ##############################################################################

# Exit driver:
# If not, if yout Ctrl-C your way out of the script or if fails while scrapping,
# Selenium will remain open consuming precious RAM.
driver.quit()

# Sort csv file
df_csv = pd.read_csv(EXPORT_FILE)

df_csv = df_csv.sort_values(by=['NH', 'Percentage', 'BookFndr'], ascending=[False, False, True], ignore_index=True)

df_csv.to_csv(EXPORT_FILE, mode='w', index=False, header=True)
