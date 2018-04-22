import datetime

from dateutil import parser
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UnicodeText

from db.setup import Base


class Post(Base):
    __tablename__ = 'posts'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String(128), nullable=False)
    tagline = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    day = Column(String(12), nullable=False)
    comments_count = Column(Integer, nullable=False)
    votes_count = Column(Integer, nullable=False)
    discussion_url = Column(String(256), nullable=False)
    redirect_url = Column(String(256))
    screenshot_url = Column(String(256))
    maker_inside = Column(Boolean, nullable=False)
    hunter_id = Column(BigInteger, nullable=False)
    description = Column(String(2048), nullable=False)
    featured = Column(Boolean)
    product_state = Column(String(48))
    reviews_count = Column(Integer, nullable=False)
    positive_reviews_count = Column(Integer, nullable=False)
    negative_reviews_count = Column(Integer, nullable=False)
    neutral_reviews_count = Column(Integer, nullable=False)

    ## ??? remove
    category_id = Column(String(32))
    platforms = Column(String(32))
    exclusive = Column(String(32))

    def __init__(self, post_id, name, tagline, created_at, day, comments_count, votes_count, discussion_url,
                 redirect_url, screenshot_url, maker_inside, hunter_id, description=None, featured=None,
                 exclusive=None, product_state=None, category_id=None, reviews_count=None, positive_reviews_count=None,
                 negative_reviews_count=None, neutral_reviews_count=None, platforms=None):
        self.id = post_id
        self.name = name
        self.tagline = tagline
        if created_at is not None and created_at != 'None':
            st = parser.parse(created_at)
            self.created_at = datetime.datetime(st.year, st.month, st.day, st.hour, st.minute, st.second)
        else:
            self.created_at = None
        self.day = day
        self.comments_count = comments_count
        self.votes_count = votes_count
        self.discussion_url = discussion_url
        self.redirect_url = redirect_url
        self.screenshot_url = screenshot_url
        self.maker_inside = maker_inside
        self.hunter_id = hunter_id
        self.description = description
        self.featured = featured
        self.product_state = product_state
        self.reviews_count = reviews_count
        self.positive_reviews_count = positive_reviews_count
        self.negative_reviews_count = negative_reviews_count
        self.neutral_reviews_count = neutral_reviews_count

        self.category_id = category_id  # ???
        self.platforms = platforms  # ???
        self.exclusive = exclusive  # ???

    @staticmethod
    def parse(user):
        pass


class RelatedPost(Base):
    __tablename__ = 'related_posts'

    post_id = Column(BigInteger, primary_key=True, autoincrement=False)
    related_post_id = Column(BigInteger, primary_key=True, autoincrement=False)

    def __init__(self, post_id, related_post_id):
        self.post_id = post_id
        self.related_post_id = related_post_id


class Topic(Base):
    __tablename__ = 'topics'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    post_id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False)

    def __init__(self, topic_id, name, slug, post_id):
        self.id = topic_id
        self.name = name
        self.slug = slug
        self.post_id = post_id

    @staticmethod
    def parse(topic, post_id):
        return Topic(topic.id, topic.name, topic.slug, post_id)


class Badge(Base):
    __tablename__ = 'badges'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    post_id = Column(BigInteger, primary_key=True, autoincrement=False)
    badge_type = Column(String(128))
    created_at = Column(DateTime(timezone=False))
    period = Column(String(16))
    position = Column(Integer)

    def __init__(self, badge_id, badge_type, date, period, position, post_id):
        self.id = badge_id
        self.badge_type = badge_type
        if date is not None and date != 'None':
            st = parser.parse(date)
            self.created_at = datetime.datetime(st.year, st.month, st.day)
        else:
            self.created_at = None
        self.period = period
        self.position = position
        self.post_id = post_id

    @staticmethod
    def parse(badge, post_id):
        return Badge(badge.id, badge.type, badge.date, badge.period, badge.position, post_id)


