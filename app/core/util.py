#!/usr/bin/env python

"""Flask App Template helpers"""

import logging
logger = logging.getLogger(__name__)

# General imports

from collections import defaultdict
from csv import DictReader
from datetime import datetime
from functools import partial, wraps
from sqlalchemy.orm.attributes import InstrumentedAttribute

# Helpers
# =======

def convert(value, return_type):
    """Converts a string to another builtin type."""
    if return_type == 'int':
        return int(value)
    elif return_type == 'float':
        return float(value)
    elif return_type == 'bool':
        if value.lower() == 'true' or value == '1':
            return True
        elif not value or value.lower() == 'false' or value == '0':
            return False
        else:
            raise Exception('Can\'t convert %s to boolean.' % value)
    elif return_type == 'unicode':
        return unicode(value, encoding='utf-8', errors='replace')
    else:
        return value

def exponential_smoothing(data, alpha=0.5):
    """Helper function for smoothing data.

    :param data: list of tuples. The smoothing will be done on
        the first item of each tuple.
    :type data: ``list``
    :param alpha: the discount factor
    :type alpha: ``float``
    :rtype: ``list``
    
    """
    sorted_data = sorted(data, key=lambda e: e[0])
    return [(x, sum(_y * alpha ** (x - _x) for (_x, _y) in sorted_data[:i+1])
                / sum(alpha ** (x - _x) for (_x, _y) in sorted_data[:i+1]))
            for i, (x, y) in enumerate(sorted_data)]

def histogram(
        data,
        key=lambda a: a,
        bins=50,
        restrict=None,
        categories=None,
        sorted=0,
        expand=False
):
    """Returns a histogram of counts for the data.

        :param restrict: if provided, only data elements which return `True`
            will be included in the histogram. Default is `None` (all elements
            are included).
        :type restrict: function or None
        :param categories: if provided, elements will be counted in separate
            categories. This changes the format of the output to a dictionary
            with the different categories as keys in each bin.
        :type categories: function or None
        :param bins: either an int (total number of bins, which will be 
            uniformly spread) or a list of increasing bin values. smaller
            values will be in the first bin, larger in the last one.
        :type bins: int or list(int)
        :param sorted: 0 if data isn't sorted, 1 if sorted in ascending, -1 if
            sorted in descending order.
        :type sorted: string

    Possible extension: allow categories to return a list of keys, which would
    allow elements to be included in several counts.

    """
    if isinstance(bins, int):
        n_bins = bins
        if not n_bins > 0: raise Exception("Number of bins must be > 0.")
        if sorted == '1':
            max_value = key(data[-1])
            min_value = key(data[0])
        elif sorted == '-1':
            max_value = key(data[0])
            min_value = key(data[-1])
        else:
            max_value = max(key(e) for e in data)
            min_value = min(key(e) for e in data)
        if n_bins == 1 or max_value == min_value:
            # If everything is equal, or just one bin, return one bin. Duh.
            return {min_value: len(data)}
        else:
            bin_width = float(max_value - min_value) / n_bins
            bins = [min_value + float(i) * bin_width for i in xrange(n_bins)]
            def find_bin(e):
                # this is faster than default iterating over bins
                index = min(int((key(e) - min_value) / bin_width), n_bins - 1)
                return bins[index]
    else:
        if len(bins) == 1:
            # not very interesting but for compatibility
            return {bins[0]: len(data)}
        def find_bin(a):
            # default bin iterator
            if a < bins[0]:
                return bins[0]
            for bin in reversed(bins):
                if a >= bin:
                    return bin
    if categories is None:
        data_histogram = dict.fromkeys(bins, 0)
        for e in data:
            if restrict is None or restrict(e):
                data_histogram[find_bin(key(e))] += 1
        return data_histogram
    else:
        data_histogram = defaultdict(lambda: defaultdict(int))
        for e in data:
            if restrict is None or restrict(e):
                data_histogram[find_bin(key(e))][categories(e)] += 1
        data_histogram = dict((k, dict(v)) for (k, v) in data_histogram.iteritems())
        if expand:
            keys = set(key for v in data_histogram.values() for key in v.keys())
            data_histogram = dict(
                    (key, dict((k, v.get(key, 0)) for (k, v) in data_histogram.iteritems()))
                    for key in keys
            )
        return data_histogram

