__author__ = 'piligrim'

import re
from phonenumbers import *
import pandas as pd


# accepts lower case addresses
def address_splitter(addr_string):
    split_addr_regex = re.compile('^(\D*)(.*)$')
    addr_string = str(addr_string)

    special_cases_partials = ['квартал',
                              'беляева', 'бригадна.',
                              'влксм',
                              'горяна.',
                              'дивизи', 'дивізі', 'дн[ие]пропетровщин[иы]',
                              'їзду', 'їзда', 'езду', 'езда',
                              'изюмский переулок', 'иллича', 'илъича',
                              'ильича',
                              'комсомола', 'комсомол',
                              'леваневского',
                              'марта', 'мая',
                              'октября', 'осипенко',
                              'победы', '22 партизана',
                              'парус[-\s]*1', 'парус[-\s]*2', 'парус[-\s]*3',
                              'років перемоги',
                              'січня',
                              'сокол[-\s]*1', 'сокол[-\s]*2', 'сокол[-\s]*3',
                              'т[-\s]*1', 'т[-\s]*2', 'т[-\s]*3',
                              'тополь[-\s]*1', 'тополь[-\s]*2', 'топол[ья][-\s]*3', 'травня',
                              'ульяновской', 'января']

    special_case_regex = '(.*%s)(.*)'
    regexes = list()

    for x in special_cases_partials:
        regex = re.compile(special_case_regex % x)
        regexes.append(regex)

    regexes.append(split_addr_regex)

    match = None
    for r in regexes:
        match = r.search(addr_string)
        if match:
            break

    if not match:
        return '<error>', '<error>'

    return match.groups()


def tel_matcher(tel):
    if pd.isnull(tel):
        return []
    matcher = PhoneNumberMatcher(tel, region="UA", leniency=Leniency.POSSIBLE)
    return [x.number.national_number for x in matcher]


def parse_tel(tel1, tel2):
    result1 = tel_matcher(str(tel1))
    result2 = tel_matcher(str(tel2))

    result = result1 + result2
    size = len(result)
    tup = ('', '', '')
    if size >= 3:
        tup = result[:3]
    if size == 2:
        tup = result + ['']
    if size == 1:
        tup = result + ['', '']
    return tuple(tup)


print(tel_matcher('0523 23 23      434 54 454'))


class AddressNumber:
    NOT_FOUND = '<not found>'

    def __init__(self, text):
        self.text = text
        self.build = self.NOT_FOUND
        self.build_suffix = None
        self.corpus = None
        self.apt = None

    def __str__(self, *args, **kwargs):
        suffix = ''
        if self.build_suffix:
            suffix = '-' + self.build_suffix
        if self.corpus:
            suffix += '/' + self.corpus
        if self.apt:
            suffix += ', #' + str(self.apt)
        return self.build + suffix


SEP = ['/', '\\', '-', ' ', ',']
APT_SEP_REGEX = '[,;\s]'
SEP_SPLIT_REGEX = '[%s]*' % ''.join(['/', '\\', '-', ','])
DIGIT_GROUPS = re.compile('\d+')


def next_(string, fun):
    for i, c in enumerate(string):
        if fun(c):
            return i, c


def while_(string, fun):
    prev_index, prev_char = -1, ''
    for i, c in enumerate(string):
        if not fun(c):
            return prev_index, prev_char
        prev_index, prev_char = i, c


def find_by_predicate(str_, predicate):
    for i, c in enumerate(str_):
        if predicate(c):
            return i, c
    return None, None


def rfind_by_predicate(str_, predicate):
    for i, c in enumerate(reversed(str_)):
        if predicate(c):
            return i, c
    return None, None


def parse_build_num_suffix(string):
    # potential_bld_alpha_idx, c = while_(string, lambda cur: cur is ' ' or cur.isalpha())
    suffix = re.search('[\d\w]{1,3}', string)

    if not suffix or len(suffix.group(0)) > 2:
        return ''

    return suffix.group(0)


def is_multiple_apt(addr):
    apt_start = addr.rfind('кв')
    apt = addr[apt_start:]
    return len(DIGIT_GROUPS.findall(apt)) > 1


def is_multi_delimited_string(str_, delimiters):
    delims = []
    for d in delimiters:
        if d in str_:
            delims.append(d)

    return len(delims) > 1, delims


