#!/usr/bin/env python

from datetime import datetime
from time import time
from flasker.ext.orm import Model
from flasker.util import JSONEncodedDict
from os.path import join
from pandas import DataFrame, Series
from sklearn.externals import joblib
from sqlalchemy import (Boolean, Column, Float, ForeignKey, Integer, String,
  DateTime, Numeric, Text)
from sqlalchemy.orm import backref, relationship
from sys import modules

class SKLErr(Exception):

  pass


class SKL(object):

  __state = {}
  __registered = False

  config = {
    'FOLDER': 'skl'
  }

  def __init__(self):
    if not self.__registered:
      self.__dict__ = self.__state
      self.__registered = True

  def on_register(self, project):
    self.folder_path = join(project.root_dir, self.config['FOLDER'])


# Models

class ClassifierParam(Model):

  _cache = None
  id = Column(Integer, primary_key=True)
  type = Column(String(64))
  description = Column(Text)
  added = Column(DateTime, default=datetime.now)
  penalty = Column(String(32))
  dual = Column(Boolean)
  C = Column(Numeric(precision=64, scale=30))
  fit_intercept = Column(Boolean)
  intercept_scaling = Column(Numeric(precision=64, scale=30))
  random_state = Column(Boolean)
  class_weight = Column(JSONEncodedDict)
  tol = Column(Numeric(precision=64, scale=30))

  __mapper_args__ = {
    'polymorphic_on': type,
    'polymorphic_identity': 'param'
  }

  __valid = []

  def get_classifier(self):
    module, cls = self.type.rsplit('.', 1)
    __import__(module)
    engine_factory = getattr(modules[module], cls)
    return Classifier(engine_factory, **self.get_valid_params())

  def get_valid_params(self):
    return {k: v for k, v in self.jsonify().items() if k in self.__valid}


class LogisticRegressionParam(ClassifierParam):

  __tablename__ = None
  __mapper_args__ = {
    'polymorphic_identity': 'sklearn.linear_model.logistic.LogisticRegression'
  }

  __valid = [
    'penalty', 'dual', 'C', 'fit_intercept', 'intercept_scaling',
    'class_weight', 'tol', 'random_state'
  ]


class ClassifierFit(Model):

  _cache = None
  id = Column(Integer, primary_key=True)
  description = Column(Text)
  added = Column(DateTime, default=datetime.now)
  duration = Column(Float)
  param_id = Column(ForeignKey('classifier_params.id'))

  param = relationship(
    'ClassifierParam',
    backref=backref('fits')
  )

  def __str__(self):
    return 'Fit [P#%s, F#%s] %s' % (self.param.id, self.id, self.description)

  @property
  def filepath(self):
    return join(SKL().folder_path, 'fit', '%s.joblib.pkl' % self.id)

  def get_fitted_engine(self):
    return joblib.load(self.filepath)

  def get_fitted_classifier(self):
    clf = Classifier(self.get_fitted_engine())
    clf.current_fit = self
    return clf


class ClassifierTest(Model):

  _cache = None
  id = Column(Integer, primary_key=True)
  fit_id = Column(ForeignKey('classifier_fits.id'))
  description = Column(Text)
  added = Column(DateTime, default=datetime.now)
  duration = Column(Float)
  _results = None

  fit = relationship(
    'ClassifierFit',
    backref=backref('tests')
  )

  def __str__(self):
    return 'Test [P#%s, F#%s, T#%s] %s' % (
      self.fit.param.id, self.fit.id, self.id, self.description
    )

  @property
  def filepath(self):
    return join(SKL().folder_path, 'test', '%s.pkl' % self.id)

  @property
  def results(self):
    if self._results is None:
      self._results = DataFrame.load(self.filepath)
    return self._results

  @property
  def counts(self):
    counts = self.results.groupby('truth')['prediction'].value_counts()
    def _get_or_zero(series, key):
      try:
        return int(series.get_value(key))
      except KeyError:
        return 0.0
    return {
      'true_pos': _get_or_zero(counts, (1,1)),
      'true_neg': _get_or_zero(counts, (0,0)),
      'false_pos': _get_or_zero(counts, (0,1)),
      'false_neg': _get_or_zero(counts, (1,0)),
    }

  @property
  def scores(self):
    c = self.counts
    return {
      'precision': float(c['true_pos']) / (c['true_pos'] + c['false_pos']),
      'recall': float(c['true_pos']) / (c['true_pos'] + c['false_neg']),
      'fpr': float(c['false_pos']) / (c['false_pos'] + c['true_neg']),
    }

  def save(self):
    self._results.save(self.filepath)


# Classifiers

class Classifier(object):

  """Adds tracking to classifier methods."""

  def __init__(self, engine, **kwargs):
    if callable(engine): # this is a factory
      self.engine = engine(**kwargs)
    else:
      self.engine = engine
    self.param, self.flag = ClassifierParam.retrieve(
      type='%s.%s' % (
        self.engine.__module__,
        self.engine.__class__.__name__
      ),
      **self.engine.get_params()
    )
    if self.flag:
      self.param.flush()
    self.current_fit = None

  def __repr__(self):
    if self.is_fitted():
      return '<Fitted %r>' % self.engine
    else:
      return '<Unfitted %r>' % self.engine

  def set_description(self, description):
    self.param.description = description

  def is_fitted(self):
    return self.current_fit is not None

  def get_fits(self):
    return self.param.fits

  def set_fit(self, fit):
    self.engine = fit.get_fitted_engine()
    self.current_fit = fit

  def get_tests(self, fit=None):
    if fit is None:
      fit = self.current_fit
    return fit.tests

  def train(self, Xdf, ys, description, test_in_sample=True):
    """Fit then test in sample.

    :param Xdf: features
    :type Xdf: pandas.DataFrame
    :param ys: labels
    :type ys: pandas.Series

    """
    self._fit(Xdf.values, ys.values, description)
    if test_in_sample:
      self.test(Xdf, ys, 'in sample test')

  def test(self, Xdf, ys, description):
    """Test.

    :param Xdf:
    :type Xdf: pandas.DataFrame
    :param ys: optional truth
    :type ys: pandas.Series

    """
    if not self.is_fitted():
      raise SKLError('Classifier must be trained before testing.')
    now = time()
    test = ClassifierTest(fit=self.current_fit, description=description)
    prediction = self.engine.predict(Xdf.values)
    test.duration = time() - now
    test._results = DataFrame({'truth': ys, 'prediction': prediction})
    test.flush()
    test.save()
    return test

  def _fit(self, X, y, description):
    now = time()
    fit = ClassifierFit(param=self.param, description=description)
    self.engine.fit(X, y)
    fit.duration = time() - now
    fit.flush()
    joblib.dump(self.engine, fit.filepath)
    self.current_fit = fit
    

