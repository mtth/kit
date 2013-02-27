#!/usr/bin/env python

from datetime import datetime
from time import time
from flasker.ext.orm import Model
from flasker.util import JSONEncodedDict
from os.path import join
from pandas import concat, DataFrame, Series
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
    'FOLDER': 'skl',
    'AUTOCOMMIT': True,
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

  valid = []

  def describe(self):
    kwargs = Series({
      k: v for k, v in self.jsonify().items() if k in self.valid_kwargs
    })
    misc = Series({
      'id': self.id,
      'fits': len(self.fits),
      'tests': sum(len(fit.tests) if fit.tests else 0 for fit in self.fits),
      'description': self.description,
      'added': self.added,
    })
    return concat(
      [kwargs, misc],
      keys=['kwargs', 'misc']
    )

  def describe_fits(self):
    return concat(
      [fit.describe() for fit in self.fits],
      keys=range(len(self.fits))
    )

  def describe_tests(self):
    return concat(
      [fit.describe_tests() for fit in self.fits],
      keys=range(len(self.fits))
    )

  def _get_classifier(self):
    module, cls = self.type.rsplit('.', 1)
    __import__(module)
    engine_factory = getattr(modules[module], cls)
    return Classifier(
      engine_factory,
      **{k: v for k, v in self.jsonify().items() if k in self.valid_kwargs}
    )


class LogisticRegressionParam(ClassifierParam):

  __tablename__ = None
  __mapper_args__ = {
    'polymorphic_identity': 'sklearn.linear_model.logistic.LogisticRegression'
  }

  valid_kwargs = [
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

  def describe(self):
    return Series({
      'id': self.id,
      'param_id': self.param.id,
      'tests': len(self.tests),
      'description': self.description,
      'duration': self.duration,
      'added': self.added,
    })

  def describe_tests(self):
    return DataFrame({
      index: t.describe() for index, t in enumerate(self.tests)
    }).T

  @property
  def _filepath(self):
    return join(SKL().folder_path, 'fit', '%s.joblib.pkl' % self.id)

  def _get_fitted_classifier(self):
    engine = joblib.load(self._filepath)
    clf = Classifier(engine)
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

  @property
  def results(self):
    if self._results is None:
      self._results = DataFrame.load(self._filepath)
    return self._results

  @property
  def misc(self):
    return Series({
      'id': self.id,
      'fit_id': self.fit.id,
      'param_id': self.fit.param.id,
      'description': self.description,
      'added': self.added,
      'duration': self.duration,
    })

  @property
  def counts(self):
    counts = self.results.groupby('truth')['prediction'].value_counts()
    def _get_or_zero(series, key):
      try:
        return int(series.get_value(key))
      except KeyError:
        return 0.0
    return Series({
      'true_pos': _get_or_zero(counts, (1,1)),
      'true_neg': _get_or_zero(counts, (0,0)),
      'false_pos': _get_or_zero(counts, (0,1)),
      'false_neg': _get_or_zero(counts, (1,0)),
    })

  @property
  def scores(self):
    c = self.counts
    return Series({
      'precision': float(c['true_pos']) / (c['true_pos'] + c['false_pos']),
      'recall': float(c['true_pos']) / (c['true_pos'] + c['false_neg']),
      'fpr': float(c['false_pos']) / (c['false_pos'] + c['true_neg']),
    })

  def describe(self):
    return concat(
      [self.counts, self.scores, self.misc],
      keys=['counts', 'scores', 'misc']
    )

  @property
  def _filepath(self):
    return join(SKL().folder_path, 'test', '%s.pkl' % self.id)

  def _save(self):
    self._results.save(self._filepath)


# Classifiers

class Classifier(object):

  """Adds tracking to classifier methods."""

  @classmethod
  def get_available_params(cls, engine_factory):
    return {
      p.id: p
      for p in ClassifierParam.q.filter_by(
        type='%s.%s' % (
          engine_factory.__module__,
          engine_factory.__name__
        )
      )
    }

  @classmethod
  def view_available_params(cls, engine_factory):
    """Maybe change index to a + if current param. Should also
    probably return a dataframe to show all the parameters."""
    params = cls.get_available_params(engine_factory).values()
    if params:
      return concat([p.describe() for p in params], axis=1).T
    return None

  @classmethod
  def from_param_id(clf, param_id):
    param = ClassifierParam.q.get(param_id)
    return param._get_classifier()

  @classmethod
  def get_available_fits(clf, engine_factory, param_id=None):
    if param_id:
      params = [ClassifierParam.q.get(param_id)]
    else:
      params = ClassifierParam.q.filter_by(
        type='%s.%s' % (
          engine_factory.__module__,
          engine_factory.__name__
        )
      )
    return {
      fit.id: fit
      for p in params for fit in p.fits
    }

  @classmethod
  def view_available_fits(cls, engine_factory, param_id=None):
    fits = cls.get_available_fits(engine_factory, param_id).values()
    if fits:
      return concat([fit.describe() for fit in fits], axis=1).T
    return None

  @classmethod
  def from_fit_id(clf, fit_id):
    fit = ClassifierFit.q.get(fit_id)
    return fit._get_fitted_classifier()

  def __init__(self, engine, **kwargs):
    if callable(engine): # this is a factory
      self.engine = engine()
    else:
      self.engine = engine
    self.engine.set_params(**kwargs)
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

  def is_fitted(self):
    return self.current_fit is not None

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
    test._save()
    return test

  def _fit(self, X, y, description):
    now = time()
    fit = ClassifierFit(param=self.param, description=description)
    self.engine.fit(X, y)
    fit.duration = time() - now
    fit.flush()
    joblib.dump(self.engine, fit._filepath)
    self.current_fit = fit
    
