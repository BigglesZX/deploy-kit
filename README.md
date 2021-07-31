# deploy-kit

Canonical versions of my config files for deploying (typically) Django projects on (typically) Ubuntu servers.

## Fabric

Fabric is used to run predefined sets of commands in the local and remote environment.

It requires a Python 3 environment on the local side, and the `Fabric3` package must be installed:

```shell
$ pip install Fabric3
```

For legacy reasons we're using the python 2.7-compatible fork `Fabric3` rather than `Fabric` for now; this requirement will probably be removed soon.

Copy `fabfile.py` and replace the values of `PROJECT_NAME`, `USER_NAME` and `HOST_NAME`.

Example initial deployment:

```shell
$ fab live bootstrap deploy:master start:gunicorn restart:nginx
```

Example routine deployment:

```shell
$ fab live deploy:master migrate restart:gunicorn restart:nginx
```

Other commands:

```shell
$ fab live destroy              # remove the environment (careful now!)
$ fab live configtext           # run nginx configtest
$ fab live django_admin:foobar  # run `django-admin foobar`
```

## Gunicorn

Gunicorn runs the Python application and is configured using `systemd`.

Copy `gunicorn.conf.py`, `gunicorn.service` and `gunicorn.socket` and replace the values of `PROJECT_NAME`, `USER_NAME` and `ENVIRONMENT_NAME`.

Note that `PROJECT_NAME` is used in the path of the Python application module (`PROJECT_NAME.wsgi:application`) and the environment config path (`--config PROJECT_NAME/config/ENVIRONMENT_NAME/gunicorn.conf.py`), which may need adjusting if the project name and top-level module name are not the same.

The gunicorn config file (`gunicorn.conf.py`) sets the number of workers at `2`; you may wish to change this for larger projects.

## Logrotate

The Ubuntu logrotate service is used for.. log rotation.

Copy `logrotate.conf` and replace the values of `PROJECT_NAME`, `USER_NAME` and `ENVIRONMENT_NAME`.

## Nginx

Nginx fronts the Python application, static files and various other bits.

Copy `nginx.conf` and replace the values of `PROJECT_NAME`, `USER_NAME` and `ENVIRONMENT_NAME`. Also replace `[www.]example.com` with your real domain names.

## Let's Encrypt certificate generation

On the remote server (replacing `PROJECT_NAME`, `USER_NAME` and `ENVIRONMENT_NAME`):

```shell
$ sudo certbot certonly --webroot --webroot-path=/home/USER_NAME/sites/PROJECT_NAME/ENVIRONMENT_NAME/lets-encrypt-validation -d example.com -d www.example.com
```

## Plausible markup fragment that matches this Nginx config

```html
<script defer data-domain="example.com" data-api="/p/api/event" src="/p/js/script.js"></script>
```
