# manage.py
import eventlet
eventlet.monkey_patch()

import os
import unittest
import coverage

from flask import request
from flask_script import Manager, Server
from flask_migrate import Migrate, MigrateCommand

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


COV = coverage.coverage(
    branch=True,
    include='project/*',
    omit=[
        'project/tests/*',
        'project/server/config.py',
        'project/server/*/__init__.py'
    ]
)
COV.start()

from project.server import app, db, models

migrate = Migrate(app, db)
manager = Manager(app)

# migrations
manager.add_command('db', MigrateCommand)

@manager.command
def test():
    """Runs the unit tests without test coverage."""
    tests = unittest.TestLoader().discover('project/tests', pattern='test*.py')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        return 0
    return 1


@manager.command
def cov():
    """Runs the unit tests with coverage."""
    tests = unittest.TestLoader().discover('project/tests')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        COV.stop()
        COV.save()
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        COV.erase()
        return 0
    return 1


@manager.command
def create_db():
    """Creates the db tables."""
    db.create_all()

@manager.command
def drop_db():
    """Drops the db tables."""
    try:
        db.drop_all()
        pass
    except Exception as e:
        raise e

if __name__ == '__main__':
    logger.info('Running create_db command')
    create_db()
    logger.info('Initialize Application')
    import eventlet.wsgi
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)