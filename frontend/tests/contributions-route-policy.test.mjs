import test from "node:test";
import assert from "node:assert/strict";
import { permitted } from "../lib/route-policy.mjs";
const uuid = "00000000-0000-4000-8000-000000000001";
test("contribution intake is exact-path allowlisted", () => {
  assert.equal(permitted("GET", "/contributions/"), true);
  assert.equal(permitted("POST", "/contributions/"), true);
  assert.equal(permitted("GET", "/contributions/units/"), true);
  assert.equal(permitted("GET", `/contributions/${uuid}/`), true);
  assert.equal(permitted("POST", `/contributions/${uuid}/withdraw/`), true);
  assert.equal(permitted("POST", `/contributions/${uuid}/`), false);
  assert.equal(permitted("PUT", "/contributions/"), false);
  assert.equal(permitted("GET", "/contributions/admin/"), false);
  assert.equal(permitted("POST", "/contributions/publish/"), false);
});
