module.exports=[161002,e=>{"use strict";e.s(["formatCost",0,function(e){let s=Number(e||0);return Number.isFinite(s)&&0!==s?s<.01?`$${s.toFixed(6)}`:s<1?`$${s.toFixed(4)}`:`$${s.toFixed(2)}`:"$0.00"},"formatResetCountdown",0,function(e){if(!e)return null;let s="number"==typeof e?e:new Date(e).getTime();if(isNaN(s))return null;let r=s-Date.now();if(r<=0)return null;let t=Math.floor(r/1e3),_=Math.floor(t/3600),n=Math.floor(t%3600/60),c=t%60;return _>0?`${_}h ${n}m`:n>0?`${n}m ${c}s`:`${c}s`},"safePercentage",0,function(e){return"number"==typeof e&&isFinite(e)?e:void 0}])},643622,e=>{"use strict";let s={tested:0,alive:0};e.s(["getRelayProbeStats",0,function(){return{...s}},"recordRelayProbe",0,function(e){s={tested:s.tested+1,alive:s.alive+ +!!e}},"resetRelayProbeStats",0,function(){s={tested:0,alive:0}}])},154945,e=>{"use strict";e.s(["buildPresetUnifiedSource",0,function(e){let{sinceIso:s,untilIso:r,rawCutoffDate:t,apiKeyWhere:_,apiKeyParams:n}=e,c=s?.split("T")[0]??null,i=(!c||c<t)&&!_,a={},o=[];i?(o.push("timestamp >= @presetRawCutoff"),a.presetRawCutoff=t):s&&(o.push("timestamp >= @presetSince"),a.presetSince=s),_&&(o.push(_),Object.assign(a,n));let u=o.length>0?`WHERE ${o.join(" AND ")}`:"",h=[];i&&(s&&(h.push("date >= @presetSinceDate"),a.presetSinceDate=c),h.push("date < @presetRawCutoffDate"),a.presetRawCutoffDate=t);let l=h.length>0?`WHERE ${h.join(" AND ")}`:"";return{unifiedSource:i?`(
        SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${u}
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
        ${l}
      )`:`(SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${u}
      )`,unifiedParams:a}},"buildUnifiedSource",0,function(e){let{sinceIso:s,untilIso:r,rawCutoffDate:t,apiKeyWhere:_,apiKeyParams:n}=e,c=s?.split("T")[0]??null,i=(!c||c<t)&&!_,a={},o=[];i?(o.push("timestamp >= @rawCutoff"),a.rawCutoff=t):s&&(o.push("timestamp >= @since"),a.since=s),r&&(o.push("timestamp <= @until"),a.until=r),_&&(o.push(_),Object.assign(a,n));let u=o.length>0?`WHERE ${o.join(" AND ")}`:"",h=[];i&&(s&&(h.push("date >= @sinceDate"),a.sinceDate=c),r&&(h.push("date <= @untilDate"),a.untilDate=r.split("T")[0]),h.push("date < @rawCutoffDate"),a.rawCutoffDate=t);let l=h.length>0?`WHERE ${h.join(" AND ")}`:"";return{unifiedSource:i?`(
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
        ${u}
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
        ${l}
       )`:`(SELECT
          timestamp, provider, model,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning,
          service_tier, success, latency_ms,
          connection_id, api_key_id, api_key_name
        FROM usage_history
        ${u}
       )`,unifiedParams:a}}])},49794,e=>{e.v(s=>Promise.all(["server/chunks/src_shared_1mb3ron._.js","server/chunks/src_shared_constants_pricing_ts_1y5sqnp._.js"].map(s=>e.l(s))).then(()=>s(404503)))},727431,e=>{e.v(s=>Promise.all(["server/chunks/_0z_enjr._.js","server/chunks/src_1iie02i._.js","server/chunks/_1y-5a1f._.js","server/chunks/src_lib_tokenHealthCheck_ts_0xts4cn._.js","server/chunks/_0o13n7k._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_172x5f9._.js","server/chunks/src_18gpj41._.js","server/chunks/[root-of-the-server]__15tq_jl._.js","server/chunks/src_0xeelr4._.js","server/chunks/_1j7s7oh._.js","server/chunks/node_modules_undici_20gvchs._.js","server/chunks/src_lib_0ihae3b._.js","server/chunks/open-sse_services_1mmgcms._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_lib_db_0uaekd0._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/_07pfj6-._.js","server/chunks/[root-of-the-server]__0mz2rpp._.js","server/chunks/src_lib_db_0t9xnky._.js","server/chunks/src_lib_db_0pm239y._.js"].map(s=>e.l(s))).then(()=>s(791588)))},73006,e=>{e.v(s=>Promise.all(["server/chunks/_1tbfc4v._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/[root-of-the-server]__1q5ou7b._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_lib_db_0uaekd0._.js","server/chunks/src_lib_db_1k7t86u._.js"].map(s=>e.l(s))).then(()=>s(910263)))},33456,e=>{e.v(s=>Promise.all(["server/chunks/[root-of-the-server]__15a3kf3._.js","server/chunks/src_172x5f9._.js","server/chunks/src_1iie02i._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/src_18gpj41._.js","server/chunks/_1y-5a1f._.js","server/chunks/_07pfj6-._.js","server/chunks/node_modules_undici_20gvchs._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/src_lib_db_0t9xnky._.js","server/chunks/src_lib_db_0uaekd0._.js","server/chunks/[root-of-the-server]__10r_6fh._.js","server/chunks/src_lib_0ihae3b._.js"].map(s=>e.l(s))).then(()=>s(675308)))},927129,e=>{e.v(e=>Promise.resolve().then(()=>e(403122)))},263404,e=>{e.v(s=>Promise.all(["server/chunks/_1_btc87._.js"].map(s=>e.l(s))).then(()=>s(710876)))},579042,e=>{e.v(s=>Promise.all(["server/chunks/src_shared_utils_apiKey_ts_1-k4saf._.js"].map(s=>e.l(s))).then(()=>s(65448)))},589812,e=>{e.v(s=>Promise.all(["server/chunks/[root-of-the-server]__059_1fa._.js","server/chunks/src_1iie02i._.js"].map(s=>e.l(s))).then(()=>s(439951)))},123492,e=>{e.v(s=>Promise.all(["server/chunks/_0a96jor._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/[root-of-the-server]__1szx-un._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/[root-of-the-server]__1q5ou7b._.js"].map(s=>e.l(s))).then(()=>s(20954)))}];

//# sourceMappingURL=_1nrfmj9._.js.map