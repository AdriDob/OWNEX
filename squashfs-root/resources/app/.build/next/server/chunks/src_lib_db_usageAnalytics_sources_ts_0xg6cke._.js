module.exports=[154945,e=>{"use strict";e.s(["buildPresetUnifiedSource",0,function(e){let{sinceIso:t,untilIso:s,rawCutoffDate:a,apiKeyWhere:n,apiKeyParams:i}=e,o=t?.split("T")[0]??null,_=(!o||o<a)&&!n,u={},r=[];_?(r.push("timestamp >= @presetRawCutoff"),u.presetRawCutoff=a):t&&(r.push("timestamp >= @presetSince"),u.presetSince=t),n&&(r.push(n),Object.assign(u,i));let c=r.length>0?`WHERE ${r.join(" AND ")}`:"",p=[];_&&(t&&(p.push("date >= @presetSinceDate"),u.presetSinceDate=o),p.push("date < @presetRawCutoffDate"),u.presetRawCutoffDate=a);let d=p.length>0?`WHERE ${p.join(" AND ")}`:"";return{unifiedSource:_?`(
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
      )`,unifiedParams:u}},"buildUnifiedSource",0,function(e){let{sinceIso:t,untilIso:s,rawCutoffDate:a,apiKeyWhere:n,apiKeyParams:i}=e,o=t?.split("T")[0]??null,_=(!o||o<a)&&!n,u={},r=[];_?(r.push("timestamp >= @rawCutoff"),u.rawCutoff=a):t&&(r.push("timestamp >= @since"),u.since=t),s&&(r.push("timestamp <= @until"),u.until=s),n&&(r.push(n),Object.assign(u,i));let c=r.length>0?`WHERE ${r.join(" AND ")}`:"",p=[];_&&(t&&(p.push("date >= @sinceDate"),u.sinceDate=o),s&&(p.push("date <= @untilDate"),u.untilDate=s.split("T")[0]),p.push("date < @rawCutoffDate"),u.rawCutoffDate=a);let d=p.length>0?`WHERE ${p.join(" AND ")}`:"";return{unifiedSource:_?`(
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
       )`,unifiedParams:u}}])}];

//# sourceMappingURL=src_lib_db_usageAnalytics_sources_ts_0xg6cke._.js.map