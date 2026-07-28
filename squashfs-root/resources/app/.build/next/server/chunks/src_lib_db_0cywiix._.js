module.exports=[643622,e=>{"use strict";let t={tested:0,alive:0};e.s(["getRelayProbeStats",0,function(){return{...t}},"recordRelayProbe",0,function(e){t={tested:t.tested+1,alive:t.alive+ +!!e}},"resetRelayProbeStats",0,function(){t={tested:0,alive:0}}])},154945,e=>{"use strict";e.s(["buildPresetUnifiedSource",0,function(e){let{sinceIso:t,untilIso:s,rawCutoffDate:a,apiKeyWhere:n,apiKeyParams:i}=e,o=t?.split("T")[0]??null,r=(!o||o<a)&&!n,_={},u=[];r?(u.push("timestamp >= @presetRawCutoff"),_.presetRawCutoff=a):t&&(u.push("timestamp >= @presetSince"),_.presetSince=t),n&&(u.push(n),Object.assign(_,i));let c=u.length>0?`WHERE ${u.join(" AND ")}`:"",p=[];r&&(t&&(p.push("date >= @presetSinceDate"),_.presetSinceDate=o),p.push("date < @presetRawCutoffDate"),_.presetRawCutoffDate=a);let d=p.length>0?`WHERE ${p.join(" AND ")}`:"";return{unifiedSource:r?`(
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
        ${d}
      )`:`(SELECT timestamp, provider, model, service_tier,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning
        FROM usage_history
        ${c}
      )`,unifiedParams:_}},"buildUnifiedSource",0,function(e){let{sinceIso:t,untilIso:s,rawCutoffDate:a,apiKeyWhere:n,apiKeyParams:i}=e,o=t?.split("T")[0]??null,r=(!o||o<a)&&!n,_={},u=[];r?(u.push("timestamp >= @rawCutoff"),_.rawCutoff=a):t&&(u.push("timestamp >= @since"),_.since=t),s&&(u.push("timestamp <= @until"),_.until=s),n&&(u.push(n),Object.assign(_,i));let c=u.length>0?`WHERE ${u.join(" AND ")}`:"",p=[];r&&(t&&(p.push("date >= @sinceDate"),_.sinceDate=o),s&&(p.push("date <= @untilDate"),_.untilDate=s.split("T")[0]),p.push("date < @rawCutoffDate"),_.rawCutoffDate=a);let d=p.length>0?`WHERE ${p.join(" AND ")}`:"";return{unifiedSource:r?`(
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
        ${d}
       )`:`(SELECT
          timestamp, provider, model,
          tokens_input, tokens_output,
          tokens_cache_read, tokens_cache_creation, tokens_reasoning,
          service_tier, success, latency_ms,
          connection_id, api_key_id, api_key_name
        FROM usage_history
        ${c}
       )`,unifiedParams:_}}])}];

//# sourceMappingURL=src_lib_db_0cywiix._.js.map