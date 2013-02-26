#!/usr/bin/env python

from datetime import datetime
from time import time
from flasker.ext.orm import Model
from flasker.util import JSONEncodedDict
from sqlalchemy import (Boolean, Column, Float, ForeignKey, Integer, String,
  DateTime, Numeric)
from sqlalchemy.orm import backref, relationship
from sys import modules

class SKLErr(Exception):

  pass


class SKL(object):

  config = {
    'FOLDER': 'skl'
  }

  def __init__(self):
    pass

  def on_register(self, project):
    pass


# Models

class ClassifierParam(Model):

  _cache = None
  id = Column(Integer, primary_key=True)
  type = Column(String(64))
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

  id = Column(Integer, primary_key=True)
  added = Column(DateTime, default=datetime.now)
  duration = Column(Float)
  param_id = Column(ForeignKey('classifier_params.id'))

  param = relationship(
    'ClassifierParam',
    backref=backref('fits')
  )

  def get_fitted_classifier(self):
    pass


class ClassifierPredict(Model):

  id = Column(Integer, primary_key=True)
  added = Column(DateTime, default=datetime.now)
  duration = Column(Float)
  fit_id = Column(ForeignKey('classifier_fits.id'))

  fit = relationship(
    'ClassifierFit',
    backref=backref('predicts')
  )


# Classifiers

class Classifier(object):

  """Adds tracking to classifier methods."""

  def __init__(self, engine_factory, **kwargs):
    self.engine = engine_factory(**kwargs)
    self.param, self.flag = ClassifierParam.retrieve(
      type='%s.%s' % (engine_factory.__module__, engine_factory.__name__),
      **self.engine.get_params()
    )
    if self.flag:
      self.param.flush()
    self.current_fit = None

  def fit(self, *args, **kwargs):
    now = time()
    fit = ClassifierFit(param=self.param)
    self.engine.fit(*args, **kwargs)
    fit.duration = time() - now
    fit.flush()
    self.current_fit = fit
    # TODO save fitted classifier

  def predict(self, *args, **kwargs):
    if self.current_fit is None:
      raise SKLError('Classifier must be fit before predicting.')
    now = time()
    predict = ClassifierPredict(fit=self.current_fit)
    prediction = self.engine.predict(*args, **kwargs)
    predict.duration = time() - now
    predict.flush()
    # TODO save prediction results
    return prediction

