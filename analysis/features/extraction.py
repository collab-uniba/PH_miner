import logging
import os

# Libraries used for check if an url is a gif image
import requests
import mimetypes

# Libraries used for regular expression
import emoji
import regex
import gensim

import numpy as np

# Library used for checking day from datetime
import calendar

# Library used to operate on features csv file
import pandas as pd

# Libraries used for discretizing continuous variables using k-means clustering
from sklearn.cluster import KMeans
from sklearn.preprocessing import KBinsDiscretizer

# Libraries used to do topic modeling
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import GridSearchCV
from pprint import pprint

# Library used to visualize graphics
import matplotlib.pyplot as plt

# Library used for implementing Clustering Visualizers, in particular the elbow method was used
from yellowbrick.cluster import KElbowVisualizer

# Libraries used for natural language preprocessing
from nltk import sent_tokenize  # this library is used to find sentences in text
import spacy  # this library is used to execute the lemmatization necessary to execute the topic modeling

# Libraries used to access to database
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.exc import MultipleResultsFound

# Library used for extracting the sentiment of makers based on description posts and their comments
from sentistrength import PySentiStr

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
    media = __extract_media(session)
    comments = __extract_comments(session)
    entries = __aggregate(posts, media, comments, session, logger)
    return entries


def __extract_hunted_posts(session):
    posts = session.query(Post.id, Post.name, Post.tagline, Post.created_at, Post.day, Post.discussion_url,
                          Post.hunter_id, Post.description, Post.featured, Post.maker_inside, Post.product_state,
                          Post.overall_review_score, Post.comments_count, Post.votes_count, Post.reviews_count,
                          Post.positive_reviews_count, Post.negative_reviews_count, Post.neutral_reviews_count)
    return posts


def __extract_media(session):
    _media = []
    media = session.query(Media.post_id, Media.media_type, Media.video_id, Media.original_width, Media.original_height,
                          Media.image_url).filter(Media.post_id == Post.id)
    for m in media:
        _media.append(m)
    return _media


def __extract_comments(session):
    _comments = []
    comments = session.query(Comment.id, Comment.body, Comment.created_at, Comment.post_id, Comment.user_id,
                             Comment.maker).filter(Comment.post_id == Post.id)
    for c in comments:
        _comments.append(c)
    return _comments


def get_day_name_from_date(year, month, day):
    my_date = datetime.datetime(year, month, day)
    date_day = calendar.day_name[my_date.weekday()]
    return date_day


def is_best_posted_time(_hour, _minute, _second):
    _found = False
    if (_hour > 00) and (_hour < 9):
        _found = True
    elif _hour == 00:
        if (_minute == 00) and ((_second > 00) and (_second < 59)):
            _found = True
        elif _minute > 0:
            _found = True
        else:
            _found = False
    return _found


def is_best_launched_day(_hour, _minute, _second, _ld):
    _found = False
    if (_hour >= 00) and (_minute > 1):
        if (_ld == 'Monday') or (_ld == 'Tuesday'):
            _found = True
    else:
        _found = False
    return _found


def is_weekend(followers_count, max_follower, _ld):
    _found = False
    if (followers_count < max_follower) and ((_ld == 'Saturday') or (_ld == 'Sunday')):
        _found = True
    else:
        _found = False
    return _found


def get_sentence(text):
    sentence = sent_tokenize(text)
    return sentence


def __extract_bullet_points_explicit_features(text):
    _bullet_points = []
    bullet_character = '\u2022'
    for i in range(0, len(text)):
        if bullet_character in text[i]:
            _bullet_points.append(text[i])
    return _bullet_points


def __extract_emoji(text):
    emoji_list = []
    data = regex.findall(r'\X', str(text))
    for word in data:
        if any(character in emoji.UNICODE_EMOJI for character in word):
            emoji_list.append(word)
    return emoji_list


def get_keyword_based_heuristics(_keyword):
    return regex.compile(_keyword)


def __extract_version(url):
    url = url + ' '
    version_number = '1.0'
    keyword = get_keyword_based_heuristics(r'-+v+([\d-]+)+\s|-+([\d-]+)+\s')
    _version = keyword.search(url)
    if _version:
        v = _version.group()
        v = v.replace('-', '.')
        if v[1] == 'v':
            if v.count('.') >= 2:
                version_number = v[2:]
            else:
                version_number = v[2:len(v)-1] + '.0'
        else:
            if v.count('.') >= 2:
                version_number = v[1:]
            else:
                version_number = v[1:len(v)-1] + '.0'
    return version_number


