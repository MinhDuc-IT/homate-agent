"""Versioned dialogue storage and fail-stop plan execution contracts."""
from typing import Protocol


class WorkflowConflict(ValueError):
    pass


WRITE_TOOLS = frozenset({'control_device', 'execute_scene', 'create_scene', 'update_scene',
    'delete_scene', 'set_scene_enabled', 'create_schedule', 'update_schedule',
    'delete_schedule', 'set_schedule_enabled'})
READ_TOOLS = frozenset({'get_home_snapshot', 'get_energy_report', 'list_scenes', 'get_scene',
    'list_schedules', 'get_schedule', 'get_schedule_runs'})


class WorkflowRepository(Protocol):
    def begin(self, user, request_id, input_hash, session_id=None, expected_version=None): ...
    def commit(self, user, request_id, state, response, invalidate, steps, summary, ttl, lease_id, auto_execute=False): ...
    def abort(self, user, request_id, lease_id): ...
    def fetch(self, user, session_id): ...
    def get_plan(self, user, plan_id): ...
    def close(self, user, session_id): ...
    def recover(self, user, plan_id, version): ...
    def claim(self, user, plan_id, version, approved): ...
    def start_step(self, plan_id, ordinal): ...
    def finish_step(self, plan_id, ordinal, status, result): ...
    def finish_plan(self, plan_id, status, result): ...


class AgentWorkflowService:
    def __init__(self, repository: WorkflowRepository):
        self.repository = repository

    def decide(self, user, plan_id, version, approved, preflight, execute):
        plan = self.repository.claim(user, plan_id, version, approved)
        if not plan.pop('claimed', False):
            return plan
        return self.execute_claimed(plan, preflight, execute)

    def execute_claimed(self, plan, preflight, execute):
        plan_id = plan['id']
        try:
            # Validate the complete sequence before the first side effect.
            preflight(plan['steps'])
        except Exception:
            return self.repository.finish_plan(plan_id, 'failed', {
                'message': 'Dữ liệu hoặc quyền đã thay đổi; chưa chạy bước nào. Hãy lập kế hoạch mới.'})
        for step in plan['steps']:
            self.repository.start_step(plan_id, step['ordinal'])
            try:
                result = execute(step['tool'], step['prepared'])
            except Exception:
                self.repository.finish_step(plan_id, step['ordinal'], 'failed', {
                    'message': 'Bước thất bại; có thể đã có tác động. Kiểm tra trạng thái thực tế trước khi thử lại.'})
                return self.repository.finish_plan(plan_id, 'failed', {
                    'message': 'Đã dừng tại bước thất bại. Các bước còn lại bị bỏ qua; không tự động hoàn tác.'})
            if not self.repository.finish_step(plan_id, step['ordinal'], 'succeeded', result):
                return self.repository.finish_plan(plan_id, 'failed', {'message': 'Kế hoạch đã được đóng; không chạy tiếp.'})
        return self.repository.finish_plan(plan_id, 'executed', {'message': 'Đã thực hiện tất cả các bước.'})
