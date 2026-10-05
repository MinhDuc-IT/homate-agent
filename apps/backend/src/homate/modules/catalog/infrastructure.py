"""PostgreSQL adapter. Composite foreign keys enforce home boundaries."""
from uuid import uuid4

from sqlalchemy import (MetaData, Table, Column, String, Boolean, Integer, DateTime,
                        ForeignKey, ForeignKeyConstraint, UniqueConstraint, Uuid, func, select, delete, update)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

from homate.modules.catalog.domain import CatalogError

metadata = MetaData()


def base_columns():
    return [Column("id", Uuid, primary_key=True),
            Column("name", String(120), nullable=False),
            Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False)]


homes = Table("homes", metadata, *base_columns(), Column("timezone", String(80), nullable=False))
rooms = Table("rooms", metadata, *base_columns(),
              Column("home_id", Uuid, ForeignKey("homes.id", ondelete="RESTRICT"), nullable=False, index=True),
              UniqueConstraint("id", "home_id"), UniqueConstraint("home_id", "name"))
devices = Table("devices", metadata, *base_columns(),
                Column("home_id", Uuid, ForeignKey("homes.id", ondelete="RESTRICT"), nullable=False, index=True),
                Column("room_id", Uuid, nullable=False),
                Column("kind", String(40), nullable=False),
                Column("capabilities", JSONB, nullable=False),
                ForeignKeyConstraint(["room_id", "home_id"], ["rooms.id", "rooms.home_id"], ondelete="RESTRICT"),
                UniqueConstraint("id", "home_id"), UniqueConstraint("home_id", "name"))
scenes = Table("scenes", metadata, *base_columns(),
               Column("home_id", Uuid, ForeignKey("homes.id", ondelete="RESTRICT"), nullable=False, index=True),
               Column("is_enabled", Boolean, nullable=False),
               UniqueConstraint("id", "home_id"), UniqueConstraint("home_id", "name"))
steps = Table("scene_steps", metadata,
              Column("id", Uuid, primary_key=True), Column("scene_id", Uuid, nullable=False),
              Column("home_id", Uuid, nullable=False), Column("device_id", Uuid, nullable=False),
              Column("position", Integer, nullable=False), Column("action", String(80), nullable=False),
              Column("parameters", JSONB, nullable=False),
              ForeignKeyConstraint(["scene_id", "home_id"], ["scenes.id", "scenes.home_id"], ondelete="CASCADE"),
              ForeignKeyConstraint(["device_id", "home_id"], ["devices.id", "devices.home_id"], ondelete="RESTRICT"),
              UniqueConstraint("scene_id", "position"))
TABLES = {"homes": homes, "rooms": rooms, "devices": devices, "scenes": scenes}


class PostgresCatalogRepository:
    def __init__(self, connection):
        self.connection = connection

    def _serialize(self, kind, row):
        result = dict(row)
        if kind == "scenes":
            result["steps"] = [dict(s) for s in self.connection.execute(
                select(steps.c.device_id, steps.c.action, steps.c.parameters)
                .where(steps.c.scene_id == result["id"]).order_by(steps.c.position)).mappings()]
        return result

    def list(self, kind, home_id=None):
        table = TABLES[kind]
        query = select(table).order_by(table.c.created_at, table.c.id)
        if home_id is not None and kind != "homes":
            query = query.where(table.c.home_id == home_id)
        return [self._serialize(kind, row) for row in self.connection.execute(query).mappings().all()]

    def get(self, kind, identifier):
        table = TABLES[kind]
        row = self.connection.execute(select(table).where(table.c.id == identifier)).mappings().first()
        return self._serialize(kind, row) if row else None

    def save(self, kind, identifier, values, create):
        values = dict(values)
        scene_steps = values.pop("steps", [])
        table = TABLES[kind]
        try:
            if create:
                self.connection.execute(table.insert().values(id=identifier, **values))
            else:
                self.connection.execute(update(table).where(table.c.id == identifier).values(**values))
            if kind == "scenes":
                self.connection.execute(delete(steps).where(steps.c.scene_id == identifier))
                for position, step in enumerate(scene_steps):
                    self.connection.execute(steps.insert().values(
                        id=uuid4(), scene_id=identifier, home_id=values["home_id"], position=position, **step))
            return self.get(kind, identifier)
        except IntegrityError:
            raise CatalogError("Tên bị trùng hoặc dữ liệu liên kết không còn hợp lệ.", 409) from None

    def delete(self, kind, identifier):
        table = TABLES[kind]
        try:
            self.connection.execute(delete(table).where(table.c.id == identifier))
        except IntegrityError:
            raise CatalogError("Dữ liệu đang được sử dụng. Hãy xóa hoặc chuyển các mục liên quan trước.", 409) from None
