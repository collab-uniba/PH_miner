# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import logging
from time import sleep

from pytz import timezone
from sqlalchemy.orm import exc

from db.orm.tables import *
from ph_miner import setup_db, setup_ph_client
from ph_py.error import ProductHuntError
from .items import ReviewItem, UserItem

db_config_file = '../../db/cfg/dbsetup.yml'
ph_config_file = '../../credentials.yml'
logger = logging.getLogger('scrapy_pipes')


def wait_if_no_rate_limit_remaining(ph_client):
    """ 900 API calls allowed every 15 minutes """
    limit_remaining, reset = ph_client.get_rate_limit_remaining()
    if limit_remaining < 50:
        logger.log(level=logging.INFO, msg='Going to wait for %s min to reset rate limit' % int(reset / 60))
        sleep(reset / 60)
    logger.log(level=logging.DEBUG, msg="API calls remaining %s (%s min to reset)" % (limit_remaining, int(reset / 60)))


class ReviewCrawlerPipeline(object):
    session = setup_db(db_config_file)
    ph_client = setup_ph_client(ph_config_file)
    today = datetime.datetime.now(timezone('US/Pacific')).strftime("%Y-%m-%d")

    def _store_review(self, item):
        try:
            wait_if_no_rate_limit_remaining(self.ph_client)
            reviewer = self.ph_client.get_user(item['reviewer_username'])
            if reviewer is not None:
                try:
                    post = self.session.query(Post.id, Post.name).filter_by(
                        discussion_url=item['post_url']).one_or_none()
                    if post:
                        logger.log(level=logging.INFO, msg='Storing review from %s on product \'%s\' into database' % (
                            item['reviewer_name'], post.name))
                        try:
                            review = self.session.query(Review).filter_by(reviewer_id=reviewer.id,
                                                                          post_id=post.id).one()
                            logger.log(level=logging.DEBUG,
                                       msg="Review from %s (%s) on %s already present, updating" % (
                                           item['reviewer_username'],
                                           reviewer.id, post.id))
                            review.helpful_count = item['helpful_count']
                            review.comments_count = item['comments_count']
                            review.overall_score = item['product_score']
                            self.session.add(review)
                        except exc.NoResultFound:
                            logger.log(level=logging.DEBUG,
                                       msg="Adding review from %s (%s) on %s" % (item['reviewer_username'],
                                                                                 reviewer.id, post.id))
                            b = Review.parse(reviewer.id, post.id, item['date'], item['sentiment'],
                                             item['product_score'],
                                             item['pros'], item['cons'], item['body'], item['helpful_count'],
                                             item['comments_count'])
                            self.session.add(b)

                        # if we're scraping a post reviews, then the post must be in the db
                        try:
                            p = self.session.query(Post).filter_by(id=post.id).one()
                            p.overall_review_score = item['product_score']
                            self.session.add(p)
                        except exc.NoResultFound:
                            logger.log(logging.ERROR, msg="No result found querying post \'%s\' (%s)" % (post.name,
                                                                                                         post.id))
                        # if we're scraping a post reviews, then the post history for today must be in the db
                        try:
                            ph = self.session.query(PostHistory).filter_by(post_id=post.id, date=self.today).one()
                            ph.overall_score = item['product_score']
                            self.session.add(ph)
                        except exc.NoResultFound:
                            logger.log(logging.ERROR,
                                       "No result found querying history of post \'%s\' (%s) on %s" % (post.name,
                                                                                                       post.id,
                                                                                                       self.today))
                        self.session.commit()
                    else:
                        logger.log(logging.ERROR,
                                   "No post found in database with url \'%s\', updating" % item['post_url'])
                except exc.NoResultFound as nrfe:
                    logger.log(level=logging.ERROR, msg="NoResultFound error in ReviewCrawlerPipeline._store_item()\n" +
                                                        str(nrfe))
        except ProductHuntError as phe:
            logger.log(level=logging.ERROR,
                       msg="ProductHunt API error in ReviewCrawlerPipeline._store_item()\n" + str(phe))

    def process_item(self, item, spider):
        if isinstance(item, ReviewItem):
            self._store_review(item)
        return item


