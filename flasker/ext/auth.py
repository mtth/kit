#!/usr/bin/env python

"""Auth Extension."""

from flask import (Blueprint, current_app, flash, request, redirect,
  render_template, url_for)
from flask.ext.login import (current_user, login_user, logout_user,
  LoginManager, UserMixin)
from json import loads
from os.path import abspath, join, dirname
from urllib import urlencode
from urllib2 import Request, urlopen

from ..util import Loggable

class User(Loggable, UserMixin):

  """Base user class."""

  __all__ =  {}

  def __init__(self, email):
    self.id = email

  def __repr__(self):
    return '<User id=%r>' % self.id

  @property
  def __logger__(self):
    return current_app.logger

  def get_id(self):
    """Necessary for Flask login extension."""
    return self.id

  @classmethod
  def get_from_id(cls, id):
    if id in cls.__all__:
      rv = cls.__all__[id]
    else:
      rv = None
    return rv

class Auth(object):

  config = {
    'URL_PREFIX': '/auth',
    'PROTECT_ALL_VIEWS': True,
  }

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      self.config[k.upper()] = v

  def _create_blueprint(self, project):

    return Blueprint(
      'auth',
      project.config['PROJECT']['FLASK_ROOT_FOLDER'] + '.auth',
      template_folder=abspath(join(dirname(__file__), 'templates', 'auth')),
      url_prefix=self.config['URL_PREFIX']
    )

  def _create_login_manager(self):

    login_manager = LoginManager()
    login_manager.login_view = self.config['URL_PREFIX'] + '/sign_in'
    login_manager.login_message = 'Please sign in'

    @login_manager.user_loader
    def load_user(id):
      """Return the user from his email.

      Necessary for flask.login module.
        
      """
      return User.get_from_id(id)

    return login_manager

  def on_register(self, project):
    """Will be called right before the blueprint is registered."""

    self.blueprint = self._create_blueprint(project)
    self.login_manager = self._create_login_manager()

    @project.before_startup
    def handler(project):
      project.flask.register_blueprint(self.blueprint)
      self.login_manager.setup_app(project.flask)

      if self.config['PROTECT_ALL_VIEWS']:

        @project.flask.before_request
        def check_if_logged_in():
          if (request.blueprint != 'auth'
              and request.endpoint # favicon
              and not request.endpoint == 'static' # static files
              and not current_user.is_authenticated()):
            return self.login_manager.unauthorized()
          return None

class GoogleAuth(Auth):

  config = {
    'URL_PREFIX': '/auth',
    'PROTECT_ALL_VIEWS': True,
    'CLIENT_ID': '',
    'AUTHORIZED_EMAILS': None,
    'CALLBACK_URL': '/oauth2callback',
    'ENDPOINTS': {
        'get_token_or_code': "https://accounts.google.com/o/oauth2/auth",
        'validate_token': "https://www.googleapis.com/oauth2/v1/tokeninfo",
        'get_token_from_code': "https://accounts.google.com/o/oauth2/token",
        'get_user_info': "https://www.googleapis.com/oauth2/v2/userinfo",
    },
    'SCOPES': {
        'email': "https://www.googleapis.com/auth/userinfo.email",
        'profile': "https://www.googleapis.com/auth/userinfo.profile"
    },
    'RESPONSE_TYPE': "token",
    'GRANT_TYPE': "authorization_code",
    'ACCESS_TYPE': "offline",
  }

  def on_register(self, project):

    super(GoogleAuth, self).on_register(project)

    emails = self.config['AUTHORIZED_EMAILS']
    if isinstance(emails, list):
      for email in emails:
        User.__all__[email] = User(email)
    elif isinstance(emails, str):
      for email in emails.split(','):
        email = email.strip()
        if email:
          User.__all__[email] = User(email)

    bp = self.blueprint

    @bp.route('/sign_in')
    def sign_in():
      """Sign in view."""
      values = {'sign_in_url': self.login_url}
      return render_template('google_sign_in.html', **values)

    @bp.route('/sign_out')
    def sign_out():
      """Sign out."""
      if current_user.is_authenticated():
        current_user.info('Signed out.')
        logout_user()
        flash('Goodbye')
      return redirect(url_for('.sign_in'))


    @bp.route(self.config['CALLBACK_URL'])
    def oauth2callback():
      """Handles OAuth2 callback.

      Callbacks from the Google API first arrive here. However, since the token
      information is stored after the hash in the URL, Flask can't process it
      directly. Therefore this page renders a page with only JavaScript which
      then catches the token information and redirects to ``catch_token``.

      """
      values = {'catch_token_url': url_for('.catch_token')}
      return render_template('get_token_from_hash.html', **values)

    @bp.route('/catch_token')
    def catch_token():
      """Catches the token and signs in the user if it passes validation.

      If the user got to the sign in page from an non anonymous authorized page
      he will be directly redirected there after sign in. Otherwise he will be
      redirected to the home page.

      """
      token = request.args['access_token']
      if not self.validate_token(token):
        flash('Invalid token')
        return redirect(url_for('.sign_in'))
      user_infos = self.get_user_info_from_token(token)
      user = User.get_from_id(user_infos['email'])
      if user:
        login_user(user)
        user.info('Signed in.')
        return redirect(request.args['state'])
      else:
        current_app.logger.warn('%s tried to sign in.' % user_infos['email'])
        flash('Unauthorized')
        return redirect(url_for('.sign_in'))

  @property
  def login_url(self):
    """Combines the endpoint with the parameters to generate the API url."""
    return self.config['ENDPOINTS']['get_token_or_code'] + '?' + urlencode(self.get_params())
    
  def get_params(self):
    """Builds the dictionary of parameters required the API request."""
    return {
      'scope': self.config['SCOPES']['email'],
      'redirect_uri': request.url_root[:-1] + self.blueprint.url_prefix + self.config['CALLBACK_URL'],
      'response_type': self.config['RESPONSE_TYPE'],
      'state': request.args['next'] if 'next' in request.args else '/',
      'client_id': self.config['CLIENT_ID']
    }

  def validate_token(self, token):
    """Checks if the token is valid."""
    url = self.config['ENDPOINTS']['validate_token'] + '?access_token=' + token
    req = Request(url)
    token_info = loads(urlopen(req).read())
    return False if 'error' in token_info else True

  def get_user_info_from_token(self, token):
    """Grabs user email from token. """
    url = self.config['ENDPOINTS']['get_user_info']
    headers = {'Authorization': 'Bearer ' + token}
    req = Request(url, headers=headers)
    res = loads(urlopen(req).read())
    return res