# The two following functions establish if an image is a tweetable image calculating its dimension (roughly and ratio)
def get_gcd(a, b):
    """ The GCD (greatest common divisor) is the highest number that evenly divides both width and height. """
    return a if b == 0 else get_gcd(b, a % b)


def calculate_aspect_ratio(width, height):
    temp = 0
    if width == height:
        return 1, 1
    if width < height:
        temp = width
        width = height
        height = temp

    divisor = get_gcd(width, height)
    x = int(width / divisor) if not temp else int(height / divisor)
    y = int(height / divisor) if not temp else int(width / divisor)
    return x, y


def is_gif(url):
    found = False
    response = requests.get(url)
    content_type = response.headers['content-type']
    extension = mimetypes.guess_extension(content_type)
    if extension.endswith('gif'):
        found = True
    return found


def __extract_offers(text):
    _offers = []
    keywords = get_keyword_based_heuristics(r'\d% off|\d% OFF|\d\d% off|\d\d% OFF|\d\d\d% off|\d\d\d% OFF')
    offer = keywords.search(text)
    if offer:
        _offers.append(offer.group())
    return _offers


def __extract_promo_codes(text):
    _promo_codes = regex.findall('promo=[A-Z0-9]+[a-zA-Z0-9_.+-]+|promo code [A-Z0-9]+[a-zA-Z0-9_.+-]+|discount=[A-Z0-9]+[a-zA-Z0-9_.+-]+|discount code [A-Z0-9]+[a-zA-Z0-9_.+-]+', text)
    return _promo_codes


def __extract_questions(text):
    _questions = []
    keyword = get_keyword_based_heuristics(
        r'Let [a-zA-Z0-9_.+-]*|What [a-zA-Z0-9_.+-]*|Where [a-zA-Z0-9_.+-]*|Who [a-zA-Z0-9_.+-]*|Why [a-zA-Z0-9_.+-]*')
    sentence = get_sentence(text)
    for j in range(0, len(sentence)):
        q = keyword.search(sentence[j])
        if q:
            _questions.append(sentence[j])
    return _questions


# Setup the path of SentiStrength tool
def setup_sentistrength_path(s):
    s.setSentiStrengthPath(os.getcwd() + '\\affect_resources\\SentiStrengthCom.jar')
    s.setSentiStrengthLanguageFolderPath(os.getcwd() + '\\affect_resources\\SentiStrength_Data\\')


def __extract_maker_sentiment(sentiment, text):
    maker_sentiment = sentiment.getSentiment(text, score='binary')
    return maker_sentiment


