module.exports=[161002,e=>{"use strict";e.s(["formatCost",0,function(e){let s=Number(e||0);return Number.isFinite(s)&&0!==s?s<.01?`$${s.toFixed(6)}`:s<1?`$${s.toFixed(4)}`:`$${s.toFixed(2)}`:"$0.00"},"formatResetCountdown",0,function(e){if(!e)return null;let s="number"==typeof e?e:new Date(e).getTime();if(isNaN(s))return null;let r=s-Date.now();if(r<=0)return null;let _=Math.floor(r/1e3),t=Math.floor(_/3600),n=Math.floor(_%3600/60),c=_%60;return t>0?`${t}h ${n}m`:n>0?`${n}m ${c}s`:`${c}s`},"safePercentage",0,function(e){return"number"==typeof e&&isFinite(e)?e:void 0}])},643622,e=>{"use strict";let s={tested:0,alive:0};e.s(["getRelayProbeStats",0,function(){return{...s}},"recordRelayProbe",0,function(e){s={tested:s.tested+1,alive:s.alive+ +!!e}},"resetRelayProbeStats",0,function(){s={tested:0,alive:0}}])},154945,e=>{"use strict";e.s(["buildPresetUnifiedSource",0,function(e){let{sinceIso:s,untilIso:r,rawCutoffDate:_,apiKeyWhere:t,apiKeyParams:n}=e,c=s?.split("T")[0]??null,i=(!c||c<_)&&!t,o={},u=[];i?(u.push("timestamp >= @presetRawCutoff"),o.presetRawCutoff=_):s&&(u.push("timestamp >= @presetSince"),o.presetSince=s),t&&(u.push(t),Object.assign(o,n));let a=u.length>0?`WHERE ${u.join(" AND ")}`:"",h=[];i&&(s&&(h.push("date >= @presetSinceDate"),o.presetSinceDate=c),h.push("date < @presetRawCutoffDate"),o.presetRawCutoffDate=_);let k=h.length>0?`WHERE ${h.join(" AND ")}`:"";return{unifiedSource:i?`(
        SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${a}
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
        ${a}
      )`,unifiedParams:o}},"buildUnifiedSource",0,function(e){let{sinceIso:s,untilIso:r,rawCutoffDate:_,apiKeyWhere:t,apiKeyParams:n}=e,c=s?.split("T")[0]??null,i=(!c||c<_)&&!t,o={},u=[];i?(u.push("timestamp >= @rawCutoff"),o.rawCutoff=_):s&&(u.push("timestamp >= @since"),o.since=s),r&&(u.push("timestamp <= @until"),o.until=r),t&&(u.push(t),Object.assign(o,n));let a=u.length>0?`WHERE ${u.join(" AND ")}`:"",h=[];i&&(s&&(h.push("date >= @sinceDate"),o.sinceDate=c),r&&(h.push("date <= @untilDate"),o.untilDate=r.split("T")[0]),h.push("date < @rawCutoffDate"),o.rawCutoffDate=_);let k=h.length>0?`WHERE ${h.join(" AND ")}`:"";return{unifiedSource:i?`(
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
        ${a}
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
        ${a}
       )`,unifiedParams:o}}])},379812,e=>{e.v(e=>Promise.resolve().then(()=>e(901686)))},49794,e=>{e.v(s=>Promise.all(["server/chunks/src_shared_1mb3ron._.js","server/chunks/src_shared_constants_pricing_ts_1y5sqnp._.js"].map(s=>e.l(s))).then(()=>s(404503)))},727431,e=>{e.v(s=>Promise.all(["server/chunks/_016x8f_._.js","server/chunks/src_1iie02i._.js","server/chunks/_19fi1-5._.js","server/chunks/_1ajfw-k._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/src_0xeelr4._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/_0o13n7k._.js","server/chunks/[root-of-the-server]__136jtfz._.js","server/chunks/src_lib_db_0l4-ciw._.js","server/chunks/src_18gpj41._.js","server/chunks/[root-of-the-server]__15tq_jl._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/node_modules_undici_20gvchs._.js","server/chunks/src_lib_0ihae3b._.js","server/chunks/src_lib_db_0uaekd0._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/_0oai2qq._.js","server/chunks/open-sse_services_1mmgcms._.js","server/chunks/src_lib_tokenHealthCheck_ts_0xts4cn._.js","server/chunks/src_lib_db_0t9xnky._.js","server/chunks/_1z6ap4j._.js","server/chunks/_07pfj6-._.js","server/chunks/_1j7s7oh._.js","server/chunks/open-sse_1exxloq._.js"].map(s=>e.l(s))).then(()=>s(791588)))},73006,e=>{e.v(s=>Promise.all(["server/chunks/_0ti2n3u._.js","server/chunks/_19fi1-5._.js","server/chunks/src_lib_db_0uaekd0._.js","server/chunks/_1ajfw-k._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/open-sse_1exxloq._.js","server/chunks/_0oai2qq._.js"].map(s=>e.l(s))).then(()=>s(910263)))},33456,e=>{e.v(s=>Promise.all(["server/chunks/[root-of-the-server]__0mi_d0t._.js","server/chunks/_19fi1-5._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/src_lib_db_0l4-ciw._.js","server/chunks/src_1iie02i._.js","server/chunks/_1ajfw-k._.js","server/chunks/[root-of-the-server]__136jtfz._.js","server/chunks/src_lib_db_0uaekd0._.js","server/chunks/src_18gpj41._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/_07pfj6-._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/open-sse_1exxloq._.js","server/chunks/_0oai2qq._.js","server/chunks/node_modules_undici_20gvchs._.js","server/chunks/src_lib_db_0t9xnky._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/_1ny9p4g._.js","server/chunks/src_lib_0ihae3b._.js"].map(s=>e.l(s))).then(()=>s(675308)))},927129,e=>{e.v(e=>Promise.resolve().then(()=>e(403122)))},263404,e=>{e.v(s=>Promise.all(["server/chunks/_0nxyffi._.js"].map(s=>e.l(s))).then(()=>s(710876)))},579042,e=>{e.v(s=>Promise.all(["server/chunks/src_shared_utils_apiKey_ts_1-k4saf._.js"].map(s=>e.l(s))).then(()=>s(65448)))},589812,e=>{e.v(s=>Promise.all(["server/chunks/src_1q57rcs._.js","server/chunks/[root-of-the-server]__1gfqkgj._.js"].map(s=>e.l(s))).then(()=>s(439951)))},123492,e=>{e.v(s=>Promise.all(["server/chunks/_19fi1-5._.js","server/chunks/_1ajfw-k._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/_0oai2qq._.js","server/chunks/[root-of-the-server]__0wzssvf._.js","server/chunks/open-sse_1exxloq._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/_0_dl02g._.js"].map(s=>e.l(s))).then(()=>s(20954)))}];

//# sourceMappingURL=_1dr3aba._.js.map