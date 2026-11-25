import test from 'node:test';
import assert from 'node:assert/strict';
import {permitted} from '../lib/route-policy.mjs';

const U = '11111111-1111-4111-8111-111111111111';
const V = '22222222-2222-4222-8222-222222222222';

test('student tutor can only GET released explanation path via BFF', () => {
  const path = `/study-tutor/attempts/${U}/questions/${V}/explanation/`;
  assert.equal(permitted('GET', path), true);
  assert.equal(permitted('POST', path), false);
  assert.equal(permitted('PUT', path), false);
});

test('staff tutor draft route is POST-only; no arbitrary source file path', () => {
  const draft = `/study-tutor/revisions/${U}/draft/`;
  assert.equal(permitted('POST', draft), true);
  assert.equal(permitted('GET', draft), false);
  assert.equal(permitted('POST', '/study-tutor/upload/'), false);
  assert.equal(permitted('GET', `/study-tutor/attempts/${U}/questions/not-a-uuid/explanation/`), false);
});
