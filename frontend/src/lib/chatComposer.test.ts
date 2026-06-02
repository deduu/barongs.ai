import assert from "node:assert/strict";
import test from "node:test";
import {
  getAutoResizeHeight,
  getConversationBootstrapAction,
  WELCOME_TEXTAREA_CLASS_NAME,
} from "./chatComposer.ts";

test("bootstraps a new conversation when none is active and none exist", () => {
  assert.equal(getConversationBootstrapAction(null, 0), "new-chat");
});

test("loads the first saved conversation when auth resets the active id", () => {
  assert.equal(getConversationBootstrapAction(null, 2), "load-first");
});

test("does not re-bootstrap when a conversation is already active", () => {
  assert.equal(getConversationBootstrapAction("conv-123", 2), "none");
});

test("keeps the welcome textarea content away from the border", () => {
  assert.match(WELCOME_TEXTAREA_CLASS_NAME, /\bbox-border\b/);
  assert.match(WELCOME_TEXTAREA_CLASS_NAME, /\bpx-4\b/);
  assert.match(WELCOME_TEXTAREA_CLASS_NAME, /\bpy-3\b/);
});

test("clamps autoresize height to the configured range", () => {
  assert.equal(getAutoResizeHeight(24, 76, 160), 76);
  assert.equal(getAutoResizeHeight(96, 76, 160), 96);
  assert.equal(getAutoResizeHeight(320, 76, 160), 160);
});
