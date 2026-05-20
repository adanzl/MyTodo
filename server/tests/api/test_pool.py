"""
奖池维护功能测试
"""
import os
import unittest
import tempfile
from flask import Flask
from sqlalchemy import text
from core.db.db_mgr import db_mgr
from core.db import db_obj


class TestGiftPool(unittest.TestCase):
    """测试 t_gift_pool 表相关功能"""

    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.mkdtemp()
        cls._tmp_db_path = os.path.join(cls._tmp_dir, 'test.db')

        cls.app = Flask(__name__)
        cls.app.config['TESTING'] = True
        cls.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{cls._tmp_db_path}'
        cls.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db_mgr._initialized = False
        db_obj.init_app(cls.app)
        db_mgr._initialized = True

        with cls.app.app_context():
            db_obj.create_all()
            inspector = db_obj.inspect(db_obj.engine)
            for table, schema in [
                ('t_gift_pool', 'id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, cost INTEGER, enable INTEGER DEFAULT 1, description TEXT'),
                ('t_gift', 'id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, image TEXT, cost INTEGER, pool_id INTEGER, enable INTEGER DEFAULT 1'),
            ]:
                if not inspector.has_table(table):
                    db_obj.session.execute(text(f"CREATE TABLE {table} ({schema})"))
            db_obj.session.commit()

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)

    def setUp(self):
        with self.app.app_context():
            for table_name in ['t_gift', 't_gift_pool', 't_user', 't_score_history']:
                inspector = db_obj.inspect(db_obj.engine)
                if inspector.has_table(table_name):
                    db_obj.session.execute(text(f"DELETE FROM {table_name}"))
            db_obj.session.commit()

    def test_pool_table_exists(self):
        with self.app.app_context():
            inspector = db_obj.inspect(db_obj.engine)
            self.assertTrue(inspector.has_table('t_gift_pool'))

    def test_pool_crud(self):
        with self.app.app_context():
            create_result = db_mgr.set_data('t_gift_pool', {'name': '测试奖池', 'cost': 15})
            self.assertEqual(create_result['code'], 0)
            pool_id = create_result['data']

            get_result = db_mgr.get_data('t_gift_pool', pool_id, '*')
            self.assertEqual(get_result['code'], 0)
            self.assertEqual(get_result['data']['name'], '测试奖池')
            self.assertEqual(get_result['data']['cost'], 15)

            update_result = db_mgr.set_data('t_gift_pool', {'id': pool_id, 'name': '更新后的奖池', 'cost': 25})
            self.assertEqual(update_result['code'], 0)

            get_result = db_mgr.get_data('t_gift_pool', pool_id, '*')
            self.assertEqual(get_result['data']['name'], '更新后的奖池')
            self.assertEqual(get_result['data']['cost'], 25)

            delete_result = db_mgr.del_data('t_gift_pool', pool_id)
            self.assertEqual(delete_result['code'], 0)

            get_result = db_mgr.get_data('t_gift_pool', pool_id, '*')
            self.assertEqual(get_result['code'], 0)
            self.assertEqual(get_result['data'], {})

    def test_pool_list(self):
        with self.app.app_context():
            result = db_mgr.get_list('t_gift_pool', 1, 10)
            self.assertEqual(result['code'], 0)
            self.assertIn('data', result['data'])
            self.assertIn('totalCount', result['data'])

    def test_gift_pool_id_field(self):
        with self.app.app_context():
            pool_result = db_mgr.get_list('t_gift_pool', 1, 1)
            if pool_result['code'] == 0 and pool_result['data']['data']:
                pool_id = pool_result['data']['data'][0]['id']
                gift_result = db_mgr.set_data('t_gift', {
                    'name': '测试奖品',
                    'image': '',
                    'cost': 10,
                    'pool_id': pool_id,
                    'enable': 1
                })
                self.assertEqual(gift_result['code'], 0)
                gift_id = gift_result['data']

                get_gift = db_mgr.get_data('t_gift', gift_id, '*')
                self.assertEqual(get_gift['code'], 0)
                self.assertEqual(get_gift['data']['pool_id'], pool_id)

                db_mgr.del_data('t_gift', gift_id)


if __name__ == '__main__':
    unittest.main()
