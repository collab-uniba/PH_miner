import datetime
import logging
import os

from pytz import timezone
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from twisted.internet import defer
from twisted.internet import reactor

from db.orm.tables import Post
from logger import logging_config
from review_user_crawler.spiders.producthunt import ReviewSpider, UserSpider

logger = logging_config.get_logger(_dir=datetime.datetime.now(timezone('US/Pacific')).strftime("%Y-%m-%d"),
                                   name="ph_crawler", console_level=logging.INFO)

"""
Code to work around the twisted.internet.error.ReactorNotRestartable limitation of the Twisted library
See here: https://doc.scrapy.org/en/latest/topics/practices.html
"""


class CrawlersLauncher:

    def __init__(self, session):
        self.session = session
        self.review_urls = []
        self.profile_urls = []
        self.runner = CrawlerRunner()
        self.__configure_project_logging()

    @staticmethod
    def __configure_project_logging():
        cwd = os.getcwd()
        os.chdir(os.path.join('scraper', 'review_user_crawler'))
        scrapy_settings = get_project_settings()
        os.chdir(cwd)
        configure_logging(scrapy_settings)

    def setup_single_post_reviews(self, pid):
        logger.debug('Retrieving post with id %d' % pid)
        post_url = self.session.query(Post.discussion_url).filter_by(id=pid).one_or_none()
        if post_url:
            logger.debug('Building post-review url')
            self.review_urls = [post_url[0] + '/reviews']
        else:
            logger.error('No post found in database with id %d' % pid)

    def setup_post_reviews_crawler(self, day):
        logger.debug('Retrieving discussion urls for posts created on %s' % day)
        urls = self.session.query(Post.discussion_url).filter_by(day=day).all()
        if urls:
            logger.debug('Building post-review urls')
            self.review_urls = self.review_urls + [url[0] + '/reviews' for url in urls]
            self.review_urls = list(set(self.review_urls))

    def set_user_profiles_crawler(self, user_ids):
        logger.debug('Building user-profile urls')
        if user_ids:
            self.profile_urls = self.profile_urls + ['https://www.producthunt.com/@' + str(uid) for uid in user_ids]
            self.profile_urls = list(set(self.profile_urls))

    @defer.inlineCallbacks
    def __crawl(self, parsed_user_names):
        yield self.runner.crawl(ReviewSpider, **{'start_urls': self.review_urls,
                                                 'parsed_user_names': parsed_user_names})
        yield self.runner.crawl(UserSpider, **{'start_urls': self.profile_urls})
        reactor.stop()

    def start(self, parsed_user_names):
        self.__crawl(parsed_user_names)
        reactor.run()  # the script will block here until the last crawl call is finished
