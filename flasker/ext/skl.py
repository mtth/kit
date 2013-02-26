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

  @property
  def filepath(self):
    return join(SKL().folder_path, 'fit', '%s.joblib.pkl' % self.id)

  def get_fitted_classifier(self):
    return Classifier(joblib.load(self.filepath))


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
  def filepath(self):
    return join(SKL().folder_path, 'test', '%s.pkl' % self.id)

  @property
  def results(self):
    if self._results is None:
      self._results = DataFrame.load(self.filepath)
    return self._results

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

  def is_fitted(self):
    return self.current_fit is not None

  def train(self, Xdf, ys, description=''):
    """Fit then test in sample.

    :param Xdf: features
    :type Xdf: pandas.DataFrame
    :param ys: labels
    :type ys: pandas.Series

    """
    self._fit(Xdf.values, ys.values, description)
    return self.test(Xdf, ys, 'in sample test')

  def test(self, Xdf, ys, description=''):
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

  def set_description(self, description):
    self.param.description = description

  def _fit(self, X, y, description):
    now = time()
    fit = ClassifierFit(param=self.param, description=description)
    self.engine.fit(X, y)
    fit.duration = time() - now
    fit.flush()
    joblib.dump(self.engine, fit.filepath)
    self.current_fit = fit
    

