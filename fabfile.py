# version: 2021.1

from __future__ import unicode_literals

import time
import os

from os.path import join
from fabric.api import env, run, prompt, local, sudo
from fabric.context_managers import cd

env.pyversion = '3'
env.project = 'PROJECT_NAME'
env.user = 'USER_NAME'
env.hosts = ['HOST_NAME']
env.root = '/home/%(user)s/sites/%(project)s/%(target)s'
env.bin = '/home/%(user)s/.virtualenvs/%(project)s_%(target)s/bin'
env.settings = '%(project)s.config.%(target)s.settings'
env.branch = 'master'

def symlink(target, linkname):
    ''' Create a symlink on the remote host '''
    sudo('if [ -L %s ]; then rm %s; fi' % (linkname, linkname))
    sudo('ln -s %s %s' % (target, linkname))

def stage():
    ''' Use the stage environment for all commands '''
    env.target = 'stage'
    env.root = env.root % env
    env.bin = env.bin % env
    env.settings = env.settings % env

def live():
    ''' Use the live environment for all commands '''
    env.target = 'live'
    env.root = env.root % env
    env.bin = env.bin % env
    env.settings = env.settings % env

def bootstrap():
    ''' Perform the initial project setup including virtualenv, database etc '''
    run('mkdir -p %s' % env.root)
    with cd(env.root):
        run('git init')
        run('git config receive.denyCurrentBranch ignore')
        run('mkdir -p logs static')
        run('touch logs/{access,error,gunicorn.error,gunicorn.access}.log')
        run('chmod 777 logs/*')

    run('virtualenv --python=python%(pyversion)s /home/%(user)s/.virtualenvs/%(project)s_%(target)s --no-site-packages' % env)
    run('echo "cd %(root)s" > %(bin)s/postactivate' % env)
    run('echo "export DJANGO_SETTINGS_MODULE=%(project)s.config.%(target)s.settings" >> %(bin)s/postactivate' % env)

    run('%(bin)s/pip install --upgrade pip setuptools wheel' % env)

    create = prompt('Create a MySQL database [Y/n]: ')
    if create in ['Y', 'y', '',]:
        mysql_root_user = prompt('Please enter MySQL root username (or hit Enter for \'root\'): ')
        mysql_root_pass = prompt('Please enter MySQL root password (or hit Enter if none): ')
        if not mysql_root_user: mysql_root_user = 'root'

        mysql = "mysql -u {0}".format(mysql_root_user)
        if mysql_root_pass:
            mysql = "mysql -u {0} -p{1}".format(mysql_root_user, mysql_root_pass)

        create_database = prompt('Create database? [Y/n]:')
        if create_database in ['Y', 'y', '']:
            db_name = prompt('Please enter new MySQL database name: ')
            command = mysql + " --execute='CREATE DATABASE IF NOT EXISTS " \
                              "`{0}` /*!40100 DEFAULT CHARACTER SET utf8 COLLATE " \
                              "utf8_unicode_ci */'".format(db_name)
            run(command)

            create_user = prompt('Create user for database {0}? [Y/n]:'.format(db_name))
            if create_user in ['Y', 'y', '']:
                username = prompt('New database user\'s username: ')
                password = prompt('New database user\'s password: ')
                command = mysql + " --execute=\"GRANT ALL PRIVILEGES "\
                                  "ON {0}.* TO {1}@'localhost' IDENTIFIED BY "\
                                  "'{2}'\"".format(db_name, username, password)
                run(command)


