import logging
import os

from pytz import timezone

from csvio import CsvWriter
from db import SessionWrapper
from db.orm.tables import *
from logger import logging_config


def setup_db(config_file):
    SessionWrapper.load_config(config_file)
    _session = SessionWrapper.new(init=True)
    assert _session is not None, "Fatal error trying to establish a database connection"
    return _session


def extract_all_features(session, logger):
    posts = __extract_hunted_posts(session)
    # hunters = __extract_post_hunters()
    # makers = __extract_post_makers()
    __extract_time(logger)
    __extract_linguistic(logger)
    __extract_affect(logger)
    entries = __aggregate(posts, session, logger)
    return entries


# FIXME post entries are duplicated
def __extract_hunted_posts(session):
    posts = session.query(Post.id, Post.name, Post.hunter_id, Post.day, Post.created_at, Post.featured,
                          Post.maker_inside, Post.product_state, Post.overall_review_score, Post.comments_count,
                          Post.votes_count, Post.reviews_count, Post.positive_reviews_count,
                          Post.negative_reviews_count, Post.neutral_reviews_count).filter(
        Post.id == Hunts.post_id).limit(1000)
    return posts


# def __extract_post_hunters():
#     hunters = session.query(User.id, User.username, User.created_at, User.twitter_username, User.website_url,
#                             User.followings_count, User.followers_count, User.hunts_count, User.apps_made_count,
#                             User.upvotes_count, User.collections_made_count, User.collections_followed_count,
#                             User.followed_topics_count, User.daily_upvote_streak).filter(
#         User.id == Hunts.hunter_id).distinct()
#     return hunters
#
#
# def __extract_post_makers():
#     makers = session.query(User.id, User.username, User.created_at, User.twitter_username, User.website_url,
#                            User.followings_count, User.followers_count, User.hunts_count, User.apps_made_count,
#                            User.upvotes_count, User.collections_made_count, User.collections_followed_count,
#                            User.followed_topics_count, User.daily_upvote_streak).filter(
#         User.id == Apps.maker_id).distinct()
#     return makers


def __extract_time(logger):
    logger.warning("Time-based features extraction unimplemented")
    pass


def __extract_linguistic(logger):
    logger.warning("Linguistic features extraction unimplemented")
    pass


def __extract_affect(logger):
    logger.warning("Affect-based features extraction unimplemented")
    pass


# fixme oftentimes, one() returns multiple or no rows
def __aggregate(_posts, session, logger):
    _entries = list()
    for p in _posts:
        try:
            entry = [p.id, p.featured, p.votes_count, p.day, p.created_at]

            hunter_id = session.query(Hunts.hunter_id).filter(Hunts.post_id == p.id).one()[0]
            hunter = session.query(User.id, User.followers_count, User.twitter_username, User.website_url).filter(
                User.id == hunter_id).one()
            entry = entry + [hunter.id, hunter.followers_count, hunter.twitter_username, hunter.website_url]

            maker_id = session.query(Apps.maker_id).filter(Apps.post_id == p.id).one()[0]
            maker = session.query(User.id, User.followers_count, User.twitter_username, User.website_url).filter(
                User.id == maker_id).one()
            entry = entry + [maker.id, maker.followers_count, maker.twitter_username, maker.website_url]

            _entries.append(entry)
        except Exception as ex:
            logger.error(str(ex))
            continue
    return _entries


# TODO
# - daily streak (remove the first char if not null)
def clean_all_features(_entries):
    _cleaned_entries = list()
    for e in _entries:
        is_featured = 1
        if not e[1]:
            is_featured = 0
        e[1] = is_featured
        has_twitter = 1
        if not e[7]:
            has_twitter = 0
        e[7] = has_twitter
        has_website = 1
        if not e[8]:
            has_website = 0
        e[8] = has_website
        _cleaned_entries.append(e)
        has_twitter = 1
        if not e[11]:
            has_twitter = 0
        e[11] = has_twitter
        has_website = 1
        if not e[12]:
            has_website = 0
        e[12] = has_website
        _cleaned_entries.append(e)
    return _cleaned_entries


def write_all_features(outfile, _entries):
    writer = CsvWriter(outfile)
    header = ['post_id', 'is_featured', 'score', 'created_at_day', 'created_at_daytime', 'hunter_id',
              'hunter_followers', 'hunter_has_twitter', 'hunter_has_website', 'maker_id', 'maker_followers',
              'maker_has_twitter', 'maker_has_website']
    writer.writerow(header)
    writer.writerows(_entries)
    writer.close()


if __name__ == '__main__':
    """ set up logging """
    now = datetime.datetime.now(timezone('US/Pacific')).strftime("%Y-%m-%d")
    logger = logging_config.get_logger(_dir=now, name="ph_feature_extraction", console_level=logging.ERROR)

    """ set up environment vars """
    os.environ['DB_CONFIG'] = os.path.abspath('db/cfg/dbsetup.yml')
    session = setup_db(os.environ['DB_CONFIG'])
    os.environ['FEATURES'] = os.path.abspath('temp.csv')

    entries = extract_all_features(session, logger)
    entries = clean_all_features(entries)
    write_all_features(os.environ['FEATURES'], entries)
