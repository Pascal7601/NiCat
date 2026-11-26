import {test} from 'node:test';
import assert from 'node:assert/strict';
import {permitted} from '../lib/route-policy.mjs';
const ID='00000000-0000-4000-8000-000000000001';
test('document intake is strictly allowlisted',()=>{
  for(const path of [
    '/document-intake/', '/document-intake/programmes/',
    `/document-intake/programmes/${ID}/units/`,
    '/document-intake/staff/',`/document-intake/staff/${ID}/`,
  ])assert.equal(permitted('GET',path),true,path);
  assert.equal(permitted('POST',`/document-intake/${ID}/withdraw/`),true);
  assert.equal(permitted('POST',`/document-intake/staff/${ID}/review/`),true);
  assert.equal(permitted('POST','/document-intake/'),false,'multipart must use a dedicated route');
  assert.equal(permitted('GET',`/document-intake/staff/${ID}/file/`),false);
  assert.equal(permitted('DELETE',`/document-intake/staff/${ID}/`),false);
  assert.equal(permitted('GET','/document-intake/../../admin/'),false);
});
