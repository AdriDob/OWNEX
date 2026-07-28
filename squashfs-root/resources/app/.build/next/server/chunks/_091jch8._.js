module.exports=[161002,s=>{"use strict";s.s(["formatCost",0,function(s){let e=Number(s||0);return Number.isFinite(e)&&0!==e?e<.01?`$${e.toFixed(6)}`:e<1?`$${e.toFixed(4)}`:`$${e.toFixed(2)}`:"$0.00"},"formatResetCountdown",0,function(s){if(!s)return null;let e="number"==typeof s?s:new Date(s).getTime();if(isNaN(e))return null;let r=e-Date.now();if(r<=0)return null;let _=Math.floor(r/1e3),n=Math.floor(_/3600),t=Math.floor(_%3600/60),c=_%60;return n>0?`${n}h ${t}m`:t>0?`${t}m ${c}s`:`${c}s`},"safePercentage",0,function(s){return"number"==typeof s&&isFinite(s)?s:void 0}])},643622,s=>{"use strict";let e={tested:0,alive:0};s.s(["getRelayProbeStats",0,function(){return{...e}},"recordRelayProbe",0,function(s){e={tested:e.tested+1,alive:e.alive+ +!!s}},"resetRelayProbeStats",0,function(){e={tested:0,alive:0}}])},154945,s=>{"use strict";s.s(["buildPresetUnifiedSource",0,function(s){let{sinceIso:e,untilIso:r,rawCutoffDate:_,apiKeyWhere:n,apiKeyParams:t}=s,c=e?.split("T")[0]??null,o=(!c||c<_)&&!n,u={},a=[];o?(a.push("timestamp >= @presetRawCutoff"),u.presetRawCutoff=_):e&&(a.push("timestamp >= @presetSince"),u.presetSince=e),n&&(a.push(n),Object.assign(u,t));let i=a.length>0?`WHERE ${a.join(" AND ")}`:"",h=[];o&&(e&&(h.push("date >= @presetSinceDate"),u.presetSinceDate=c),h.push("date < @presetRawCutoffDate"),u.presetRawCutoffDate=_);let k=h.length>0?`WHERE ${h.join(" AND ")}`:"";return{unifiedSource:o?`(
        SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${i}
        UNION ALL
        SELECT
          date || 'T12:00:00.000Z' as timestamp,
          provider, model,
          'standard' as service_tier,
          total_input_tokens as tokens_input,
          total_output_tokens as tokens_output,
          0 as tokens_cache_read,
          0 as tokens_cache_creation,
          0 as tokens_reasoning
        FROM daily_usage_summary
        ${k}
      )`:`(SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${i}
      )`,unifiedParams:u}},"buildUnifiedSource",0,function(s){let{sinceIso:e,untilIso:r,rawCutoffDate:_,apiKeyWhere:n,apiKeyParams:t}=s,c=e?.split("T")[0]??null,o=(!c||c<_)&&!n,u={},a=[];o?(a.push("timestamp >= @rawCutoff"),u.rawCutoff=_):e&&(a.push("timestamp >= @since"),u.since=e),r&&(a.push("timestamp <= @until"),u.until=r),n&&(a.push(n),Object.assign(u,t));let i=a.length>0?`WHERE ${a.join(" AND ")}`:"",h=[];o&&(e&&(h.push("date >= @sinceDate"),u.sinceDate=c),r&&(h.push("date <= @untilDate"),u.untilDate=r.split("T")[0]),h.push("date < @rawCutoffDate"),u.rawCutoffDate=_);let k=h.length>0?`WHERE ${h.join(" AND ")}`:"";return{unifiedSource:o?`(
        SELECT
          timestamp,
          provider,
          model,
          tokens_input,
          tokens_output,
          tokens_cache_read,
          tokens_cache_creation,
          tokens_reasoning,
          service_tier,
          success,
          latency_ms,
          connection_id,
          api_key_id,
          api_key_name
        FROM usage_history
        ${i}
        UNION ALL
        SELECT
          date || 'T12:00:00.000Z' as timestamp,
          provider,
          model,
          total_input_tokens as tokens_input,
          total_output_tokens as tokens_output,
          0 as tokens_cache_read,
          0 as tokens_cache_creation,
          0 as tokens_reasoning,
          'standard' as service_tier,
          1 as success,
          0 as latency_ms,
          NULL as connection_id,
          NULL as api_key_id,
          NULL as api_key_name
        FROM daily_usage_summary
        ${k}
       )`:`(SELECT
          timestamp, provider, model,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning,
          service_tier, success, latency_ms,
          connection_id, api_key_id, api_key_name
        FROM usage_history
        ${i}
       )`,unifiedParams:u}}])},500929,s=>{s.v(e=>Promise.all(["server/chunks/[root-of-the-server]__0e014b0._.js"].map(e=>s.l(e))).then(()=>e(854474)))},606102,s=>{s.v(e=>Promise.all(["server/chunks/[root-of-the-server]__1f-xq1x._.js","server/chunks/_19fi1-5._.js","server/chunks/[root-of-the-server]__1sdgs2d._.js","server/chunks/_1ajfw-k._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/open-sse_1exxloq._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_1akg35a._.js"].map(e=>s.l(e))).then(()=>e(548941)))},789543,s=>{s.v(e=>Promise.all(["server/chunks/_0kktc4f._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/_19fi1-5._.js","server/chunks/[root-of-the-server]__1sdgs2d._.js","server/chunks/_1ajfw-k._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_1akg35a._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/open-sse_1exxloq._.js","server/chunks/[root-of-the-server]__1we3fgj._.js","server/chunks/src_lib_db_1cebbnr._.js"].map(e=>s.l(e))).then(()=>e(385498)))},379812,s=>{s.v(e=>Promise.all(["server/chunks/[root-of-the-server]__0a6_b_f._.js"].map(e=>s.l(e))).then(()=>e(901686)))},49794,s=>{s.v(e=>Promise.all(["server/chunks/src_shared_1mb3ron._.js","server/chunks/src_shared_constants_pricing_ts_1y5sqnp._.js"].map(e=>s.l(e))).then(()=>e(404503)))},727431,s=>{s.v(e=>Promise.all(["server/chunks/_0_cp8bf._.js","server/chunks/src_1iie02i._.js","server/chunks/_19fi1-5._.js","server/chunks/_0o13n7k._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/src_0xeelr4._.js","server/chunks/src_18gpj41._.js","server/chunks/[root-of-the-server]__1sdgs2d._.js","server/chunks/src_lib_tokenHealthCheck_ts_0xts4cn._.js","server/chunks/_0oai2qq._.js","server/chunks/_1ajfw-k._.js","server/chunks/open-sse_services_1mmgcms._.js","server/chunks/src_lib_db_0uaekd0._.js","server/chunks/src_lib_db_0t9xnky._.js","server/chunks/_07pfj6-._.js","server/chunks/src_1akg35a._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/open-sse_1exxloq._.js","server/chunks/_1y-5a1f._.js","server/chunks/node_modules_undici_20gvchs._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_lib_db_0l4-ciw._.js","server/chunks/src_lib_0ihae3b._.js","server/chunks/[root-of-the-server]__04qa1zo._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/[root-of-the-server]__15tq_jl._.js","server/chunks/_1j7s7oh._.js"].map(e=>s.l(e))).then(()=>e(791588)))},73006,s=>{s.v(e=>Promise.all(["server/chunks/_0psf9mr._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/_19fi1-5._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/_1ajfw-k._.js","server/chunks/[root-of-the-server]__1we3fgj._.js","server/chunks/src_1akg35a._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/src_lib_db_0uaekd0._.js","server/chunks/[root-of-the-server]__1sdgs2d._.js","server/chunks/open-sse_1exxloq._.js","server/chunks/src_lib_db_1cebbnr._.js"].map(e=>s.l(e))).then(()=>e(910263)))},33456,s=>{s.v(e=>Promise.all(["server/chunks/[root-of-the-server]__1ubz91d._.js","server/chunks/_19fi1-5._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/_1ajfw-k._.js","server/chunks/src_1iie02i._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/_1y-5a1f._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/src_lib_db_0l4-ciw._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/src_18gpj41._.js","server/chunks/node_modules_undici_20gvchs._.js","server/chunks/_07pfj6-._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/[root-of-the-server]__1sdgs2d._.js","server/chunks/src_lib_0ihae3b._.js","server/chunks/src_lib_db_0uaekd0._.js","server/chunks/src_lib_db_0t9xnky._.js","server/chunks/_0oai2qq._.js","server/chunks/src_1akg35a._.js","server/chunks/[root-of-the-server]__0mbiv9n._.js","server/chunks/open-sse_1exxloq._.js"].map(e=>s.l(e))).then(()=>e(675308)))},927129,s=>{s.v(e=>Promise.all(["server/chunks/src_lib_db_1wqtkru._.js"].map(e=>s.l(e))).then(()=>e(403122)))},263404,s=>{s.v(e=>Promise.all(["server/chunks/_0kgl1lq._.js"].map(e=>s.l(e))).then(()=>e(710876)))},579042,s=>{s.v(e=>Promise.all(["server/chunks/[root-of-the-server]__0q0aafu._.js"].map(e=>s.l(e))).then(()=>e(65448)))},589812,s=>{s.v(e=>Promise.all(["server/chunks/src_1q57rcs._.js","server/chunks/[root-of-the-server]__1m1ci6q._.js","server/chunks/[root-of-the-server]__1sdgs2d._.js","server/chunks/src_1akg35a._.js"].map(e=>s.l(e))).then(()=>e(439951)))},123492,s=>{s.v(e=>Promise.all(["server/chunks/_19fi1-5._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/[root-of-the-server]__0e6xwrc._.js","server/chunks/[root-of-the-server]__1sdgs2d._.js","server/chunks/_1ajfw-k._.js","server/chunks/_0_dl02g._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_1akg35a._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/[root-of-the-server]__1we3fgj._.js","server/chunks/open-sse_1exxloq._.js","server/chunks/src_lib_db_0pm239y._.js"].map(e=>s.l(e))).then(()=>e(20954)))}];

//# sourceMappingURL=_091jch8._.js.map