# Classes
# -------

class UnicodeDictReader(object):

    """Helper for importing .csv files.

    :param csvfile: open file instance
    :type csvfile: ``file``
    :param fields: sequence of tuples (fieldname, fieldtype)
    :rtype: generator

    Some csv files have unicode data which raises errors. This helper function
    automatically replaces non-ascii characters.

    """

    def __init__(self, csvfile, fields, **kwargs):
        kwargs['fieldnames'] = [field[0] for field in fields]
        fieldtypes = dict(fields)
        fieldtypes['extra'] = 'list'
        reader = DictReader(
                csvfile,
                delimiter='\t',
                quotechar='\x07',   # Hack for silly chars
                **kwargs
        )
        for row in reader:
            try:
                processed_row = dict(
                        (key, convert(value, fieldtypes[key]))
                        for key, value in row.iteritems()
                        if fieldtypes[key]
                )
            except Exception as e:
                print 'The misbehaving row: %s' % row
                raise e
            yield processed_row

class Jsonifiable(object):

    """For easy API calls."""

    def jsonify(self, simple=False):
        """Returns all keys and properties of an instance in a dictionary.

        :param simple: turn off the automatic transformation of the result
            to a `Dict`
        :type simple: bool
        :rtype: Dict or dict

        """
        try:
            d = dict(self)
        except:
            d = {}
        cls = self.__class__
        varnames = [
                e for e in dir(cls)
                if not e.startswith('_')    # don't show private properties
                if not e == 'metadata'      # for when used with models
        ]
        for varname in varnames:
            cls_value = getattr(cls, varname)
            if isinstance(cls_value, (property, InstrumentedAttribute)):
                value = getattr(self, varname)
                if isinstance(value, (dict, float, int, long, str)):
                    d[varname] = getattr(self, varname)
                elif isinstance(value, datetime):
                    d[varname] = str(getattr(self, str(varname)))
                elif not value:
                    d[varname] = None
                else:
                    # for debugging mostly
                    d[varname] = str(type(value))
        return d if simple else Dict(d)

class Loggable(object):

    """To easily log stuff.

    To be able to trace back the instance logged to where it is defined,
    it is recommended to reassign the logger property in the children
    classes.

    """

    logger = logger

    def _logger(self, message, loglevel):
        action = getattr(self.logger, loglevel)
        return action('%s :: %s' % (self, message))

    def __getattr__(self, varname):
        if varname in ['debug', 'info', 'warn', 'error']:
            return partial(self._logger, loglevel=varname)
        else:
            raise AttributeError

class RunningStatistic(object):

    """ To compute running statistics efficiently."""

    def __init__(self):
        self.count = 0
        self.mean = float(0)
        self.unweighted_variance = float(0)

    def push(self, n):
        if n == None:
            return
        self.count += 1
        if self.count == 1:
            self.mean = float(n)
            self.unweighted_variance = float(0)
        else:
            mean = self.mean
            s = self.unweighted_variance
            self.mean = mean + (n - mean) / self.count
            self.unweighted_variance = s + (n - self.mean) * (n - mean)

    def variance(self):
            if self.count>1:
                return self.unweighted_variance/(self.count-1)
            return 0