def __aggregate(_posts, _media, _comments, session, logger):
    _entries = list()

    # Initialize sentistrength variable
    senti = PySentiStr()
    setup_sentistrength_path(senti)

    for p in _posts:
        try:
            """ Id, name of a post """
            entry = [p.id, p.name]

            """ Number of version of a post """
            version = __extract_version(p.discussion_url)
            entry = entry + [version]

            """ Number of tags for a product """
            tags_number = session.query(func.count(Topic.name)).filter(Topic.post_id == p.id).scalar()
            entry = entry + [tags_number]

            entry = entry + [p.featured, p.votes_count, p.day, p.created_at]

            """ Time features """
            launch_day = get_day_name_from_date(p.created_at.year, p.created_at.month, p.created_at.day)
            best_launch_time = is_best_posted_time(p.created_at.hour, p.created_at.minute, p.created_at.second)
            best_launch_day = is_best_launched_day(p.created_at.hour, p.created_at.minute, p.created_at.second,
                                                   launch_day)
            max_follower = session.query(func.max(User.followers_count)).scalar()
            maker_id = session.query(Apps.maker_id).filter(Apps.post_id == p.id).one()[0]
            maker = session.query(User.id, User.name, User.twitter_username, User.website_url,
                                  User.followers_count).filter(User.id == maker_id).one()
            weekend = is_weekend(maker.followers_count, max_follower, launch_day)
            entry = entry + [launch_day, best_launch_time, best_launch_day, weekend]

            """ Presentation features """
            entry = entry + [p.description]
            if p.description:
                """ Extraction of maker sentiment based on the description of his post """
                sentiment_description = __extract_maker_sentiment(senti, p.description)
                entry = entry + [sentiment_description[0][0], sentiment_description[0][1], '', '', '']

                # Text length
                entry = entry + [len(p.description)]

                # Sentence length
                sentence = get_sentence(p.description)
                sentence_length_sum = 0
                for i in range(0, len(sentence)):
                    sentence_length_sum = sentence_length_sum + len(sentence[i])
                try:
                    sentence_length_average = sentence_length_sum / len(sentence)
                except ZeroDivisionError:
                    sentence_length_average = 0.0
                entry = entry + [round(sentence_length_average)]

                # Bullet points / Explicit features
                bullet_points_explicit_features = __extract_bullet_points_explicit_features(sentence)
                entry = entry + [bullet_points_explicit_features]

                # Emoji in description
                emoji_description = __extract_emoji(p.description)
                entry = entry + [emoji_description]
            else:
                entry = entry + [1, -1, '', '', '', 0, 0, 'No', 'No']

            entry = entry + [p.tagline]
            if p.tagline:
                # Tagline length
                entry = entry + [len(p.tagline)]

                # Emoji in tagline
                emoji_tagline = __extract_emoji(p.tagline)
                entry = entry + [emoji_tagline]
            else:
                entry = entry + [0, 'No']

            # Video, Tweetable images, Gif and Gif's number for a post
            video = []
            tweetable_images = []
            gif = []
            index_media = 0
            while index_media < len(_media):
                # check if the current post_id is equal to the post_id of the current media
                if p.id == _media[index_media][0]:
                    # check if the media type is 'video'
                    if _media[index_media][1] == 'video':
                        # append to the list the link of the video
                        video = video + [_media[index_media][2]]

                    # calculate the image size passing its width and its height
                    roughly, ratio = calculate_aspect_ratio(_media[index_media][3], _media[index_media][4])
                    # check if the image is a tweetable image
                    if (roughly == 2) and (ratio == 1):
                        # append to the list the image url
                        tweetable_images = tweetable_images + [_media[index_media][5]]

                    # check if the image is a gif image passing its url
                    found = is_gif(_media[index_media][5])
                    if found:
                        # append to the list the image url
                        gif = gif + [_media[index_media][5]]
                index_media = index_media + 1
            if video:
                entry = entry + ['Yes']
            else:
                entry = entry + ['No']
            if tweetable_images:
                entry = entry + ['Yes']
            else:
                entry = entry + ['No']
            if gif:
                entry = entry + [gif, len(gif)]
            else:
                entry = entry + ['', len(gif)]

            # Offers, Promo/Discount Codes, Questions, Maker_inside, Hunter_inside in comment body for a post
            offers = []
            questions = []
            promo_codes = []
            maker_follows_up_on_comments = []
            hunter_follows_up_on_comments = []
            index_comment = 0
            while index_comment < len(_comments):
                # check if the current post_id is equal to the post_id of the current comment
                if p.id == _comments[index_comment][3]:
                    # extract offers passing the comment body
                    offer = __extract_offers(_comments[index_comment][1])
                    if offer:
                        offers = offers + offer

                    # extract questions passing the comment body
                    question = __extract_questions(_comments[index_comment][1])
                    if question:
                        questions = questions + question

                    # extract promo_codes passing the comment body
                    promo_code = __extract_promo_codes(_comments[index_comment][1])
                    if promo_code:
                        promo_codes = promo_codes + promo_code

                    # check if the maker_id that follows up on the current comment is equal to the current maker_id
                    if _comments[index_comment][4] == maker_id:
                        maker_follows_up_on_comments.insert(0, _comments[index_comment][5])
                    else:
                        hunter_follows_up_on_comments.insert(0, _comments[index_comment][5])
                index_comment = index_comment + 1
            if offers:
                entry = entry + ['Yes']
            else:
                entry = entry + ['No']
            if promo_codes:
                entry = entry + ['Yes']
            else:
                entry = entry + ['No']
            if questions:
                entry = entry + ['Yes']
            else:
                entry = entry + ['No']

            # Hunter reputation
            hunter_id = session.query(Hunts.hunter_id).filter(Hunts.post_id == p.id).one()[0]
            hunter = session.query(User.id, User.name, User.twitter_username, User.website_url, User.followers_count,
                                   User.apps_made_count).filter(User.id == hunter_id).one()
            entry = entry + [hunter.id, hunter.name, hunter.twitter_username, hunter.website_url,
                             hunter.followers_count, hunter.apps_made_count]

            if hunter_follows_up_on_comments:
                entry = entry + ['Yes']
            else:
                entry = entry + ['No']

            # Maker reputation
            entry = entry + [maker.id, maker.name, maker.twitter_username, maker.website_url, maker.followers_count]

            if maker_follows_up_on_comments:
                entry = entry + ['Yes']
            else:
                entry = entry + ['No']

            _entries.append(entry)
        except NoResultFound as ex:
            logger.error(str(ex))
            continue
        except MultipleResultsFound as ex:
            logger.error(str(ex))
            continue
    return _entries


