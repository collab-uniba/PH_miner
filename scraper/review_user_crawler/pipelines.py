# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import logging
from logging import log

from sqlalchemy.orm import exc

from db.orm.tables import User, Review, Post
from ph_py.error import ProductHuntError
from phminer import setup_db, setup_ph_client

db_config_file = '../../db/cfg/dbsetup.yml'
ph_config_file = '../../credentials.yml'


class ReviewCrawlerPipeline(object):
    session = setup_db(db_config_file)
    ph_client = setup_ph_client(ph_config_file)

    def _store_review(self, item):
        try:
            reviewer = self.ph_client.get_user(item['reviewer_username'])
            if reviewer is not None:
                try:
                    post = self.session.query(Post.id, Post.name).filter_by(
                        discussion_url=item['post_url']).one_or_none()
                    if post:
                        log(level=logging.INFO, msg='Storing review from %s on product %s into database' % (
                            item['reviewer_name'], post.name))
                        try:
                            review = self.session.query(Review).filter_by(reviewer_id=reviewer.id,
                                                                          post_id=post.id).one()
                            log(level=logging.INFO,
                                msg="Review from %s on %s already present, updating" % (reviewer.id, post.id))
                            review.helpful_count = item['helpful_count']
                            review.comments_count = item['comments_count']
                            review.overall_score = item['product_score']
                            self.session.add(review)
                        except exc.NoResultFound:
                            log(level=logging.INFO, msg="Adding review from %s on %s" % (reviewer.id, post.id))
                            b = Review.parse(reviewer.id, post.id, item['date'], item['sentiment'],
                                             item['product_score'],
                                             item['pros'], item['cons'], item['body'], item['helpful_count'],
                                             item['comments_count'])
                            self.session.add(b)
                        self.session.commit()
                        return reviewer.id
                    else:
                        log(logging.ERROR, "No post found in database with url %s, updating" % item['post_url'])
                except exc.NoResultFound as nrfe:
                    log(level=logging.ERROR, msg=str(nrfe))
        except ProductHuntError as phe:
            log(level=logging.ERROR, msg=str(phe))

    def process_item(self, item, spider):
        self._store_review(item)
        return item


class ReviewUserCrawlerPipeline(object):
    session = setup_db(db_config_file)
    ph_client = setup_ph_client(ph_config_file)

    def _store_reviewer(self, username):
        log(level=logging.INFO, msg='Storing reviewer %s into database' % username)
        try:
            reviewer = self.ph_client.get_user(username)
            if reviewer is not None:
                try:
                    user = self.session.query(User).filter_by(id=reviewer.id).one()
                    log(level=logging.INFO, msg="Reviewer %s already present, updating" % reviewer.id)
                    user.headline = reviewer.headline
                    user.image_url = reviewer.image_url["220px"]
                    user.profile_url = reviewer.profile_url
                    user.twitter_username = reviewer.twitter_username
                    user.website_url = reviewer.website_url
                    self.session.add(user)
                except exc.NoResultFound:
                    log(level=logging.INFO, msg="Adding reviewer %s" % reviewer.id)
                    b = User.parse(reviewer)
                    self.session.add(b)
                self.session.commit()
        except ProductHuntError as phe:
            log(level=logging.ERROR, msg=str(phe))

    def process_item(self, item, spider):
        self._store_reviewer(item['reviewer_username'])
        return item
