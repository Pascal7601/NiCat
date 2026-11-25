import test from 'node:test';
import assert from 'node:assert/strict';
import {staffReturnPath} from '../lib/staff-login-next.mjs';

test('returns to the requested known staff page after sign-in', () => {
  assert.equal(staffReturnPath('?next=%2Fstaff'), '/staff');
  assert.equal(staffReturnPath('?next=%2Fstaff%2Fsources'), '/staff/sources');
  assert.equal(staffReturnPath('?next=%2Fstaff%2Ftutor'), '/staff/tutor');
  assert.equal(staffReturnPath('?next=%2Fstaff%2Fcontributions'), '/staff/contributions');
  assert.equal(staffReturnPath('?next=%2Fstaff%2Ffollowups'), '/staff/followups');
});

test('rejects unsafe or unexpected post-login redirect targets', () => {
  for (const path of [
    '', '//evil.example', 'https://evil.example', '/\\evil.example',
    '/staff/../../logout', '/staff?x=1', '/staff/unknown', '/dashboard',
  ]) {
    assert.equal(staffReturnPath(`?next=${encodeURIComponent(path)}`), '/dashboard', path);
  }
});