def find_suffix_delimiter(apt_part, delim_candidates):
    suffix_delimiter = None
    # find non apt delimiter, eg 23-a or 23/a
    alpha_index, alpha = find_by_predicate(apt_part, lambda x: x.isalpha())
    digit_index, digit = rfind_by_predicate(apt_part[:alpha_index], lambda x: x.isdigit())
    # treat delimiter between digit and character as non apt delimiter
    for delim_candidate in delim_candidates:
        if delim_candidate in apt_part[digit_index: alpha_index]:
            suffix_delimiter = delim_candidate

    return suffix_delimiter


def parse_apt(addr, potential_apt):
    apts = '<error>'
    apt_group_start = len(addr)
    apt_num_search = re.search('\d+', potential_apt)
    if apt_num_search:
        apt_group_start = addr.rfind(potential_apt)
        apt_start = apt_num_search.start()
        apt_part = potential_apt[apt_start:]

        apt_delimiter, suffix_delimiter = None, None
        possible_delimiters = [',', ';', '/', '\\', '-']
        is_multi_delim, delim_candidates = is_multi_delimited_string(apt_part, possible_delimiters)

        if is_multi_delim:
            suffix_delimiter = find_suffix_delimiter(apt_part, delim_candidates)
        if suffix_delimiter:
            delim_candidates.remove(suffix_delimiter)
        apt_delimiter = delim_candidates[0] if len(delim_candidates) > 0 else None

        if apt_delimiter:
            apt_groups = apt_part.split(apt_delimiter)
            trans_table = str.maketrans('()', '  ')
            apts = [apt.translate(trans_table) for apt in apt_groups]
        else:
            apts = re.findall('[\d\-\w]{1,5}', apt_part)

    return apts, apt_group_start


def find_groups(addr):
    prefix = addr
    possible_delimiters = [',', '/', '\\', ';']
    is_multi_delim, potential_delims = is_multi_delimited_string(prefix, possible_delimiters)
    scores = {}
    if ',' in potential_delims:
        scores = {',': 1}

    apt = None
    search = re.search('кв', addr)
    if search:
        prefix, apt = addr[: search.start()], addr[search.start():]
        position, delim = rfind_by_predicate(prefix, lambda x: not x.isdigit() and x in possible_delimiters)
        if not delim:
            position, delim = rfind_by_predicate(prefix, lambda x: not x.isdigit() and x == ' ')
        prefix = prefix[: -(position + 1)]

        if delim not in scores:
            scores[delim] = 1
        else:
            scores[delim] += 1

    for d in potential_delims:
        scores.setdefault(d, prefix.count(d)) + prefix.count(d)

    delimiter = max(scores, key=scores.get)
    delimited_groups = prefix.split(delimiter)
    numeric_groups = DIGIT_GROUPS.findall(prefix)
    groups = delimited_groups if len(delimited_groups) < len(numeric_groups) else numeric_groups
    if apt:
        groups.append(apt)
    return groups

    # tuple_ = addr.split('кв')
    #
    # if len(tuple_) < 2:
    #     return DIGIT_GROUPS.findall(addr)
    #
    # prefix, suffix = tuple_
    # search = re.search('\d+', suffix)
    # if search:
    #     apt = suffix[search.start():]
    # return DIGIT_GROUPS.findall(prefix) + [apt]