def discretize_affect_feature(positive_sentiment, negative_sentiment):
    discretized_positive_sentiment_score = False
    discretized_negative_sentiment_score = False
    discretized_neutral_sentiment_score = False
    if (positive_sentiment == +1) and ((negative_sentiment == -2) or (negative_sentiment == -3) or
                                       (negative_sentiment == -4) or (negative_sentiment == -5)):
        discretized_positive_sentiment_score = False
        discretized_negative_sentiment_score = True
        discretized_neutral_sentiment_score = False
    elif ((positive_sentiment == +2) or (positive_sentiment == +3) or (positive_sentiment == +4) or
          (positive_sentiment == +5)) and (negative_sentiment == -1):
        discretized_positive_sentiment_score = True
        discretized_negative_sentiment_score = False
        discretized_neutral_sentiment_score = False
    elif (positive_sentiment == +1) and (negative_sentiment == -1):
        discretized_positive_sentiment_score = False
        discretized_negative_sentiment_score = False
        discretized_neutral_sentiment_score = True
    elif ((positive_sentiment == +2) or (positive_sentiment == +3) or (positive_sentiment == +4) or
          (positive_sentiment == +5)) and ((negative_sentiment == -2) or (negative_sentiment == -3) or
                                           (negative_sentiment == -4) or (negative_sentiment == -5)):
        discretized_positive_sentiment_score = True
        discretized_negative_sentiment_score = True
        discretized_neutral_sentiment_score = False
    return discretized_positive_sentiment_score, discretized_negative_sentiment_score, discretized_neutral_sentiment_score


def clean_features(_entries):
    _cleaned_entries = list()
    for e in _entries:
        # Insert Yes if the post is featured, No viceversa
        # 4 is the position in the list where the is_featured element is located
        is_featured = 'Yes'
        if (not e[4]) or (e[4] == 0):
            is_featured = 'No'
        e[4] = is_featured

        # Insert Yes if the post was launched in the suggested time, No viceversa
        # 9 is the position in the list where the is_best_time_to_launch element is located
        best_posted_time = 'Yes'
        if not e[9]:
            best_posted_time = 'No'
        e[9] = best_posted_time

        # Insert Yes if the post was launched in the suggested day, No viceversa
        # 10 is the position in the list where the is_best_day_to_launch element is located
        best_launched_day = 'Yes'
        if not e[10]:
            best_launched_day = 'No'
        e[10] = best_launched_day

        # Insert Yes if the post was launched in weekend, No viceversa
        # 11 is the position in the list where the is_weekend element is located
        is_weekend = 'Yes'
        if not e[11]:
            is_weekend = 'No'
        e[11] = is_weekend

        # Discretize positive sentiment and negative sentiment to Positive, Negative and Neutral
        # 13 is the position in the list where positive_description_sentiment element is located
        # 14 is the position in the list where negative_description_sentiment element is located
        # 15 is the position in the list where discretized_positive_description_score is located
        # 16 is the position in the list where discretized_negative_description_score is located
        # 17 is the position in the list where discretized_neutral_description_score is located
        discretized_positive_score, discretized_negative_score, discretized_neutral_score = discretize_affect_feature(
            e[13], e[14])
        e[15] = discretized_positive_score
        e[16] = discretized_negative_score
        e[17] = discretized_neutral_score

        # Insert Yes if the description post contains bullet points or explicit features, No viceversa
        # 20 is the position in the list where the bullet_points_explicit_features element is located
        are_there_bullet_points_explicit_features = 'Yes'
        if not e[20]:
            are_there_bullet_points_explicit_features = 'No'
        e[20] = are_there_bullet_points_explicit_features

        # Insert Yes if the description post contains emojis, No viceversa
        # 21 is the position in the list where the emoji_in_description element is located
        are_there_emoji_in_description = 'Yes'
        if not e[21]:
            are_there_emoji_in_description = 'No'
        e[21] = are_there_emoji_in_description

        # Insert Yes if the tagline post contains emojis, No viceversa
        # 24 is the position in the list where the emoji_in_tagline element is located
        are_there_emoji_in_tagline = 'Yes'
        if not e[24]:
            are_there_emoji_in_tagline = 'No'
        e[24] = are_there_emoji_in_tagline

        # Insert Yes if the post contains gif images, No viceversa
        # 27 is the position in the list where the are_there_gif_images element is located
        are_there_gif_images = 'Yes'
        if not e[27]:
            are_there_gif_images = 'No'
        e[27] = are_there_gif_images

        # Insert Yes if the hunter that hunted the post has a twitter account, No viceversa
        # 34 is the position in the list where the hunter_has_twitter element is located
        hunter_has_twitter = 'Yes'
        if not e[34]:
            hunter_has_twitter = 'No'
        e[34] = hunter_has_twitter

        # Insert Yes if the hunter that hunted the post has a website, No viceversa
        # 35 is the position in the list where the hunter_has_website element is located
        hunter_has_website = 'Yes'
        if not e[35]:
            hunter_has_website = 'No'
        e[35] = hunter_has_website

        # Insert Yes if the maker that launched the post has a twitter account, No viceversa
        # 41 is the position in the list where the maker_has_twitter element is located
        maker_has_twitter = 'Yes'
        if not e[41]:
            maker_has_twitter = 'No'
        e[41] = maker_has_twitter

        # Insert Yes if the maker that launched the post has a website, No viceversa
        # 42 is the position in the list where the maker_has_website element is located
        maker_has_website = 'Yes'
        if not e[42]:
            maker_has_website = 'No'
        e[42] = maker_has_website

        _cleaned_entries.append(e)
    return _cleaned_entries


