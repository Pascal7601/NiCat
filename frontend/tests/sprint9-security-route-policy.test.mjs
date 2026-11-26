import test from 'node:test';
import assert from 'node:assert/strict';
import { permitted } from '../lib/route-policy.mjs';

const a = '11111111-1111-4111-8111-111111111111';
const b = '22222222-2222-4222-8222-222222222222';

test('Sprint 9: no arbitrary URL, admin, or wildcard proxy access', () => {
  for (const method of ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']) {
    assert.equal(permitted(method, '/admin/'), false);
    assert.equal(permitted(method, '/api/v1/schema/'), false);
    assert.equal(permitted(method, '/http://evil.example/'), false);
  }
  assert.equal(permitted('GET', '/study-coach/recommendations/../../admin/'), false);
});

test('Sprint 9: public access never grants a staff-only draft path by method escalation', () => {
  const draft = `/study-tutor/revisions/${a}/draft/`;
  assert.equal(permitted('GET', draft), false);
  assert.equal(permitted('PUT', draft), false);
  assert.equal(permitted('DELETE', draft), false);
  // POST is intentionally permitted by the BFF but Django must enforce staff permissions.
  assert.equal(permitted('POST', draft), true);
});

test('Sprint 9: student followups are exact-path only; private grading has no GET proxy', () => {
  const followup = `/study-coach/attempts/${a}/questions/${b}/followups/`;
  assert.equal(permitted('GET', followup), true);
  assert.equal(permitted('POST', followup), true);
  assert.equal(permitted('PATCH', followup), false);
  assert.equal(permitted('GET', `${followup}../admin/`), false);
  assert.equal(permitted('GET', `/review/grade-items/${a}/mark/`), false);
});
