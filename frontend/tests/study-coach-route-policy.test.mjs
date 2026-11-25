import test from "node:test";
import assert from "node:assert/strict";
import { permitted } from "../lib/route-policy.mjs";

const U = "11111111-1111-4111-8111-111111111111";
const V = "22222222-2222-4222-8222-222222222222";
const followups = `/study-coach/attempts/${U}/questions/${V}/followups/`;

test("Sprint 8 follow-ups allow only GET and POST on exact UUID path", () => {
  assert.equal(permitted("GET", followups), true);
  assert.equal(permitted("POST", followups), true);
  assert.equal(permitted("PUT", followups), false);
  assert.equal(permitted("DELETE", followups), false);
  assert.equal(permitted("GET", `/study-coach/attempts/not-uuid/questions/${V}/followups/`), false);
});

test("Sprint 8 recommendations are read-only", () => {
  assert.equal(permitted("GET", "/study-coach/recommendations/"), true);
  assert.equal(permitted("POST", "/study-coach/recommendations/"), false);
});
