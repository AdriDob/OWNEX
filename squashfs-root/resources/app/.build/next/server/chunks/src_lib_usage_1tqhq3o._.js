module.exports=[315056,e=>{"use strict";e.i(830471);var t=e.i(417358);async function o(){let e=(0,t.getUserDatabaseSettings)().aggregation.rawDataRetentionDays,o=new Date;return o.setDate(o.getDate()-e),o.toISOString().split("T")[0]}async function s(){return(0,t.getUserDatabaseSettings)().aggregation.enabled}e.s(["getRawDataCutoffDate",0,o,"isAggregationEnabled",0,s])},645449,e=>e.a(async(t,o)=>{try{var s=e.i(830471),n=e.i(950412),a=e.i(643275),i=e.i(947170),r=e.i(642259),c=e.i(315056),_=t([a]);function u(e){return e&&"object"==typeof e&&!Array.isArray(e)?e:{}}function p(e){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let t=Number(e);return Number.isFinite(t)?t:0}return 0}function k(e){return"string"==typeof e?e:""}[a]=_.then?(await _)():_;let S=`
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
`;async function d(e){let t=k(e.provider)||"unknown",o=k(e.model)||"unknown",s=k(e.service_tier)||"standard",n=p(e.stored_cost),a=await (0,r.calculateCost)(t,o,{input:p(e.cost_tokens_input??e.tokens_input),output:p(e.cost_tokens_output??e.tokens_output),cacheRead:p(e.cost_tokens_cache_read??e.tokens_cache_read),cacheCreation:p(e.cost_tokens_cache_creation??e.tokens_cache_creation),reasoning:p(e.cost_tokens_reasoning??e.tokens_reasoning)},{provider:t,serviceTier:s,flatRateAsZero:!0});return n+a}function E(e,t,o,s,n){e.requests+=t,e.promptTokens+=o,e.completionTokens+=s,e.cost+=n}async function l(e,t){if(!e||!t)return{costUsd:0,requests:0};let o=(0,s.getDbInstance)().prepare(`SELECT model,
          COALESCE(SUM(tokens_input), 0) AS input,
          COALESCE(SUM(tokens_output), 0) AS output,
          COALESCE(SUM(tokens_cache_read), 0) AS cacheRead,
          COALESCE(SUM(tokens_cache_creation), 0) AS cacheCreation,
          COALESCE(SUM(tokens_reasoning), 0) AS reasoning,
          COUNT(*) AS requests
       FROM usage_history
       WHERE connection_id = ? AND provider = ? AND success = 1
       GROUP BY model`).all(t,e),n=0,a=0;for(let t of o){a+=Math.max(0,Number(t.requests??0));let o="string"==typeof t.model?t.model:"",s={input:Number(t.input??0),output:Number(t.output??0),cacheRead:Number(t.cacheRead??0),cacheCreation:Number(t.cacheCreation??0),reasoning:Number(t.reasoning??0)};n+=await (0,r.calculateCost)(e,o,s,{provider:e,model:o,flatRateAsZero:!0})}return{costUsd:Math.max(0,n),requests:a}}async function C(){let t=(0,s.getDbInstance)(),o=await (0,c.isAggregationEnabled)(),r=o?await (0,c.getRawDataCutoffDate)():null,_=o?`
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
    `,l=o&&r?[r,r]:[],{getProviderConnections:C}=await e.A(893682),m=[];try{let e=await C();m=Array.isArray(e)?e:[]}catch{}let A={};for(let e of m){let t=u(e),o=k(t.id);o&&(A[o]=k(t.name)||k(t.email)||o)}let g=new Map;try{for(let e of(await (0,n.getApiKeys)()))"string"==typeof e.id&&"string"==typeof e.name&&g.set(e.id,e.name)}catch{}let O=(0,a.getPendingRequests)(),y={totalRequests:0,totalPromptTokens:0,totalCompletionTokens:0,totalCost:0,byProvider:{},byModel:{},byAccount:{},byApiKey:{},last10Minutes:[],pending:O,activeRequests:[]};for(let[e,t]of Object.entries(O.byAccount))for(let[o,s]of Object.entries(t))if(s>0){let t=A[e]||(0,i.getAccountDisplayName)({id:e}),n=o.match(/^(.*) \((.*)\)$/);y.activeRequests.push({model:n?n[1]:o,provider:n?n[2]:"unknown",account:t,count:s})}let L=new Date,h=new Date(6e4*Math.floor(L.getTime()/6e4)),U={};for(let e=0;e<10;e++){let t=new Date(h.getTime()-(9-e)*6e4).getTime();U[t]={requests:0,promptTokens:0,completionTokens:0,cost:0},y.last10Minutes.push(U[t])}let M=new Date(h.getTime()-54e4);for(let e of t.prepare(`
        WITH usage_source AS (${_})
        SELECT provider, model, service_tier, ${S}
        FROM usage_source
        GROUP BY provider, model, service_tier
      `).all(...l)){let t=u(e),o=k(t.provider)||"unknown",s=k(t.model)||"unknown",n=k(t.last_used)||new Date(0).toISOString(),a=p(t.request_count),i=p(t.tokens_input),r=p(t.tokens_output),c=await d(t);y.totalRequests+=a,y.totalPromptTokens+=i,y.totalCompletionTokens+=r,y.totalCost+=c,y.byProvider[o]||(y.byProvider[o]={requests:0,promptTokens:0,completionTokens:0,cost:0}),E(y.byProvider[o],a,i,r,c);let _=`${s} (${o})`;y.byModel[_]||(y.byModel[_]={requests:0,promptTokens:0,completionTokens:0,cost:0,rawModel:s,provider:o,lastUsed:n}),E(y.byModel[_],a,i,r,c),new Date(n)>new Date(y.byModel[_].lastUsed||n)&&(y.byModel[_].lastUsed=n)}for(let e of t.prepare(`
        WITH usage_source AS (${_})
        SELECT provider, model, connection_id, service_tier, ${S}
        FROM usage_source
        WHERE connection_id IS NOT NULL AND connection_id != ''
        GROUP BY provider, model, connection_id, service_tier
      `).all(...l)){let t=u(e),o=k(t.provider)||"unknown",s=k(t.model)||"unknown",n=k(t.last_used)||new Date(0).toISOString(),a=k(t.connection_id),r=p(t.request_count),c=p(t.tokens_input),_=p(t.tokens_output),l=await d(t);if(a){let e=A[a]||(0,i.getAccountDisplayName)({id:a}),t=`${s} (${o} - ${e})`;y.byAccount[t]||(y.byAccount[t]={requests:0,promptTokens:0,completionTokens:0,cost:0,rawModel:s,provider:o,connectionId:a,accountName:e,lastUsed:n}),E(y.byAccount[t],r,c,_,l),new Date(n)>new Date(y.byAccount[t].lastUsed||n)&&(y.byAccount[t].lastUsed=n)}}for(let e of t.prepare(`
        WITH usage_source AS (${_})
        SELECT provider, model, api_key_id, api_key_name, service_tier, ${S}
        FROM usage_source
        WHERE (api_key_id IS NOT NULL AND api_key_id != '')
           OR (api_key_name IS NOT NULL AND api_key_name != '')
        GROUP BY provider, model, api_key_id, api_key_name, service_tier
      `).all(...l)){let t=u(e),o=k(t.last_used)||new Date(0).toISOString(),s=k(t.api_key_id)||null,n=k(t.api_key_name)||null,a=p(t.request_count),i=p(t.tokens_input),r=p(t.tokens_output),c=await d(t);if(s||n){let e=s?`id:${s}`:`name:${n||"unknown"}`,t=(s?g.get(s):void 0)||n||s||"unknown";y.byApiKey[e]||(y.byApiKey[e]={requests:0,promptTokens:0,completionTokens:0,cost:0,apiKeyId:s,apiKeyName:t,historicalApiKeyNames:[],lastUsed:o});let _=y.byApiKey[e];n&&!_.historicalApiKeyNames?.includes(n)&&_.historicalApiKeyNames?.push(n),_.apiKeyName=t,E(_,a,i,r,c),new Date(o)>new Date(_.lastUsed||o)&&(_.lastUsed=o)}}for(let e of t.prepare(`
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
      `).all(M.toISOString(),L.toISOString())){let t=u(e),o=k(t.minute),s=new Date(o).getTime();if(!U[s])continue;let n=p(t.request_count),a=p(t.tokens_input),i=p(t.tokens_output),r=await d(t);E(U[s],n,a,i,r)}return y}e.s(["getConnectionSpendUsdSinceAdded",0,l,"getMonthlyProviderTokensForConnection",0,function(e,t){if(!e||!t)return 0;let o=(0,s.getDbInstance)(),n=new Date,a=new Date(Date.UTC(n.getUTCFullYear(),n.getUTCMonth(),1)).toISOString(),i=o.prepare(`SELECT COALESCE(SUM(tokens_input), 0)
            + COALESCE(SUM(tokens_output), 0)
            + COALESCE(SUM(tokens_cache_read), 0)
            + COALESCE(SUM(tokens_cache_creation), 0)
            + COALESCE(SUM(tokens_reasoning), 0) AS total
       FROM usage_history
       WHERE provider = ? AND connection_id = ? AND timestamp >= ?`).get(e,t,a);return Math.max(0,Number(i?.total??0))},"getUsageStats",0,C]),o()}catch(e){o(e)}},!1)];

//# sourceMappingURL=src_lib_usage_1tqhq3o._.js.map