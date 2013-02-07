#!/usr/bin/env python

"""API blueprint.

Inspired by Flask-restless.

"""

class APIError(HTTPException):

  """Thrown when an API call is invalid.

  The error code will sent as error code for the response.

  """

  def __init__(self, code, message):
    self.code = code
    super(APIError, self).__init__(message)

  def __repr__(self):
    return '<APIError %r: %r>' % (self.code, self.message)


def api_response(default_depth=0, default_limit=20, wrap=True):
  """Decorator for API calls.

  Creates the response around any jsonifiable object. Also times the
  processing time and catches HTTPExceptions.

  If wrap is True, this wraps the result of the wrapped call with extra
  info before jsonifying the query results.

  Else, this sends back the results (jsonified if available) of the returned
  object.

  """
  def _api_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      timer = time()
      processing_times = []
      try:
        result = func(*args, **kwargs)
      except HTTPException as e:
        logger.error(format_exc())
        return jsonify({
          'status': 'error',
          'request': {
            'base_url': request.base_url,
            'method': request.method,
            'values': request.values
          },
          'content': str(e)
        }), e.code
      else:
        params = dict(request.args) # request.args is immutable
        offset = max(0, int(params.pop('offset', [0])[0]))
        limit = max(0, int(params.pop('limit', [default_limit])[0]))
        depth = max(0, int(params.pop('depth', [default_depth])[0]))
        if wrap == True or (
          isinstance(wrap, dict) and wrap[request.method] == True
        ):
          loaded = params.pop('loaded', '')
          if loaded:
            loaded = [int(e) for e in loaded.split(',')]
          else:
            loaded = []
          processing_times.append(('request', time() - timer))
          timer = time()
          if isinstance(result, Query):
            sort = params.pop('sort', '')
            instance = result.column_descriptions[0]['type']
            for k, v in params.items():
              if hasattr(instance, k):
                result = result.filter(getattr(instance, k) == v[0])
            total_matches = result.count()
            processing_times.append(('query', time() - timer))
            timer = time()
            if loaded:
              result = result.filter(~instance.id.in_(loaded))
            if sort:
              if sort[0] == '-':
                result = result.order_by(-getattr(instance, sort[1:]))
              else:
                result = result.order_by(getattr(instance, sort))
            if limit:
              result = result.limit(limit)
            response_content = [
              e.jsonify(depth=depth)
              for e in result.offset(offset)
            ]
          else:
            total_matches = len(result)
            response_content = [
              e.jsonify(depth=depth)
              for e in result[offset:offset + limit]
              if not e.id in loaded
            ]
          processing_times.append(('jsonification', time() - timer))
          return jsonify({
            'status': 'success',
            'processing_time': processing_times,
            'matches': {
              'total': total_matches,
              'returned': len(response_content)
            },
            'request': {
              'base_url': request.base_url,
              'method': request.method,
              'values': request.values
            },
            'content': response_content
          }), 200
        else:
          if hasattr(result, 'jsonify'):
            return jsonify(result.jsonify(depth=depth)), 200
          elif isinstance(result, dict):
            return jsonify(result), 200
          else:
            return jsonify({'result': result}), 200
    return wrapper
  return _api_response

