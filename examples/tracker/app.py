#!/usr/bin/env python

"""Basic kit example.

This example implements a very simple page view tracker.

It comprises of a single Flask view and SQLAlchemy table to store the visits
to our view.

"""

from datetime import datetime
from kit import Flask, get_sessions
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

app = Flask(__name__)
session = get_sessions()[0]

# SQLAlchemy
# ==========
# 
# First, we use SQLAlchemy declarative to create the table where we will
# keep track of the visits. This is very similar to what you can find in
# the tutorial (http://docs.sqlalchemy.org/en/rel_0_8/orm/tutorial.html).

Base = declarative_base()

class Visit(Base):

  """Simple model to track visits.

  Each visit contains an ``id`` and the date it was added to the database.
  
  """

  __tablename__ = 'visits'

  id = Column(Integer, primary_key=True)
  date = Column(DateTime, default=datetime.now)

Base.metadata.create_all(session.get_bind())

# Flask
# =====
#
# We are now ready to create our Flask view!
# For more information on creating views and routing, refer to the excellent
# Flask online documentation (http://flask.pocoo.org/docs/tutorial/).

@app.route('/')
def index():
  """This view returns the number of times it has been visited.

  Note that since the option `commit_on_teardown` is set to ``True`` in our
  configuration file, we don't need to commit our changes manually, it is
  done automatically after the request ends.
  
  """
  visit = Visit()                           # we create a new visit
  session.add(visit)                    # we add it to our session
  count = session.query(Visit).count()  # the total number of visits
  return 'This page has been visited %s times now!' % (count, )
