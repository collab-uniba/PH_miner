import scrapy


class ReviewItem(scrapy.Item):
    reviewer_name = scrapy.Field()
    reviewer_username = scrapy.Field()
    reviewer_tagline = scrapy.Field()
    reviewer_url = scrapy.Field()
    post_url = scrapy.Field()
    pros = scrapy.Field()
    cons = scrapy.Field()
    body = scrapy.Field()
    sentiment = scrapy.Field()
    helpful_count = scrapy.Field()
    comments_count = scrapy.Field()
    date = scrapy.Field()
    product_score = scrapy.Field()
    #
    reviewer_badges = scrapy.Field()
    reviewer_daily_upvote_streak = scrapy.Field()
    reviewer_collections_followed_count = scrapy.Field()


class UserItem(scrapy.Item):
    id = scrapy.Field()
    badges = scrapy.Field()
    daily_upvote_streak = scrapy.Field()
    collections_followed_count = scrapy.Field()
