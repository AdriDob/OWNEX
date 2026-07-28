module.exports=[666680,(a,b,c)=>{b.exports=a.x("node:crypto",()=>require("node:crypto"))},577018,a=>{"use strict";let b=new Set(["host","connection","content-length","keep-alive","proxy-connection","transfer-encoding","te","trailer","upgrade"].map(a=>a.toLowerCase()));["authorization","x-api-key","x-goog-api-key","api-key","cookie"].map(a=>a.toLowerCase()),a.s(["isForbiddenUpstreamHeaderName",0,function(a){return b.has(String(a).trim().toLowerCase())}])},148099,a=>{"use strict";a.s(["formatCost",0,function(a){let b=Number(a||0);return Number.isFinite(b)&&0!==b?b<.01?`$${b.toFixed(6)}`:b<1?`$${b.toFixed(4)}`:`$${b.toFixed(2)}`:"$0.00"},"formatResetCountdown",0,function(a){if(!a)return null;let b="number"==typeof a?a:new Date(a).getTime();if(isNaN(b))return null;let c=b-Date.now();if(c<=0)return null;let d=Math.floor(c/1e3),e=Math.floor(d/3600),f=Math.floor(d%3600/60),g=d%60;return e>0?`${e}h ${f}m`:f>0?`${f}m ${g}s`:`${g}s`}])},73810,a=>{"use strict";a.s(["buildPresetUnifiedSource",0,function(a){let{sinceIso:b,untilIso:c,rawCutoffDate:d,apiKeyWhere:e,apiKeyParams:f}=a,g=b?.split("T")[0]??null,h=(!g||g<d)&&!e,i={},j=[];h?(j.push("timestamp >= @presetRawCutoff"),i.presetRawCutoff=d):b&&(j.push("timestamp >= @presetSince"),i.presetSince=b),e&&(j.push(e),Object.assign(i,f));let k=j.length>0?`WHERE ${j.join(" AND ")}`:"",l=[];h&&(b&&(l.push("date >= @presetSinceDate"),i.presetSinceDate=g),l.push("date < @presetRawCutoffDate"),i.presetRawCutoffDate=d);let m=l.length>0?`WHERE ${l.join(" AND ")}`:"";return{unifiedSource:h?`(
        SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${k}
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
        ${m}
      )`:`(SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${k}
      )`,unifiedParams:i}},"buildUnifiedSource",0,function(a){let{sinceIso:b,untilIso:c,rawCutoffDate:d,apiKeyWhere:e,apiKeyParams:f}=a,g=b?.split("T")[0]??null,h=(!g||g<d)&&!e,i={},j=[];h?(j.push("timestamp >= @rawCutoff"),i.rawCutoff=d):b&&(j.push("timestamp >= @since"),i.since=b),c&&(j.push("timestamp <= @until"),i.until=c),e&&(j.push(e),Object.assign(i,f));let k=j.length>0?`WHERE ${j.join(" AND ")}`:"",l=[];h&&(b&&(l.push("date >= @sinceDate"),i.sinceDate=g),c&&(l.push("date <= @untilDate"),i.untilDate=c.split("T")[0]),l.push("date < @rawCutoffDate"),i.rawCutoffDate=d);let m=l.length>0?`WHERE ${l.join(" AND ")}`:"";return{unifiedSource:h?`(
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
        ${k}
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
        ${m}
       )`:`(SELECT
          timestamp, provider, model,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning,
          service_tier, success, latency_ms,
          connection_id, api_key_id, api_key_name
        FROM usage_history
        ${k}
       )`,unifiedParams:i}}])},950378,a=>{"use strict";let b={tested:0,alive:0};a.s(["getRelayProbeStats",0,function(){return{...b}},"recordRelayProbe",0,function(a){b={tested:b.tested+1,alive:b.alive+ +!!a}},"resetRelayProbeStats",0,function(){b={tested:0,alive:0}}])},87386,a=>a.a(async(b,c)=>{try{var d=a.i(147921),e=a.i(949908),f=a.i(382752);a.i(44148),a.i(148099),a.i(95097),a.i(925352),a.i(913754),a.i(871487),a.i(18294),a.i(364299),a.i(585868),a.i(446801),a.i(518501),a.i(743255),a.i(426720);var g=a.i(215779);a.i(674311);var h=a.i(625699);a.i(241897),a.i(266054),a.i(273294),a.i(606373),a.i(913555);var i=a.i(112496);a.i(651316),a.i(724738),a.i(441114),a.i(132758),a.i(984827),a.i(282178),a.i(431018),a.i(177727),a.i(638132),a.i(784797),a.i(240597),a.i(382140),a.i(393373),a.i(593870),a.i(752258),a.i(220766),a.i(112135),a.i(738242),a.i(97505),a.i(595370),a.i(776279),a.i(199369),a.i(63170),a.i(517267),a.i(796486),a.i(244119),a.i(363270),a.i(17743),a.i(792497),a.i(536134),a.i(226786);var j=a.i(101328);a.i(388292),a.i(86683),a.i(163880),a.i(189484),a.i(730699),a.i(519260),a.i(639367),a.i(27886),a.i(799229),a.i(163772),a.i(489874),a.i(913437),a.i(73810),a.i(227257),a.i(894810),a.i(201277),a.i(100479),a.i(174222),a.i(570481),a.i(950378);var k=b([d,e,g,j]);[d,e,g,j]=k.then?(await k)():k,a.s(["getCachedSettings",()=>i.getCachedSettings,"getPricingForModel",()=>h.getPricingForModel,"getProviderConnections",()=>e.getProviderConnections,"getProviderNodeById",()=>f.getProviderNodeById,"getSettings",()=>g.getSettings]),c()}catch(a){c(a)}},!1),860153,a=>{a.v(a=>Promise.resolve().then(()=>a(112496)))},863206,a=>{a.v(b=>Promise.all(["server/chunks/ssr/_110k8hr._.js"].map(b=>a.l(b))).then(()=>b(954773)))},499674,a=>{a.v(b=>Promise.all(["server/chunks/ssr/src_shared_utils_apiKey_ts_0-a-g4-._.js"].map(b=>a.l(b))).then(()=>b(44403)))},692613,a=>{a.v(b=>Promise.all(["server/chunks/ssr/[root-of-the-server]__0hau6z-._.js","server/chunks/ssr/src_0f_fv0w._.js"].map(b=>a.l(b))).then(()=>b(964639)))},350566,a=>{a.v(b=>Promise.all(["server/chunks/ssr/[root-of-the-server]__11bshmt._.js","server/chunks/ssr/src_1krv4xw._.js","server/chunks/ssr/_1m2fzk5._.js","server/chunks/ssr/src_lib_1ts_4q7._.js"].map(b=>a.l(b))).then(()=>b(981593)))}];

//# sourceMappingURL=%5Broot-of-the-server%5D__1ov-ajg._.js.map