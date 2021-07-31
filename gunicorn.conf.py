# version: 2021.1

bind = 'unix:/run/gunicorn_PROJECT_NAME_ENVIRONMENT_NAME.sock'
name = 'PROJECT_NAME_ENVIRONMENT_NAME'
accesslog = 'logs/gunicorn.access.log'
errorlog = 'logs/gunicorn.error.log'
workers = 2
preload = True
debug = False
