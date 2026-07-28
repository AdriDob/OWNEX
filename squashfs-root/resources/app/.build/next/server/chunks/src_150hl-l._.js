module.exports=[836571,e=>{"use strict";e.s(["formatCost",0,function(e){let t=Number(e||0);return Number.isFinite(t)&&0!==t?t<.01?`$${t.toFixed(6)}`:t<1?`$${t.toFixed(4)}`:`$${t.toFixed(2)}`:"$0.00"},"formatResetCountdown",0,function(e){if(!e)return null;let t="number"==typeof e?e:new Date(e).getTime();if(isNaN(t))return null;let i=t-Date.now();if(i<=0)return null;let s=Math.floor(i/1e3),n=Math.floor(s/3600),a=Math.floor(s%3600/60),o=s%60;return n>0?`${n}h ${a}m`:a>0?`${a}m ${o}s`:`${o}s`}])},203203,e=>{"use strict";e.s(["buildPresetUnifiedSource",0,function(e){let{sinceIso:t,untilIso:i,rawCutoffDate:s,apiKeyWhere:n,apiKeyParams:a}=e,o=t?.split("T")[0]??null,r=(!o||o<s)&&!n,u={},c=[];r?(c.push("timestamp >= @presetRawCutoff"),u.presetRawCutoff=s):t&&(c.push("timestamp >= @presetSince"),u.presetSince=t),n&&(c.push(n),Object.assign(u,a));let _=c.length>0?`WHERE ${c.join(" AND ")}`:"",d=[];r&&(t&&(d.push("date >= @presetSinceDate"),u.presetSinceDate=o),d.push("date < @presetRawCutoffDate"),u.presetRawCutoffDate=s);let p=d.length>0?`WHERE ${d.join(" AND ")}`:"";return{unifiedSource:r?`(
        SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${_}
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
        ${p}
      )`:`(SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${_}
      )`,unifiedParams:u}},"buildUnifiedSource",0,function(e){let{sinceIso:t,untilIso:i,rawCutoffDate:s,apiKeyWhere:n,apiKeyParams:a}=e,o=t?.split("T")[0]??null,r=(!o||o<s)&&!n,u={},c=[];r?(c.push("timestamp >= @rawCutoff"),u.rawCutoff=s):t&&(c.push("timestamp >= @since"),u.since=t),i&&(c.push("timestamp <= @until"),u.until=i),n&&(c.push(n),Object.assign(u,a));let _=c.length>0?`WHERE ${c.join(" AND ")}`:"",d=[];r&&(t&&(d.push("date >= @sinceDate"),u.sinceDate=o),i&&(d.push("date <= @untilDate"),u.untilDate=i.split("T")[0]),d.push("date < @rawCutoffDate"),u.rawCutoffDate=s);let p=d.length>0?`WHERE ${d.join(" AND ")}`:"";return{unifiedSource:r?`(
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
        ${_}
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
        ${p}
       )`:`(SELECT
          timestamp, provider, model,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning,
          service_tier, success, latency_ms,
          connection_id, api_key_id, api_key_name
        FROM usage_history
        ${_}
       )`,unifiedParams:u}}])},664958,e=>{"use strict";let t={tested:0,alive:0};e.s(["getRelayProbeStats",0,function(){return{...t}},"recordRelayProbe",0,function(e){t={tested:t.tested+1,alive:t.alive+ +!!e}},"resetRelayProbeStats",0,function(){t={tested:0,alive:0}}])},521710,e=>e.a(async(t,i)=>{try{var s=e.i(265935),n=e.i(261574),a=e.i(307682);e.i(6930),e.i(836571),e.i(557769),e.i(796800),e.i(342507),e.i(229122),e.i(359624),e.i(839193),e.i(660623),e.i(53671),e.i(203119),e.i(542876),e.i(376369);var o=e.i(298422);e.i(463602);var r=e.i(141833);e.i(410701),e.i(267365),e.i(825538),e.i(223194),e.i(109536);var u=e.i(655734);e.i(130521),e.i(658112),e.i(510864),e.i(33900),e.i(825849),e.i(788468),e.i(912386),e.i(110002),e.i(188356),e.i(689724),e.i(620561),e.i(104472),e.i(653900),e.i(91973),e.i(490484),e.i(389769),e.i(504525),e.i(63477),e.i(423421),e.i(163971),e.i(584993),e.i(53906),e.i(525503),e.i(47894),e.i(330837),e.i(162186),e.i(897325),e.i(797640),e.i(829778),e.i(316020),e.i(115205);var c=e.i(90896);e.i(52530),e.i(807741),e.i(269032),e.i(218550),e.i(675367),e.i(255329),e.i(472139),e.i(581904),e.i(976974),e.i(979158),e.i(846702),e.i(513586),e.i(203203),e.i(633274),e.i(657986),e.i(997721),e.i(605555),e.i(164456),e.i(976119),e.i(664958);var _=t([s,n,o,c]);[s,n,o,c]=_.then?(await _)():_,e.s(["getCachedSettings",()=>u.getCachedSettings,"getPricingForModel",()=>r.getPricingForModel,"getProviderConnections",()=>n.getProviderConnections,"getProviderNodeById",()=>a.getProviderNodeById,"getSettings",()=>o.getSettings]),i()}catch(e){i(e)}},!1)];

//# sourceMappingURL=src_150hl-l._.js.map