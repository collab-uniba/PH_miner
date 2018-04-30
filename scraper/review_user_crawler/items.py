import scrapy


class ReviewCrawlerItem(scrapy.Item):
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
