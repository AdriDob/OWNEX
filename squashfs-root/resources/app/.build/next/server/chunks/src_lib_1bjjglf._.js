module.exports=[918521,e=>{"use strict";e.i(899378);var t=e.i(167213);async function o(){let e=(0,t.getUserDatabaseSettings)().aggregation.rawDataRetentionDays,o=new Date;return o.setDate(o.getDate()-e),o.toISOString().split("T")[0]}async function n(){return(0,t.getUserDatabaseSettings)().aggregation.enabled}e.s(["getRawDataCutoffDate",0,o,"isAggregationEnabled",0,n])},662636,e=>{"use strict";e.s(["getAccountDisplayName",0,function(e){if(!e)return"Unknown Account";let t="string"==typeof e.name&&e.name.trim()||"string"==typeof e.displayName&&e.displayName.trim()||"string"==typeof e.email&&e.email.trim();return t||("string"==typeof e.id&&e.id?`Account #${e.id.slice(0,6)}`:"Unknown Account")},"getProviderDisplayName",0,function(e,t){if(t?.name?.trim())return t.name.trim();if(t?.prefix?.trim())return t.prefix.trim();if(!e)return"Unknown Provider";let o=e.match(/^(openai|anthropic)-compatible-(?:chat|responses)-[0-9a-f-]{10,}$/i);return o?`Compatible (${o[1]})`:/^anthropic-compatible-cc-[0-9a-f-]{10,}$/i.test(e)?"CC Compatible":e}])},897114,e=>e.a(async(t,o)=>{try{var n=e.i(899378),s=e.i(125852),a=e.i(27663),i=e.i(662636),r=e.i(15844),c=e.i(918521),_=t([a]);function u(e){return e&&"object"==typeof e&&!Array.isArray(e)?e:{}}function p(e){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let t=Number(e);return Number.isFinite(t)?t:0}return 0}function k(e){return"string"==typeof e?e:""}[a]=_.then?(await _)():_;let m=`
  SUM(request_count) as request_count,
  COALESCE(SUM(tokens_input), 0) as tokens_input,
  COALESCE(SUM(tokens_output), 0) as tokens_output,
  COALESCE(SUM(tokens_cache_read), 0) as tokens_cache_read,
  COALESCE(SUM(tokens_cache_creation), 0) as tokens_cache_creation,
  COALESCE(SUM(tokens_reasoning), 0) as tokens_reasoning,
  COALESCE(SUM(cost_tokens_input), 0) as cost_tokens_input,
  COALESCE(SUM(cost_tokens_output), 0) as cost_tokens_output,
  COALESCE(SUM(cost_tokens_cache_read), 0) as cost_tokens_cache_read,
  COALESCE(SUM(cost_tokens_cache_creation), 0) as cost_tokens_cache_creation,
  COALESCE(SUM(cost_tokens_reasoning), 0) as cost_tokens_reasoning,
  COALESCE(SUM(stored_cost), 0.0) as stored_cost,
  MAX(timestamp) as last_used
`;async function l(e){let t=k(e.provider)||"unknown",o=k(e.model)||"unknown",n=k(e.service_tier)||"standard",s=p(e.stored_cost),a=await (0,r.calculateCost)(t,o,{input:p(e.cost_tokens_input??e.tokens_input),output:p(e.cost_tokens_output??e.tokens_output),cacheRead:p(e.cost_tokens_cache_read??e.tokens_cache_read),cacheCreation:p(e.cost_tokens_cache_creation??e.tokens_cache_creation),reasoning:p(e.cost_tokens_reasoning??e.tokens_reasoning)},{provider:t,serviceTier:n,flatRateAsZero:!0});return s+a}function d(e,t,o,n,s){e.requests+=t,e.promptTokens+=o,e.completionTokens+=n,e.cost+=s}async function E(e,t){if(!e||!t)return{costUsd:0,requests:0};let o=(0,n.getDbInstance)().prepare(`SELECT model,
          COALESCE(SUM(tokens_input), 0) AS input,
          COALESCE(SUM(tokens_output), 0) AS output,
          COALESCE(SUM(tokens_cache_read), 0) AS cacheRead,
          COALESCE(SUM(tokens_cache_creation), 0) AS cacheCreation,
          COALESCE(SUM(tokens_reasoning), 0) AS reasoning,
          COUNT(*) AS requests
       FROM usage_history
       WHERE connection_id = ? AND provider = ? AND success = 1
       GROUP BY model`).all(t,e),s=0,a=0;for(let t of o){a+=Math.max(0,Number(t.requests??0));let o="string"==typeof t.model?t.model:"",n={input:Number(t.input??0),output:Number(t.output??0),cacheRead:Number(t.cacheRead??0),cacheCreation:Number(t.cacheCreation??0),reasoning:Number(t.reasoning??0)};s+=await (0,r.calculateCost)(e,o,n,{provider:e,model:o,flatRateAsZero:!0})}return{costUsd:Math.max(0,s),requests:a}}async function C(){let t=(0,n.getDbInstance)(),o=await (0,c.isAggregationEnabled)(),r=o?await (0,c.getRawDataCutoffDate)():null,_=o?`
    SELECT
      provider,
      model,
      timestamp,
      connection_id,
      api_key_id,
      api_key_name,
      COALESCE(tokens_input, 0) as tokens_input,
      COALESCE(tokens_output, 0) as tokens_output,
      COALESCE(tokens_cache_read, 0) as tokens_cache_read,
      COALESCE(tokens_cache_creation, 0) as tokens_cache_creation,
      COALESCE(tokens_reasoning, 0) as tokens_reasoning,
      COALESCE(tokens_input, 0) as cost_tokens_input,
      COALESCE(tokens_output, 0) as cost_tokens_output,
      COALESCE(tokens_cache_read, 0) as cost_tokens_cache_read,
      COALESCE(tokens_cache_creation, 0) as cost_tokens_cache_creation,
      COALESCE(tokens_reasoning, 0) as cost_tokens_reasoning,
      0.0 as stored_cost,
      COALESCE(service_tier, 'standard') as service_tier,
      1 as request_count
    FROM usage_history
    WHERE DATE(timestamp) >= ?

    UNION ALL

    SELECT
      provider,
      model,
      date || 'T12:00:00.000Z' as timestamp,
      NULL as connection_id,
      NULL as api_key_id,
      NULL as api_key_name,
      COALESCE(total_input_tokens, 0) as tokens_input,
      COALESCE(total_output_tokens, 0) as tokens_output,
      0 as tokens_cache_read,
      0 as tokens_cache_creation,
      0 as tokens_reasoning,
      0 as cost_tokens_input,
      0 as cost_tokens_output,
      0 as cost_tokens_cache_read,
      0 as cost_tokens_cache_creation,
      0 as cost_tokens_reasoning,
      COALESCE(total_cost, 0.0) as stored_cost,
      'standard' as service_tier,
      COALESCE(total_requests, 0) as request_count
    FROM daily_usage_summary
    WHERE date < ?
  `:`
      SELECT
        provider,
        model,
        timestamp,
        connection_id,
        api_key_id,
        api_key_name,
        COALESCE(tokens_input, 0) as tokens_input,
        COALESCE(tokens_output, 0) as tokens_output,
        COALESCE(tokens_cache_read, 0) as tokens_cache_read,
        COALESCE(tokens_cache_creation, 0) as tokens_cache_creation,
        COALESCE(tokens_reasoning, 0) as tokens_reasoning,
        COALESCE(tokens_input, 0) as cost_tokens_input,
        COALESCE(tokens_output, 0) as cost_tokens_output,
        COALESCE(tokens_cache_read, 0) as cost_tokens_cache_read,
        COALESCE(tokens_cache_creation, 0) as cost_tokens_cache_creation,
        COALESCE(tokens_reasoning, 0) as cost_tokens_reasoning,
        0.0 as stored_cost,
        COALESCE(service_tier, 'standard') as service_tier,
        1 as request_count
      FROM usage_history
    `,E=o&&r?[r,r]:[],{getProviderConnections:C}=await e.A(605589),S=[];try{let e=await C();S=Array.isArray(e)?e:[]}catch{}let A={};for(let e of S){let t=u(e),o=k(t.id);o&&(A[o]=k(t.name)||k(t.email)||o)}let g=new Map;try{for(let e of(await (0,s.getApiKeys)()))"string"==typeof e.id&&"string"==typeof e.name&&g.set(e.id,e.name)}catch{}let y=(0,a.getPendingRequests)(),O={totalRequests:0,totalPromptTokens:0,totalCompletionTokens:0,totalCost:0,byProvider:{},byModel:{},byAccount:{},byApiKey:{},last10Minutes:[],pending:y,activeRequests:[]};for(let[e,t]of Object.entries(y.byAccount))for(let[o,n]of Object.entries(t))if(n>0){let t=A[e]||(0,i.getAccountDisplayName)({id:e}),s=o.match(/^(.*) \((.*)\)$/);O.activeRequests.push({model:s?s[1]:o,provider:s?s[2]:"unknown",account:t,count:n})}let L=new Date,h=new Date(6e4*Math.floor(L.getTime()/6e4)),f={};for(let e=0;e<10;e++){let t=new Date(h.getTime()-(9-e)*6e4).getTime();f[t]={requests:0,promptTokens:0,completionTokens:0,cost:0},O.last10Minutes.push(f[t])}let U=new Date(h.getTime()-54e4);for(let e of t.prepare(`
        WITH usage_source AS (${_})
        SELECT provider, model, service_tier, ${m}
        FROM usage_source
        GROUP BY provider, model, service_tier
      `).all(...E)){let t=u(e),o=k(t.provider)||"unknown",n=k(t.model)||"unknown",s=k(t.last_used)||new Date(0).toISOString(),a=p(t.request_count),i=p(t.tokens_input),r=p(t.tokens_output),c=await l(t);O.totalRequests+=a,O.totalPromptTokens+=i,O.totalCompletionTokens+=r,O.totalCost+=c,O.byProvider[o]||(O.byProvider[o]={requests:0,promptTokens:0,completionTokens:0,cost:0}),d(O.byProvider[o],a,i,r,c);let _=`${n} (${o})`;O.byModel[_]||(O.byModel[_]={requests:0,promptTokens:0,completionTokens:0,cost:0,rawModel:n,provider:o,lastUsed:s}),d(O.byModel[_],a,i,r,c),new Date(s)>new Date(O.byModel[_].lastUsed||s)&&(O.byModel[_].lastUsed=s)}for(let e of t.prepare(`
        WITH usage_source AS (${_})
        SELECT provider, model, connection_id, service_tier, ${m}
        FROM usage_source
        WHERE connection_id IS NOT NULL AND connection_id != ''
        GROUP BY provider, model, connection_id, service_tier
      `).all(...E)){let t=u(e),o=k(t.provider)||"unknown",n=k(t.model)||"unknown",s=k(t.last_used)||new Date(0).toISOString(),a=k(t.connection_id),r=p(t.request_count),c=p(t.tokens_input),_=p(t.tokens_output),E=await l(t);if(a){let e=A[a]||(0,i.getAccountDisplayName)({id:a}),t=`${n} (${o} - ${e})`;O.byAccount[t]||(O.byAccount[t]={requests:0,promptTokens:0,completionTokens:0,cost:0,rawModel:n,provider:o,connectionId:a,accountName:e,lastUsed:s}),d(O.byAccount[t],r,c,_,E),new Date(s)>new Date(O.byAccount[t].lastUsed||s)&&(O.byAccount[t].lastUsed=s)}}for(let e of t.prepare(`
        WITH usage_source AS (${_})
        SELECT provider, model, api_key_id, api_key_name, service_tier, ${m}
        FROM usage_source
        WHERE (api_key_id IS NOT NULL AND api_key_id != '')
           OR (api_key_name IS NOT NULL AND api_key_name != '')
        GROUP BY provider, model, api_key_id, api_key_name, service_tier
      `).all(...E)){let t=u(e),o=k(t.last_used)||new Date(0).toISOString(),n=k(t.api_key_id)||null,s=k(t.api_key_name)||null,a=p(t.request_count),i=p(t.tokens_input),r=p(t.tokens_output),c=await l(t);if(n||s){let e=n?`id:${n}`:`name:${s||"unknown"}`,t=(n?g.get(n):void 0)||s||n||"unknown";O.byApiKey[e]||(O.byApiKey[e]={requests:0,promptTokens:0,completionTokens:0,cost:0,apiKeyId:n,apiKeyName:t,historicalApiKeyNames:[],lastUsed:o});let _=O.byApiKey[e];s&&!_.historicalApiKeyNames?.includes(s)&&_.historicalApiKeyNames?.push(s),_.apiKeyName=t,d(_,a,i,r,c),new Date(o)>new Date(_.lastUsed||o)&&(_.lastUsed=o)}}for(let e of t.prepare(`
        SELECT
          strftime('%Y-%m-%dT%H:%M:00.000Z', timestamp) as minute,
          provider,
          model,
          COALESCE(service_tier, 'standard') as service_tier,
          COUNT(*) as request_count,
          COALESCE(SUM(tokens_input), 0) as tokens_input,
          COALESCE(SUM(tokens_output), 0) as tokens_output,
          COALESCE(SUM(tokens_cache_read), 0) as tokens_cache_read,
          COALESCE(SUM(tokens_cache_creation), 0) as tokens_cache_creation,
          COALESCE(SUM(tokens_reasoning), 0) as tokens_reasoning
        FROM usage_history
        WHERE timestamp >= ? AND timestamp <= ?
        GROUP BY minute, provider, model, service_tier
      `).all(U.toISOString(),L.toISOString())){let t=u(e),o=k(t.minute),n=new Date(o).getTime();if(!f[n])continue;let s=p(t.request_count),a=p(t.tokens_input),i=p(t.tokens_output),r=await l(t);d(f[n],s,a,i,r)}return O}e.s(["getConnectionSpendUsdSinceAdded",0,E,"getMonthlyProviderTokensForConnection",0,function(e,t){if(!e||!t)return 0;let o=(0,n.getDbInstance)(),s=new Date,a=new Date(Date.UTC(s.getUTCFullYear(),s.getUTCMonth(),1)).toISOString(),i=o.prepare(`SELECT COALESCE(SUM(tokens_input), 0)
            + COALESCE(SUM(tokens_output), 0)
            + COALESCE(SUM(tokens_cache_read), 0)
            + COALESCE(SUM(tokens_cache_creation), 0)
            + COALESCE(SUM(tokens_reasoning), 0) AS total
       FROM usage_history
       WHERE provider = ? AND connection_id = ? AND timestamp >= ?`).get(e,t,a);return Math.max(0,Number(i?.total??0))},"getUsageStats",0,C]),o()}catch(e){o(e)}},!1)];

//# sourceMappingURL=src_lib_1bjjglf._.js.map