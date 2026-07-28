module.exports=[254799,(e,s,t)=>{s.exports=e.x("crypto",()=>require("crypto"))},750227,(e,s,t)=>{s.exports=e.x("node:path",()=>require("node:path"))},902157,(e,s,t)=>{s.exports=e.x("node:fs",()=>require("node:fs"))},814747,(e,s,t)=>{s.exports=e.x("path",()=>require("path"))},522734,(e,s,t)=>{s.exports=e.x("fs",()=>require("fs"))},446786,(e,s,t)=>{s.exports=e.x("os",()=>require("os"))},785148,(e,s,t)=>{s.exports=e.x("better-sqlite3-90e2652d1716b047",()=>require("better-sqlite3-90e2652d1716b047"))},844376,(e,s,t)=>{s.exports=e.x("node:module",()=>require("node:module"))},792509,(e,s,t)=>{s.exports=e.x("url",()=>require("url"))},865498,e=>{"use strict";var s=e.i(830471);function t(){(0,s.getDbInstance)().exec(`
    CREATE TABLE IF NOT EXISTS compression_run_telemetry (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp INTEGER NOT NULL,
      request_id TEXT,
      model TEXT,
      provider TEXT,
      source TEXT,
      tokens_before INTEGER NOT NULL,
      tokens_after INTEGER NOT NULL,
      ratio REAL,
      cost_delta REAL,
      output_styles TEXT,
      output_style_bypass TEXT,
      output_tokens INTEGER
    )
  `)}e.s(["getCompressionRunTelemetrySummary",0,function(){let e=(0,s.getDbInstance)();t();let r=e.prepare(`SELECT tokens_before, tokens_after, output_styles, output_style_bypass, output_tokens
       FROM compression_run_telemetry`).all(),o={totalRuns:r.length,totalTokensSaved:0,runsWithStyles:0,bypassCount:0,totalOutputTokens:0,appliedStyleCounts:{}};for(let e of r)if(o.totalTokensSaved+=Math.max(0,e.tokens_before-e.tokens_after),o.totalOutputTokens+=e.output_tokens??0,e.output_style_bypass&&(o.bypassCount+=1),e.output_styles){o.runsWithStyles+=1;try{for(let s of JSON.parse(e.output_styles))o.appliedStyleCounts[s.id]=(o.appliedStyleCounts[s.id]??0)+1}catch{}}return o},"insertCompressionRunTelemetryRow",0,function(e){try{let r=(0,s.getDbInstance)();t(),r.prepare(`INSERT INTO compression_run_telemetry (
        timestamp, request_id, model, provider, source,
        tokens_before, tokens_after, ratio, cost_delta,
        output_styles, output_style_bypass, output_tokens
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(Date.now(),e.requestId??null,e.model??null,e.provider??null,e.source??null,e.tokensBefore,e.tokensAfter,e.ratio,e.costDelta??null,e.outputStyles&&e.outputStyles.length>0?JSON.stringify(e.outputStyles):null,e.outputStyleBypass??null,e.outputTokens??null)}catch{}}])},933762,e=>{e.v(s=>Promise.all(["server/chunks/[root-of-the-server]__1gewhnw._.js"].map(s=>e.l(s))).then(()=>s(223764)))},136388,e=>{e.v(s=>Promise.all(["server/chunks/[root-of-the-server]__17w9vqo._.js","server/chunks/_1x9c0iw._.js","server/chunks/open-sse_config_1rrbh50._.js","server/chunks/src_0wq7v2g._.js","server/chunks/src_1wuy3dw._.js","server/chunks/open-sse_1z9kdvh._.js","server/chunks/src_lib_1wb6kq4._.js","server/chunks/src_0x2xa7h._.js","server/chunks/src_lib_db_proxies_ts_0ajwjxa._.js"].map(s=>e.l(s))).then(()=>s(974210)))},833389,e=>{e.v(s=>Promise.all(["server/chunks/_1x9c0iw._.js","server/chunks/open-sse_config_1rrbh50._.js","server/chunks/src_lib_1wb6kq4._.js","server/chunks/src_0wq7v2g._.js","server/chunks/[root-of-the-server]__1gesd81._.js","server/chunks/src_1wuy3dw._.js","server/chunks/src_lib_db_proxies_ts_0ajwjxa._.js","server/chunks/src_0x2xa7h._.js","server/chunks/src_lib_db_1jw9mwb._.js","server/chunks/open-sse_1z9kdvh._.js"].map(s=>e.l(s))).then(()=>s(543125)))}];

//# sourceMappingURL=%5Broot-of-the-server%5D__16cgxj4._.js.map