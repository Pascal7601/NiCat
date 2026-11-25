import {test} from 'node:test';
import assert from 'node:assert/strict';
import {permitted} from '../lib/route-policy.mjs';
const ID = '00000000-0000-4000-8000-000000000001';
test('verified unit creation has an explicit allowlist entry and no broad wildcard', () => {
  assert.equal(permitted('POST', `/document-intake/staff/${ID}/create-unit/`), true);
  assert.equal(permitted('GET', `/document-intake/staff/${ID}/create-unit/`), false);
  assert.equal(permitted('POST', `/document-intake/staff/${ID}/dangerous/`), false);
});
