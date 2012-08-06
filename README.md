Amazon research project
=======================

Overview
--------
*Predicting successful products on [amazon][1] from reviews and specs!*

Each product has a list of features (including price, rating, technical
specifications, etc.) which we use to predict how popular it will be. Namely
we try to predict how customers purchase products when offered a certain
selection of items.

We frame our problem as a log likelihood maximization problem. We have two
algorithms: *EM* and *2S*.

Things to do
------------
*   fix amazton product importer to work with new framework
*   redo lasso curve for em

Setup
-----
### download and activate [gurobi][3]

    $ grbget <gurobikey>

### create [virtualenv][4] with python2.6
and create sym link to gurobi python bindings

    $ virtualenv -p /usr/bin/python2.6 venv
    $ cd <project_home_directory>
    $ cd venv/lib/python2.6/site-packages
    $ ln -s /Library/Python/2.6/site-packages/gurobipy gurobipy

### activate the virtual environment and install a few packages
note that sqlite must be installed as well

    $ cd <project_home_directory>
    $ . venv/bin/activate
    (venv)$ pip install sqlalchemy
    (venv)$ pip install pysqlite
    (venv)$ pip install elixir
    (venv)$ pip install python-dateutil
    (venv)$ pip install numpy
    (venv)$ pip install sphinx

### since the code is installed as a package, we need to add a symlink

    $ cd <project_home_directory>
    $ cd venv/lib/python2.6/site-packages/
    $ ln -s <project_home_directory> amzn

### all set!
just run package scripts in the virtual environment's python interpreter

    (venv)$ python <code_to_run>.py

### to deactivate

    (venv)$ deactivate

Algorithms
----------
See tex document for details.

Data
----
Product informations and reviews were gathered off [amazon][1] and price
history was generously given by Daniel Green of [camelcamelcamel][2].

The data in the coffeemakers and tvs folders is final.

It corresponds to the informations, price history and review history of 70 tvs
and 52 coffeemakers. The data spans over a time horizon ranging from
DATE\_OF\_INTRODUCTION\_OF\_FIRST\_PRODUCT to 03/16/2012.

Each folder is organized as follows:

+ folder/
    - products.txt
        contains general information on all the products (asin, name, seller,
        average rating, total number of reviews)
    + prices/
        contains the history of price changes for each product (one file per)
    + reviews/
        contains the history of reviews for each product (one file per). each
        review consists of a date, rating and comment

[1]: http://www.amazon.com/
[2]: http://camelcamelcamel.com/
[3]: http://www.gurobi.com/
[4]: http://www.virtualenv.org/
