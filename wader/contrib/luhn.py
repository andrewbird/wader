#!/usr/bin/python
#
# From Wikipedia: http://en.wikipedia.org/wiki/Luhn_algorithm
#
# The Luhn algorithm or Luhn formula, also known as the "modulus 10"
# or "mod 10" algorithm, is a simple checksum formula used to validate
# a variety of identification numbers, such as credit card numbers,
# IMEI numbers, etc.
#
# The algorithm is in the public domain and is in wide use today. It
# is specified in ISO/IEC 7812-1.

# This following code is copied from Wikipedia:


def is_luhn_valid(cc):
    num = [int(x) for x in str(cc)]
    return sum(num[::-2] +
               [sum(divmod(d * 2, 10)) for d in num[-2::-2]]) % 10 == 0
