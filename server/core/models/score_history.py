from typing import Optional

from core.db import db_obj
from sqlalchemy.orm import Mapped, mapped_column


class ScoreHistory(db_obj.Model):
    __tablename__ = 't_score_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    value: Mapped[int] = mapped_column(default=0, nullable=False)
    action: Mapped[str] = mapped_column(nullable=False)
    pre_value: Mapped[int] = mapped_column(default=0, nullable=False)
    current: Mapped[int] = mapped_column(default=0, nullable=False)
    msg: Mapped[str] = mapped_column(default='', nullable=True)
    dt: Mapped[str] = mapped_column(default='', nullable=False)
    # 关联外部对象（如抽奖礼物 id 等），可为空
    out_key: Mapped[Optional[int]] = mapped_column(nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "value": self.value,
            "action": self.action,
            "pre_value": self.pre_value,
            "current": self.current,
            "msg": self.msg,
            "dt": self.dt,
            "out_key": self.out_key,
        }
        