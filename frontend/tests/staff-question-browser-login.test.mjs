import {test} from 'node:test';
import assert from 'node:assert/strict';
import {staffReturnPath} from '../lib/staff-login-next.mjs';

test('staff question bank deep links return to the requested staff page', () => {
  assert.equal(staffReturnPath('?next=%2Fstaff%2Fquestions'), '/staff/questions');
  assert.equal(staffReturnPath('?next=%2Fstaff%2Fdocuments'), '/staff/documents');
  assert.equal(staffReturnPath('?next=https%3A%2F%2Fevil.example'), '/dashboard');
});
