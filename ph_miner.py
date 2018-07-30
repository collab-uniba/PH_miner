#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2018 Collab
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
    PH_miner - A Python 3 script to mine the 'products of the day' from Product Hunt
"""

__author__ = '@bateman'
__license__ = "MIT"
__date__ = '22-04-2018'
__version_info__ = (0, 2, 1)
__version__ = '.'.join(str(i) for i in __version_info__)
__home__ = 'https://github.com/collab-uniba/PH_miner'
__download__ = 'https://github.com/collab-uniba/PH_miner/archive/master.zip'

import logging
import os
import re
import sys
import time
from datetime import timedelta
from getopt import getopt, GetoptError

import yaml
from bs4 import BeautifulSoup
from pytz import timezone
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy import or_
from sqlalchemy.orm import exc

from db import SessionWrapper
from db.orm.tables import *
from logger import logging_config
from ph_crawler import CrawlersLauncher
from ph_py import ProductHuntClient
from ph_py.error import ProductHuntError


class PhMiner:

    def __init__(self, session, phc, today=None, today_dt=None, user_details=None, user_scrape=None):
        self.session = session
        self.phc = phc
        self.today = today
        self.today_dt = today_dt
        self.user_details_once_a_day = user_details
        self.user_scrape_update_pending = user_scrape
        """ for user badges from discussion_url """
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--test-type")
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")  # for ubuntu compatibility
        self.driver = webdriver.Chrome(chrome_options=options)

    def clean_up(self):
        self.driver.quit()

    def get_newest_posts(self):
        discussion_urls = list()
        slugs = list()
        post_ids = list()

        url = 'https://www.producthunt.com/newest'
        try:
            self.driver.get(url)
            """ explicit wait for page to load """
            WebDriverWait(self.driver, 120)
            time.sleep(10)
            bs = BeautifulSoup(self.driver.page_source, "lxml")
            posts = bs.find_all("ul", {"class": "postsList_b2208"})
            posts = posts[len(posts) - 1].contents
            for post in posts:
                try:
                    extract = post.find_all("a", {"class": "link_523b9"})[0]['href'][7:]
                    slugs.append(extract)
                    discussion_urls.append('https://www.producthunt.com/posts/' + extract)
                except IndexError:
                    pass  # ignore promoted posts

            i = -1
            for slug in slugs[:]:
                i += 1
                logger.info("Retrieving id for post \'%s\'" % slug)
                try:
                    _str = bs.find_all('script')[13].get_text()
                    res = re.findall(pattern=r'"shortened_url":"/r/p/(\d{6})","slug":"%s"' % slug, string=_str)
                    if res:
                        post_id = int(res[0])
                        post_ids.append(post_id)
                        """ include yesterday as there can be issues for post created around midnight of prev day """
                        yesterday = (self.today_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                        np = self.session.query(NewestPost).filter_by(post_id=post_id).filter(
                            or_(NewestPost.day == self.today,
                                NewestPost.day == yesterday)).one_or_none()
                        if not np:
                            np = NewestPost(post_id, self.today, discussion_urls[i])
                            self.session.add(np)
                    else:
                        logger.warning('No id found for post \'%s\' (likely a promoted post), skipping it' % slug)
                        slugs.remove(slug)
                        discussion_urls.remove(discussion_urls[i])
                except IndexError as ie:
                    logger.error(str(ie) + 'Processing \'%s\' (iteration \'%d\')'.format(slug, i))
                except Exception as e:
                    logger.error(str(e))
            self.session.commit()

            """ scrape social media links for the post """
            i = -1
            for url in discussion_urls:
                i += 1
                self.driver.get(url)
                WebDriverWait(self.driver, 120)
                time.sleep(10)
                bs = BeautifulSoup(self.driver.page_source, "lxml")
                posts = bs.find_all("a", {"class": "item_6443c"})
                try:
                    logger.info('Retrieving social link for post \'%s\'' % slugs[i])
                    for p in posts:
                        title = p['title']
                        href = p['href']
                        link = self.session.query(PostSocialLinks).filter_by(post_id=post_ids[i],
                                                                             site=title).one_or_none()
                        if not link:
                            link = PostSocialLinks(post_ids[i], title, href)
                        self.session.add(link)
                except IndexError:
                    logger.error('Index error retrieving social link for post \'%s\'' % slugs[i])
            self.session.commit()
        except TimeoutException:
            logger.error('Timeout error waiting for resolution of {0}'.format(url))
            self.driver.save_screenshot('timeout_%s.png' % url)
        except WebDriverException as wde:
            logger.error(str(wde))
            self.driver.save_screenshot('webdriver_%s.png' % url)

    def get_post(self, post_id):
        if not self.user_details_once_a_day:
            self.user_details_once_a_day = set()
        self.meta_store(post_id)
        return self.user_details_once_a_day, self.user_scrape_update_pending

    def get_todays_featured_posts(self):
        if not self.user_details_once_a_day:
            self.user_details_once_a_day = set()
        self.phc.wait_if_no_rate_limit_remaining()
        daily_posts = [post.id for post in self.phc.get_todays_posts()]
        """ get details for each post by id """
        for post_id in daily_posts:
            self.meta_store(post_id)
        return self.user_details_once_a_day, self.user_scrape_update_pending

    def get_featured_posts_at(self, day):
        if not self.user_details_once_a_day:
            self.user_details_once_a_day = set()
        self.phc.wait_if_no_rate_limit_remaining()
        daily_posts = [post.id for post in self.phc.get_specific_days_posts(day)]
        """ get details for each post by id """
        for post_id in daily_posts:
            self.meta_store(post_id)
        return self.user_details_once_a_day, self.user_scrape_update_pending

    def get_todays_non_featured_posts(self):
        if not self.user_details_once_a_day:
            self.user_details_once_a_day = set()
        """ today's newest posts... """
        todays_newest_posts = self.session.query(NewestPost.post_id).filter_by(day=self.today).all()
        """ ... that are *NOT* featured, i.e., not in Post table """
        todays_featured = self.session.query(Post.id).filter_by(day=self.today).all()
        """ get details for each non-featured today's post """
        todays_non_featured_posts = set(todays_newest_posts) - set(todays_featured)
        logger.debug("There are %d non-featured posts to retrieve", len(todays_non_featured_posts))
        for post_id in todays_non_featured_posts:
            self.meta_store(post_id)
        return self.user_details_once_a_day, self.user_scrape_update_pending

    def update_posts_at_day(self, day):
        if not self.user_details_once_a_day:
            self.user_details_once_a_day = set()
        daily_posts = self.session.query(Post.id).filter_by(day=day).all()
        """ get details for each post by id """
        for post_id in daily_posts:
            self.meta_store(post_id)
        return self.user_details_once_a_day, self.user_scrape_update_pending

    def meta_store(self, post_id):
        try:
            self.phc.wait_if_no_rate_limit_remaining()
            post = self.phc.get_details_of_post(post_id=post_id)
            self.store(post, self.today)
            self.user_scrape_update_pending = self.user_scrape_update_pending.union(set(
                [maker.username for maker in post.makers]))
            self.user_scrape_update_pending.add(post.user.username)
        except ProductHuntError as phe:
            logger.warning('Error storing post with id \'%s\'' % post_id)
            logger.warning(phe.error_message)
            logger.warning(phe.status_code)

    def store(self, post, day):
        self._store_post(post, day)

        hunter = post.user
        self._store_post_hunter(hunter, post, day)

        makers = post.makers
        self._store_post_makers(makers, post, day)

        comments = post.comments
        self._store_post_comments_and_commenters(comments, post, day)
        self._store_user_badges(post.discussion_url)

        votes = post.votes
        self._store_post_votes(post, votes)

        badges = post.badges
        self._store_post_badges(badges, post)

        topics = post.topics
        self._store_post_topics(post, topics)

        ext_links = post.external_links
        self._store_post_external_links(ext_links, post)

        inst_links = post.install_links
        self._store_post_install_links(inst_links, post)

        rel_links = post.related_links
        self._store_post_related_links(post, rel_links)

        rel_posts = post.related_posts
        self._store_post_related_posts(post, rel_posts)

        media = post.media
        self._store_post_media(media, post)

    def _store_post(self, post, day):
        assert post is not None, "Fatal error trying to store a null post"
        p = self.session.query(Post).filter_by(id=post.id).one_or_none()
        if p:
            logger.info("Post \'%s\' (%s) already present, updating" % (post.name, post.id))
            """ update """
            p.name = post.name
            p.tagline = post.tagline
            p.comments_count = post.comments_count
            p.votes_count = post.votes_count
            p.redirect_url = post.redirect_url
            p.screenshot_url = post.screenshot_url["850px"]
            p.maker_inside = post.maker_inside
            p.description = post.description
            p.featured = post.featured
            p.exclusive = post.exclusive
            p.product_state = post.product_state
            p.category_id = post.category_id
            p.reviews_count = post.reviews_count
            p.positive_reviews_count = post.positive_reviews_count
            p.negative_reviews_count = post.negative_reviews_count
            p.neutral_reviews_count = post.neutral_reviews_count
            p.platforms = post.platforms
        else:
            logger.info("Adding post \'%s\' (%s)" % (post.name, post.id))
            p = Post(post.id, post.name, post.tagline, post.created_at, day, post.comments_count,
                     post.votes_count, post.discussion_url, post.redirect_url, post.screenshot_url["850px"],
                     post.maker_inside, post.user.id, post.description, post.featured, post.exclusive,
                     post.product_state, post.category_id,
                     None,  # overall_review_score available through review mining
                     post.reviews_count, post.positive_reviews_count, post.negative_reviews_count,
                     post.neutral_reviews_count, post.platforms)
        self.session.add(p)

        ph = self.session.query(PostHistory).filter_by(post_id=post.id, date=self.today).one_or_none()
        if ph:
            # TODO XXX maybe we should update this one too...
            # TODO in case, remember to update also the scraper cloned part
            logger.info("Post history already up to date")
        else:
            logger.info("Storing post history")
            ph = PostHistory.parse(post, self.today)
            self.session.add(ph)
        self.session.commit()

    def _store_user_followers(self, user_id, fof):
        logger.debug("Storing followers of user %s" % user_id)
        if fof:
            elems = [(elem["id"], elem["created_at"]) for elem in fof]
            for _id, date in elems:
                e = self.session.query(UserFollowerList).filter_by(user_id=user_id, follower_id=_id).one_or_none()
                if e:
                    logger.debug("Follower %s of user %s already present, ignore" % (_id, user_id))
                else:
                    logger.debug("Adding follower %s of user %s" % (_id, user_id))
                    e = UserFollowerList(user_id, _id, date)
                    self.session.add(e)
            self.session.commit()

    def _store_user_followings(self, user_id, fof):
        logger.debug("Storing followings of user %s" % user_id)
        if fof:
            elems = [(elem["id"], elem["created_at"]) for elem in fof]
            for _id, date in elems:
                e = self.session.query(UserFollowingList).filter_by(user_id=user_id, following_id=_id).one_or_none()
                if e:
                    logger.debug("Following %s of user %s already present, ignore" % (_id, user_id))
                else:
                    logger.debug("Adding following %s of user %s" % (_id, user_id))
                    e = UserFollowingList(user_id, _id, date)
                    self.session.add(e)
            self.session.commit()

    def _store_user_votes(self, user_id, votes):
        if votes:
            logger.debug("Storing votes of user %s" % user_id)
            elems = [(elem["post_id"], elem["created_at"]) for elem in votes]
            for post_id, date in elems:
                e = self.session.query(UserVoteList).filter_by(user_id=user_id, post_id=post_id).one_or_none()
                if e:
                    logger.debug("Vote of user %s on post %s already present, ignore" % (user_id, post_id))
                else:
                    logger.debug("Adding vote of user %s on post %s" % (user_id, post_id))
                    e = UserVoteList(user_id, post_id, date)
                    self.session.add(e)
            self.session.commit()

    def _store_user_hunts(self, user_id, hunts):
        if hunts:
            logger.debug("Storing hunts of user %s" % user_id)
            elems = [(elem["id"], elem["created_at"]) for elem in hunts]
            for post_id, date in elems:
                e = self.session.query(UserHuntsList).filter_by(user_id=user_id, post_id=post_id).one_or_none()
                if e:
                    logger.debug("Post %s hunted by user %s already present, ignore" % (post_id, user_id))
                else:
                    logger.debug("Adding post %s hunted by user %s" % (post_id, user_id))
                    e = UserHuntsList(user_id, post_id, date)
                    self.session.add(e)
            self.session.commit()

    def _store_user_apps_made(self, user_id, apps):
        if apps:
            logger.debug("Storing apps made by user %s" % user_id)
            elems = [(elem["id"], elem["created_at"]) for elem in apps]
            for post_id, date in elems:
                e = self.session.query(UserAppsMadeList).filter_by(user_id=user_id, post_id=post_id).one_or_none()
                if e:
                    logger.debug("App %s made by user %s already present, ignore" % (post_id, user_id))
                else:
                    logger.debug("Adding app %s made by user %s" % (post_id, user_id))
                    e = UserAppsMadeList(user_id, post_id, date)
                    self.session.add(e)
            self.session.commit()

    def _store_post_hunter(self, h, post, day):
        logger.info("Storing hunter")
        if h.username not in self.user_details_once_a_day:
            try:
                hunter = self.phc.get_details_of_user(h.username)
                if hunter:
                    self.user_details_once_a_day.add(hunter.username)
                    self._store_user(hunter)
                    # store hunts
                    user = self.session.query(Hunts).filter_by(hunter_id=hunter.id, post_id=post.id).one_or_none()
                    if user:
                        logger.debug("Hunt of post %s by %s already present, ignore" % (post.id, hunter.id))
                    else:
                        logger.debug("Adding hunt of post %s by user %s" % (post.id, hunter.id,))
                        b = Hunts(hunter.id, post.id)
                        self.session.add(b)
                    self.session.commit()
            except ProductHuntError as e:
                logger.error(str(e))
        else:
            logger.debug("Detailed info for user %s have been already requested on day %s" % (h.username, day))

    def _store_post_makers(self, makers, post, day):
        logger.info("Storing makers")
        if makers:
            for maker in makers:
                if maker.username not in self.user_details_once_a_day:
                    m = self.phc.get_details_of_user(maker.username)
                    if m:
                        try:
                            self.user_details_once_a_day.add(m.username)
                            self._store_user(m)
                            # store apps
                            try:
                                self.session.query(Apps).filter_by(maker_id=maker.id, post_id=post.id).one()
                                logger.debug("App %s made by %s already present, ignore" % (post.id, maker.id))
                            except exc.NoResultFound:
                                logger.debug("Adding app %s made by %s" % (post.id, maker.id))
                                b = Apps(maker.id, post.id)
                                self.session.add(b)
                        except ProductHuntError as e:
                            logger.error(str(e))
                else:
                    logger.debug("Detailed info for user %s have been already requested on day %s" % (maker.username,
                                                                                                      day))
                self.session.commit()

    def _store_user(self, user):
        """
        This should be called only after a phc.get_details_of_user(username) invocation and
        user is the result of that.
        """
        logger.debug("Storing user %s and updating history if need be" % user.id)
        u = self.session.query(User).filter_by(id=user.id).one_or_none()
        if u:
            logger.debug("User %s already present, updating" % user.id)
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
            logger.debug("Adding user %s" % user.id)
            u = User.parse(user)
        self.session.add(u)

        """ update user history if there isn't an event for today yet """
        uh = self.session.query(UserHistory).filter_by(user_id=user.id, date=self.today).one_or_none()
        if uh:
            logger.debug("User %s details already present in UserHistory for %s, ignore" % (user.id, self.today))
        else:
            uh = UserHistory.parse(user, self.today)
            logger.debug("Adding entry fot user \'%s\' to UserHistory for %s" % (user.id, self.today))
            self.session.add(uh)
        self.session.commit()

        self._store_user_hunts(user.id, user.posts)
        self._store_user_apps_made(user.id, user.maker_of)
        self._store_user_followers(user.id, user.followers)
        self._store_user_followings(user.id, user.followings)
        self._store_user_votes(user.id, user.votes)

    def _store_post_media(self, media, post):
        if media is not None:
            logger.info("Storing media")
            for m in media:
                try:
                    self.session.query(Media).filter_by(id=m.id, post_id=post.id).one()
                    logger.debug("Media  %s already present, ignore" % m.id)
                except exc.NoResultFound:
                    b = Media.parse(m, post.id)
                    self.session.add(b)
                    logger.debug("Adding media %s" % m.id)
            self.session.commit()

    def _store_post_related_posts(self, post, rel_posts):
        if rel_posts is not None:
            logger.info("Storing related posts")
            for rel_post in rel_posts:
                try:
                    self.session.query(RelatedPost).filter_by(post_id=post.id, related_post_id=rel_post).one()
                    logger.debug("Related post %s already present, ignore" % rel_post)
                except exc.NoResultFound:
                    b = RelatedPost(post.id, rel_post)
                    self.session.add(b)
                    logger.debug("Adding related post %s" % rel_post)
            self.session.commit()

    def _store_post_related_links(self, post, rel_links):
        if rel_links is not None:
            logger.info("Storing related links")
            for link in rel_links:
                try:
                    self.session.query(RelatedLink).filter_by(id=link.id, post_id=post.id).one()
                    logger.debug("Related link %s already present, ignore" % link.id)
                except exc.NoResultFound:
                    b = RelatedLink.parse(link, post.id)
                    self.session.add(b)
                    logger.debug("Adding related link %s" % link.id)
            self.session.commit()

    def _store_post_install_links(self, inst_links, post):
        if inst_links is not None:
            logger.info("Storing install links")
            for link in inst_links:
                try:
                    self.session.query(InstallLink).filter_by(redirect_url=link.redirect_url, post_id=post.id).one()
                    logger.debug("Install link %s already present, ignore" % link.redirect_url)
                except exc.NoResultFound:
                    b = InstallLink.parse(link, post.id)
                    self.session.add(b)
                    logger.debug("Adding install link %s" % link.redirect_url)
            self.session.commit()

    def _store_post_external_links(self, ext_links, post):
        if ext_links is not None:
            logger.info("Storing external links")
            for link in ext_links:
                try:
                    self.session.query(ExternalLink).filter_by(id=link.id, post_id=post.id).one()
                    logger.debug("External link %s already present, ignore" % link.id)
                except exc.NoResultFound:
                    b = ExternalLink.parse(link, post.id)
                    self.session.add(b)
                    logger.debug("Adding external link %s" % link.id)
            self.session.commit()

    def _store_post_votes(self, post, votes):
        if votes is not None:
            logger.info("Storing votes")
            for vote in votes:
                try:
                    self.session.query(Vote).filter_by(id=vote["id"], post_id=post.id).one()
                    logger.debug("Vote %s already present, ignore" % vote["id"])
                except exc.NoResultFound:
                    b = Vote.parse(vote, post.id)
                    self.session.add(b)
                    logger.debug("Adding vote %s" % vote["id"])
            self.session.commit()

    def _store_post_topics(self, post, topics):
        if topics is not None:
            logger.info("Storing topics")
            for topic in topics:
                try:
                    self.session.query(Topic).filter_by(id=topic.id, post_id=post.id).one()
                    logger.debug("Topic %s already present, ignore" % topic.id)
                except exc.NoResultFound:
                    b = Topic.parse(topic, post.id)
                    self.session.add(b)
                    logger.debug("Adding topic %s" % topic.id)
            self.session.commit()

    def _store_post_badges(self, badges, post):
        if badges is not None:
            logger.info("Storing badges links")
            for badge in badges:
                try:
                    self.session.query(Badge).filter_by(id=badge.id, post_id=post.id).one()
                    logger.debug("Badge %s already present, ignore" % badge.id)
                except exc.NoResultFound:
                    b = Badge.parse(badge, post.id)
                    self.session.add(b)
                    logger.debug("Adding badge %s" % badge.id)
            self.session.commit()

    def _store_post_comments_and_commenters(self, comments, post, day):
        if comments is not None:
            logger.info("Storing comments and commenters")
            for comment in comments:
                c = self.session.query(Comment).filter_by(id=comment.id).one_or_none()
                if c:
                    logger.debug("Comment %s already present, ignore" % comment.id)
                else:
                    b = Comment.parse(comment)
                    self.session.add(b)
                    logger.debug("Adding comment %s" % comment.id)

                commenter = self.session.query(Commenter).filter_by(comment_id=comment.id, commenter_id=comment.user_id,
                                                                    post_id=post.id).one_or_none()
                if commenter:
                    logger.debug("Commenter %s of comment %s in post %s already present, ignore"
                                 % (comment.user_id, comment.id, post.id))
                else:
                    logger.debug("Adding commenter %s of comment %s in post %s"
                                 % (comment.user_id, comment.id, post.id))
                    b = Commenter(comment.id, comment.user_id, post.id)
                    self.session.add(b)
                self.session.commit()

                if comment.user.username not in self.user_details_once_a_day:
                    try:
                        user = self.phc.get_details_of_user(comment.user.username)
                        if user:
                            self.user_details_once_a_day.add(user.username)
                            self._store_user(user)
                    except ProductHuntError as e:
                        logger.error(str(e))
                else:
                    logger.debug("Detailed info for user %s have been already requested on day %s"
                                 % (comment.user.username, day))

                self._store_post_comments_and_commenters(comment.child_comments, post, day)

    def _store_user_badges(self, discussion_url):
        logger.info("Storing user badges for post commenters")
        try:
            self.driver.get(discussion_url)
            """ explicit wait for page to load """
            try:
                WebDriverWait(self.driver, 60)
                try:
                    btn = self.driver.find_element_by_xpath('//div[@class="loadMore_f1388"]/button')
                    while btn:
                        self.driver.find_element_by_css_selector(
                            '.button_30e5c.fluidSize_c4dc2.mediumSize_c215f.simpleVariant_8a863').click()
                        time.sleep(10)
                        btn = self.driver.find_element_by_xpath('//div[@class="loadMore_f1388"]/button')
                except NoSuchElementException:
                    """ no more buttons to click """
                    pass
                except Exception as e:
                    post = discussion_url.split('https://www.producthunt.com/posts/')[1].split('?')[0]
                    logger.error('Error retrieving badges of commenters for post \'%s\', see screenshot' % post)
                    logger.error(str(e))
                    f = '{0}-store-badges-{1}.png'.format(post, datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
                    self.driver.get_screenshot_as_file(filename=f)
                bs = BeautifulSoup(self.driver.page_source, "lxml")
                spans = bs.find_all("span",
                                    {"class": "font_9d927 black_476ed small_231df semiBold_e201b headline_8ed42"})
                for span in spans:
                    user_name = span.next['href'][2:]
                    user_badges = list()
                    if user_name:
                        try:
                            for tag in span.span.contents:
                                user_badges.append(tag.get_text())
                            if user_name and user_badges:
                                user = self.session.query(User).filter_by(username=user_name).one_or_none()
                                if user:
                                    user.badges = ','.join(user_badges)
                                    self.session.add(user)
                                    self.session.commit()
                        except AttributeError:
                            continue
            except TimeoutException:
                logger.error('Timeout error waiting for resolution of {0}'.format(discussion_url))
                self.driver.save_screenshot('timeout_%s.png' % discussion_url)
            except WebDriverException as wde:
                logger.error(str(wde))
                self.driver.save_screenshot('webdriver_%s.png' % discussion_url)
        except BrokenPipeError as bpe:
            logger.error('Connection error while scraping user badges:\n' + str(bpe))


def setup_db(config_file):
    SessionWrapper.load_config(config_file)
    _session = SessionWrapper.new(init=True)
    assert _session is not None, "Fatal error trying to establish a database connection"
    return _session


def setup_ph_client(config_file):
    with open(os.path.join(os.getcwd(), config_file), 'r') as config:
        cfg = yaml.load(config)
        key = cfg['api']['key']
        secret = cfg['api']['secret']
        uri = cfg['api']['redirect_uri']
        token = cfg['api']['dev_token']

    return ProductHuntClient(key, secret, uri, token)


if __name__ == '__main__':
    now = datetime.datetime.now(timezone('US/Pacific')).strftime("%Y-%m-%d")
    now_dt = datetime.datetime.strptime(now, '%Y-%m-%d').date()
    day = None
    day_dt = None
    newest = False
    update = False
    pid = None
    phm = None
    ph_credentials = 'credentials_miner.yml'
    help_string = 'Usage:\n\tpython ph_miner.py [-d|--day=<YYYY-MM-DD>] [-p|--postid=N] [-n|--newest] [-u|--update] ' \
                  '[-c|--credentials=credentials.yml] [--h|--help]'
    logger = logging_config.get_logger(_dir=now, name="ph_miner", console_level=logging.INFO)

    exit_code = 0
    try:
        opts, _ = getopt(sys.argv[1:], "hd:p:nuc:", ["help", "day=", "postid=", "newest", "update", "credentials="])
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(help_string)
                exit(0)
            elif opt in ("-d", "--day"):
                day = arg
                day_dt = datetime.datetime.strptime(day, "%Y-%m-%d").date()
            elif opt in ("-p", "--postid"):
                pid = int(arg)
            elif opt in ("-n", "--newest"):
                newest = True
            elif opt in ("-u", "--update"):
                update = True
            elif opt in ("-c", "--credentials"):
                ph_credentials = arg
    except GetoptError as ge:
        """ print help information and exit: """
        logger.error(str(ge))
        print(help_string)
        exit_code = 1

    """ set up environment vars """
    os.environ['DB_CONFIG'] = os.path.abspath('db/cfg/dbsetup.yml')
    os.environ['PH_CREDENTIALS'] = os.path.abspath(ph_credentials)

    try:
        logger.info("Creating Product Hunt app")
        ph_client = setup_ph_client(ph_credentials)
        rl, rt = ph_client.get_rate_limit_remaining()
        logger.info("API calls remaining %s (%s min to reset)" % (rl, int(rt / 60)))

        logger.info("Creating a new database connection and initializing tables")
        s = setup_db(os.environ['DB_CONFIG'])

        user_details_parsed_today = dict()
        users_scraper_pending = set()

        if pid:
            logger.info("Retrieving single post %s" % str(pid))
            phm = PhMiner(s, ph_client, now, now_dt, user_details_parsed_today, users_scraper_pending)
            user_details_parsed_today, users_scraper_pending = phm.get_post(pid)
            logger.info("Retrieving review for post %d as of %s" % (pid, now))
            launcher = CrawlersLauncher(session=s)
            launcher.setup_single_post_reviews(pid=pid)
            launcher.set_user_profiles_crawler(user_ids=users_scraper_pending)
            launcher.start(parsed_user_names=user_details_parsed_today)
            logger.info("Done")
            exit_code = 0
        elif newest:
            logger.info("Retrieving newest posts of %s available now" % now)
            phm = PhMiner(s, ph_client, now, now_dt)
            phm.get_newest_posts()
            logger.info("Done")
            exit_code = 0
        elif day and day_dt:
            logger.info("Retrieving daily posts of %s" % day)
            phm = PhMiner(s, ph_client, day, day_dt, user_details_parsed_today, users_scraper_pending)
            user_details_parsed_today, users_scraper_pending = phm.get_featured_posts_at(day)
            logger.info("Retrieving reviews for daily posts of %s" % day)
            launcher = CrawlersLauncher(session=s)
            launcher.setup_post_reviews_crawler(day=day)
            launcher.set_user_profiles_crawler(user_ids=users_scraper_pending)
            launcher.start(parsed_user_names=user_details_parsed_today)
            logger.info("Done")
            exit_code = 0
        elif update:
            """
            retrieve the list of days up to two weeks ago, and re-mine posts up to then altogether, so as to reduce the
            number of calls to ph_client.user_details_once_a_day(), which is very time-consuming
            """
            launcher = CrawlersLauncher(session=s)
            one_week_ago_dt = now_dt - datetime.timedelta(weeks=1)
            logger.info("Updating history of both featured and non-featured posts up to one week ago (%s)"
                        % one_week_ago_dt.strftime("%Y-%m-%d"))
            ith_day_dt = one_week_ago_dt
            while ith_day_dt < now_dt:
                ith_day = ith_day_dt.strftime("%Y-%m-%d")
                """ first update history from API """
                logger.info("Updating history of posts created on %s" % ith_day)
                phm = PhMiner(s, ph_client, now, now_dt, user_details_parsed_today, users_scraper_pending)
                user_details_parsed_today, users_scraper_pending = phm.update_posts_at_day(ith_day)
                """ then, update history by retrieving info that can only be obtained via scraping """
                logger.info("Yielding scrape of pending updates for posts created on %s" % ith_day)
                launcher.setup_post_reviews_crawler(day=ith_day)
                """ and update pending reviewer's info via scraping """
                logger.info("Yielding scrape of pending updates for users")
                launcher.set_user_profiles_crawler(user_ids=users_scraper_pending)
                ith_day_dt = ith_day_dt + timedelta(days=1)
            """ finally, launch all the queued crawlers """
            launcher.start(parsed_user_names=user_details_parsed_today)
            logger.info("Done")
            exit_code = 0
        elif now and now_dt:
            """ analyze today's featured post """
            logger.info("Retrieving daily featured posts of %s" % now)
            phm = PhMiner(s, ph_client, now, now_dt, user_details_parsed_today, users_scraper_pending)
            phm.get_todays_featured_posts()
            """
            analyze daily posts (newest) that didn't make it to the popular list (featured)
            """
            logger.info("Retrieving daily non-featured posts of %s" % now)
            user_details_parsed_today, users_scraper_pending = phm.get_todays_non_featured_posts()
            """
            now scrape pending content for all of today's posts, both featured and not-featured
            """
            launcher = CrawlersLauncher(session=s)
            logger.info("Yielding scrape of pending updates for posts created on %s" % now)
            launcher.setup_post_reviews_crawler(day=now)
            logger.info("Yielding scrape of pending updates for users")
            launcher.set_user_profiles_crawler(user_ids=users_scraper_pending)
            logger.info("Scraping pending updates for users")
            launcher.start(parsed_user_names=user_details_parsed_today)
            logger.info("Done")
            exit_code = 0
    except KeyboardInterrupt:
        logger.error("Received Ctrl-C or other break signal. Exiting.")
        exit_code = -1
    except Exception as e:
        logger.exception('Unexpected exception:\n' + str(e))
        exit_code = -2
    finally:
        """ in any case, we force quitting the webdriver"""
        if phm:
            phm.clean_up()
        exit(exit_code)
