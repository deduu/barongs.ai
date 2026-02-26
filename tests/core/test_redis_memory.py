"""Tests for RedisMemory backend."""

from __future__ import annotations

import pytest

from src.core.memory.redis import RedisMemory


@pytest.fixture
async def redis_memory() -> RedisMemory:
    """Create a RedisMemory backed by fakeredis."""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    memory = RedisMemory(client=client)
    yield memory
    await client.flushdb()
    await client.aclose()


class TestRedisMemoryGetSet:
    async def test_get_returns_none_for_missing_key(self, redis_memory: RedisMemory) -> None:
        result = await redis_memory.get("nonexistent")
        assert result is None

    async def test_set_and_get_string(self, redis_memory: RedisMemory) -> None:
        await redis_memory.set("key1", "hello")
        result = await redis_memory.get("key1")
        assert result == "hello"

    async def test_set_and_get_dict(self, redis_memory: RedisMemory) -> None:
        data = {"app_name": "todo", "entities": ["Task", "User"]}
        await redis_memory.set("requirements", data)
        result = await redis_memory.get("requirements")
        assert result == data

    async def test_set_and_get_list(self, redis_memory: RedisMemory) -> None:
        files = ["models.py", "routes.py", "main.py"]
        await redis_memory.set("files", files)
        result = await redis_memory.get("files")
        assert result == files

    async def test_set_and_get_nested_structure(self, redis_memory: RedisMemory) -> None:
        appspec = {
            "app": {"name": "todo", "version": "1.0"},
            "entities": [{"name": "Task", "fields": [{"name": "title", "type": "str"}]}],
        }
        await redis_memory.set("appspec", appspec)
        result = await redis_memory.get("appspec")
        assert result == appspec

    async def test_set_with_ttl(self, redis_memory: RedisMemory) -> None:
        await redis_memory.set("temp", "value", ttl_seconds=3600)
        result = await redis_memory.get("temp")
        assert result == "value"

    async def test_overwrite_existing_key(self, redis_memory: RedisMemory) -> None:
        await redis_memory.set("key", "v1")
        await redis_memory.set("key", "v2")
        result = await redis_memory.get("key")
        assert result == "v2"


class TestRedisMemoryDelete:
    async def test_delete_existing_key(self, redis_memory: RedisMemory) -> None:
        await redis_memory.set("key", "value")
        deleted = await redis_memory.delete("key")
        assert deleted is True
        assert await redis_memory.get("key") is None

    async def test_delete_nonexistent_key(self, redis_memory: RedisMemory) -> None:
        deleted = await redis_memory.delete("nonexistent")
        assert deleted is False


class TestRedisMemorySearch:
    async def test_search_by_key_pattern(self, redis_memory: RedisMemory) -> None:
        await redis_memory.set("job:123:requirements", {"app": "todo"})
        await redis_memory.set("job:123:appspec", {"models": ["Task"]})
        await redis_memory.set("job:456:requirements", {"app": "chat"})

        results = await redis_memory.search("job:123:*")
        assert len(results) == 2
        keys = {r["key"] for r in results}
        assert "job:123:requirements" in keys
        assert "job:123:appspec" in keys

    async def test_search_respects_top_k(self, redis_memory: RedisMemory) -> None:
        for i in range(10):
            await redis_memory.set(f"item:{i}", f"value_{i}")

        results = await redis_memory.search("item:*", top_k=3)
        assert len(results) == 3

    async def test_search_with_namespace(self, redis_memory: RedisMemory) -> None:
        await redis_memory.set("ns1:key1", "a")
        await redis_memory.set("ns2:key2", "b")

        results = await redis_memory.search("*", namespace="ns1")
        assert len(results) == 1
        assert results[0]["key"] == "ns1:key1"

    async def test_search_no_matches(self, redis_memory: RedisMemory) -> None:
        results = await redis_memory.search("nonexistent:*")
        assert results == []


class TestRedisMemoryClear:
    async def test_clear_all(self, redis_memory: RedisMemory) -> None:
        await redis_memory.set("a", "1")
        await redis_memory.set("b", "2")
        count = await redis_memory.clear()
        assert count == 2
        assert await redis_memory.get("a") is None

    async def test_clear_with_namespace(self, redis_memory: RedisMemory) -> None:
        await redis_memory.set("ns1:a", "1")
        await redis_memory.set("ns1:b", "2")
        await redis_memory.set("ns2:c", "3")

        count = await redis_memory.clear(namespace="ns1")
        assert count == 2
        assert await redis_memory.get("ns1:a") is None
        assert await redis_memory.get("ns2:c") == "3"

    async def test_clear_empty(self, redis_memory: RedisMemory) -> None:
        count = await redis_memory.clear()
        assert count == 0
