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


def parse_apt(addr, potential_apt):
    apt_num_search = re.search('\d+', potential_apt)
    apts = '<error>'
    apt_group_start = addr.rfind(potential_apt)
    if apt_num_search:
        apt_start = apt_num_search.start()
        apt_part = potential_apt[apt_start:]
        apts = re.findall('[\d\-\w]{1,5}', apt_part)

    return apts, apt_group_start


def find_groups(addr):
    search = re.search('кв', addr)
    if not search:
        return DIGIT_GROUPS.findall(addr)

    prefix, apt = addr[: search.start()], addr[search.start():]
    return DIGIT_GROUPS.findall(prefix) + [apt]

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
        (parsed.build, build_suffix, corpus, apt) = num_groups
        # parse apt
        parsed.apt, rend = parse_apt(addr, apt)

        # parse building numer
        tail = addr[: rend]
        build_num_start = tail.find(parsed.build)
        parsed.build_suffix = parse_build_num_suffix(tail[build_num_start + len(parsed.build):])
        return parsed

    if complexity == 3:
        (build_num, corpus, apt) = num_groups
        # parse apt
        parsed.apt, rend = parse_apt(addr, apt)

        # parse building number
        tail = addr[: rend]
        build_num_start = tail.find(build_num)
        build_num_end = tail.find(corpus)

        suffix = parse_build_num_suffix(tail[build_num_start + len(build_num): build_num_end])
        parsed.build = '-'.join(filter(None, (build_num, suffix)))

        # parse corpus
        tail = tail[build_num_end:]
        parsed.corpus = re.search(r'[\d\w]{1,3}', tail).group(0)
        return parsed

    if complexity == 2:
        (build_num, apt) = num_groups
        # parse apt
        parsed.apt, rend = parse_apt(addr, apt)

        # parse building number
        tail = addr[: rend]
        build_num_start = tail.find(build_num)
        build_num_end = tail.find(apt)

        suffix = parse_build_num_suffix(tail[build_num_start + len(build_num): build_num_end])
        parsed.build = '-'.join(filter(None, (build_num, suffix)))

        return parsed


        # if complexity == 1:
    #     build_num_start = addr.find(build_num)
    #     build_num_end = rend
    #     tail = addr[build_num_start + len(build_num): build_num_end]
    #     build_num += parse_build_num_suffix(tail)
    #
    # if corpus:
    #     build_num_end = addr.find(corpus)

    # tail = addr[build_num_start + len(build_num): build_num_end]
    # build_parsed = build_num + parse_build_num_suffix(tail)
    #
    # build_num_start, c = next_(addr, str.isdigit)
    # # is next is end of string  == build number found, return
    # # is next is alpha -> move until not digit
    # #     is next is digit or separator  == end of potential build
    # #     is next is alpha -> move until digit or separator == end of potential build
    #
    # build_num_end, c = while_(addr, str.isdigit)
    # build_num = addr[build_num_start:build_num_end + 1]
    #
    # if build_num_end + 1 > end:
    #     return build_num
    #
    # rest = addr[build_num_end + 1:]
    #
    # second_part_start, c = next_(rest, str.isdigit)
    # potential_build_alpha, second_part = rest[:second_part_start], rest[second_part_start:]
    # build_num += parse_build_num_suffix(potential_build_alpha)
    #
    # return build_parsed


import time
samples = [
    ', 22, корп.7, кв.61', '23  -3d/12, кв.11;12-2', '19а, кв.115', '2, кв. 10-а', '8, кв.267',
    '101, кв.906', '40а, кв. 6', '9а, кв.24', '105, кв. 44', '8, кв. 543', '28в, кв.102',
    '6, кв. 271)', '80, кв. 406', ', 106, кв.1', '112, кв. 47', ', 22, корп.7, кв.61',
    '18, кв. 1а)',
    '60, кв. 259)',
    '83, корп.3, кв.56', '37, кв. 167', '38 кв 180', '6, кв. 104', '16, кв.433',
    '122/148', '164а, кв. 37', '97а/51', ', буд. 57, кв. 154', '20б, кв.77', ', 3, кв.159',
    '60, кв. 65', '5т, кв. 89', '63, кв. 71', '164а, кв. 110', '34а, кв.7', ', 51, корп.3, кв.86',
    '70б, кв.52', '73, кв.110', '77, кв.48', '46, кв. 441', '127а/68',
    ]

start = time.clock()
for s in samples:
    address = parse_build_number(s)
    print(str(s) + ' ->> ' + str(address))

print('time: ' + str(time.clock() - start))
print('sample size: ' + str(len(samples)))