import json
import traceback
import datetime
from datetime import timezone, timedelta

from core.db import db_obj
from core.log_config import root_logger
from sqlalchemy import func
from sqlalchemy import MetaData, Table, select, text
from core.models.user import User
from core.models.score_history import ScoreHistory

log = root_logger()

DB_NAME = "data.db"
TABLE_SAVE = "t_user_save"

class DB_Mgr:

    @staticmethod
    def init(app):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./' + DB_NAME  # SQLite 数据库
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭修改跟踪（减少内存消耗）
        db_obj.init_app(app)
        log.info("DB_Mgr init")

    @staticmethod
    def set_save(id, user_name, data) -> dict:
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

    @staticmethod
    def get_data_idx(table, id, idx=1):
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

    @staticmethod
    def get_data(table, id, fields):
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

    @staticmethod
    def set_data(table, data):
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

    @staticmethod
    def add_score(user_id, value, action, msg):
        '''
            增加积分
        '''
        try:
            # 查找用户
            user = User.query.get(user_id)
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

    @staticmethod
    def del_data(table, id: int) -> dict:
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

    @staticmethod
    def query(sql) -> dict:
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

    @staticmethod
    def get_list(table, page_num=1, page_size=20, fields: str | list = '*', conditions=None) -> dict:
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
