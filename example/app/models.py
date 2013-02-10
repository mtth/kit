#!/usr/bin/env python

from flasker import Model
from sqlalchemy import Column, Integer, ForeignKey, String

# some sample models

class House(Model):

  id = Column(Integer, primary_key=True)
  address = Column(Unicode(128))


class Cat(Model):

  name = Column(String(64), primary_key=True)
  house_id = Column(ForeignKey('houses.id'))
  house = relationship('House', backref='cats')

