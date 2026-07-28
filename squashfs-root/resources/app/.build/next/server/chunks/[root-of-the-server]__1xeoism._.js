module.exports=[254799,(e,t,s)=>{t.exports=e.x("crypto",()=>require("crypto"))},750227,(e,t,s)=>{t.exports=e.x("node:path",()=>require("node:path"))},902157,(e,t,s)=>{t.exports=e.x("node:fs",()=>require("node:fs"))},814747,(e,t,s)=>{t.exports=e.x("path",()=>require("path"))},522734,(e,t,s)=>{t.exports=e.x("fs",()=>require("fs"))},446786,(e,t,s)=>{t.exports=e.x("os",()=>require("os"))},785148,(e,t,s)=>{t.exports=e.x("better-sqlite3-90e2652d1716b047",()=>require("better-sqlite3-90e2652d1716b047"))},844376,(e,t,s)=>{t.exports=e.x("node:module",()=>require("node:module"))},792509,(e,t,s)=>{t.exports=e.x("url",()=>require("url"))},704553,e=>{"use strict";var t=e.i(830471);let s=null,o=[["actual_prompt_tokens","INTEGER"],["actual_completion_tokens","INTEGER"],["actual_total_tokens","INTEGER"],["actual_cache_read_tokens","INTEGER"],["actual_cache_write_tokens","INTEGER"],["estimated_usd_saved","REAL"],["mcp_description_tokens_saved","INTEGER DEFAULT 0"],["multimodal_skip_count","INTEGER DEFAULT 0"],["receipt_source","TEXT"],["validation_fallback","INTEGER DEFAULT 0"],["output_mode","TEXT"],["compression_combo_id","TEXT"],["engine","TEXT"],["rtk_raw_output_pointer","TEXT"],["rtk_raw_output_bytes","INTEGER"],["rtk_raw_output_pointers","TEXT"],["rtk_raw_output_total_bytes","INTEGER"],["skip_reason","TEXT"]];function n(){let e=(0,t.getDbInstance)();if(s===e)return;let n=new Set(e.prepare("PRAGMA table_info(compression_analytics)").all().map(e=>e.name));for(let[t,s]of o)n.has(t)||e.exec(`ALTER TABLE compression_analytics ADD COLUMN ${t} ${s}`);s=e}function a(e){let s=(0,t.getDbInstance)();n(),s.prepare(`
    INSERT INTO compression_analytics (
      timestamp, combo_id, compression_combo_id, engine, provider, mode, original_tokens, compressed_tokens, tokens_saved,
      duration_ms, request_id, actual_prompt_tokens, actual_completion_tokens,
      actual_total_tokens, actual_cache_read_tokens, actual_cache_write_tokens,
      estimated_usd_saved, mcp_description_tokens_saved, multimodal_skip_count,
      receipt_source, validation_fallback, output_mode, rtk_raw_output_pointer, rtk_raw_output_bytes,
      rtk_raw_output_pointers, rtk_raw_output_total_bytes, skip_reason
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(e.timestamp,e.combo_id??null,e.compression_combo_id??null,e.engine??e.mode,e.provider??null,e.mode,e.original_tokens,e.compressed_tokens,e.tokens_saved,e.duration_ms??null,e.request_id??null,e.actual_prompt_tokens??null,e.actual_completion_tokens??null,e.actual_total_tokens??null,e.actual_cache_read_tokens??null,e.actual_cache_write_tokens??null,e.estimated_usd_saved??null,e.mcp_description_tokens_saved??0,e.multimodal_skip_count??0,e.receipt_source??null,+!!e.validation_fallback,e.output_mode??null,e.rtk_raw_output_pointer??null,e.rtk_raw_output_bytes??null,e.rtk_raw_output_pointers??null,e.rtk_raw_output_total_bytes??null,e.skip_reason??null)}let r=null;function _(e){if("number"==typeof e&&Number.isFinite(e))return Math.max(0,Math.floor(e));if("string"==typeof e&&e.trim()){let t=Number(e);if(Number.isFinite(t))return Math.max(0,Math.floor(t))}return null}function i(e,t){return e?`${e} AND ${t}`:`WHERE ${t}`}e.s(["attachCompressionUsageReceipt",0,function(e,s,o="provider"){if(!e||!s||"object"!=typeof s)return;let a=_(s.prompt_tokens),r=_(s.completion_tokens),i=_(s.total_tokens)??(a??0)+(r??0),c=s.prompt_tokens_details&&"object"==typeof s.prompt_tokens_details?s.prompt_tokens_details:{},l=_(s.cache_read_input_tokens??s.cached_tokens??c.cached_tokens),p=_(s.cache_creation_input_tokens??c.cache_creation_tokens);if(null===a&&null===r&&i<=0)return;let u=(0,t.getDbInstance)();n(),u.prepare(`
    UPDATE compression_analytics
    SET actual_prompt_tokens = ?,
        actual_completion_tokens = ?,
        actual_total_tokens = ?,
        actual_cache_read_tokens = ?,
        actual_cache_write_tokens = ?,
        receipt_source = ?
    WHERE request_id = ?
      AND id = (
        SELECT id FROM compression_analytics
        WHERE request_id = ?
        ORDER BY id DESC
        LIMIT 1
      )
  `).run(a,r,i,l,p,o,e,e)},"getCompressionAnalyticsSummary",0,function(e){let s=(0,t.getDbInstance)();n();let o=null;"24h"===e?o=new Date(Date.now()-864e5).toISOString():"7d"===e?o=new Date(Date.now()-6048e5).toISOString():"30d"===e&&(o=new Date(Date.now()-2592e6).toISOString());let a=o?"WHERE timestamp >= ?":"",r=o?[o]:[],_=i(a,"skip_reason IS NULL"),c=s.prepare(`
    SELECT
      COUNT(*) as total,
      COALESCE(SUM(tokens_saved), 0) as totalSaved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct,
      COALESCE(AVG(duration_ms), 0) as avgDur
    FROM compression_analytics ${_}
  `).get(...r),l=s.prepare(`
    SELECT mode, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct
    FROM compression_analytics ${_}
    GROUP BY mode
  `).all(...r),p=s.prepare(`
    SELECT mode, COUNT(*) as cnt
    FROM compression_analytics ${i(a,"skip_reason IS NOT NULL")}
    GROUP BY mode
  `).all(...r),u={};for(let e of l)u[e.mode]={count:e.cnt,tokensSaved:e.saved,avgSavingsPct:Math.round(e.avgPct),skipped:0};for(let e of p)u[e.mode]?u[e.mode].skipped=e.cnt:u[e.mode]={count:0,tokensSaved:0,avgSavingsPct:0,skipped:e.cnt};let d=s.prepare(`
    SELECT COALESCE(engine, mode) as engine, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct
    FROM compression_analytics ${_}
    GROUP BY COALESCE(engine, mode)
  `).all(...r),E={};for(let e of d)E[e.engine]={count:e.cnt,tokensSaved:e.saved,avgSavingsPct:Math.round(e.avgPct)};let m=s.prepare(`
    SELECT compression_combo_id as compressionComboId, COUNT(*) as cnt,
      COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics ${i(_,"compression_combo_id IS NOT NULL")}
    GROUP BY compression_combo_id ORDER BY cnt DESC
  `).all(...r),k={};for(let e of m)k[e.compressionComboId??"unknown"]={count:e.cnt,tokensSaved:e.saved};let T=s.prepare(`
    SELECT provider, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics ${_}
    GROUP BY provider ORDER BY cnt DESC
  `).all(...r),S={};for(let e of T)S[e.provider??"unknown"]={count:e.cnt,tokensSaved:e.saved};let v=new Map,C=new Date;for(let e=23;e>=0;e--){let t=new Date(C.getTime()-60*e*6e4).toISOString().substring(0,14)+"00:00Z";v.set(t,{hour:t,count:0,tokensSaved:0})}for(let e of s.prepare(`
    SELECT strftime('%Y-%m-%dT%H:00:00Z', timestamp) as hour,
      COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics
    WHERE timestamp >= ? AND skip_reason IS NULL
    GROUP BY hour ORDER BY hour ASC
  `).all(new Date(C.getTime()-864e5).toISOString()))v.has(e.hour)&&v.set(e.hour,{hour:e.hour,count:e.cnt,tokensSaved:e.saved});let g=Array.from(v.values()),h=s.prepare(`
    SELECT receipt_source as source, COUNT(*) as cnt,
      COALESCE(SUM(actual_prompt_tokens), 0) as prompt,
      COALESCE(SUM(actual_completion_tokens), 0) as completion,
      COALESCE(SUM(actual_total_tokens), 0) as total,
      COALESCE(SUM(actual_cache_read_tokens), 0) as cacheRead,
      COALESCE(SUM(actual_cache_write_tokens), 0) as cacheWrite,
      COALESCE(SUM(estimated_usd_saved), 0) as usdSaved
    FROM compression_analytics ${i(_,"receipt_source IS NOT NULL")}
    GROUP BY receipt_source
  `).all(...r),O={requestsWithReceipts:0,promptTokens:0,completionTokens:0,totalTokens:0,cacheReadTokens:0,cacheWriteTokens:0,estimatedUsdSaved:0,bySource:{}};for(let e of h){let t=e.source??"unknown";O.requestsWithReceipts+=e.cnt,O.promptTokens+=e.prompt,O.completionTokens+=e.completion,O.totalTokens+=e.total,O.cacheReadTokens+=e.cacheRead,O.cacheWriteTokens+=e.cacheWrite,O.estimatedUsdSaved+=e.usdSaved,O.bySource[t]=e.cnt}let L=s.prepare(`
    SELECT COUNT(*) as cnt
    FROM compression_analytics ${i(_,"validation_fallback = 1")}
  `).get(...r),N=s.prepare(`
    SELECT COUNT(*) as cnt, COALESCE(SUM(mcp_description_tokens_saved), 0) as saved
    FROM compression_analytics ${i(_,"mcp_description_tokens_saved > 0")}
  `).get(...r),R=s.prepare(`
    SELECT skip_reason as reason, COUNT(*) as cnt
    FROM compression_analytics ${i(a,"skip_reason IS NOT NULL")}
    GROUP BY skip_reason
  `).all(...r),b={},A=0;for(let e of R)b[e.reason??"unknown"]=e.cnt,A+=e.cnt;return{totalRequests:c?.total??0,totalTokensSaved:c?.totalSaved??0,avgSavingsPct:Math.round(c?.avgPct??0),avgDurationMs:Math.round(c?.avgDur??0),byMode:u,byEngine:E,byCompressionCombo:k,byProvider:S,last24h:g,totalSkipped:A,bySkipReason:b,validationFallbacks:L?.cnt??0,realUsage:O,mcpDescriptionCompression:{snapshots:N?.cnt??0,estimatedTokensSaved:N?.saved??0}}},"getLatestCompressionAnalyticsRun",0,function(){return(0,t.getDbInstance)().prepare(`SELECT id, timestamp, combo_id, compression_combo_id, mode,
              original_tokens, compressed_tokens, tokens_saved, duration_ms,
              request_id, engine, validation_fallback
         FROM compression_analytics
        ORDER BY timestamp DESC, id DESC
        LIMIT 1`).get()},"insertCompressionAnalyticsRow",0,a,"insertCompressionEngineBreakdown",0,function(e){let s;if(!e.length)return;let o=(0,t.getDbInstance)();s=(0,t.getDbInstance)(),r!==s&&(s.exec(`
    CREATE TABLE IF NOT EXISTS compression_engine_breakdown (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT NOT NULL,
      request_id TEXT,
      engine TEXT NOT NULL,
      original_tokens INTEGER NOT NULL DEFAULT 0,
      compressed_tokens INTEGER NOT NULL DEFAULT 0,
      tokens_saved INTEGER NOT NULL DEFAULT 0,
      duration_ms INTEGER
    );
    CREATE INDEX IF NOT EXISTS idx_ceb_engine_ts ON compression_engine_breakdown(engine, timestamp);
    CREATE INDEX IF NOT EXISTS idx_ceb_request ON compression_engine_breakdown(request_id);
  `),r=s);let n=o.prepare(`INSERT INTO compression_engine_breakdown
       (timestamp, request_id, engine, original_tokens, compressed_tokens, tokens_saved, duration_ms)
     VALUES (?, ?, ?, ?, ?, ?, ?)`);o.transaction(e=>{for(let t of e)n.run(t.timestamp,t.request_id??null,t.engine,t.original_tokens,t.compressed_tokens,t.tokens_saved,t.duration_ms??null)})(e)},"recordContextEditingTelemetry",0,function(e,t,s="claude"){let o=t?.clearedInputTokens??0;Number.isFinite(o)&&!(o<=0)&&a({timestamp:new Date().toISOString(),provider:s,mode:"context-editing",engine:"context-editing",original_tokens:o,compressed_tokens:0,tokens_saved:o,request_id:e?`${e}::context-editing`:null})}])},933762,e=>{e.v(t=>Promise.all(["server/chunks/[root-of-the-server]__1gewhnw._.js"].map(t=>e.l(t))).then(()=>t(223764)))},136388,e=>{e.v(t=>Promise.all(["server/chunks/[root-of-the-server]__17w9vqo._.js","server/chunks/_1x9c0iw._.js","server/chunks/open-sse_config_1rrbh50._.js","server/chunks/src_0wq7v2g._.js","server/chunks/src_1wuy3dw._.js","server/chunks/open-sse_1z9kdvh._.js","server/chunks/src_lib_1wb6kq4._.js","server/chunks/src_0x2xa7h._.js","server/chunks/src_lib_db_proxies_ts_0ajwjxa._.js"].map(t=>e.l(t))).then(()=>t(974210)))},833389,e=>{e.v(t=>Promise.all(["server/chunks/_1x9c0iw._.js","server/chunks/open-sse_config_1rrbh50._.js","server/chunks/src_lib_1wb6kq4._.js","server/chunks/src_0wq7v2g._.js","server/chunks/[root-of-the-server]__1gesd81._.js","server/chunks/src_1wuy3dw._.js","server/chunks/src_lib_db_proxies_ts_0ajwjxa._.js","server/chunks/src_0x2xa7h._.js","server/chunks/src_lib_db_1jw9mwb._.js","server/chunks/open-sse_1z9kdvh._.js"].map(t=>e.l(t))).then(()=>t(543125)))}];

//# sourceMappingURL=%5Broot-of-the-server%5D__1xeoism._.js.map