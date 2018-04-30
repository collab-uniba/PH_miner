import logging
import time
from datetime import datetime
from logging import log

import scrapy
from bs4 import BeautifulSoup
from scrapy.spiders import CrawlSpider
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from review_user_crawler.items import ReviewCrawlerItem


class ProducthuntSpider(CrawlSpider):
    name = 'producthunt'
    allowed_domains = ['producthunt.com']
    start_urls = []
    today = datetime.now().strftime("%Y-%m-%d")

    def __init__(self, start_urls=None, browser='Chrome', *a, **kw):
        super(ProducthuntSpider, self).__init__(*a, **kw)

        if browser == "Chrome":
            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-certificate-errors')
            options.add_argument("--test-type")
            options.add_argument("--headless")
            self.driver = webdriver.Chrome(chrome_options=options)

        self.start_urls = start_urls.split(',')

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
            log(logging.ERROR, 'Timeout error waiting for resolution of {0}'.format(response.url))
            self.driver.save_screenshot('timeout-error.png')
            return
        except WebDriverException as wde:
            log(level=logging.ERROR, msg=str(wde))
            self.driver.save_screenshot('webdriver-error.png')
            return
        try:
            overall_score = \
                scrapy.Selector(text=self.driver.page_source) \
                    .xpath(
                    '//span[@class="font_9d927 black_476ed small_231df normal_d2e66 numericalRating_42e93"]/text()') \
                    .extract()
            overall_score = ''.join(overall_score)

            review_list = scrapy.Selector(text=self.driver.page_source).xpath('//ul[@class="list_5def0"]/li').extract()
            for review in review_list:
                soup = BeautifulSoup(review, 'html.parser')
                review_item = ReviewCrawlerItem()
                review_item['product_score'] = overall_score
                review_item['post_url'] = response.url.split('/reviews')[0]

                reviewer = soup.find('span',
                                     {'class': 'font_9d927 black_476ed small_231df semiBold_e201b headline_8ed42'})
                review_item['reviewer_name'] = reviewer.text
                temp = reviewer.next_element.attrs['href']
                review_item['reviewer_username'] = temp[2:]
                review_item['reviewer_url'] = 'https://www.producthunt.com' + temp
                try:
                    review_item['reviewer_tagline'] = soup.find('span', {
                        'class': 'font_9d927 grey_bbe43 small_231df normal_d2e66 text_afddf'}).text
                except AttributeError:
                    review_item['reviewer_tagline'] = ''

                review_item['pros'] = soup.find('div', {'class': 'pros_c0958'}).text[6:].strip()
                review_item['cons'] = soup.find('div', {'class': 'cons_2aaba'}).text[6:].strip()
                review_item['body'] = soup.find('div', {'class': 'body_b651b'}).text
                review_item['helpful_count'] = soup.find('span', {
                    'class': 'font_9d927 xSmall_1a46e semiBold_e201b buttonContainer_b6eb3 uppercase_a49b4'}).text.split()[
                    2]
                review_item['comments_count'] = soup.find('a', {
                    'class': 'font_9d927 grey_bbe43 xSmall_1a46e semiBold_e201b uppercase_a49b4'}).text.split('(')[1][
                                                :1]
                review_item['date'] = soup.find('time').attrs['datetime']
                review_item['sentiment'] = soup.find('div', {'class': 'sentiment_1f783'}).attrs['class'][1].split('_')[
                    0]
                yield review_item

            # matches = re.findall(r'/@\w+', self.driver.page_source, re.MULTILINE)
            # for m in set(matches):
            #     review_user = ReviewUserCrawlerItem()
            #     review_user['reviewer_username'] = m[2:]
            #     yield review_user

        except NoSuchElementException:
            log(logging.ERROR, 'Unexpected structure error on page %s' % response.url)
            return
