import pytest
import json
from flask import Flask
from sqlalchemy import text
from unittest.mock import patch

from core.db.db_mgr import db_mgr as db_manager
from core.db import db_obj
from core.models.user import User

TABLE_SAVE = "t_user_save"


@pytest.fixture(scope='module')
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    yield app

    with app.app_context():
        try:
            db_obj.session.remove()
        except Exception:
            pass
        try:
            if db_obj.engine:
                db_obj.engine.dispose()
        except Exception:
            pass


@pytest.fixture(scope='function')
def db_mgr(app):
    db_manager._initialized = False
    if 'sqlalchemy' in app.extensions:
        with app.app_context():
            db_obj.engine.dispose()
        del app.extensions['sqlalchemy']

    db_manager.init(app)

    with app.app_context():
        db_obj.create_all()
        inspector = db_obj.inspect(db_obj.engine)
        if not inspector.has_table(TABLE_SAVE):
            create_table_sql = text(f"""
            CREATE TABLE {TABLE_SAVE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                data TEXT
            );
            """)
            db_obj.session.execute(create_table_sql)
            db_obj.session.commit()

        db_obj.session.execute(text(f"DELETE FROM {TABLE_SAVE}"))
        db_obj.session.execute(text("DELETE FROM t_user"))
        db_obj.session.execute(text("DELETE FROM t_score_history"))
        db_obj.session.commit()

    db_manager.app = app
    return db_manager


def test_init(db_mgr):
    assert db_mgr._initialized is True


def test_set_and_get_save(db_mgr):
    with db_mgr.app.app_context():
        user_name = 'testuser'
        data_json = '{"key":"value"}'
        result = db_mgr.set_save(id=None, user_name=user_name, data=data_json)
        assert result['code'] == 0
        record_id = result['data']
        assert record_id is not None

        retrieved_data = db_mgr.get_data(TABLE_SAVE, record_id, '*')
        assert retrieved_data['code'] == 0
        assert retrieved_data['data']['user_name'] == user_name
        assert retrieved_data['data']['data'] == data_json

        updated_data_json = '{"key":"updated"}'
        update_result = db_mgr.set_save(id=record_id, user_name=user_name, data=updated_data_json)
        assert update_result['code'] == 0

        retrieved_updated_data = db_mgr.get_data(TABLE_SAVE, record_id, 'data')
        assert retrieved_updated_data['code'] == 0
        assert retrieved_updated_data['data']['data'] == updated_data_json


def test_del_data(db_mgr):
    with db_mgr.app.app_context():
        result = db_mgr.set_save(id=None, user_name='todelete', data='{}')
        record_id = result['data']

        del_result = db_mgr.del_data(TABLE_SAVE, record_id)
        assert del_result['code'] == 0
        assert del_result['data'] == 1

        get_result = db_mgr.get_data(TABLE_SAVE, record_id, '*')
        assert get_result['code'] == 0
        assert get_result['data'] == {}


def test_add_score(db_mgr):
    with db_mgr.app.app_context():
        user = User(name='scorer', score=100, icon='default_icon', pwd='default_pwd')
        db_obj.session.add(user)
        db_obj.session.commit()
        user_id = user.id

        add_score_result = db_mgr.add_score(user_id=user_id, value=50, action='test_add', msg='Test')
        assert add_score_result['code'] == 0
        assert add_score_result['data'] == 150

        updated_user = db_obj.session.get(User, user_id)
        assert updated_user.score == 150

        history_result = db_mgr.query(f"SELECT * FROM t_score_history WHERE user_id = {user_id}")
        assert history_result['code'] == 0
        assert len(history_result['data']) == 1
        assert history_result['data'][0]['value'] == 50