class Comment(Base):
    __tablename__ = 'comments'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    body = Column(UnicodeText, nullable=False)
    created_at = Column(DateTime(timezone=True))
    post_id = Column(BigInteger, nullable=False)
    parent_comment_id = Column(BigInteger, unique=True)
    user_id = Column(BigInteger, nullable=False)
    maker = Column(Boolean)
    child_comments_count = Column(Integer)

    def __init__(self, comment_id, body, created_at, post_id, parent_comment_id, user_id,
                 child_comments_count, maker):
        self.id = comment_id
        self.body = body
        if created_at is not None and created_at != 'None':
            st = parser.parse(created_at)
            self.created_at = datetime.datetime(st.year, st.month, st.day)
        else:
            self.created_at = None
        self.post_id = post_id
        self.parent_comment_id = parent_comment_id
        self.user_id = user_id
        self.child_comments_count = child_comments_count
        self.maker = maker

    @staticmethod
    def parse(comment):
        return Comment(comment.id, comment.body, comment.created_at, comment.post_id, comment.parent_comment_id,
                       comment.user_id, comment.child_comments_count, comment.maker)


class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String(128), nullable=False)
    headline = Column(String(512))
    created_at = Column(DateTime, nullable=False)
    username = Column(String(128), nullable=False, unique=True)
    image_url = Column(String(256))
    profile_url = Column(String(256))
    twitter_username = Column(String(256))
    website_url = Column(String(256))

    def __init__(self, user_id, name, headline, created_at, username, image_url, profile_url, twitter_username=None,
                 website_url=None):
        self.id = user_id
        self.name = name
        self.headline = headline
        if created_at is not None and created_at != 'None':
            st = parser.parse(created_at)
            self.created_at = datetime.datetime(st.year, st.month, st.day)
        else:
            self.created_at = None
        self.username = username
        self.image_url = image_url
        self.profile_url = profile_url
        self.twitter_username = twitter_username
        self.website_url = website_url

    @staticmethod
    def parse(user):
        return User(user.id, user.name, user.headline, user.created_at, user.username, user.image_url["220px"],
                    user.profile_url,
                    user.twitter_username, user.website_url)


class Maker(Base):
    __tablename__ = 'makers'

    maker_id = Column(BigInteger, primary_key=True, autoincrement=False)
    post_id = Column(BigInteger, primary_key=True, autoincrement=False)

    def __init__(self, maker_id, post_id):
        self.maker_id = maker_id
        self.post_id = post_id


class Hunter(Base):
    __tablename__ = 'hunters'

    hunter_id = Column(BigInteger, primary_key=True, autoincrement=False)
    post_id = Column(BigInteger, primary_key=True, autoincrement=False)

    def __init__(self, hunter_id, post_id):
        self.hunter_id = hunter_id
        self.post_id = post_id


class Commenter(Base):
    __tablename__ = 'commenters'

    comment_id = Column(BigInteger, primary_key=True, autoincrement=False)
    commenter_id = Column(BigInteger, primary_key=True, autoincrement=False)
    post_id = Column(BigInteger, primary_key=True, autoincrement=False)

    def __init__(self, comment_id, commenter_id, post_id):
        self.comment_id = comment_id
        self.commenter_id = commenter_id
        self.post_id = post_id


class ExternalLink(Base):
    __tablename__ = 'external_links'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    post_id = Column(BigInteger, primary_key=True, autoincrement=False)
    url = Column(String(256), nullable=False)
    title = Column(String(128), nullable=False)
    source = Column(String(64))
    author = Column(String(64))
    headline = Column(String(512))
    favicon_image_uuid = Column(String(128))
    link_type = Column(String(64))

    def __init__(self, external_link_id, url, title, description, author, source, favicon_image_uuid, link_type,
                 post_id):
        self.id = external_link_id
        self.url = source
        self.title = url
        self.source = author
        self.author = description
        self.headline = title
        self.favicon_image_uuid = favicon_image_uuid
        self.link_type = link_type
        self.post_id = post_id

    @staticmethod
    def parse(link, post_id):
        return ExternalLink(link.id, link.url, link.title, link.description, link.author, link.source,
                            link.favicon_image_uuid, link.link_type, post_id)


