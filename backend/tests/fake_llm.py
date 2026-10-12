"""A fake DeepSeek server for tests: returns scripted chat-completion responses in order."""
import json

import httpx

from app.agent.llm import DeepSeekClient


def completion(content=None, tool_calls=None, finish="stop"):
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
        finish = "tool_calls"
    return {"choices": [{"index": 0, "message": msg, "finish_reason": finish}], "usage": {"total_tokens": 1}}


def tool_call(name, args, call_id="call_1"):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class FakeLLM:
    def __init__(self, responses, status=200):
        self.responses = list(responses)
        self.requests: list[dict] = []
        self.status = status

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        if self.status != 200:
            return httpx.Response(self.status, json={"error": "boom"})
        body = self.responses.pop(0) if self.responses else completion("done")
        if isinstance(body, int):  # scripted HTTP error for this call
            return httpx.Response(body, json={"error": "scripted"})
        return httpx.Response(200, json=body)

    def client(self) -> DeepSeekClient:
        return DeepSeekClient("test-key", "https://fake.deepseek", "deepseek-flash", transport=httpx.MockTransport(self.handler))
