"""
奖池维护功能测试
"""
import unittest
from core.db.db_mgr import db_mgr


class TestGiftPool(unittest.TestCase):
    """测试 t_gift_pool 表相关功能"""

    def test_pool_table_exists(self):
        """测试 t_gift_pool 表是否存在"""
        result = db_mgr.get_list('t_gift_pool', 1, 10)
        self.assertEqual(result['code'], 0)

    def test_pool_crud(self):
        """测试奖池的增删改查"""
        # 创建
        create_result = db_mgr.set_data('t_gift_pool', {'name': '测试奖池', 'cost': 15})
        self.assertEqual(create_result['code'], 0)
        pool_id = create_result['data']['id']

        # 查询
        get_result = db_mgr.get_data('t_gift_pool', pool_id, '*')
        self.assertEqual(get_result['code'], 0)
        self.assertEqual(get_result['data']['name'], '测试奖池')
        self.assertEqual(get_result['data']['cost'], 15)

        # 更新
        update_result = db_mgr.set_data('t_gift_pool', {'id': pool_id, 'name': '更新后的奖池', 'cost': 25})
        self.assertEqual(update_result['code'], 0)

        # 验证更新
        get_result = db_mgr.get_data('t_gift_pool', pool_id, '*')
        self.assertEqual(get_result['data']['name'], '更新后的奖池')
        self.assertEqual(get_result['data']['cost'], 25)

        # 删除
        delete_result = db_mgr.del_data('t_gift_pool', pool_id)
        self.assertEqual(delete_result['code'], 0)

        # 验证删除
        get_result = db_mgr.get_data('t_gift_pool', pool_id, '*')
        self.assertNotEqual(get_result['code'], 0)

    def test_pool_list(self):
        """测试获取奖池列表"""
        result = db_mgr.get_list('t_gift_pool', 1, 10)
        self.assertEqual(result['code'], 0)
        self.assertIn('data', result['data'])
        self.assertIn('totalCount', result['data'])

    def test_gift_pool_id_field(self):
        """测试 t_gift 表的 pool_id 字段"""
        # 查询默认奖池
        pool_result = db_mgr.get_list('t_gift_pool', 1, 1)
        if pool_result['code'] == 0 and pool_result['data']['data']:
            pool_id = pool_result['data']['data'][0]['id']

            # 创建测试奖品
            gift_result = db_mgr.set_data('t_gift', {
                'name': '测试奖品',
                'image': '',
                'cost': 10,
                'pool_id': pool_id,
                'enable': 1
            })
            self.assertEqual(gift_result['code'], 0)
            gift_id = gift_result['data']['id']

            # 验证 pool_id
            get_gift = db_mgr.get_data('t_gift', gift_id, '*')
            self.assertEqual(get_gift['code'], 0)
            self.assertEqual(get_gift['data']['pool_id'], pool_id)

            # 清理
            db_mgr.del_data('t_gift', gift_id)


if __name__ == '__main__':
    unittest.main()