class InstallLink(Base):
    __tablename__ = 'install_links'

    post_id = Column(BigInteger, primary_key=True, autoincrement=False)
    redirect_url = Column(String(256), primary_key=True)
    platform = Column(String(128))  ## ?
    created_at = Column(DateTime(timezone=True))

    def __init__(self, platform, created_at, redirect_url, post_id):
        self.redirect_url = redirect_url
        self.platform = platform
        if created_at is not None and created_at != 'None':
            st = parser.parse(created_at)
            self.created_at = datetime.datetime(st.year, st.month, st.day, st.hour, st.minute, st.second)
        else:
            self.created_at = None
        self.post_id = post_id

    @staticmethod
    def parse(link, post_id):
        return InstallLink(link.platform, link.created_at, link.redirect_url, post_id)


class RelatedLink(Base):
    __tablename__ = 'related_links'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    post_id = Column(BigInteger, primary_key=True, autoincrement=False)
    url = Column(String(256))
    title = Column(String(256))
    domain = Column(String(256))  ##??
    favicon = Column(String(256))  ##?
    user_id = Column(BigInteger, unique=True)

    def __init__(self, related_link_id, url, title, domain, favicon, user_id, post_id):
        self.id = related_link_id
        self.url = url
        self.title = title
        self.domain = domain
        self.favicon = favicon
        self.post_id = post_id
        self.user_id = user_id

    @staticmethod
    def parse(link, post_id):
        return RelatedLink(link.id, link.url, link.title, link.domain, link.favicon, link.user_id, post_id)


class Vote(Base):
    __tablename__ = 'votes'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    post_id = Column(BigInteger, primary_key=True, autoincrement=False)
    user_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True))

    def __init__(self, vote_id, created_at, user_id, post_id):
        self.id = vote_id
        if created_at is not None and created_at != 'None':
            st = parser.parse(created_at)
            self.created_at = datetime.datetime(st.year, st.month, st.day, st.hour, st.minute, st.second)
        else:
            self.created_at = None
        self.post_id = post_id
        self.user_id = user_id

    @staticmethod
    def parse(vote, post_id):
        return Vote(vote.id, vote.created_at, vote.user.id, post_id)


class Media(Base):
    __tablename__ = 'media'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    post_id = Column(BigInteger, primary_key=True, autoincrement=False)
    kindle_asin = Column(String(128))  ##?
    media_type = Column(String(24))
    priority = Column(Integer)
    platform = Column(String(64))  ## ?
    video_id = Column(String(64))
    original_width = Column(Integer)
    original_height = Column(Integer)
    image_url = Column(String(256))
    metadata_url = Column(String(256))

    def __init__(self, media_id, kindle_asin, media_type, priority, platform, video_id, original_width,
                 original_height, image_url, metadata_url, post_id):
        self.id = media_id
        self.kindle_asin = kindle_asin
        self.media_type = media_type
        self.priority = priority
        self.platform = platform
        self.video_id = video_id
        self.original_width = original_width
        self.original_height = original_height
        self.image_url = image_url
        self.metadata_url = metadata_url
        self.post_id = post_id

    @staticmethod
    def parse(media, post_id):
        return Media(media.id, media.kindle_asin, media.media_type, media.priority, media.platform, media.video_id,
                     media.original_width, media.original_height, media.image_url, media.metadata_url, post_id)


# class Review(Base):
#     __tablename__ = "reviews"
#
#     reviewer_id
#     pros
#     cons
#     review_body
#     review_type # helpful, favorable, critical
#     helpful_count
#     comments_count
#     used_app_for
