"""Bind explicit application repository methods to PostgreSQL transactions."""
from homate.infrastructure.postgres import household


class PostgresHouseholdRepository:
    def __init__(self, database_url): self.database_url = database_url
    def load_home(self): return household.load_home(self.database_url)
    def load_devices(self): return household.load_devices(self.database_url)
    def get_user(self, user_id): return household.get_user(self.database_url, user_id)
    def list_users(self, home_id): return household.list_users(self.database_url, home_id)
    def create_user(self, home_id, data): return household.create_user(self.database_url, home_id, data)
    def update_user(self, home_id, user_id, data): return household.update_user(self.database_url, home_id, user_id, data)
    def deactivate_user(self, home_id, user_id): return household.deactivate_user(self.database_url, home_id, user_id)
    def list_scenes(self, home_id): return household.list_scenes(self.database_url, home_id)
    def get_scene(self, home_id, scene_id): return household.get_scene(self.database_url, home_id, scene_id)
    def create_scene(self, home_id, **data): return household.create_scene(self.database_url, home_id, **data)
    def update_scene(self, home_id, scene_id, **data): return household.update_scene(self.database_url, home_id, scene_id, **data)
    def delete_scene(self, home_id, scene_id): return household.delete_scene(self.database_url, home_id, scene_id)
    def get_home_settings(self, home_id): return household.get_home_settings(self.database_url, home_id)
    def update_home_settings(self, home_id, data): return household.update_home_settings(self.database_url, home_id, data)
    def list_command_logs(self, home_id, **filters): return household.list_command_logs(self.database_url, home_id, **filters)
    def append_command_log(self, home_id, **data): return household.append_command_log(self.database_url, home_id, **data)
    def list_hitl_policies(self, home_id): return household.list_hitl_policies(self.database_url, home_id)
    def replace_hitl_policies(self, home_id, data): return household.replace_hitl_policies(self.database_url, home_id, data)
    def load_rooms_ambient(self, home_id): return household.load_rooms_ambient(self.database_url, home_id)
    def set_room_mock(self, home_id, room_id, **data): return household.set_room_mock(self.database_url, home_id, room_id, **data)
    def mark_room_suggested(self, home_id, room_id): return household.mark_room_suggested(self.database_url, home_id, room_id)