def test_set_data(db_mgr):
    with db_mgr.app.app_context():
        data_to_insert = {'user_name': 'set_data_user', 'data': '{"test": 1}'}
        result = db_mgr.set_data(TABLE_SAVE, data_to_insert)
        assert result['code'] == 0
        record_id = result['data']
        assert record_id is not None

        retrieved = db_mgr.get_data(TABLE_SAVE, record_id, '*')
        assert retrieved['data']['user_name'] == 'set_data_user'

        data_to_update = {'id': record_id, 'user_name': 'set_data_user_updated', 'data': '{"test": 2}'}
        update_result = db_mgr.set_data(TABLE_SAVE, data_to_update)
        assert update_result['code'] == 0

        retrieved_updated = db_mgr.get_data(TABLE_SAVE, record_id, '*')
        assert retrieved_updated['data']['user_name'] == 'set_data_user_updated'


def test_get_data_idx(db_mgr):
    with db_mgr.app.app_context():
        user_name = 'idx_user'
        data_json = '{"a": 1}'
        result = db_mgr.set_save(id=None, user_name=user_name, data=data_json)
        record_id = result['data']

        retrieved = db_mgr.get_data_idx(TABLE_SAVE, record_id, idx=1)
        assert retrieved['code'] == 0
        assert retrieved['data'] == user_name

        retrieved_data = db_mgr.get_data_idx(TABLE_SAVE, record_id, idx=2)
        assert retrieved_data['code'] == 0
        assert retrieved_data['data'] == {'a': 1}


def test_query(db_mgr):
    with db_mgr.app.app_context():
        db_mgr.set_save(id=None, user_name='query_user', data='{}')

        sql = f"SELECT user_name FROM {TABLE_SAVE} WHERE user_name = 'query_user'"
        result = db_mgr.query(sql)
        assert result['code'] == 0
        assert len(result['data']) == 1
        assert result['data'][0]['user_name'] == 'query_user'


def test_get_list(db_mgr):
    with db_mgr.app.app_context():
        for i in range(25):
            db_mgr.set_save(id=None, user_name=f'user_{i}', data=f'{{"val":{i}}}')

        list_result = db_mgr.get_list(TABLE_SAVE, page_num=1, page_size=10)
        assert list_result['code'] == 0
        assert list_result['data']['totalCount'] == 25
        assert len(list_result['data']['data']) == 10
        assert list_result['data']['data'][0]['user_name'] == 'user_24'

        list_fields = db_mgr.get_list(TABLE_SAVE, page_num=1, page_size=5, fields=['user_name'])
        assert list_fields['code'] == 0
        assert 'id' not in list_fields['data']['data'][0]
        assert 'user_name' in list_fields['data']['data'][0]

        list_filtered = db_mgr.get_list(TABLE_SAVE, conditions={'user_name': 'user_5'})
        assert list_filtered['code'] == 0
        assert list_filtered['data']['totalCount'] == 1
        assert list_filtered['data']['data'][0]['user_name'] == 'user_5'


def test_set_data_with_list_serialization(db_mgr):
    with db_mgr.app.app_context():
        data_to_insert = {'user_name': 'list_user', 'data': [1, 2, 3]}
        result = db_mgr.set_data(TABLE_SAVE, data_to_insert)
        assert result['code'] == 0
        record_id = result['data']

        retrieved = db_mgr.get_data(TABLE_SAVE, record_id, '*')
        assert retrieved['data']['data'] == json.dumps([1, 2, 3])


def test_db_operation_exception_handling(db_mgr, monkeypatch):
    with db_mgr.app.app_context():
        # Patch the session to raise an exception
        with patch.object(db_obj.session, 'execute', side_effect=Exception("DB error")):
            result = db_mgr.set_save(id=None, user_name='fail_user', data='{}')
            assert result['code'] == -1
            assert 'DB error' in result['msg']


def test_get_data_idx_not_found(db_mgr):
    with db_mgr.app.app_context():
        retrieved = db_mgr.get_data_idx(TABLE_SAVE, 999, idx=1)
        assert retrieved['code'] == 0
        assert retrieved['data'] == '{}'


def test_add_score_user_not_found(db_mgr):
    with db_mgr.app.app_context():
        result = db_mgr.add_score(user_id=999, value=10, action='test', msg='test')
        assert result['code'] == -1
        assert '用户不存在' in result['msg']
