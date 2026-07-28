module.exports=[161002,e=>{"use strict";e.s(["formatCost",0,function(e){let t=Number(e||0);return Number.isFinite(t)&&0!==t?t<.01?`$${t.toFixed(6)}`:t<1?`$${t.toFixed(4)}`:`$${t.toFixed(2)}`:"$0.00"},"formatResetCountdown",0,function(e){if(!e)return null;let t="number"==typeof e?e:new Date(e).getTime();if(isNaN(t))return null;let s=t-Date.now();if(s<=0)return null;let n=Math.floor(s/1e3),a=Math.floor(n/3600),i=Math.floor(n%3600/60),o=n%60;return a>0?`${a}h ${i}m`:i>0?`${i}m ${o}s`:`${o}s`},"safePercentage",0,function(e){return"number"==typeof e&&isFinite(e)?e:void 0}])},643622,e=>{"use strict";let t={tested:0,alive:0};e.s(["getRelayProbeStats",0,function(){return{...t}},"recordRelayProbe",0,function(e){t={tested:t.tested+1,alive:t.alive+ +!!e}},"resetRelayProbeStats",0,function(){t={tested:0,alive:0}}])},154945,e=>{"use strict";e.s(["buildPresetUnifiedSource",0,function(e){let{sinceIso:t,untilIso:s,rawCutoffDate:n,apiKeyWhere:a,apiKeyParams:i}=e,o=t?.split("T")[0]??null,r=(!o||o<n)&&!a,u={},_=[];r?(_.push("timestamp >= @presetRawCutoff"),u.presetRawCutoff=n):t&&(_.push("timestamp >= @presetSince"),u.presetSince=t),a&&(_.push(a),Object.assign(u,i));let c=_.length>0?`WHERE ${_.join(" AND ")}`:"",p=[];r&&(t&&(p.push("date >= @presetSinceDate"),u.presetSinceDate=o),p.push("date < @presetRawCutoffDate"),u.presetRawCutoffDate=n);let l=p.length>0?`WHERE ${p.join(" AND ")}`:"";return{unifiedSource:r?`(
        SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${c}
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
        ${c}
      )`,unifiedParams:u}},"buildUnifiedSource",0,function(e){let{sinceIso:t,untilIso:s,rawCutoffDate:n,apiKeyWhere:a,apiKeyParams:i}=e,o=t?.split("T")[0]??null,r=(!o||o<n)&&!a,u={},_=[];r?(_.push("timestamp >= @rawCutoff"),u.rawCutoff=n):t&&(_.push("timestamp >= @since"),u.since=t),s&&(_.push("timestamp <= @until"),u.until=s),a&&(_.push(a),Object.assign(u,i));let c=_.length>0?`WHERE ${_.join(" AND ")}`:"",p=[];r&&(t&&(p.push("date >= @sinceDate"),u.sinceDate=o),s&&(p.push("date <= @untilDate"),u.untilDate=s.split("T")[0]),p.push("date < @rawCutoffDate"),u.rawCutoffDate=n);let l=p.length>0?`WHERE ${p.join(" AND ")}`:"";return{unifiedSource:r?`(
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
        ${c}
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
        ${c}
       )`,unifiedParams:u}}])}];

//# sourceMappingURL=src_1ak1bsc._.js.map