'Anxiety Free Web server.'
import functools
import os
import traceback

import flasgger
import flask
import flask_cors

import api_spec
import conversation
import logs

logs.setup()

LOGGER = logs.logging.getLogger('anx.web')
APP = flask.Flask('anx')
APP.config['SECRET_KEY'] = os.environ.get('ANX_SESSIONS_KEY', os.urandom(24))
APP.config['SWAGGER'] = api_spec.CONFIG
flasgger.Swagger(APP)
flask_cors.CORS(APP, resources={'*': {'origins': '*'}})
DEBUG = bool(os.environ.get('ANX_DEBUG', False))
SESSION = conversation.Session()


class ArgumentMismatch(Exception):
    'Wrong arguments supplied to call.'


class Unauthorized(Exception):
    'An unauthorized request.'


def make_response(status=None, error_name=None, error_message=None, **kwargs):
    'Make a dict for a basic server response.'
    if error_name is not None:
        if isinstance(error_name, Exception):
            kwargs['error_name'] = type(error_name).__name__
            kwargs['error_message'] = str(error_name)
        else:
            kwargs['error_name'] = error_name
    if error_message is not None:
        kwargs['error_message'] = error_message
    kwargs['status'] = status or 200
    return flask.jsonify(dict(kwargs)), kwargs['status']


def check_arguments(required_arguments, given_arguments):
    'Raise exception if request arguments do not match requirements.'
    if required_arguments is None:
        required_arguments = set()
    elif not isinstance(required_arguments, set):
        required_arguments = set(required_arguments)
    if not isinstance(given_arguments, set):
        given_arguments = set(given_arguments)
    missing_arguments = required_arguments - given_arguments
    if missing_arguments:
        raise ArgumentMismatch(f"request does not contain arguments(s): {', '.join(missing_arguments)}")


def parse_argument(key, value):
    'Parse a single argument in a request.'
    if key == 'answer':
        if not isinstance(value, str):
            LOGGER.warning(f"argument {key} is {type(value).__name__} and not string, will convert")
            return str(value)
    return value


def parse_request(request, required_arguments):
    'Validate and parse a request.'
    given_arguments = request.values.to_dict()
    check_arguments(required_arguments, given_arguments.keys())
    return {key: parse_argument(key, value) for key, value in given_arguments.items()}


def optional_arg_decorator(decorator):
    'A decorator for decorators than can accept optional arguments.'
    @functools.wraps(decorator)
    def wrapped_decorator(*args, **kwargs):
        'A wrapper to return a filled up function in case arguments are given.'
        if len(args) == 1 and not kwargs and callable(args[0]):
            return decorator(args[0])
        return lambda decoratee: decorator(decoratee, *args, **kwargs)
    return wrapped_decorator


@optional_arg_decorator
# Since this is a decorator the handler argument will never be None, it is
# defined as such only to comply with python's syntactic sugar.
def call(handler=None, required_arguments=None):
    'A decorator for API calls.'
    @functools.wraps(handler)
    def _call(*_, **__):
        request = None
        # If anything fails, we want to catch it here.
        # pylint: disable=broad-except
        try:
            request = parse_request(flask.request, required_arguments)
            response = handler(**request)
        except conversation.InvalidFlow as invalid_flow:
            response = dict(status=400, error_name=invalid_flow)
        except Unauthorized as unauthorized_exception:
            response = dict(status=403, error_name=unauthorized_exception)
        except Exception as exception:
            LOGGER.exception(f"unexpected server exception on {flask.request.url}: {request}")
            response = dict(status=500, error_name=exception)
            if DEBUG:
                response['stacktrace'] = traceback.format_exc().split('\n')
        # pylint: enable=broad-except
        try:
            return make_response(**(response))
        except TypeError:
            error = f"handler {handler.__name__} returned an unparsable response"
            LOGGER.exception(f"{error}\n{response}")
            return make_response(500, 'InternalError', error)
    return _call


@APP.route("/update", methods=['GET'])
@flasgger.swag_from(api_spec.UPDATE)
@call
def update_handler():
    'Update bot lines and flows.'
    conversation.update_lines()
    return dict(status=201, message='bot lines and flows updated')


@APP.route("/next", methods=['POST'])
@flasgger.swag_from(api_spec.NEXT)
@call
def next_handler(answer=None):
    'Get the next interaction.'
    return dict(status=200, response=SESSION.next(answer))


@APP.route("/five_hundred", methods=['POST'])
@call(['reason'])
def five_hundred_handler(reason):
    'Test our 500 reporting - only for testing, but also available in production.'
    if reason == 'response':
        return None
    raise Exception('five hundred response was requested')


@APP.route('/')
@APP.route('/<path:path>', methods=['GET', 'POST'])
def catch_all_handler(path='index.html'):
    'All undefined endpoints try to serve from the static directories.'
    for directory in ['static']:
        if os.path.isfile(os.path.join(directory, path)):
            return flask.send_from_directory(directory, path)
    return flask.jsonify(make_response(403, Unauthorized(f"Forbidden path: {path}"))), 403
