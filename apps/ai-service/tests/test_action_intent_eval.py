"""Opt-in provider eval with the production agent and in-memory software only.

RUN_ACTION_INTENT_EVAL=1 python -m pytest tests/test_action_intent_eval.py -q
Uses configured provider/key (billable); never connects to the real backend.
Checks write proposals and explicit limitation wording for unsupported requests.
Wording checks are a limited heuristic, not a general semantic judge.
"""
import asyncio
import json
import os
import re
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from homate_ai.agent.tool_agent import ToolConversationAgent
from homate_ai.clients.llm import CompatibleChatModel
from homate_ai.config import Settings
from test_runtime import Backend, Workflow


CASES = json.loads((Path(__file__).parents[1] / 'evals/action_intent.json').read_text(encoding='utf-8'))


@pytest.mark.skipif(os.environ.get('RUN_ACTION_INTENT_EVAL') != '1', reason='Opt-in billable provider evaluation')
@pytest.mark.parametrize('case', CASES, ids=[case['id'] for case in CASES])
def test_provider_action_intent(case):
    async def run():
        settings = Settings()
        base = 'https://api.openai.com/v1/' if settings.llm_provider == 'openai' else 'https://openrouter.ai/api/v1/'
        async with httpx.AsyncClient(base_url=base, timeout=40) as client:
            workflow = Workflow()
            agent = ToolConversationAgent(CompatibleChatModel(client, settings.model, settings.api_key), Backend(), workflow)
            previous = None
            for index, text in enumerate(case['turns']):
                previous = await agent.chat('valid', str(uuid4()), text, [],
                    previous['conversation_id'] if previous else None,
                    previous['conversation_version'] if previous else None)
                proposed = bool(workflow.commits[-1]['steps'])
                # Earlier turns in these conversations are questions or lack a room.
                expected = case['propose'] if index == len(case['turns']) - 1 else False
                if not expected:
                    assert not any(item['tool'] == 'propose_plan' for item in previous['trace']), \
                        f"{case['id']} turn {index + 1}: unexpected write proposal attempt"
                assert proposed == expected, (f"{case['id']} turn {index + 1}: expected propose={expected}, got {proposed}; "
                    f"reply={previous['reply']}; trace={previous['trace']}")
                if case.get('require_limit') or index in case.get('limit_turns', []):
                    assert re.search(r'(?:không|chưa)\s+(?:được\s+)?(?:thể|hỗ trợ|thực hiện|cho phép)|vượt\s+(?:quá\s+)?(?:khả năng|giới hạn)', previous['reply'], re.I), \
                        f"{case['id']} turn {index + 1}: must explain the limit, not merely ask for confirmation; reply={previous['reply']}"
    asyncio.run(run())
