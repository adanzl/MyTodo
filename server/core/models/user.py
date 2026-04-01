from core.db import db_obj
from sqlalchemy.orm import Mapped, mapped_column


class User(db_obj.Model):
    __tablename__ = 't_user'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    icon: Mapped[str]
    pwd: Mapped[str]
    score: Mapped[int] = mapped_column(default=0)
    admin: Mapped[int] = mapped_column(default=0)
    wish_progress: Mapped[int] = mapped_column(default=0)
    wish_list: Mapped[str] = mapped_column(default='[]')

    def to_dict(self):
        return {"id": self.id, "name": self.name, "icon": self.icon, "score": self.score, "admin": self.admin, "wish_progress": self.wish_progress, "wish_list": self.wish_list}
