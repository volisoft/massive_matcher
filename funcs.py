__author__ = 'piligrim'

import re
from phonenumbers import *
import pandas as pd


# accepts lower case addresses
def address_splitter(addr_string):
    split_addr_regex = re.compile(r'^(\D*)(.*)$')
    addr_string = str(addr_string)

    special_cases_partials = ['лет.*победы', 'років перемоги', 'ульяновской', 'влксм', 'осипенко',
                              'дивизи', 'дивізі', 'бригадна', 'травня', 'мая', 'комсомол', 'партсъезда',
                              'партсьезда', '22партзїзду', 'изюмский переулок', 'горяна', 'иллича', 'ильича', 'илъича'
                              'комсомола', '12[\s*]квартал', 'беляева', 'леваневского',
                              'октября', 'марта', 'січня', 'января',
                              'тополь[-\s]*1', 'тополь[-\s]*2', 'тополь[-\s]*3', 'т[-\s]*1',
                              'т[-\s]*2', 'т[-\s]*3']

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
