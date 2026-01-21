import json
import traceback
import datetime
from datetime import timezone, timedelta
from typing import Any, Dict, List, Optional, Union

from flask import Flask
from core.db import db_obj
from core.config import app_logger, config
from sqlalchemy import func
from sqlalchemy import MetaData, Table, select, text
from core.models.user import User
from core.models.score_history import ScoreHistory

log = app_logger

DB_NAME = "data.db"
TABLE_SAVE = "t_user_save"


class DbMgr:
    """数据库管理类，封装通用 CRUD 操作"""

    def __init__(self):
        self._initialized = False

    def init(self, app: Flask) -> None:
        """初始化数据库连接"""
        # 防止重复初始化
        if self._initialized:
            return

        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭修改跟踪（减少内存消耗）

        db_uri = 'sqlite:///./' + DB_NAME
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri

        # 针对 SQLite，SQLAlchemy 默认使用 NullPool，它会忽略 pool_size 等参数。
        # 为清晰起见，我们只设置必要的参数，并明确告知 gevent/多线程环境需要关闭线程检查。
        if 'sqlite' in db_uri:
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}
            log.info("DbMgr init with SQLite, using default NullPool and connect_args={'check_same_thread': False}")
        else:
            # 为其他数据库（如 PostgreSQL/MySQL）保留连接池配置
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_size': config.DB_POOL_SIZE,
                'max_overflow': config.DB_MAX_OVERFLOW,
                'pool_recycle': config.DB_POOL_RECYCLE,
                'pool_pre_ping': config.DB_POOL_PRE_PING,
            }
            log.info(f"DbMgr init with pool_size={config.DB_POOL_SIZE}, max_overflow={config.DB_MAX_OVERFLOW}, "
                     f"pool_recycle={config.DB_POOL_RECYCLE}, pool_pre_ping={config.DB_POOL_PRE_PING}")

        db_obj.init_app(app)
        self._initialized = True

    def set_save(self, id: Optional[int], user_name: str, data: str) -> Dict[str, Any]:
        """
        保存或更新用户数据到 t_user_save 表。
        如果 id 存在，则更新；否则插入新记录。
        """
        try:
            metadata = MetaData()
            table_obj = Table(TABLE_SAVE, metadata, autoload_with=db_obj.engine)
            if id:
                # 查找是否存在
                stmt_sel = select(table_obj).where(table_obj.c.id == id)
                result = db_obj.session.execute(stmt_sel).fetchone()
                if result:
                    # 存在则更新
                    stmt_upd = table_obj.update().where(table_obj.c.id == id).values(user_name=user_name, data=data)
                    db_obj.session.execute(stmt_upd)
                else:
                    # 不存在则插入
                    stmt_ins = table_obj.insert().values(id=id, user_name=user_name, data=data)
                    res = db_obj.session.execute(stmt_ins)
                    id = res.inserted_primary_key[0] if res.inserted_primary_key else id
            else:
                # 没有id直接插入
                stmt_ins = table_obj.insert().values(user_name=user_name, data=data)
                res = db_obj.session.execute(stmt_ins)
                id = res.inserted_primary_key[0] if res.inserted_primary_key else None
            db_obj.session.commit()
        except Exception as e:
            db_obj.session.rollback()
            log.error(e)
            traceback.print_exc()
            return {"code": -1, "msg": 'error ' + str(e)}
        return {"code": 0, "msg": "ok", "data": id}

    def get_data_idx(self, table: str, id: int, idx: int = 1) -> Dict[str, Any]:
        """根据 id 从指定表获取单个字段的数据。"""
        try:
            metadata = MetaData()
            table_obj = Table(table, metadata, autoload_with=db_obj.engine)
            stmt = select(table_obj).where(table_obj.c.id == id)
            result = db_obj.session.execute(stmt).fetchone()
            if result:
                data = result[idx]
                try:
                    data = json.loads(data)
                except:
                    pass
            else:
                data = "{}"
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            return {"code": -1, "msg": 'error ' + str(e)}
        return {"code": 0, "msg": "ok", "data": data}

    def get_data(self, table: str, id: int, fields: Union[str, List[str]]) -> Dict[str, Any]:
        """根据 id 从指定表获取一个或多个字段的数据。"""
        try:
            metadata = MetaData()
            table_obj = Table(table, metadata, autoload_with=db_obj.engine)

            if fields == '*':
                # 返回所有列
                stmt = select(table_obj).where(table_obj.c.id == id)
                result = db_obj.session.execute(stmt).fetchone()
                if result:
                    # 获取所有列名
                    columns = [col.name for col in table_obj.columns]
                    data = dict(zip(columns, result))
                else:
                    data = {}
            else:
                # 指定字段查询
                if isinstance(fields, str):
                    fields = [f.strip() for f in fields.split(',')]
                columns = [table_obj.c[f] for f in fields if f in table_obj.c]
                if not columns:
                    return {"code": -1, "msg": f"无效的字段: {fields}", "data": None}
                stmt = select(*columns).where(table_obj.c.id == id)
                result = db_obj.session.execute(stmt).fetchone()
                if result:
                    data = dict(zip(fields, result))
                else:
                    data = {}
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            return {"code": -1, "msg": 'error ' + str(e)}
        return {"code": 0, "msg": "ok", "data": data}

    def set_data(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        向指定表插入或更新数据。
        如果 data 中包含 id 且存在，则更新；否则插入。
        """
        try:
            metadata = MetaData()
            table_obj = Table(table, metadata, autoload_with=db_obj.engine)

            # 处理数据，将list类型转换为JSON字符串
            processed_data = {}
            for key, value in data.items():
                if isinstance(value, list):
                    processed_data[key] = json.dumps(value, ensure_ascii=False)
                else:
                    processed_data[key] = value

            id = processed_data.get('id')
            if id:
                # 查找是否存在
                stmt_sel = select(table_obj).where(table_obj.c.id == id)
                result = db_obj.session.execute(stmt_sel).fetchone()
                if result:
                    # 存在则更新
                    stmt_upd = table_obj.update().where(table_obj.c.id == id).values(**processed_data)
                    db_obj.session.execute(stmt_upd)
                else:
                    # 不存在则插入
                    stmt_ins = table_obj.insert().values(**processed_data)
                    res = db_obj.session.execute(stmt_ins)
                    id = res.inserted_primary_key[0] if res.inserted_primary_key else id
            else:
                # 没有id直接插入
                stmt_ins = table_obj.insert().values(**processed_data)
                res = db_obj.session.execute(stmt_ins)
                id = res.inserted_primary_key[0] if res.inserted_primary_key else None
            db_obj.session.commit()
        except Exception as e:
            db_obj.session.rollback()
            log.error(e)
            traceback.print_exc()
            return {"code": -1, "msg": 'error ' + str(e)}
        return {"code": 0, "msg": "ok", "data": id}

    def add_score(self, user_id: int, value: int, action: str, msg: Optional[str]) -> Dict[str, Any]:
        """为用户增加或扣除积分，并记录历史。"""
        try:
            # 查找用户
            user = db_obj.session.get(User, user_id)
            if not user:
                return {"code": -1, "msg": f"用户不存在: {user_id}"}

            # 计算新的积分
            pre_score = user.score
            cur_score = pre_score + int(value)

            # 创建积分历史记录
            # 手动计算时区偏移，确保正确输出时区信息
            now = datetime.datetime.now()
            offset = now.astimezone().utcoffset()
            offset_hours = int(offset.total_seconds() / 3600)
            offset_str = f"{offset_hours:+03d}:00"

            score_history = ScoreHistory(user_id=user_id,
                                         value=value,
                                         action=action,
                                         pre_value=pre_score,
                                         current=cur_score,
                                         msg=msg,
                                         dt=now.strftime(f"%Y-%m-%d %H:%M:%S {offset_str}"))

            # 更新用户积分
            user.score = cur_score

            # 提交事务
            db_obj.session.add(score_history)
            db_obj.session.commit()

            return {"code": 0, "msg": "ok", "data": cur_score}
        except Exception as e:
            db_obj.session.rollback()
            log.error(e)
            traceback.print_exc()
            return {"code": -1, "msg": f'error: {str(e)}'}

    def del_data(self, table: str, id: int) -> Dict[str, Any]:
        """从指定表删除一条数据。"""
        try:
            # 动态获取表对象
            metadata = MetaData()
            table_obj = Table(table, metadata, autoload_with=db_obj.engine)
            stmt = table_obj.delete().where(table_obj.c.id == id)
            result = db_obj.session.execute(stmt)
            db_obj.session.commit()
            cnt = result.rowcount
        except Exception as e:
            db_obj.session.rollback()
            log.error(e)
            traceback.print_exc()
            return {"code": -1, "msg": 'error ' + str(e)}
        return {"code": 0, "msg": "ok", "data": cnt}

    def query(self, sql: str) -> Dict[str, Any]:
        """执行原生 SQL 查询。"""
        try:
            result = db_obj.session.execute(text(sql))
            rows = result.fetchall()
            columns = result.keys()
            if rows:
                data = [dict(zip(columns, row)) for row in rows]
            else:
                data = []
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            return {"code": -1, "msg": 'error ' + str(e)}
        return {"code": 0, "msg": "ok", "data": data}

    def get_list(self,
                 table: str,
                 page_num: int = 1,
                 page_size: int = 20,
                 fields: Union[str, List[str]] = '*',
                 conditions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            # 动态获取表结构
            metadata = MetaData()
            table_obj = Table(table, metadata, autoload_with=db_obj.engine)

            # 构建查询
            if fields == '*' or not isinstance(fields, list):
                query = select(table_obj)
                count_query = select(func.count()).select_from(table_obj)
            else:
                # 字段筛选
                columns = [table_obj.columns[f] for f in fields if f in table_obj.columns]
                if not columns:
                    return {"code": -1, "msg": f"无效的字段: {fields}", "data": None}
                query = select(*columns)
                count_query = select(func.count()).select_from(table_obj)

            # 条件过滤
            if conditions and isinstance(conditions, dict):
                for k, v in conditions.items():
                    if k in table_obj.columns:
                        query = query.where(table_obj.columns[k] == v)
                        count_query = count_query.where(table_obj.columns[k] == v)

            # 获取总数
            total_count = db_obj.session.execute(count_query).scalar()

            # 分页和排序
            query = query.order_by(text('id DESC')).offset((page_num - 1) * page_size).limit(page_size)

            # 执行查询
            result = db_obj.session.execute(query)

            # 转换结果
            if fields == '*' or not isinstance(fields, list):
                # 获取所有列名
                columns = [col.name for col in table_obj.columns]
                data_list = [dict(zip(columns, row)) for row in result]
            else:
                data_list = [dict(zip(fields, row)) for row in result]

            data = {
                'data': data_list,
                'totalCount': total_count,
                'pageNum': page_num,
                'pageSize': page_size,
                'totalPage': (total_count + page_size - 1) // page_size,
            }
            return {"code": 0, "msg": "ok", "data": data}
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            return {"code": -1, "msg": f'error: {str(e)}', "data": None}


db_mgr = DbMgr()
