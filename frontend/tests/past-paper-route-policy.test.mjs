import {test} from 'node:test';
import assert from 'node:assert/strict';
import {permitted} from '../lib/route-policy.mjs';
const U='00000000-0000-4000-8000-000000000001';
test('Sprint 15 permits ONLY the declared past-paper API routes',()=>{
  for(const path of [
    '/past-papers/',`/past-papers/${U}/questions/`,
    `/past-papers/${U}/page/1/`, `/past-paper-questions/${U}/variations/`,
  ])assert.equal(permitted('GET',path),true,path);
  for(const path of [
    `/past-papers/${U}/questions/`, `/past-papers/${U}/questions/manual/`,
    `/past-papers/${U}/external-authorization/`,
    `/past-paper-questions/${U}/correct/`,
    `/past-paper-questions/${U}/review/`,
    `/past-paper-questions/${U}/variations/`,
    `/past-paper-variations/${U}/edit/`,
    `/past-paper-variations/${U}/review/`,
  ])assert.equal(permitted('POST',path),true,path);
});
test('does not open raw-file, public or destructive endpoints',()=>{
  for(const path of ['/past-papers/private-file/',`/past-papers/${U}/download/`,`/past-paper-variations/${U}/publish/`]){
    assert.equal(permitted('GET',path),false);
    assert.equal(permitted('POST',path),false);
  }
  assert.equal(permitted('DELETE',`/past-papers/${U}/questions/`),false);
});
