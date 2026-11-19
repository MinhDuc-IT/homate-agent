"""Untrusted model interpretation, independently validated and never executable."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Evidence(StrictModel):
    path: str = Field(min_length=1, max_length=200, description='Đường dẫn giá trị trong arguments, ví dụ action hoặc parameters.temperature.')
    source: Literal['utterance', 'history', 'assumption']
    quote: str = Field(min_length=1, max_length=1000)


class Target(StrictModel):
    path: str = Field(min_length=1, max_length=200, description='Tham số ID thật của tool. control_device chỉ dùng device_id; phòng là bộ lọc room của target này, không phải room_id.')
    entity: Literal['device', 'room', 'scene', 'schedule']
    name: str | None = Field(default=None, max_length=200)
    room: str | None = Field(default=None, max_length=200)
    kind: str | None = Field(default=None, max_length=40)
    reference: str | None = Field(default=None, max_length=200)
    scope: Literal['single', 'all'] = 'single'
    scope_evidence: Evidence | None = Field(default=None,
        description='For scope=all, separate user evidence explicitly requesting every matching entity. A generic device type or assistant list is not evidence of all. path=scope.')
    exclusions: list[str] = Field(default_factory=list, max_length=30)
    source: Literal['utterance', 'history', 'assumption'] = 'utterance'
    quote: str = Field(default='', max_length=1000, description='Legacy diagnostic annotation; not required for contextual chat.')
    memory_ref: str | None = Field(default=None, max_length=300,
        description='Chỉ định rõ reference_id của entity trong conversation memory nếu đang nói tiếp về đối tượng đó. Code kiểm tra lại bằng chứng và quyền; không tự chọn entity nếu mơ hồ.')


class Adjustment(StrictModel):
    path: str
    operation: Literal['increase', 'decrease']
    amount: float = Field(gt=0)
    source: Literal['utterance', 'history'] = 'utterance'
    quote: str = Field(default='', max_length=1000)


class Intent(StrictModel):
    goal: str = Field(min_length=1, max_length=1000)
    capability: str | None = Field(default=None, max_length=80)
    arguments: dict[str, JsonValue] = Field(default_factory=dict, description='Chỉ tham số tool đã rõ. Không điền ID giả hoặc placeholder; bỏ ID để targets giải quyết.')
    targets: list[Target] = Field(default_factory=list, max_length=30, description='Đối tượng để điền tham số ID của API. get_home_snapshot không nhận ID: targets phải rỗng, chỉ dùng read_focus.')
    evidence: list[Evidence] = Field(default_factory=list, max_length=100, description='Bắt buộc cung cấp cho từng scalar đã điền trong arguments, gồm action. Quote nguyên văn lời user.')
    missing: list[str] = Field(default_factory=list, max_length=30)
    unresolved: list[str] = Field(default_factory=list, max_length=30)
    conditions: list[str] = Field(default_factory=list, max_length=20)
    depends_on: list[int] = Field(default_factory=list, max_length=48)
    adjustments: list[Adjustment] = Field(default_factory=list, max_length=20)
    indirect: bool = False
    read_focus: list[Target] = Field(default_factory=list, max_length=10,
        description='Đối tượng cần đọc để trả lời câu hỏi, không phải tham số API. Giải tham chiếu từ lịch sử bằng source=history và quote lời user.')
    requested_fields: list[str] = Field(default_factory=list, max_length=20,
        description='Tên thông số muốn biết từ dữ liệu backend, không điền giá trị. Để rỗng nếu cần toàn bộ thông tin.')


class DialogueDecision(StrictModel):
    relation: Literal['new_request', 'follow_up', 'clarification_answer', 'correction',
                      'resume', 'topic_change', 'cancel', 'unclear']
    task_action: Literal['preserve', 'replace', 'clear']
    topic: str = Field(default='', max_length=300)
    user_goal: str = Field(default='', max_length=1000)


class Interpretation(StrictModel):
    kind: Literal['action', 'query', 'mixed', 'conversation', 'unclear', 'cancel', 'correction']
    goal: str = Field(min_length=1, max_length=2000)
    intents: list[Intent] = Field(default_factory=list, max_length=48)
    dialogue: DialogueDecision | None = None
    answer_sources: list[Literal['backend', 'knowledge', 'conversation', 'general']] = Field(
        default_factory=list, description='Sources needed to answer this turn. Live home facts require backend; manuals require knowledge; pending-task questions use conversation.')


class Issue(StrictModel):
    code: str
    path: str
    message: str
    candidates: list[dict[str, JsonValue]] = Field(default_factory=list)


class IntentReview(StrictModel):
    goal: str
    capability: str | None
    status: Literal['ready_for_review', 'needs_clarification', 'unsupported', 'forbidden', 'needs_data']
    arguments: dict[str, JsonValue]
    provenance: dict[str, JsonValue]
    issues: list[Issue]
    requires_confirmation: bool
    read_context: dict[str, JsonValue] = Field(default_factory=dict)


class AnalysisReport(StrictModel):
    mode: Literal['observe'] = 'observe'
    executable: Literal[False] = False
    interpretation: Interpretation
    reviews: list[IntentReview]
    decision: Literal['ready_for_review', 'needs_clarification', 'unsupported', 'forbidden',
                      'needs_data', 'mixed', 'answer', 'no_active_session']
    questions: list[str]
