import logging
import time
from datetime import datetime

import scrapy
from bs4 import BeautifulSoup
from pytz import timezone
from scrapy.spiders import CrawlSpider
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from review_user_crawler.items import ReviewItem, UserItem


class ReviewSpider(CrawlSpider):
    name = 'producthunt_reviews'
    allowed_domains = ['producthunt.com']
    start_urls = []
    logger = logging.getLogger('scrapy')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        """ assumes Chrome web-driver to be installed and on the PATH """
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--test-type")
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")  # for ubuntu compatibility
        self.driver = webdriver.Chrome(chrome_options=options)

        self.today = datetime.now(timezone('US/Pacific')).strftime("%Y-%m-%d")

        start_urls = kwargs.pop('start_urls', [])
        if start_urls:
            self.start_urls = start_urls
        else:
            self.start_urls = ['https://www.producthunt.com/posts/flow-e-2-0',
                               'https://www.producthunt.com/posts/github-for-unity']  # for debugging purposes only

        parsed_user_names = kwargs.pop('parsed_user_names', [])
        if parsed_user_names:
            self.parsed_user_names = parsed_user_names
        else:
            self.parsed_user_names = {'chrismessina', 'rrhoover'}  # for debugging purposes only

    def parse_reviewer_url(self, response):
        review_item = response.meta.get('review_item')
        self.driver.get(response.url)
        """ explicit wait for page to load """
        try:
            WebDriverWait(self.driver, 60)
        except WebDriverException as wde:
            self.logger.log(level=logging.ERROR, msg="Error on WebDriverWait\n" + str(wde))
            self.driver.save_screenshot('webdriver-error.png')
            return
        try:
            streak = scrapy.Selector(text=self.driver.page_source).xpath(
                '//span[@class="streak_f9e9f"]/text()').extract()
            if streak:
                streak = ''.join(streak)
            username = response.url.split('https://www.producthunt.com')[1]
            try:
                collections_followed_count = scrapy.Selector(text=self.driver.page_source).xpath(
                    '//a[@href="%s/followed_collections"]/em/text()' % username).extract()[0]
            except IndexError:
                self.logger.warning('Index error parsing collections followed of user \'%s\', recovering...' % username)
                try:
                    collections_followed_count = scrapy.Selector(text=self.driver.page_source).xpath(
                        '//a[@href="/%s/followed_collections"]/em/text()' % username).extract()[0]
                except IndexError:
                    self.logger.error('Unrecoverable IndexError parsing collections followed of user \'%s\'' % username)
                    collections_followed_count = -1
            review_item['reviewer_badges'] = None
            review_item['reviewer_daily_upvote_streak'] = streak
            review_item['reviewer_collections_followed_count'] = collections_followed_count
            yield review_item
        except NoSuchElementException as nse:
            self.logger.log(level=logging.ERROR, msg="NoSuchElementException error scraping reviewer info\n" + str(nse))

    def parse(self, response):
        self.driver.get(response.url)
        # explicit wait for page to load
        try:
            WebDriverWait(self.driver, 60)
            while (scrapy.Selector(text=self.driver.page_source).xpath(
                    '//div[@class="loadMore_f1388"]/button').extract()):
                self.driver.find_element_by_css_selector(
                    '.button_30e5c.fluidSize_c4dc2.mediumSize_c215f.simpleVariant_8a863').click()
                time.sleep(3)
        except TimeoutException:
            self.logger.log(logging.ERROR, msg='Timeout error waiting for resolution of {0}'.format(response.url))
            self.driver.save_screenshot('timeout-error.png')
            return
        except WebDriverException as wde:
            self.logger.log(level=logging.ERROR, msg=str("Error on WebDriverWait\n" + str(wde)))
            self.driver.save_screenshot('webdriver-error.png')
            return
        try:
            overall_score = \
                scrapy.Selector(text=self.driver.page_source) \
                    .xpath(
                    '//span[@class="font_9d927 black_476ed small_231df normal_d2e66 numericalRating_42e93 lineHeight_042f1 underline_57d3c"]/text()') \
                    .extract()
            overall_score = ''.join(overall_score)

            review_list = scrapy.Selector(text=self.driver.page_source).xpath('//ul[@class="list_5def0"]/li').extract()
            for review in review_list:
                soup = BeautifulSoup(review, 'html.parser')
                review_item = ReviewItem()
                review_item['product_score'] = overall_score
                review_item['post_url'] = response.url.split('/reviews')[0]

                reviewer = soup.find('span',
                                     {
                                         'class': 'font_9d927 black_476ed small_231df semiBold_e201b headline_8ed42 lineHeight_042f1 underline_57d3c'})
                review_item['reviewer_name'] = reviewer.text
                temp = reviewer.next_element.attrs['href']
                review_item['reviewer_username'] = temp[2:]
                review_item[
                    'reviewer_url'] = 'https://www.producthunt.com' + temp
                try:
                    review_item['reviewer_tagline'] = soup.find('span', {
                        'class': 'font_9d927 grey_bbe43 small_231df normal_d2e66 text_afddf lineHeight_042f1 underline_57d3c'}).text
                except AttributeError:
                    review_item['reviewer_tagline'] = ''
                review_item['pros'] = soup.find('div', {'class': 'pros_c0958'}).text[6:].strip()
                review_item['cons'] = soup.find('div', {'class': 'cons_2aaba'}).text[6:].strip()
                review_item['body'] = soup.find('div', {'class': 'body_b651b'}).text
                review_item['helpful_count'] = soup.find('span', {
                    'class': 'font_9d927 xSmall_1a46e semiBold_e201b buttonContainer_b6eb3 lineHeight_042f1 underline_57d3c uppercase_a49b4'}).text.split()[
                    2]
                review_item['comments_count'] = soup.find('a', {
                    'class': 'font_9d927 grey_bbe43 xSmall_1a46e semiBold_e201b lineHeight_042f1 underline_57d3c uppercase_a49b4'}).text.split(
                    '(')[1][:1]
                review_item['date'] = soup.find('time').attrs['datetime']
                review_item['sentiment'] = soup.find('div', {'class': 'sentiment_1f783'}).attrs['class'][1].split('_')[
                    0]
                yield scrapy.Request(url=review_item['reviewer_url'], callback=self.parse_reviewer_url,
                                     meta={'review_item': review_item})
        except NoSuchElementException:
            self.logger.log(logging.ERROR, msg='Unexpected structure error on page %s' % response.url)


