import { test } from 'node:test';
import assert from 'node:assert/strict';
import { permitted } from '../lib/route-policy.mjs';

test('staff question browser has a single read-only JSON search route', () => {
  assert.equal(permitted('POST', '/staff/questions/search/'), true);
  for (const path of ['/staff/questions/answers/', '/staff/questions/publish/', '/staff/questions/delete/', '/staff/questions/search/other/']) {
    assert.equal(permitted('POST', path), false, path);
  }
  assert.equal(permitted('GET', '/staff/questions/search/'), false);
  assert.equal(permitted('PUT', '/staff/questions/search/'), false);
});
