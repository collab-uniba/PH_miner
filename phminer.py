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
__version_info__ = (0, 0, 1)
__version__ = '.'.join(str(i) for i in __version_info__)
__home__ = 'https://github.com/collab-uniba/PH_miner'
__download__ = 'https://github.com/collab-uniba/PH_miner/archive/master.zip'

import logging
import os

import yaml
from scrapy import cmdline
from sqlalchemy.orm import exc

from db import SessionWrapper
from db.orm.tables import *
from logger import logging_config
from ph_py import ProductHuntClient
from ph_py.error import ProductHuntError


class ScrapyLauncher:

    def __init__(self, session):
        self.session = session

    def get_or_update_posts_reviews(self):
        try:
            urls = self.session.query(Post.discussion_url).all()
            urls = [url[0] + '/reviews' for url in urls]
            urls = ','.join(urls)
            os.chdir(os.path.join('scraper', 'review_user_crawler'))
            command = "scrapy crawl producthunt -a browser=Chrome -a start_urls={0}".format(urls).split()
            cmdline.execute(command)
        except Exception as e:
            logger.error(str(e))


class PhMiner:

    def __init__(self, session, phc):
        self.session = session
        self.phc = phc

    def get_daily_posts(self):
        try:
            daily_posts = [post.id for post in self.phc.get_todays_posts()]

            # get details for each post by id
            for post_id in daily_posts:
                post = self.phc.get_details_of_post(post_id=post_id)
                self.store(post)
        except ProductHuntError as e:
            print(e.error_message)
            print(e.status_code)

    def get_posts_at(self, day):
        try:
            daily_posts = [post.id for post in self.phc.get_specific_days_posts(day)]

            # get details for each post by id
            for post_id in daily_posts:
                post = self.phc.get_details_of_post(post_id=post_id)
                self.store(post)
        except ProductHuntError as e:
            print(e.error_message)
            print(e.status_code)

    def store(self, post):
        assert post is not None, "Fatal error trying to store a null post"

        if post is not None:
            p = self.session.query(Post).filter_by(id=post.id).one_or_none()
            if p:
                logger.info("Post \'%s\' already present, updating" % post.name)
                # update
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
                logger.info("Adding post \'%s\'" % post.name)
                p = Post(post.id, post.name, post.tagline, post.created_at, post.day, post.comments_count,
                         post.votes_count,
                         post.discussion_url, post.redirect_url, post.screenshot_url["850px"], post.maker_inside,
                         post.user.id,
                         post.description, post.featured, post.exclusive, post.product_state, post.category_id,
                         post.reviews_count, post.positive_reviews_count, post.negative_reviews_count,
                         post.neutral_reviews_count,
                         post.platforms)
            self.session.add(p)
            self.session.commit()

        hunter = post.user
        self._store_hunter(hunter, post)

        badges = post.badges
        self._store_badges(badges, post)

        topics = post.topics
        self._store_topics(post, topics)

        votes = post.votes
        self._store_votes(post, votes)

        ext_links = post.external_links
        self._store_external_links(ext_links, post)

        inst_links = post.install_links
        self._store_install_links(inst_links, post)

        rel_links = post.related_links
        self._store_related_links(post, rel_links)

        rel_posts = post.related_posts
        self._store_related_posts(post, rel_posts)

        media = post.media
        self._store_media(media, post)

        makers = post.makers
        self._store_makers(makers, post)

        comments = post.comments
        self._store_comments(comments, post)

    def _store_makers(self, makers, post):
        if makers is not None:
            for maker in makers:
                try:
                    user = self.session.query(User).filter_by(id=maker.id).one()
                    logger.debug("User %s already present, updating" % maker.id)
                    user.headline = maker.headline
                    user.image_url = maker.image_url["220px"]
                    user.profile_url = maker.profile_url
                    user.twitter_username = maker.twitter_username
                    user.website_url = maker.website_url
                    self.session.add(user)
                except exc.NoResultFound:
                    logger.debug("Adding user %s" % maker.id)
                    b = User.parse(maker)
                    self.session.add(b)

                try:
                    self.session.query(Maker).filter_by(maker_id=maker.id, post_id=post.id).one()
                    logger.debug("Maker %s of post %s already present, ignore" % (maker.id, post.id))
                except exc.NoResultFound:
                    b = Maker(maker.id, post.id)
                    self.session.add(b)
                    logger.debug("Adding maker %s of post %s" % (maker.id, post.id))
            self.session.commit()

    def _store_media(self, media, post):
        if media is not None:
            for m in media:
                try:
                    self.session.query(Media).filter_by(id=m.id, post_id=post.id).one()
                    logger.debug("Media  %s already present, ignore" % m.id)
                except exc.NoResultFound:
                    b = Media.parse(m, post.id)
                    self.session.add(b)
                    logger.debug("Adding media %s" % m.id)
            self.session.commit()

    def _store_related_posts(self, post, rel_posts):
        if rel_posts is not None:
            for rel_post in rel_posts:
                try:
                    self.session.query(RelatedPost).filter_by(post_id=post.id, related_post_id=rel_post).one()
                    logger.debug("Related post %s already present, ignore" % rel_post)
                except exc.NoResultFound:
                    b = RelatedPost(post.id, rel_post)
                    self.session.add(b)
                    logger.debug("Adding related post %s" % rel_post)
            self.session.commit()

    def _store_related_links(self, post, rel_links):
        if rel_links is not None:
            for link in rel_links:
                try:
                    self.session.query(RelatedLink).filter_by(id=link.id, post_id=post.id).one()
                    logger.debug("Related link %s already present, ignore" % link.id)
                except exc.NoResultFound:
                    b = RelatedLink.parse(link, post.id)
                    self.session.add(b)
                    logger.debug("Adding related link %s" % link.id)
            self.session.commit()

    def _store_install_links(self, inst_links, post):
        if inst_links is not None:
            for link in inst_links:
                try:
                    self.session.query(InstallLink).filter_by(redirect_url=link.redirect_url, post_id=post.id).one()
                    logger.debug("Install link %s already present, ignore" % link.redirect_url)
                except exc.NoResultFound:
                    b = InstallLink.parse(link, post.id)
                    self.session.add(b)
                    logger.debug("Adding install link %s" % link.redirect_url)
            self.session.commit()

    def _store_external_links(self, ext_links, post):
        if ext_links is not None:
            for link in ext_links:
                try:
                    self.session.query(ExternalLink).filter_by(id=link.id, post_id=post.id).one()
                    logger.debug("External link %s already present, ignore" % link.id)
                except exc.NoResultFound:
                    b = ExternalLink.parse(link, post.id)
                    self.session.add(b)
                    logger.debug("Adding external link %s" % link.id)
            self.session.commit()

    def _store_votes(self, post, votes):
        if votes is not None:
            for vote in votes:
                try:
                    self.session.query(Vote).filter_by(id=vote.id, post_id=post.id).one()
                    logger.debug("Vote %s already present, ignore" % vote.id)
                except exc.NoResultFound:
                    b = Vote.parse(vote, post.id)
                    self.session.add(b)
                    logger.debug("Adding vote %s" % vote.id)
            self.session.commit()

    def _store_topics(self, post, topics):
        if topics is not None:
            for topic in topics:
                try:
                    self.session.query(Topic).filter_by(id=topic.id, post_id=post.id).one()
                    logger.debug("Topic %s already present, ignore" % topic.id)
                except exc.NoResultFound:
                    b = Topic.parse(topic, post.id)
                    self.session.add(b)
                    logger.debug("Adding topic %s" % topic.id)
            self.session.commit()

    def _store_badges(self, badges, post):
        if badges is not None:
            for badge in badges:
                try:
                    self.session.query(Badge).filter_by(id=badge.id, post_id=post.id).one()
                    logger.debug("Badge %s already present, ignore" % badge.id)
                except exc.NoResultFound:
                    b = Badge.parse(badge, post.id)
                    self.session.add(b)
                    logger.debug("Adding badge %s" % badge.id)
            self.session.commit()

    def _store_hunter(self, hunter, post):
        if hunter is not None:
            h = self.session.query(User).filter_by(id=hunter.id).one_or_none()
            if h:
                logger.debug("User %s already present, updating" % hunter.id)
                h.headline = hunter.headline
                h.image_url = hunter.image_url["220px"]
                h.profile_url = hunter.profile_url
                h.twitter_username = hunter.twitter_username
                h.website_url = hunter.website_url
                self.session.add(h)
            else:
                logger.debug("Adding user %s" % hunter.id)
                b = User.parse(hunter)
                self.session.add(b)

            h = self.session.query(Hunter).filter_by(hunter_id=hunter.id, post_id=post.id).one_or_none()
            if h:
                logger.debug("Hunter %s of post %s already present, ignore" % (hunter.id, post.id))
            else:
                logger.debug("Adding hunter %s of post %s" % (hunter.id, post.id))
                b = Hunter(hunter.id, post.id)
                self.session.add(b)
                self.session.commit()

    def _store_comments(self, comments, post):
        if comments is not None:
            for comment in comments:
                c = self.session.query(Comment).filter_by(id=comment.id).one_or_none()
                if c:
                    logger.debug("Comment %s already present, ignore" % comment.id)
                else:
                    b = Comment.parse(comment)
                    self.session.add(b)
                    logger.debug("Adding comment %s" % comment.id)

                c = self.session.query(Commenter).filter_by(comment_id=comment.id, commenter_id=comment.user_id,
                                                            post_id=post.id).one_or_none()
                if c:
                    logger.debug("Commenter %s of comment %s in post %s already present, ignore"
                                 % (comment.user_id, comment.id, post.id))
                else:
                    logger.debug("Adding commenter %s of comment %s in post %s"
                                 % (comment.user_id, comment.id, post.id))
                    b = Commenter(comment.id, comment.user_id, post.id)
                    self.session.add(b)

                c = self.session.query(User).filter_by(id=comment.user.id).one_or_none()
                if c:
                    logger.debug("User %s already present, updating" % comment.user.id)
                    c.headline = comment.user.headline
                    c.image_url = comment.user.image_url["220px"]
                    c.profile_url = comment.user.profile_url
                    c.twitter_username = comment.user.twitter_username
                    c.website_url = comment.user.website_url
                    self.session.add(c)
                else:
                    logger.debug("Adding user %s" % comment.user.id)
                    b = User.parse(comment.user)
                    self.session.add(b)

                self.session.commit()
                self._store_comments(comment.child_comments, post)


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
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    logger = logging_config.get_logger(_dir=now, name="ph-miner", console_level=logging.INFO)
    try:
        logger.info("Creating Product Hunt app")
        phc = setup_ph_client('credentials.yml')

        logger.info("Creating a new database connection and initializing tables")
        s = setup_db('db/cfg/dbsetup.yml')

        logger.info("Retrieving daily posts of %s" % now)
        phm = PhMiner(s, phc)
        #phm.get_daily_posts()
        # phm.get_posts_at('2018-04-29')

        logger.info("Retrieving reviews for daily posts of %s" % now)
        launcher = ScrapyLauncher(session=s)
        launcher.get_or_update_posts_reviews()

        logger.info("Done")
        exit(0)
    except KeyboardInterrupt:
        logger.error('Received Ctrl-C or other break signal. Exiting.')
        exit(-1)

# TODO schedule launch from python directly or cronjob??