class UserSpider(CrawlSpider):
    name = 'producthunt_users'
    allowed_domains = ['producthunt.com']
    start_urls = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        """ assumes Chrome web-driver to be installed and on the PATH """
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--test-type")
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")  # for ubuntu compatibility
        self.driver = webdriver.Chrome(chrome_options=options)

        start_urls = kwargs.pop('start_urls', [])
        if start_urls:
            self.start_urls = start_urls
        else:
            self.start_urls = ['https://www.producthunt.com/@alexandru_constantinescu',
                               'https://www.producthunt.com/@rrhoover',
                               'https://www.producthunt.com/@chrismessina']  # for debugging purposes only

    def parse(self, response):
        self.driver.get(response.url)
        """ explicit wait for page to load """
        try:
            user_item = UserItem()
            username = response.url.split('https://www.producthunt.com/')[1]
            """ workaround, sometimes split return names with a leading '/'
                this causes the rest of the script to fail
                it happens very seldom, haven't found the root cause yet
            """
            if username[0] == '/':
                username = username[1:]
            try:
                _id = scrapy.Selector(text=self.driver.page_source).xpath(
                    '//span[@class="font_9d927 white_ce488 small_231df normal_d2e66 lineHeight_042f1 underline_57d3c"]/text()').extract()[
                    1]
                user_item['id'] = _id
            except IndexError:
                self.logger.error('Index error extracting the user id of \'%s\'' % username)
            streak = scrapy.Selector(text=self.driver.page_source).xpath(
                '//span[@class="streak_f9e9f"]/text()').extract()
            if streak:
                streak = ''.join(streak)
                user_item['daily_upvote_streak'] = streak
            try:
                collections_followed_count = scrapy.Selector(text=self.driver.page_source).xpath(
                    '//a[@href="%s/followed_collections"]/em/text()' % username).extract()[0]
                user_item['collections_followed_count'] = collections_followed_count
            except IndexError:
                self.logger.warning('Index error parsing collections followed of user \'%s\', recovering...' % username)
                try:
                    collections_followed_count = scrapy.Selector(text=self.driver.page_source).xpath(
                        '//a[@href="/%s/followed_collections"]/em/text()' % username).extract()[0]
                    user_item['collections_followed_count'] = collections_followed_count
                except IndexError:
                    self.logger.error('Unrecoverable IndexError parsing collections followed of user \'%s\'' % username)
                    user_item['collections_followed_count'] = -1
            user_item['badges'] = None
            yield user_item

        except NoSuchElementException:
            self.logger.log(logging.ERROR, msg='Unexpected structure error on page %s' % response.url)
