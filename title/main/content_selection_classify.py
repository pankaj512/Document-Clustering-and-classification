import math
import operator
import pickle

from nltk.corpus import stopwords

from title.main.Utils import get_start_end_indices
from title.main.featureFunctions.features import get_feature_dict
from title.main.featureFunctions.file_level_features import get_word_range

classifier = None
tfidf_dict = {}
stop_word_list = []

TFIDF_LOCATION = 'model/tfidf.pickle'  # this file is missing  --resolved


def initialise():
    """Initialises the globally declared variables.

    These variables are used throughout the file.
    """
    global classifier, tfidf_dict, stop_word_list
    with open('model/content_selection.pickle','rb') as file:  # this file is missing
        classifier = pickle.load(file)

    with open(TFIDF_LOCATION, 'r') as file:
        for line in file:
            parts = line.strip().split(' ')
            if len(parts) >= 2:
                tfidf_dict[parts[0]] = parts[1]

    stop_word_list = stopwords.words('english')
    return

def get_tfidf_score(all_lines):
    """For an entire file text, returns a dictionary mapping word to range of tf-idf values it belongs to.

    This information is used as a part of feature function.
    """
    global tfidf_dict

    word_dict = {}

    for line in all_lines:
        word_list = line.strip().split()
        for word in word_list:
            word = word.rsplit('/', 1)[0]
            if word in tfidf_dict:
                word_dict[word] = tfidf_dict.get(word)
    all_values = list(word_dict.values())
    all_values.sort()

    length = len(all_values) - 1
    first_range_boundary = all_values[int(math.floor(0.9 * length))]
    second_range_boundary = all_values[int(math.floor(0.1 * length))]

    for (key, value) in word_dict.items():
        if value >= first_range_boundary:
            word_dict[key] = '1_10'
        elif value >= second_range_boundary:
            word_dict[key] = '10_90'
        else:
            word_dict[key] = '90_100'
    return word_dict


def get_file_level_details(file_path, headers_present=True):
    """Returns file level feature functions details.

    These are used as a part of the feature functions for querying the models.
    """
    global file_level_dict
    with open(file_path, 'r') as file:
        lines = file.readlines()
        all_lines = lines[1:]
        file_level_dict = get_word_range(all_lines)
        word_dict = get_tfidf_score(all_lines)
    return file_level_dict, word_dict


def process_sentence(sentence, file_level_dict, word_dict):
    """For the sentence passed, returns the words along with the probabilities of each word to be present in title.

    Uses the content generation model trained before to get the probability.
    """
    global classifier
    if len(sentence)<=0:
        return
    words = sentence.strip().split()

    title_words = {}

    for index in range(0, len(words)):
        start_index, end_index = get_start_end_indices(index, len(words))
        feature_dict = get_feature_dict(words[start_index: end_index],file_level_dict,word_dict,index-start_index)

        word = words[index].rsplit('/', 1)[0]
        feature_dict['stop_word'] = 1 if word in stop_word_list else 0

        output = classifier.prob_classify(feature_dict)

        if output.prob(1) > 0.0:
            title_words[words[index]] = max(output.prob(1), title_words.get(words[index], 0)) # if present then value else 0

    return title_words


def classify_dev_file(file_location):
    """For given file path, returns a dictionary of all the words along with the probability value.

    This function is called by title synthesis process during training and so return value consists of all the words.
    """
    global classifier
    file_level_dict, word_dict = get_file_level_details(file_location)
    with open(file_location, 'r') as file:
        sentences = file.readlines()
        actual_title = sentences[0]
        all_potential_title_words = {}
        sentences = sentences[1:]
        for sentence in sentences:
            title_words = process_sentence(sentence, file_level_dict, word_dict)
            """
            words with probability to be included in title
            """
            if title_words:
                for (key, value) in title_words.items():
                    all_potential_title_words[key] = max(value, all_potential_title_words.get(key, 0))

    return actual_title, all_potential_title_words
    """
    actual_title = given title of file
    all_potential_title_words = words with heighest probability
    """


def classify_new_file(file_path):
    """
    This function is called by decoding algorithm.
    For given input file, it returns a dictionary of 20 words along with their associated probability which are most
    suitable to be included in the title.
    """
    file_level_dict, word_dict = get_file_level_details(file_path, False)
    all_potential_title_words = {}

    with open(file_path, 'r') as file:
        sentences = file.readlines()
        for sentence in sentences:
            title_words = process_sentence(sentence, file_level_dict, word_dict)
            if title_words:
                for (key, value) in title_words.items():
                    all_potential_title_words[key] = max(value, all_potential_title_words.get(key, 0))

    dict_unique_words = {}
    sorted_title_words = sorted(all_potential_title_words.items(), key=operator.itemgetter(1), reverse=True)
    top_25_words= {}
    for entry in sorted_title_words:
        word_with_tag, value = entry
        word = word_with_tag.rsplit('/', 1)[0]
        if word not in dict_unique_words:
            dict_unique_words[word] = 1
        top_25_words[word_with_tag] = value
        if len(dict_unique_words) > 25:
            break
    print('\t\tReturning Top 25 Words')
    return top_25_words
    """
    top_25_words = a dictionary of word with tag and its value
    """