def write_all_features(outfile, _entries):
    writer = CsvWriter(outfile)
    header = ['post_id', 'post_name', 'version', 'tags_number', 'is_featured', 'score', 'created_at_day',
              'created_at_daytime', 'launched_day', 'is_best_time_to_launch', 'is_best_day_to_launch',
              'is_weekend', 'post_description', 'positive_description_sentiment',
              'negative_description_sentiment', 'discretized_positive_description_score',
              'discretized_negative_description_score', 'discretized_neutral_description_score',
              'text_description_length', 'sentence_length_in_the_description', 'bullet_points_explicit_features',
              'emoji_in_description', 'post_tagline', 'tagline_length', 'emoji_in_tagline', 'are_there_video',
              'are_there_tweetable_images', 'are_there_gif_images', 'number_of_gif', 'offers', 'promo_discount_codes',
              'are_there_questions', 'hunter_id', 'hunter_name', 'hunter_has_twitter', 'hunter_has_website',
              'hunter_followers', 'hunter_apps_made', 'hunter_follows_up_on_comments', 'maker_id', 'maker_name',
              'maker_has_twitter', 'maker_has_website', 'maker_followers', 'maker_follows_up_on_comments']
    writer.writerow(header)
    writer.writerows(_entries)
    writer.close()


# This function realizes topic modeling considering title, tagline and description for each post. Then each topic
# is added to the corresponding post
def realize_topic_modeling(csv_path):
    num_topics = 3  # Number of topics to generate
    document_topic_matrix = lda_topic_modeling(csv_path, num_topics)
    aggregate_topic_variable(document_topic_matrix, csv_path)


def remove_email_and_new_line_chars(text):
    _data = text.values.tolist()  # Convert to list
    _data = [regex.sub(r'\S*@\S*\s?', '', str(sent)) for sent in _data]  # Remove Emails
    _data = [regex.sub(r'\s+', ' ', str(sent)) for sent in _data]  # Remove new line characters
    _data = [regex.sub("\'", "", sent) for sent in _data]  # Remove distracting single quotes
    return _data


def sent_to_words(sentences):
    for sentence in sentences:
        yield(gensim.utils.simple_preprocess(str(sentence), deacc=True))  # deacc=True removes punctuations


def lemmatization(texts, allowed_postags, nlp):
    """https://spacy.io/api/annotation"""
    texts_out = []
    for sent in texts:
        doc = nlp(" ".join(sent))
        texts_out.append(" ".join([token.lemma_ if token.lemma_ not in ['-PRON-'] else '' for token in doc if token.pos_ in allowed_postags]))
    return texts_out