class Dict(dict):

    """Dictionary class with a few helper methods.

    The goal of this class is to make multilevel dictionary actions
    simple.

    Usage::

        d = Dict(d)
        d.flattened()

    :param cname: key used when unflattening a dictionary and a key with a
        value also becomes a branch
    :type cname: string
    :param sep: the separator used to separate hierarchy levels
    :type sep: string

    """

    cname = 'all'
    sep = '_'

    def depth(self):
        """Depth of a dictionary."""
        values = [
                Dict(value)
                for value in self.itervalues()
                if isinstance(value, dict)
        ]
        return max(value.depth() for value in values) + 1 if values else 1

    def width(self):
        """Width of a dictionary."""
        values = [
                Dict(value)
                for value in self.itervalues()
                if isinstance(value, dict)
        ]
        return sum(value.width() for value in values) + len(self) - len(values)

    def table(self, mode='horizontal', left_columns=None):
        """For HTML headers mostly."""
        items = []
        unflattened = Dict(self.unflattened())
        depth = unflattened.depth()
        width = unflattened.width()
        if mode == 'horizontal':
            levels = defaultdict(list)
            for key in sorted(self.flattened().iterkeys()):
                parts = key.split(self.sep)
                for index, part in enumerate(parts[:-1]):
                    levels[index].append([part, 1, 1, self.sep.join(parts[:(index + 1)])])
                levels[len(parts) - 1].append([parts[-1], depth - len(parts) + 1, 1, key])
            for index, level in levels.items():
                if index == 0 and left_columns:
                    row = [[column, depth, 1, column] for column in left_columns]
                else:
                    row = []
                current_label = None
                for label, height, width, full_label in level:
                    if label == current_label:
                        row[-1][2] += 1
                    else:
                        current_label = label
                        row.append([label, height, width, full_label])
                items.append(row)
        elif mode == 'vertical':
            indices = {}
            for i, key in enumerate(sorted(self.flattened().iterkeys())):
                if i == 0 and left_columns:
                    row = [[column, width, 1, column] for column in left_columns]
                else:
                    row = []
                parts = key.split(self.sep)
                k = 0
                for j, part in enumerate(parts[:-1]):
                    full_label = self.sep.join(parts[:(j + 1)])
                    if not full_label in indices:
                        indices[full_label] = (i, k)
                        row.append([part, 1, 1, full_label])
                        k += 1
                    else:
                        a, b = indices[full_label]
                        items[a][b][1] += 1
                indices[key] = (i, k)
                row.append([parts[-1], 1, depth - len(parts) + 1, key])
                items.append(row)
        return items

    def flattened(self):
        """Flattened representation of the dictionary."""
        return self.__class__.flatten(self)

    def unflattened(self):
        """Unflattened representation of the dictionary."""
        return self.__class__.unflatten(self)

    @classmethod
    def flatten(cls, dic, sep=None, prefix=''):
        """Flatten. Classmethod for convenience."""
        sep = sep if sep else cls.sep
        items = []
        for key, value in dic.iteritems():
            k = prefix + sep + key if prefix else key
            if isinstance(value, dict):
                items.extend(cls.flatten(value, sep, k).items())
            else:
                items.append((k, value))
        return dict(items)

    @classmethod
    def unflatten(cls, dic, sep=None, cname=None):
        """Unflatten. Classmethod for convenience"""
        sep = sep if sep else cls.sep
        cname = cname if cname else cls.cname
        result = {}
        keys = []
        for key in dic.iterkeys():
            keys.append(key.split(sep))
        keys.sort(key=len, reverse=True)
        for key in keys:
            d = result
            for part in key[:-1]:
                if part not in d:
                    d[part] = {}
                d = d[part]
            if key[-1] in d:
                d[key[-1]][cname] = dic[sep.join(key)]
            else:
                d[key[-1]] = dic[sep.join(key)]
        return result

# In progress
# -----------

# def pagify(func):
#     """Adds pagination to views."""
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         if 'p' in request.args:
#             page = max(0, int(request.args['p']) - 1)
#         else:
#             page = 0
#         return func(*args, page=page, **kwargs)
#     return wrapper