def deploy(branch):
    ''' Deploy the latest version of the project, run setup and copy configs '''
    if branch:
        env.branch = branch

    # set up
    env.username = os.environ['USER']
    env.timestamp = str(int(time.time()))

    # deploy
    env.rev = local('git log -1 --format=format:%%H %s' % env.branch, capture=True)
    local('git push -f ssh://%(user)s@%(host)s/%(root)s %(branch)s' % env)
    with cd(env.root):
        run('git reset --hard %(rev)s' % env)
        run('find . -name \'*.pyc\' -delete')
        run('find . -name \'__pycache__\' -type d -prune -exec rm -r {} \;')

    # log it
    env.deploy_log = join(env.root, 'logs', 'deploy.log')
    env.rollback_log = join(env.root, 'logs', 'rollback.log')
    run('echo "`date` - %(username)s - %(rev)s" >> %(deploy_log)s' % env)
    run('echo "%(rev)s" >> %(rollback_log)s' % env)

    # reqs and eggs
    with cd(env.root):
        run('%(bin)s/pip install -r requirements.txt' % env)
        run('%(bin)s/python setup.py develop' % env)

    # collectstatic
    cmd = '%(bin)s/django-admin.py' % env
    run('%s collectstatic --settings=%s --noinput' % (cmd, env.settings))

    # configs
    sudo('cp %(root)s/%(project)s/config/%(target)s/gunicorn.socket /etc/systemd/system/gunicorn_%(project)s_%(target)s.socket' % env)
    sudo('cp %(root)s/%(project)s/config/%(target)s/gunicorn.service /etc/systemd/system/gunicorn_%(project)s_%(target)s.service' % env)
    sudo('cp %(root)s/%(project)s/config/%(target)s/logrotate.conf /etc/logrotate.d/%(project)s_%(target)s' % env)
    symlink('%(root)s/%(project)s/config/%(target)s/nginx.conf' % env,
            '/etc/nginx/sites-available/%(project)s_%(target)s' % env)
    symlink('/etc/nginx/sites-available/%(project)s_%(target)s' % env,
            '/etc/nginx/sites-enabled/%(project)s_%(target)s' % env)
    sudo('systemctl daemon-reload')
    sudo('systemctl enable gunicorn_%(project)s_%(target)s.socket' % env)

def destroy():
    ''' Stop gunicorn service, remove project config files, restart nginx '''
    sudo('systemctl stop gunicorn_%(project)s_%(target)s' % env)
    sudo('systemctl disable gunicorn_%(project)s_%(target)s.socket' % env)
    sudo('rm /etc/systemd/system/gunicorn_%(project)s_%(target)s.socket' % env)
    sudo('rm /etc/systemd/system/gunicorn_%(project)s_%(target)s.service' % env)
    sudo('rm /etc/logrotate.d/%(project)s_%(target)s' % env)
    sudo('rm /etc/nginx/sites-available/%(project)s_%(target)s' % env)
    sudo('rm /etc/nginx/sites-enabled/%(project)s_%(target)s' % env)
    sudo('systemctl daemon-reload')
    sudo('systemctl restart nginx')
    print('Services updated and config files removed. To remove the environment completely, run "rmvirtualenv %(project)s_%(target)s" followed by "rm -rf %(root)s" on the server, and delete the environment database. You will also need to reboot the server before this enviroment can be bootstrapped again, due to residual socket files in /run' % env)

def start(service):
    if service == 'nginx':
        ''' Start the nginx service '''
        sudo('systemctl start nginx')
    elif service == 'gunicorn':
        ''' Start the gunicorn service '''
        sudo('systemctl start gunicorn_%(project)s_%(target)s' % env)
    else:
        print('Unknown service %s' % service)

def stop(service):
    if service == 'nginx':
        ''' Stop the nginx service '''
        sudo('systemctl stop nginx')
    elif service == 'gunicorn':
        ''' Stop the gunicorn service '''
        sudo('systemctl stop gunicorn_%(project)s_%(target)s' % env)
    else:
        print('Unknown service %s' % service)

def restart(service):
    if service == 'nginx':
        ''' Restart the nginx service '''
        sudo('systemctl restart nginx')
    elif service == 'gunicorn':
        ''' Restart the gunicorn service '''
        sudo('systemctl restart gunicorn_%(project)s_%(target)s' % env)
    else:
        print('Unknown service %s' % service)

def configtest():
    ''' Run the nginx configtest '''
    sudo('nginx -t')

def django_admin(arguments):
    ''' Run Django management commands '''
    cmd = '%(bin)s/django-admin.py' % env
    run('%s %s --settings=%s' % (cmd, arguments, env.settings))

def migrate():
    ''' Run Django's `migrate` command '''
    django_admin('migrate')