def create_document_topic_matrix(blm, doc_word_matrix, data):
    lda_output = blm.transform(doc_word_matrix)
    # column names
    topicnames = ["Topic" + str(i) for i in range(blm.n_components)]
    # index names
    docnames = ["Doc" + str(i) for i in range(len(data))]
    # Make the pandas dataframe
    df_doc_topic = pd.DataFrame(np.round(lda_output, 2), columns=topicnames, index=docnames)
    return df_doc_topic


def color_green(val):
    color = 'green' if val > .1 else 'black'
    return 'color: {col}'.format(col=color)


def make_bold(val):
    weight = 700 if val > .1 else 400
    return 'font-weight: {weight}'.format(weight=weight)


def show_topics(vectorizer, best_lda_model, n_words):
    keywords = np.array(vectorizer.get_feature_names())
    topic_keywords = []
    for topic_weights in best_lda_model.components_:
        found = 0
        key_words = []
        top_keyword_locs = (-topic_weights).argsort()[:n_words]
        for i in range(0, len(keywords.take(top_keyword_locs))):
            if keywords.take(top_keyword_locs)[i] == 'nan':
                found = 1
                top_keyword_locs = (-topic_weights).argsort()[:n_words+1]
                key_words.append(keywords.take(top_keyword_locs)[i+1])
            else:
                if found == 0:
                    key_words.append(keywords.take(top_keyword_locs)[i])
                else:
                    key_words.append(keywords.take(top_keyword_locs)[i+1])
        topic_keywords.append(key_words)
    return topic_keywords


def lda_topic_modeling(csv_file, n_topics):
    # Import dataset
    df = pd.read_csv(csv_file, delimiter=';', usecols=['post_name', 'post_description', 'post_tagline'])
    print(df.head(15))

    # Remove email and new line characters
    data = remove_email_and_new_line_chars(df.post_tagline)
    print('\n')
    pprint(data[:1])
    data = remove_email_and_new_line_chars(df.post_description)
    print('\n')
    pprint(data[:1])

    # Tokenize and Clean-up text
    data_words = list(sent_to_words(data))
    print('\n', data_words[:1])

    # Lemmatization
    nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])  # Initialize spacy 'en' model, keeping only tagger
    # component (for efficiency)
    data_lemmatized = lemmatization(data_words, ['NOUN', 'ADJ', 'VERB', 'ADV'], nlp)  # Do lemmatization keeping only
    # Noun, Adj, Verb, Adverb
    print('\n', data_lemmatized[:2])

    # Create the Document-Word matrix
    vectorizer = CountVectorizer(analyzer='word',
                                 min_df=10,  # minimum required occurences of a word
                                 stop_words='english',  # remove english stop words
                                 lowercase=True,  # convert all words to lowercase
                                 token_pattern='[a-zA-Z0-9]{3,}',  # number of chars in a word > 3
                                 )
    data_vectorized = vectorizer.fit_transform(data_lemmatized)

    # Check the Sparsicity
    data_dense = data_vectorized.todense()  # Materialize the sparse data
    print("\nSparsicity: ", ((data_dense > 0).sum() / data_dense.size) * 100, "%")  # Compute Sparsicity = Percentage of
    # Non-Zero cells

    # Build LDA model with sklearn
    lda_model = LatentDirichletAllocation(n_components=10,  # Number of topics
                                          max_iter=10,  # Max learning iterations
                                          learning_method='online',
                                          random_state=100,  # Random state
                                          batch_size=128,  # number of documents in each learning iter
                                          evaluate_every=-1,  # compute perplexity every n iters, default: Don't
                                          n_jobs=-1,  # Use all available CPUs
                                          )
    lda_output = lda_model.fit_transform(data_vectorized)
    print('\n', lda_model)  # Model attributes

    # Diagnose model performance with perplexity and log-likelihood
    print("\nLog Likelihood: ", lda_model.score(data_vectorized))  # Log Likelyhood: Higher the better
    print("Perplexity: ", lda_model.perplexity(data_vectorized))  # Perplexity: Lower the better.
    # Perplexity = exp(-1. * log-likelihood per word)
    pprint(lda_model.get_params())  # See model parameters

    # GridSearch the best LDA model
    search_params = {'n_components': [n_topics], 'learning_decay': [.5, .7, .9]}  # Define Search Param
    model = GridSearchCV(lda_model, param_grid=search_params, n_jobs=1, iid=True, cv=3, error_score='raise')  # Init Grid Search Class
    model.fit(data_vectorized)  # Do the Grid Search

    # Find the best topic model and its parameters
    best_lda_model = model.best_estimator_  # Best Model
    print("\nBest Model's Params: ", model.best_params_)  # Model Parameters
    print("Best Log Likelihood Score: ", model.best_score_)  # Log Likelihood Score
    print("Model Perplexity: ", best_lda_model.perplexity(data_vectorized))  # Perplexity

    # How to see the dominant topic in each document
    df_document_topic = create_document_topic_matrix(best_lda_model, data_vectorized, data)
    n_documents = 15  # This number indicates an excerpt of documents to which visualize their own dominant topic
    df_document_topics = df_document_topic.head(n_documents).style.applymap(color_green).applymap(
        make_bold).highlight_max(color='yellow', axis=1)
    print('\n', df_document_topics)

    # Get the top 15 keywords each topic
    topic_keywords = show_topics(vectorizer, best_lda_model, 15)  # Show top n keywords for each topic in order of
                                                                  # highest probability. In this case n is equal to 15
    df_topic_keywords = pd.DataFrame(topic_keywords)  # Topic- Keywords Dataframe
    df_topic_keywords.columns = ['Word ' + str(i) for i in range(df_topic_keywords.shape[1])]
    df_topic_keywords.index = ['Topic ' + str(i) for i in range(df_topic_keywords.shape[0])]
    print('\n', df_topic_keywords)
    return df_document_topic