class ReviewUserCrawlerPipeline(object):
    session = setup_db(db_config_file)
    ph_client = setup_ph_client(ph_config_file)
    today = datetime.datetime.now(timezone('US/Pacific')).strftime("%Y-%m-%d")

    def _store_user(self, user):
        """
        This should be called only after a phc.get_details_of_user(username) invocation and
        user is the result of that.
        """
        logger.log(level=logging.INFO, msg="Storing user %s and updating history if need be" % user.id)
        u = self.session.query(User).filter_by(id=user.id).one_or_none()
        if u:
            logger.log(level=logging.DEBUG, msg="User %s already present, updating" % user.id)
            u.headline = user.headline
            u.image_url = user.image_url["220px"]
            u.profile_url = user.profile_url
            u.twitter_username = user.twitter_username
            u.website_url = user.website_url
            #
            u.collections_made_count = user.collections_count
            u.followed_topics_count = user.followed_topics_count
            u.followers_count = user.followers_count
            u.followings_count = user.followings_count
            u.upvotes_count = user.votes_count
            u.hunts_count = user.posts_count
            u.apps_made_count = user.maker_of_count
        else:
            logger.log(level=logging.DEBUG, msg="Adding user %s" % user.id)
            u = User.parse(user)
        self.session.add(u)

        # update user history if there isn't an event for today yet
        uh = self.session.query(UserHistory).filter_by(user_id=user.id, date=self.today).one_or_none()
        if uh:
            logger.log(level=logging.DEBUG,
                       msg="User %s details already present in UserHistory for %s, ignore" % (user.id, self.today))
        else:
            uh = UserHistory.parse(user, self.today)
            logger.log(level=logging.DEBUG,
                       msg="Adding entry fot user \'%s\' to UserHistory for %s" % (user.id, self.today))
            self.session.add(uh)
        self.session.commit()

        self._store_user_hunts(user.id, user.posts)
        self._store_user_apps_made(user.id, user.maker_of)
        self._store_user_followers(user.id, user.followers)
        self._store_user_followings(user.id, user.followings)
        self._store_user_votes(user.id, user.votes)

        return u, uh

    def _store_user_hunts(self, user_id, hunts):
        if hunts:
            logger.log(level=logging.DEBUG, msg="Storing hunts of user %s" % user_id)
            elems = [(elem["id"], elem["created_at"]) for elem in hunts]
            for post_id, date in elems:
                e = self.session.query(UserHuntsList).filter_by(user_id=user_id, post_id=post_id).one_or_none()
                if e:
                    logger.log(level=logging.DEBUG,
                               msg="Post %s hunted by user %s already present, ignore" % (post_id, user_id))
                else:
                    logger.log(level=logging.DEBUG, msg="Adding post %s hunted by user %s" % (post_id, user_id))
                    e = UserHuntsList(user_id, post_id, date)
                    self.session.add(e)
            self.session.commit()

    def _store_user_apps_made(self, user_id, apps):
        if apps:
            logger.log(level=logging.INFO, msg="Storing apps made by user %s" % user_id)
            elems = [(elem["id"], elem["created_at"]) for elem in apps]
            for post_id, date in elems:
                e = self.session.query(UserAppsMadeList).filter_by(user_id=user_id, post_id=post_id).one_or_none()
                if e:
                    logger.log(level=logging.DEBUG,
                               msg="App %s made by user %s already present, ignore" % (post_id, user_id))
                else:
                    logger.log(level=logging.DEBUG, msg="Adding app %s made by user %s" % (post_id, user_id))
                    e = UserAppsMadeList(user_id, post_id, date)
                    self.session.add(e)
            self.session.commit()

    def _store_user_followers(self, user_id, fof):
        logger.log(level=logging.INFO, msg="Storing followers of user %s" % user_id)
        if fof:
            elems = [(elem["id"], elem["created_at"]) for elem in fof]
            for _id, date in elems:
                e = self.session.query(UserFollowerList).filter_by(user_id=user_id, follower_id=_id).one_or_none()
                if e:
                    logger.log(level=logging.DEBUG,
                               msg="Follower %s of user %s already present, ignore" % (_id, user_id))
                else:
                    logger.log(level=logging.DEBUG, msg="Adding follower %s of user %s" % (_id, user_id))
                    e = UserFollowerList(user_id, _id, date)
                    self.session.add(e)
            self.session.commit()

    def _store_user_followings(self, user_id, fof):
        logger.log(level=logging.INFO, msg="Storing followings of user %s" % user_id)
        if fof:
            elems = [(elem["id"], elem["created_at"]) for elem in fof]
            for _id, date in elems:
                e = self.session.query(UserFollowingList).filter_by(user_id=user_id, following_id=_id).one_or_none()
                if e:
                    logger.log(level=logging.DEBUG,
                               msg="Following %s of user %s already present, ignore" % (_id, user_id))
                else:
                    logger.log(level=logging.DEBUG, msg="Adding following %s of user %s" % (_id, user_id))
                    e = UserFollowingList(user_id, _id, date)
                    self.session.add(e)
            self.session.commit()

    def _store_user_votes(self, user_id, votes):
        if votes:
            logger.log(level=logging.INFO, msg="Storing votes of user %s" % user_id)
            elems = [(elem["post_id"], elem["created_at"]) for elem in votes]
            for post_id, date in elems:
                e = self.session.query(UserVoteList).filter_by(user_id=user_id, post_id=post_id).one_or_none()
                if e:
                    logger.log(level=logging.DEBUG,
                               msg="Vote of user %s on post %s already present, ignore" % (user_id, post_id))
                else:
                    logger.log(level=logging.DEBUG, msg="Adding vote of user %s on post %s" % (user_id, post_id))
                    e = UserVoteList(user_id, post_id, date)
                    self.session.add(e)
            self.session.commit()

    """
    In the future, when API support reviews, this will have to be moved to
    ph_miner.py file and the duplicate _store_* methods above will be useless.
    """

    def _store_reviewer(self, item, spider):
        username = item['reviewer_username']
        if username not in spider.parsed_user_names:
            logger.log(level=logging.INFO, msg='Storing reviewer %s' % username)
            try:
                wait_if_no_rate_limit_remaining(self.ph_client)
                reviewer = self.ph_client.get_details_of_user(username)
                if reviewer:
                    # update user
                    spider.parsed_user_names.add(username)
                    user, uh = self._store_user(reviewer)
                    # update elements of the user that can only be accessed through the scraper
                    user.badges = item['reviewer_badges']
                    if item['reviewer_daily_upvote_streak']:
                        user.daily_upvote_streak = item['reviewer_daily_upvote_streak']
                    user.collections_followed_count = int(item['reviewer_collections_followed_count'])
                    self.session.add(user)

                    # update user history if there isn't an event for today yet
                    if uh:
                        logger.log(level=logging.DEBUG,
                                   msg="User %s(%s) details already present in UserHistory for %s, ignore" % (username,
                                                                                                              reviewer.id,
                                                                                                              self.today))
                    else:
                        uh = UserHistory.parse(reviewer, self.today)
                        logger.log(level=logging.DEBUG,
                                   msg="Adding entry for user %s(%s) to UserHistory for %s" % (
                                       username, reviewer.id, self.today))

                    # either case, update elements of user history that can only be accessed thru the scraper
                    uh.badges = item['reviewer_badges']
                    if item['reviewer_daily_upvote_streak']:
                        uh.daily_upvote_streak = item['reviewer_daily_upvote_streak']
                    uh.collections_followed_count = int(item['reviewer_collections_followed_count'])
                    self.session.add(uh)

                    self.session.commit()
            except ProductHuntError as phe:
                logger.log(level=logging.ERROR, msg=str(phe))

    def process_item(self, item, spider):
        if isinstance(item, ReviewItem):
            self._store_reviewer(item, spider)
        return item


class UserCrawlerPipeline(object):
    session = setup_db(db_config_file)
    ph_client = setup_ph_client(ph_config_file)
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    def _store_user(self, item):
        user_id = item['id']
        if user_id:
            try:
                user = self.session.query(User).filter_by(id=user_id).one()
                user.badges = item['badges']
                if item['daily_upvote_streak']:
                    user.daily_upvote_streak = item['daily_upvote_streak']
                user.collections_followed_count = int(item['collections_followed_count'])
                self.session.add(user)
            except exc.NoResultFound:
                logger.log(level=logging.ERROR, msg="No result found querying User table by id: %s" % user_id)
            try:
                user_history = self.session.query(UserHistory).filter_by(user_id=user_id, date=self.today).one()
                user_history.badges = item['badges']
                if item['daily_upvote_streak']:
                    user_history.daily_upvote_streak = item['daily_upvote_streak']
                user_history.collections_followed_count = int(item['collections_followed_count'])
                self.session.add(user_history)
            except exc.NoResultFound:
                logger.log(level=logging.DEBUG, msg="No result found querying UserHistory table by id: %s" % user_id)
            self.session.commit()

    def process_item(self, item, spider):
        if isinstance(item, UserItem):
            self._store_user(item)
        return item