def parse_build_number(addr='23  -d/12, кв.11'):
    rend = end = len(addr) - 1
    num_groups = find_groups(addr)
    parsed = AddressNumber(addr)

    if not num_groups:
        return parsed

    complexity = len(num_groups)
    if complexity > 4:  # or is_multiple_apt(addr)
        return '<ambiguous address'

    if complexity == 4:
        (build_num, build_suffix, corpus, apt) = num_groups
        # parse apt
        parsed.apt, rend = parse_apt(addr, apt)

        # parse building number
        tail = addr[: rend]
        build_num_start = tail.find(build_num)
        corpus_start = tail.rfind(corpus)

        parsed.build = build_num
        parsed.build_suffix = parse_build_num_suffix(tail[build_num_start + len(build_num):])

        # parse corpus
        tail = tail[corpus_start:]
        parsed.corpus = re.search(r'[\d\w]{1,3}', tail).group(0)
        return parsed

    if complexity == 3:
        (build_num, corpus, apt) = num_groups
        # parse apt
        parsed.apt, rend = parse_apt(addr, apt)

        # parse building number
        tail = addr[: rend]
        build_num_start = tail.find(build_num)
        corpus_start = tail.rfind(corpus)
        suffix = tail[build_num_start + len(build_num): corpus_start]

        parsed.build = build_num
        parsed.build_suffix = parse_build_num_suffix(suffix)

        # parse corpus
        tail = addr[corpus_start: rend]
        match = re.match('[\d\w]{1,3}', tail)
        parsed.corpus = match.group(0) if match else None
        return parsed

    if complexity == 2:
        (build_num, apt) = num_groups
        # parse apt
        parsed.apt, rend = parse_apt(addr, apt)

        # parse building number
        tail = addr[: rend]
        build_num_start = tail.find(build_num)

        parsed.build = build_num
        parsed.build_suffix = parse_build_num_suffix(tail[build_num_start + len(build_num):])

        return parsed


        # if complexity == 1:
        #     build_num_start = addr.find(build_num)
        #     corpus_start = rend
        #     tail = addr[build_num_start + len(build_num): corpus_start]
        #     build_num += parse_build_num_suffix(tail)
        #
        # if corpus:
        #     corpus_start = addr.find(corpus)

        # tail = addr[build_num_start + len(build_num): corpus_start]
        # build_parsed = build_num + parse_build_num_suffix(tail)
        #
        # build_num_start, c = next_(addr, str.isdigit)
        # # is next is end of string  == build number found, return
        # # is next is alpha -> move until not digit
        # #     is next is digit or separator  == end of potential build
        # #     is next is alpha -> move until digit or separator == end of potential build
        #
        # corpus_start, c = while_(addr, str.isdigit)
        # build_num = addr[build_num_start:corpus_start + 1]
        #
        # if corpus_start + 1 > end:
        #     return build_num
        #
        # rest = addr[corpus_start + 1:]
        #
        # second_part_start, c = next_(rest, str.isdigit)
        # potential_build_alpha, second_part = rest[:second_part_start], rest[second_part_start:]
        # build_num += parse_build_num_suffix(potential_build_alpha)
        #
        # return build_parsed


import time

samples = [
    '3/4/5',
    '18, кв.205-206-207', '18, кв.207,206,205',
    '18, кв 211-212-213', '18, кв 311,316,318',
    '18, кв.701,707,709,711,721,7', '18, кв.901-907-909-911-921-923', '9, кв.88,89,90',
    '5/7, кв.5/1',
    '16/18, кв.3/4', '16/18, кв.1,2', '75а, корп.3, кв.6,7', '1, кв.24,25,26',
    '122, кв.5,7,8', '8, корп.2, кв.15,16', '4гурт, кв.141,517,518', '4гурт, кв.517,518,141',
    '7, кв.1,2,3,4', '7, кв.1/2/3/4', '5, кв.1/2/3',
    ', 22, корп.7), кв.61)',
    '19а, кв.115',
    '2, кв. 10-а', '8, кв.267',
    ', 22, корп.7, кв.61',
    '18, кв. 1а)',
    '60, кв. 259)',
    '83, корп.3, кв.56',
    '38 кв 180',
    '122/148', '164а, кв. 37', '97а/51', ', буд. 57, кв. 154', '20б, кв.77', ', 3, кв.159',
    ', 51, корп.3, кв.86',
    '70б, кв.52', '73, кв.110', '77, кв.48', '46, кв. 441', '127а/68',
]

# start = time.clock()
# for s in samples:
#     address = parse_build_number(s)
#     print(str(s) + ' ->> ' + str(address))
#
# print('time: ' + str(time.clock() - start))
# print('sample size: ' + str(len(samples)))


def test():
    d = {'18, кв.205-206-207': "18, #['205', '206', '207']",
         '18, кв.207,206,205': "18, #['207', '206', '205']"}
    for k in d:
        expected = d[k]
        actual = parse_build_number(k)
        if not actual.__eq__(expected):
            print('actual: ' + str(actual) + ', expected:  ' + expected)
            raise Exception
