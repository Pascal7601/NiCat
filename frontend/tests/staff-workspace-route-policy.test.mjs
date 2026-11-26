import test from 'node:test';
import assert from 'node:assert/strict';
import {permitted} from '../lib/route-policy.mjs';
const id='00000000-0000-4000-8000-000000000001';

test('staff workspace exact path allowlist',()=>{
 const validGet=[
  '/staff/overview/','/staff/sources/units/','/staff/sources/documents/',
  '/staff/sources/references/','/staff/sources/topics/','/staff/sources/excerpts/',
  `/staff/sources/excerpts/${id}/`,'/staff/tutor/',`/staff/tutor/${id}/`,
  '/staff/contributions/',`/staff/contributions/${id}/`,
  '/staff/followups/',`/staff/followups/${id}/`,
 ];
 for(const path of validGet) assert.equal(permitted('GET',path),true,path);
 const validPost=[
  '/staff/sources/documents/',`/staff/sources/documents/${id}/rights/`,
  '/staff/sources/references/','/staff/sources/excerpts/',
  `/staff/sources/excerpts/${id}/`,`/staff/sources/excerpts/${id}/action/`,
  '/staff/tutor/generate/',`/staff/tutor/${id}/`,`/staff/tutor/${id}/action/`,
  `/staff/contributions/${id}/`,`/staff/contributions/${id}/action/`,
  `/staff/followups/${id}/`,`/staff/followups/${id}/action/`,
 ];
 for(const path of validPost) assert.equal(permitted('POST',path),true,path);
});

test('staff rules block arbitrary methods, paths, payload endpoints',()=>{
 for(const path of [
  '/staff/anything/', '/staff/overview/extra/', '/staff/sources/documents/all/rights/',
  '/staff/sources/documents/not-a-uuid/rights/',
  '/staff/contributions/admin/', '/staff/followups/reviewer/',
 ]) assert.equal(permitted('GET',path),false,path);
 assert.equal(permitted('POST','/staff/overview/'),false);
 assert.equal(permitted('PUT','/staff/tutor/generate/'),false);
 assert.equal(permitted('DELETE',`/staff/contributions/${id}/`),false);
 assert.equal(permitted('POST',`/staff/contributions/${id}/publish/`),false);
});
