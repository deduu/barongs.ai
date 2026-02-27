from __future__ import annotations

import json

import fakeredis.aioredis
import pytest

from src.applications.search_agent.memory.redis_conversation_memory import (
    RedisConversationMemory,
)


@pytest.fixture
async def redis_client():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
async def mem(redis_client):
    return RedisConversationMemory(client=redis_client, window_size=10)


class TestRedisConversationMemory:
    async def test_add_and_get_messages(self, mem):
        await mem.set("session1", {"role": "user", "content": "Hello"})
        await mem.set("session1", {"role": "assistant", "content": "Hi there"})

        result = await mem.get("session1")
        assert result is not None
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    async def test_sliding_window_eviction(self, redis_client):
        mem = RedisConversationMemory(client=redis_client, window_size=3)
        for i in range(5):
            await mem.set("s1", {"role": "user", "content": f"msg {i}"})

        result = await mem.get("s1")
        assert result is not None
        assert len(result) == 3
        assert result[0]["content"] == "msg 2"
        assert result[2]["content"] == "msg 4"

    async def test_get_nonexistent_session(self, mem):
        result = await mem.get("nonexistent")
        assert result is None

    async def test_delete_session(self, mem):
        await mem.set("s1", {"role": "user", "content": "test"})
        deleted = await mem.delete("s1")
        assert deleted is True
        assert await mem.get("s1") is None

    async def test_delete_nonexistent(self, mem):
        deleted = await mem.delete("nonexistent")
        assert deleted is False

    async def test_search_by_content(self, mem):
        await mem.set("s1", {"role": "user", "content": "I love Python"})
        await mem.set("s1", {"role": "assistant", "content": "Python is great"})
        await mem.set("s2", {"role": "user", "content": "Hello world"})

        results = await mem.search("Python")
        assert len(results) >= 1
        assert any("Python" in str(r["value"]) for r in results)

    async def test_clear(self, mem):
        await mem.set("s1", {"role": "user", "content": "test"})
        await mem.set("s2", {"role": "user", "content": "test2"})
        count = await mem.clear()
        assert count == 2
        assert await mem.get("s1") is None

    async def test_multiple_sessions_isolated(self, mem):
        await mem.set("s1", {"role": "user", "content": "session 1"})
        await mem.set("s2", {"role": "user", "content": "session 2"})

        result1 = await mem.get("s1")
        result2 = await mem.get("s2")
        assert result1 is not None
        assert result2 is not None
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0]["content"] == "session 1"

    async def test_ttl_is_set_on_key(self, redis_client):
        mem = RedisConversationMemory(
            client=redis_client, window_size=10, session_ttl_seconds=3600
        )
        await mem.set("s1", {"role": "user", "content": "test"})
        ttl = await redis_client.ttl("bgs:session:s1")
        assert ttl > 0
        assert ttl <= 3600

    async def test_redis_stores_json(self, mem, redis_client):
        """Verify messages are stored as JSON strings in a Redis List."""
        msg = {"role": "user", "content": "hello"}
        await mem.set("s1", msg)
        raw = await redis_client.lrange("bgs:session:s1", 0, -1)
        assert len(raw) == 1
        assert json.loads(raw[0]) == msg
