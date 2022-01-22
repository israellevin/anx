'API definitions for flasgger.'

CONFIG = {
    'title': 'Anxiety Free API',
    'uiversion': 2,
    'specs_route': '/',
    'specs': [{
        'endpoint': '/',
        'route': '/apispec.json',
    }],
    'info': {
        'title': 'Anxiety Free API',
        'version': 0,
        'license': {
            'name': 'CC0',
            'url': 'https://creativecommons.org/publicdomain/zero/1.0/legalcode'
        },
        'description': 'An API for the Anxiety Free app.'
    }
}

UPDATE = {
    'description': 'Update bot lines and flows from google sheet.',
    'responses': {
        '201': {'description': 'Bot lines and flows updated'},
        '400': {'description': 'Invalid bot lines detected'}
    }
}

NEXT = {
    'description': 'Get the next step from the bot.',
    'parameters': [
        {
            'name': 'answer', 'description': 'The answer given to the current step',
            'in': 'formData', 'required': False, 'type': 'string'
        }
    ],
    'responses': {
        '200': {'description': 'The next step'}
    }
}
