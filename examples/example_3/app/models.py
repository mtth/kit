#!/usr/bin/env python

from flasker.database import Base
from sqlalchemy import Column, Integer, String

class Something(Base):

  id = Column(Integer, primary_key=True)
  name = Column(String)

  def __init__(self):
    self.name = 'a name'
