'Tests for Anxiety Free server.'
import os.path

# pylint: disable=unused-import
import pytest
# pylint: enable=unused-import

import db
import conversation
import logs
import web

LOGGER = logs.logging.getLogger('anx.test')


def initialize_test_database():
    'Initialize the database for testing.'
    assert db.DB_NAME[-5:] == '_test', f"will not run accounting tests on non test database {db.DB_NAME}"
    db.nuke_database_and_create_new_please_think_twice()
    conversation.update_lines()


def test_webserver_flow():
    'To test the full flow we run a production webserver.'
    initialize_test_database()
    web.DEBUG = False
    with web.APP.test_client() as client:
        prices_repsonse = client.post('/next')
        assert prices_repsonse.status == '200 OK'


def test_webserver_errors():
    'Test errors from the webserver.'
    initialize_test_database()
    web.DEBUG = False
    with web.APP.test_client() as client:
        for reason in ['response', 'exception']:
            error_response = client.post('/five_hundred', data=dict(reason=reason))
            assert error_response.status == '500 INTERNAL SERVER ERROR'


def test_webserver_debug():
    'Test an almost full flow in debug mode.'
    initialize_test_database()
    web.DEBUG = True
    with web.APP.test_client() as client:
        prices_repsonse = client.post('/next')
        assert prices_repsonse.status == '200 OK'


def test_database(monkeypatch, tmp_path):
    'Test database access.'
    initialize_test_database()
    with db.sql_connection() as sql:
        sql.execute('SELECT 1 FROM bot_lines')

    with pytest.raises(db.pymysql.MySQLError):
        with db.sql_connection() as sql:
            sql.execute('bad sql')

    # Try bad migrations.
    monkeypatch.setattr(db, 'MIGRATIONS_DIRECTORY', tmp_path)
    for migration, migration_file_name in (
        ('Bad SQL;', '0.bad.sql'),
        ('# No apply function.', '0.bad.py'),
        ('Bad python', '0.bad.py')
    ):
        with open(os.path.join(tmp_path, migration_file_name), 'w', encoding='utf-8') as migration_file:
            migration_file.write(migration)
        # It's okay, really.
        # pylint: disable=cell-var-from-loop
        monkeypatch.setattr(db.os, 'listdir', lambda *args, **kwargs: [migration_file_name])
        # pylint: enable=cell-var-from-loop
        with pytest.raises(db.FailedMigration):
            initialize_test_database()
    # monkeypatch.undo()

    # Invalid migration file names.
    monkeypatch.setattr(db.os.path, 'isfile', lambda *args, **kwargs: True)
    monkeypatch.setattr(db.os, 'listdir', lambda *args, **kwargs: [
        '0.schema.sqnot', 'schema.sql', '/tmp', '0.schema.sql', '0.duplicate.sql'])
    with pytest.raises(db.DuplicateMigrationNumber):
        initialize_test_database()
    monkeypatch.undo()


def test_logs():
    'Just for coverage.'
    web.logs.setup(suppress_loggers=['foo'])
