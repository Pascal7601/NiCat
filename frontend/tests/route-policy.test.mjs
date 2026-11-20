import test from 'node:test';import assert from 'node:assert/strict';import {permitted,segmentPath} from '../lib/route-policy.mjs';
const id='b11442e0-7a0e-4db0-b431-102c1766dc0a';
test('allows approved read endpoint and saves',()=>{assert.equal(permitted('GET','/exams/'),true);assert.equal(permitted('PUT',`/attempts/${id}/responses/${id}/`),true)});
test('blocks unknown endpoints or dangerous methods',()=>{assert.equal(permitted('DELETE',`/attempts/${id}/`),false);assert.equal(permitted('GET','/admin/'),false);assert.equal(permitted('POST','/review/grade-items/'),false)});
test('encodes path segments instead of accepting slashes',()=>{assert.equal(segmentPath(['attempts','../../admin']),'/attempts/..%2F..%2Fadmin/')});
