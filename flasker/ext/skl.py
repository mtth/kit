#!/usr/bin/env python

"""Thin wrapper around some sklearn algorithms.

Allows for automatic parameter saving and recovery. Saving fitted algorithms
for later reuse (convenient for parallel computing).

Test results are persisted along with a few metrics.

Currently supported:

* ``sklearn.linear_model.logistic.LogisticRegression``

Example usage:

.. code:: python

  >>> clf = Classifier.from_engine(LogisticRegression, C=3)
  >>> fitted_clf = clf.train(X_train, y_train)
  >>> test = fitted_clf.test(X_test, y_test)
  >>> test.precision
  0.9576324

"""

from datetime import datetime
from time import time
from json import loads, dumps
from os import makedirs
from os.path import exists, join
from sklearn.externals import joblib
from sqlalchemy import (Boolean, Column, Float, ForeignKey, Integer, String,
  DateTime, Numeric, Text)
from sys import modules


class SKL(object):

  def __init__(self, project, orm, table_prefix='skl_', folderpath=None,
               param_class=None, engine_class=None):

    self.table_prefix = table_prefix
    self.folderpath = folderpath or table_prefix.rstrip('_')
    self.root_dir = join(project.root_dir, self.folderpath)
    if not exists(self.root_dir): makedirs(self.root_dir)

    Param, Engine = _create_base_models(orm)

    self.Param = type(
      '%sParam' % self.folderpath.capitalize(),
      (Param, param_class or object),
      {
        '__tablename__': '%sparams' % self.table_prefix,
      }
    )

    self.Engine = type(
      '%sEngine' % self.folderpath.capitalize(),
      (Engine, engine_class or object),
      {
        '__tablename__': '%sengines' % self.table_prefix,
        'folderpath': self.folderpath,
        'param_id': Column(ForeignKey('%s.id' % self.Param.__tablename__)),
        'param': orm.relationship(
          self.Param,
          backref=orm.backref('engines', lazy='dynamic')
        )
      }
    )

  def save(self, engine, description, dump_engine=True):
    """Wrap an sklearn algorithm.

    :param engine: sklearn algorithm or algorithm factory
    :type engine: varies
    :rtype: flasker.ext.skl.UnfittedClassifier

    """
    param, flag = self.Param.retrieve(
      type='%s.%s' % (
        engine.__module__,
        engine.__class__.__name__
      ),
      **self.Param._serialize_params(**engine.get_params())
    )
    _engine = self.Engine(
      description=description,
      param=param
    )
    _engine.flush()
    if dump_engine:
      _engine.save(engine)
    return _engine

  def load(self, engine_id=None, param_id=None):
    """Load an unfitted classifier from its parameter id.

    :param param_id: the id of the parameter to use to load the engine
    :type param_id: int
    :rtype: flasker.ext.skl.UnfittedClassifier

    The parameter is persisted in the database and its kwargs are passed to 
    the classifier's constructor.

    """
    if engine_id:
      return self.Engine.q.get(engine_id).load()
    if param_id:
      return self.Param.q.get(param_id).create_engine()


def _create_base_models(orm):

  Model = orm.Model
  backref = orm.backref
  relationship = orm.relationship

  class Param(Model):

    __abstract__ = True

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
    class_weight = Column(Text)
    tol = Column(Numeric(precision=64, scale=30))
    n_estimators = Column(Integer)
    criterion = Column(String(32))
    max_features = Column(String(32))
    max_depth = Column(Integer)
    min_samples_split = Column(Integer)
    min_samples_leaf = Column(Integer)
    min_density = Column(Numeric(precision=64, scale=30))
    bootstrap = Column(Boolean)
    oob_score = Column(Boolean)
    n_jobs = Column(Integer)
    verbose = Column(Boolean)
    compute_importances = Column(Boolean)

    @classmethod
    def _serialize_params(cls, **kwargs):
      if 'class_weight' in kwargs:
        class_weight = kwargs['class_weight']
        if isinstance(class_weight, dict):
          kwargs['class_weight'] = dumps(class_weight)
      if 'max_features' in kwargs:
        kwargs['max_features'] = str(kwargs['max_features'])
      return kwargs

    @classmethod
    def _unserialize_params(cls, **kwargs):
      if 'class_weight' in kwargs and kwargs['class_weight']:
        try:
          kwargs['class_weight'] = {
            int(k): v for k, v in loads(kwargs['class_weight']).items()
          }
        except ValueError:
          pass # it is a simple string (probably 'auto')
      if 'max_features' in kwargs and kwargs['max_features']:
        try:
          kwargs['max_features'] = int(kwargs['max_features'])
        except ValueError:
          pass
      return kwargs

    def create_engine(self):
      """Create new engine."""
      module, cls = self.type.rsplit('.', 1)
      __import__(module)
      engine_factory = getattr(modules[module], cls)
      valid_kwargs = engine_factory._get_param_names()
      kwargs = self._unserialize_params(**self.to_json())
      return engine_factory(
        **{k: v for k, v in kwargs.items() if k in valid_kwargs}
      )


  class Engine(Model):

    __abstract__ = True

    _cache = None
    id = Column(Integer, primary_key=True)
    description = Column(Text)
    added = Column(DateTime, default=datetime.now)
    folderpath = None

    def load(self):
      joblib.load(join(self.folderpath, '%s.joblib.pkl' % self.id))

    def save(self, engine):
      joblib.dump(engine, join(self.folderpath, '%s.joblib.pkl' % self.id))


  return Param, Engine
