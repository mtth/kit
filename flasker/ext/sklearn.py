#!/usr/bin/env python

from datetime import datetime
from time import time
from flasker.ext.orm import Model
from flasker.util import JSONEncodedDict
from sklearn.linear_model import LogisticRegression as _LogisticRegression
from sqlalchemy import (Boolean, Column, Float, ForeignKey, Integer, String,
  DateTime)
from sqlalchemy.orm import backref, relationship

class SKErr(Exception):

  pass

class Classifier(object):

  """Adds tracking to classifier methods."""

  def __init__(self, *args, **kwargs):
    if len(args):
      raise SKErr('Only kwargs are accepted')
    super(self.__class__, self).__init__(**kwargs)
    self._param, flag = self.__param_class__.retrieve(**kwargs)

  def fit(self, *args, **kwargs):
    now = time()
    fit = ClassifierFit(param_id = self._param.id)
    super(self.__class__, self).fit(*args, **kwargs)
    fit.duration = time() - now
    return fit

  def predict(self, *args, **kwargs):
    super(self.__class__, self).predict(*args, **kwargs)


class LogisticRegression(_LogisticRegression, Classifier):

  __param_class__ = LogisticRegressionParam


# Models

class ClassifierParam(Model):

  _cache = None
  id = Column(Integer, primary_key=True)
  type = Column(String(32))
  added = Column(DateTime, default=datetime.now)
  penalty = Column(String(32))
  dual = Column(Boolean)
  C = Column(Float)
  fit_intercept = Column(Boolean)
  intercept_scaling = Column(Float)
  class_weight = Column(JSONEncodedDict)
  tol = Column(Float)

  __mapper_args__ = {
    'polymorphic_on': type,
    'polymorphic_identity': 'param'
  }
  

class LogisticRegressionParam(ClassifierParam):

  __tablename__ = None
  __mapper_args__ = {
    'polymorphic_identity': 'logistic_regression_param'
  }

  valid_params = [
    'penalty', 'dual', 'C', 'fit_intercept', 'intercept_scaling',
    'class_weight', 'tol'
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


class ClassifierPredict(Model):

  id = Column(Integer, primary_key=True)
  added = Column(DateTime, default=datetime.now)
  duration = Column(Float)
  fit_id = Column(ForeignKey('classifier_fits.id'))

  fit = relationship(
    'ClassifierFit',
    backref=backref('predicts')
  )


