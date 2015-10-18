__author__ = 'piligrim'

import pandas as pd
import ngram
from collections import defaultdict
from functools import reduce


NOT_FOUND_ = '<not found>'
ERROR_ = '<error>'
EMPTY_ = '<empty>'

# Custom fields
# Street name, lower case
STR_LC = 'street_lower'
# Building number, lower case
BUILD_LC = 'build_lower'
# Apartments number, lower case
APT_LC = 'apt_lower'


def get_from_dict(dataDict, mapList):
    return reduce(lambda d, k: d.setdefault(k, defaultdict(set)), mapList, dataDict)


def set_in_dict(dataDict, mapList, value):
    get_from_dict(dataDict, mapList[:-1])[mapList[-1]].add(value, )


class AddressParser(object):
    def __init__(self, addr_book_df=None, addr_book_file=None, street_field=None, build_field=None,
                 apt_field=None):
        self.addr_book = addr_book_df
        self.street_field = street_field
        self.build_field = build_field
        self.apt_field = apt_field

        if self.addr_book is None:
            self._load_file(addr_book_file)
        self.unique_street_names = self.addr_book.groupby(by=STR_LC, sort=False,
                                                          group_keys=True).groups.keys()
        self.street_num_ngrams = self.street_to_numbers_ngrams()
        self.street_name_ngrams = self.street_name_ngrams()

        index = defaultdict(list)
        self.addr_book.apply(
            lambda row: set_in_dict(index, (row[STR_LC], row[BUILD_LC]), row[APT_LC]), axis=1)
        self.addr_dict = index
        self.street_names_cache = {}


    def _load_file(self, addr_book_file):
        addr_book = pd.read_excel(addr_book_file, header=1, encoding='utf-8')
        addr_book[STR_LC] = addr_book[self.street_field].str.lower()
        self.cast_column_to_string(addr_book, from_=self.build_field, to_=BUILD_LC)
        self.cast_column_to_string(addr_book, from_=self.apt_field, to_=APT_LC)

        self.addr_book = addr_book

    def build_address_index(self):
        index = defaultdict(defaultdict)
        self.addr_book.apply(lambda row: set_in_dict(index, (row[STR_LC], row[BUILD_LC]),
                                                     row[APT_LC]), axis=1)

    @staticmethod
    def to_str(x):
        return x if isinstance(x, str) else str(x).split('.')[0]


    @staticmethod
    def cast_column_to_string(df, from_, to_=None):
        if not to_:
            to_ = from_
        df[to_] = df[from_].fillna(EMPTY_).apply(AddressParser.to_str).str.lower().tolist()


    def street_to_numbers_ngrams(self):
        """ Returns mapping from lower case street name to possible number's ngrams """
        str_to_addr_ngram = defaultdict(lambda: NOT_FOUND_)
        street_groups = self.addr_book.groupby(by=STR_LC, sort=False, group_keys=True)
        for street_name, group in street_groups:
            street_addresses = group[BUILD_LC] + '$' + group[APT_LC]
            st_ngr = ngram.NGram(street_addresses.tolist(), N=3)
            str_to_addr_ngram[street_name] = st_ngr
        return str_to_addr_ngram


    def street_name_ngrams(self):
        """ Returns street names ngrmas """
        return ngram.NGram(self.unique_street_names, N=2)


    def parse_street_name(self, street_name):
        if not isinstance(street_name, str):
            street_name = str(street_name)
            print('WARN! street name is not a string, casting to str: ' + street_name)

        if ERROR_ in street_name:
            return ERROR_, 0

        if street_name in self.street_names_cache:
            return self.street_names_cache[street_name]

        matched_street_name = self.street_name_ngrams.search(street_name)[0]
        self.street_names_cache[street_name] = matched_street_name
        return matched_street_name


    def parse_build_number(self, street, addr):
        """ Returns building number, apartments number and matching score"""
        if pd.isnull(addr) or ERROR_ in addr:
            print('ERROR! Address is empty for street: ' + street)
            return ERROR_, ERROR_, 0

        ngr = self.street_num_ngrams[street]
        if NOT_FOUND_ in str(ngr):
            print('ERROR! No build number ngrams for street: ' + street)
            return ERROR_, ERROR_, 0

        result = ngr.search(addr)

        if not result:
            return ERROR_, ERROR_, 0

        number, score = result[0]
        build, apt = number.split('$')
        return build, apt, score


# parser = AddressParser('address_book - Copy.xlsx', street_field='Улица', build_field='Дом', apt_field='Квартира')
# parser = AddressParser(pd.DataFrame([1, 2,3]), street_field='Улица', build_field='Дом', apt_field='Квартира')
# street_name = parser.parse_street_name('червона балка')[0]
# print(street_name[0])
#
# test_addr = [('электрическая,', ' 22'),
#              ('к.либкнехта,', ' 1/3/7'),
#              ('титова, ', '30/71'),
#              ('короленко', ''),
#              ('донецкое ш.,', ' 121/13'),
#              ('гагарина, ', '86/13'),
#              ('савченко, ', '64/55'),
#              ('карагандинская, ', '11а/61'),
#              ('20 лет победы, ', '27/30'),
#              ('20 победы, ', '27/30'),
#              ('будёного, ', '98'),
#              ('савина, ', '2/24'),
#              ('ленина, ', '9'),
#              ('калиновая, ', '19/7'),
#              ('сумская, ', '68'),
#              ('правды, ', '10/16'),
#              ('светлова, ', '65/2'),
#              ('шолохова, ', '39/88'),
#              ('минина, ', '3/99'),
#              ('арсеничева,', ' 121/42'),
#              ('победы, ', '44а/6/537')
#              ]
#
# for t in test_addr:
#     parsed_str = parser.parse_street_name(t[0])
#     street_name = parsed_str[0]
#     number = str(parser.parse_build_number(street_name, t[1]))
#     print(str(t) + ' --> ' + street_name + '  ' + number)
#
#
