import test from 'node:test';
import assert from 'node:assert/strict';
import {parseCsv, dateIso, normalizedRows, fetchCountry, base64} from '../lib/official-bond-refresh.ts';

// All numbers below are SYNTHETIC TEST INPUTS, never production observations.
test('CSV handles quoted commas, escaped quotes, CRLF and missing values', () => {
  assert.deepEqual(parseCsv('"a,b",c\r\n"x""y",\r\n'), [['a,b','c'],['x"y','']]);
  assert.throws(() => parseCsv('"unfinished'), /unterminated/);
});
test('real calendar dates, full history and conflicting duplicates are guarded', () => {
  assert.equal(dateIso(2024,2,29),'2024-02-29');
  assert.throws(() => dateIso(2023,2,29), /Invalid calendar/);
  assert.throws(() => normalizedRows([], new Date('2026-10-17')), /unexpectedly short/);
  assert.throws(() => normalizedRows([{date:'2020-01-02',value:1},{date:'2020-01-02',value:2}], new Date('2026-10-17')), /Conflicting duplicate/);
  assert.throws(() => normalizedRows([{date:'2099-01-02',value:1}], new Date('2026-10-17')), /future/);
});
test('base64 encoding preserves binary raw-source bytes', () => {
  const bytes=Uint8Array.from([0,128,255,34,10]);
  assert.deepEqual([...Buffer.from(base64(bytes),'base64')],[...bytes]);
});
const syntheticDays=Array.from({length:100},(_,i)=>new Date(Date.UTC(2020,0,i+1)).toISOString().slice(0,10));
test('Japan current MOF table takes precedence over overlapping historical date', async () => {
  const original=globalThis.fetch;
  globalThis.fetch=async url=>new Response('Date,10Y\n'+(url.includes('historical')?syntheticDays.map((date,i)=>date.replaceAll('-','/')+','+(i/100)).join('\n'):'2020/01/03,8.765'));
  try {
    const result=await fetchCountry('Japan',new Date('2026-10-17'));
    assert.equal(result.rows.length,100);
    assert.equal(result.rows.find(row=>row.date==='2020-01-03').value,8.765);
    assert.equal(result.raw.length,2);
  } finally {globalThis.fetch=original;}
});
test('German export ignores descriptive metadata and retains negative synthetic values', async () => {
  const original=globalThis.fetch;
  globalThis.fetch=async()=>new Response('description,not an observation\n'+syntheticDays.map((date,i)=>date+','+(i===0?'-0.123':i/100)).join('\n'));
  try {
    const result=await fetchCountry('Germany',new Date('2026-10-17'));
    assert.equal(result.rows[0].value,-0.123);
    assert.equal(result.rows.length,100);
  } finally {globalThis.fetch=original;}
});
test('HTTP failure never becomes a successful empty snapshot', async () => {
  const original=globalThis.fetch;
  globalThis.fetch=async()=>new Response('unavailable',{status:503});
  try {await assert.rejects(fetchCountry('Germany',new Date('2026-10-17')),/HTTP 503/);}
  finally {globalThis.fetch=original;}
});
