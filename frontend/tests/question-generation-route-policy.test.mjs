import {test} from 'node:test';
import assert from 'node:assert/strict';
import {permitted} from '../lib/route-policy.mjs';
const U='00000000-0000-4000-8000-000000000001';
test('Sprint 14 explicitly permits narrow staff generation endpoints',()=>{
  for(const path of ['/question-generation/sources/','/question-generation/jobs/',`/question-generation/jobs/${U}/`]){
    assert.equal(permitted('GET',path),true,path);
  }
  for(const path of ['/question-generation/jobs/',`/question-generation/candidates/${U}/edit/`,
                     `/question-generation/candidates/${U}/action/`,'/question-generation/external-authorizations/']){
    assert.equal(permitted('POST',path),true,path);
  }
});
test('unknown routes and methods remain rejected',()=>{
  assert.equal(permitted('GET','/question-generation/candidates/'),false);
  assert.equal(permitted('PUT','/question-generation/jobs/'),false);
  assert.equal(permitted('POST',`/question-generation/jobs/${U}/`),false);
  assert.equal(permitted('GET','/question-generation/private-file/'),false);
});