def aggregate_topic_variable(doc_topic_matrix, csv):
    # Add column Topic to the features csv file
    dominant_topic = np.argmax(doc_topic_matrix.values, axis=1)
    features = pd.read_csv(csv, delimiter=';')
    features['topic'] = dominant_topic

    # Update csv file with Topic column
    features.to_csv(csv, sep=';', index=False)


# The elbow method to determine the number of clusters
def elbow_method(column):
    # Instantiate the clustering model
    model = KMeans()
    visualizer = KElbowVisualizer(model, k=(1, 11), timings=False)
    # Plot visualizer
    plt.figure(figsize=(10, 5))
    # Fit the data to the visualizer
    visualizer.fit(column)
    return visualizer


# Create the directory where to save plot graphs
def create_plot_directory(directory):
    os.mkdir(directory)


# Clustering-based discretization using k-means clustering
def discretize(column, n_bins):
    disc = KBinsDiscretizer(n_bins, encode='ordinal', strategy='kmeans')
    disc.fit(column)
    disc.transform(column)
    return disc


def create_bins(values):
    bins = []
    for i in range(0, len(values)):
        bins.append(int(values[i]))
    return bins


# Discretizing continuous variables
def discretize_continuous_variables(csv):
    data = pd.read_csv(csv, delimiter=';')
    data_disc = data.copy()

    # Create the directory where to save the plot graphs
    plot_save_dir = os.getcwd() + "\\plot_figures"
    if not os.path.isdir(plot_save_dir):
        create_plot_directory(plot_save_dir)

    # Text description length discretization
    text_length = data_disc.iloc[:, 18:19]  # position where is located the column text_description_length
    plotter = elbow_method(text_length)
    plotter.show(plot_save_dir + "\\clustering-based discretization for Text Length")
    disc = discretize(text_length, plotter.elbow_value_)
    bins = create_bins(disc.bin_edges_[0])
    print("Range of numbers for Text Length {}".format(bins))
    group_names = ['Short', 'Medium', 'Long']
    text_length['text_description_length'] = pd.cut(text_length['text_description_length'], bins, labels=group_names,
                                                 include_lowest=True)

    # Sentence length discretization
    sentence_length = data_disc.iloc[:, 19:20]  # position where is located the column sentence_length_in_the_description
    plotter = elbow_method(sentence_length)
    plotter.show(plot_save_dir + "\\clustering-based discretization for Sentence Length")
    disc = discretize(sentence_length, plotter.elbow_value_)
    bins = create_bins(disc.bin_edges_[0])
    print("Range of numbers for Sentence Length {}".format(bins))
    group_names = ['Short', 'Medium', 'Long']
    sentence_length['sentence_length_in_the_description'] = pd.cut(
        sentence_length['sentence_length_in_the_description'], bins, labels=group_names, include_lowest=True)

    # Tagline length discretization
    tagline_length = data_disc.iloc[:, 23:24]  # position where is located the column tagline_length
    plotter = elbow_method(tagline_length)
    plotter.show(plot_save_dir + "\\clustering-based discretization for Tagline Length")
    disc = discretize(tagline_length, 3)
    bins = create_bins(disc.bin_edges_[0])
    print("Range of numbers for Tagline Length {}".format(bins))
    group_names = ['Short', 'Medium', 'Long']
    tagline_length['tagline_length'] = pd.cut(tagline_length['tagline_length'], bins, labels=group_names,
                                              include_lowest=True)

    # Hunter followers discretization
    hunter_followers = data_disc.iloc[:, 36:37]  # position where is located the column hunter_followers
    plotter = elbow_method(hunter_followers)
    plotter.show(plot_save_dir + "\\clustering-based discretization for Hunter Followers")
    disc = discretize(hunter_followers, plotter.elbow_value_)
    bins = create_bins(disc.bin_edges_[0])
    print("Range of numbers for Hunter Followers {}".format(bins))
    group_names = ['Low', 'Good', 'High']
    hunter_followers['hunter_followers'] = pd.cut(hunter_followers['hunter_followers'], bins, labels=group_names,
                                                  include_lowest=True)

    # Hunter apps made discretization
    hunter_apps_made = data_disc.iloc[:, 37:38]  # position where is located the column hunter_apps_made
    plotter = elbow_method(hunter_apps_made)
    plotter.show(plot_save_dir + "\\clustering-based discretization for Hunter Apps Made")
    disc = discretize(hunter_apps_made, plotter.elbow_value_)
    bins = create_bins(disc.bin_edges_[0])
    print("Range of numbers for Hunter Apps Made {}".format(bins))
    group_names = ['Few', 'Satisfactory', 'Many']
    hunter_apps_made['hunter_apps_made'] = pd.cut(hunter_apps_made['hunter_apps_made'], bins, labels=group_names,
                                                  include_lowest=True)

    # Maker followers discretization
    maker_followers = data_disc.iloc[:, 43:44]  # position where is located the column maker_followers
    plotter = elbow_method(maker_followers)
    plotter.show(plot_save_dir + "\\clustering-based discretization for Maker Followers")
    disc = discretize(maker_followers, plotter.elbow_value_)
    bins = create_bins(disc.bin_edges_[0])
    print("Range of numbers for Maker Followers {}".format(bins))
    group_names = ['Low', 'Good', 'High']
    maker_followers['maker_followers'] = pd.cut(maker_followers['maker_followers'], bins, labels=group_names,
                                                include_lowest=True)

    # Topic discretization
    topic = data_disc.iloc[:, 45:46]  # position where is located the column Topic
    topic['topic'] = topic['topic'].map({0: 'web development', 1: 'creativity', 2: 'community'})

    # Changing continuous variables with discretized values for text length, sentence length, tagline length,
    # hunter_followers, hunter_apps_made, maker_followers and topic column
    data_disc['text_description_length'] = text_length
    data_disc['sentence_length_in_the_description'] = sentence_length
    data_disc['tagline_length'] = tagline_length
    data_disc['hunter_followers'] = hunter_followers
    data_disc['hunter_apps_made'] = hunter_apps_made
    data_disc['maker_followers'] = maker_followers
    data_disc['topic'] = topic
    data_disc.to_csv("features.csv", sep=';', index=False)


def main():
    """ set up logging """
    now = datetime.datetime.now(timezone('US/Pacific')).strftime("%Y-%m-%d")
    logger = logging_config.get_logger(_dir=now, name="ph_feature_extraction", console_level=logging.ERROR)

    csv_file_name = 'features.csv'  # csv file name where the features will be saved

    """ set up environment vars """
    os.environ['DB_CONFIG'] = os.path.abspath('db/cfg/dbsetup.yml')
    session = setup_db(os.environ['DB_CONFIG'])
    os.environ['FEATURES'] = os.path.abspath(csv_file_name)

    entries = extract_all_features(session, logger)
    entries = clean_features(entries)
    write_all_features(os.environ['FEATURES'], entries)

    csv_path = os.getcwd() + '\\' + csv_file_name
    realize_topic_modeling(csv_path)

    discretize_continuous_variables(csv_path)


if __name__ == '__main__':
    main()
    exit(0)
