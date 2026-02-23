from __future__ import annotations

from src.applications.search_agent.memory.conversation_memory import ConversationMemory
from src.applications.search_agent.memory.semantic_memory import SemanticMemory

# --- Conversation Memory Tests ---


class TestConversationMemory:
    async def test_add_and_get_messages(self):
        mem = ConversationMemory(window_size=10)
        await mem.set("session1", {"role": "user", "content": "Hello"})
        await mem.set("session1", {"role": "assistant", "content": "Hi there"})

        result = await mem.get("session1")
        assert result is not None
        assert len(result) == 2

    async def test_sliding_window_eviction(self):
        mem = ConversationMemory(window_size=3)
        for i in range(5):
            await mem.set("s1", {"role": "user", "content": f"msg {i}"})

        result = await mem.get("s1")
        assert result is not None
        assert len(result) == 3
        assert result[0]["content"] == "msg 2"
        assert result[2]["content"] == "msg 4"

    async def test_get_nonexistent_session(self):
        mem = ConversationMemory(window_size=10)
        result = await mem.get("nonexistent")
        assert result is None

    async def test_delete_session(self):
        mem = ConversationMemory(window_size=10)
        await mem.set("s1", {"role": "user", "content": "test"})
        deleted = await mem.delete("s1")
        assert deleted is True
        assert await mem.get("s1") is None

    async def test_delete_nonexistent(self):
        mem = ConversationMemory(window_size=10)
        deleted = await mem.delete("nonexistent")
        assert deleted is False

    async def test_search_by_content(self):
        mem = ConversationMemory(window_size=10)
        await mem.set("s1", {"role": "user", "content": "I love Python"})
        await mem.set("s1", {"role": "assistant", "content": "Python is great"})
        await mem.set("s2", {"role": "user", "content": "Hello world"})

        results = await mem.search("Python")
        assert len(results) >= 1
        assert any("Python" in str(r["value"]) for r in results)

    async def test_clear(self):
        mem = ConversationMemory(window_size=10)
        await mem.set("s1", {"role": "user", "content": "test"})
        await mem.set("s2", {"role": "user", "content": "test2"})
        count = await mem.clear()
        assert count == 2
        assert await mem.get("s1") is None

    async def test_multiple_sessions_isolated(self):
        mem = ConversationMemory(window_size=10)
        await mem.set("s1", {"role": "user", "content": "session 1"})
        await mem.set("s2", {"role": "user", "content": "session 2"})

        result1 = await mem.get("s1")
        result2 = await mem.get("s2")
        assert result1 is not None
        assert result2 is not None
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0]["content"] == "session 1"


# --- Semantic Memory Tests ---


class TestSemanticMemory:
    async def test_store_and_retrieve_fact(self):
        mem = SemanticMemory()
        await mem.set("user:lang", "User prefers Python")
        result = await mem.get("user:lang")
        assert result == "User prefers Python"

    async def test_get_nonexistent(self):
        mem = SemanticMemory()
        result = await mem.get("nonexistent")
        assert result is None

    async def test_delete_fact(self):
        mem = SemanticMemory()
        await mem.set("fact1", "Some fact")
        deleted = await mem.delete("fact1")
        assert deleted is True
        assert await mem.get("fact1") is None

    async def test_delete_nonexistent(self):
        mem = SemanticMemory()
        deleted = await mem.delete("nonexistent")
        assert deleted is False

    async def test_search_by_keyword(self):
        mem = SemanticMemory()
        await mem.set("pref:lang", "User prefers Python programming")
        await mem.set("pref:editor", "User uses VSCode as IDE")
        await mem.set("fact:name", "User name is Alice")

        results = await mem.search("Python")
        assert len(results) >= 1
        assert any("Python" in str(r["value"]) for r in results)

    async def test_search_top_k(self):
        mem = SemanticMemory()
        for i in range(10):
            await mem.set(f"fact:{i}", f"Fact number {i} about Python")

        results = await mem.search("Python", top_k=3)
        assert len(results) == 3

    async def test_search_with_namespace(self):
        mem = SemanticMemory()
        await mem.set("pref:lang", "User prefers Python", namespace="preferences")
        await mem.set("fact:name", "User is Alice", namespace="facts")

        results = await mem.search("User", namespace="preferences")
        assert len(results) == 1
        assert results[0]["key"] == "pref:lang"

    async def test_clear_all(self):
        mem = SemanticMemory()
        await mem.set("f1", "fact 1")
        await mem.set("f2", "fact 2")
        count = await mem.clear()
        assert count == 2

    async def test_clear_by_namespace(self):
        mem = SemanticMemory()
        await mem.set("p1", "pref 1", namespace="prefs")
        await mem.set("f1", "fact 1", namespace="facts")
        count = await mem.clear(namespace="prefs")
        assert count == 1
        assert await mem.get("f1") == "fact 1"

    async def test_set_with_namespace(self):
        mem = SemanticMemory()
        await mem.set("key1", "value1", namespace="ns1")
        await mem.set("key1", "value2", namespace="ns2")
        # Same key, different namespace — both should exist
        result = await mem.get("key1")
        # get without namespace returns the last one set at that key
        assert result is not None
