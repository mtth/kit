#!/usr/bin/env python

from app.core.util import UnicodeDictReader

fields = [
        ('name', 'str'),
        ('count', 'int'),
        ('pop', 'float'),
        ('is_it', 'bool'),
]

with open('/Users/Matt/Documents/Flask/app/core/tests/sample_inputs/a.csv') as f:
    reader = UnicodeDictReader(f, fields)
    for row in reader:
        print row

