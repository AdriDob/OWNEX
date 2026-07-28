module.exports=[15844,e=>{"use strict";var t=e.i(284655);let o=new Set(["minimax","kimi-coding","kimi-coding-apikey","xiaomi-mimo","bailian-coding-plan","glm","glm-cn"]);function n(e){if(!e||!e.includes("/"))return e;let t=e.split("/");return t[t.length-1]}function s(e){let t=e?.cost_in_usd_ticks;return"number"==typeof t&&Number.isFinite(t)&&t>=0?t/1e10:null}function a(e,t=0){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let o=Number(e);return Number.isFinite(o)?o:t}return t}function r(e){return"string"==typeof e?e.trim().toLowerCase():""}function i(e){return e.replace(/-(?:ultra|max|xhigh|high|medium|low|none)$/i,"")}function c(e,t,o){let s=r(e),a=r(o);if("codex"!==s&&"cx"!==s)return 1;if("flex"===a)return .5;if("priority"!==a&&"fast"!==a)return 1;let c=i(n(String(t||"")).toLowerCase()),_=c.replace(/-/g,"");return/^gpt-5\.6-(?:sol|terra|luna)$/.test(c)||/^gpt5\.6(?:sol|terra|luna)$/.test(_)?1.5:"gpt-5.5"===c||"gpt5.5"===_?2.5:"gpt-5.4"===c||"gpt5.4"===_?2:1}function _(e,n,r={}){if(!n)return 0;let i=s(n);if(null!==i)return i;if(!e||r.flatRateAsZero&&function(e){if(!e||"string"!=typeof e)return!1;let n=e.trim().toLowerCase();return!!n&&(!!o.has(n)||Object.prototype.hasOwnProperty.call(t.WEB_COOKIE_PROVIDERS,n))}(r.provider))return 0;let u=a(e.input,0),p=a(e.cached,u),l=a(e.output,0),d=a(e.reasoning,l),k=a(e.cache_creation,u),m=0,C=n.input??n.prompt_tokens??n.input_tokens??0,E=n.cacheRead??n.cached_tokens??n.cache_read_input_tokens??0,S=n.cacheCreation??n.cache_creation_input_tokens??0;m+=u/1e6*Math.max(0,C-E-S),E>0&&(m+=p/1e6*E),m+=l/1e6*(n.output??n.completion_tokens??n.output_tokens??0);let g=n.reasoning??n.reasoning_tokens??0;return g>0&&(m+=d/1e6*g),S>0&&(m+=k/1e6*S),m*c(r.provider,r.model,r.serviceTier)}async function u(t,o,a,c={}){if(!a||!t||!o)return 0;let p=s(a);if(null!==p)return p;try{let{getPricingForModel:s}=await e.A(605589),u=await s(t,o);if(!u){let e=n(o);e!==o&&(u=await s(t,e));let a=r(t);if(!u&&("codex"===a||"cx"===a)){let o=i(e);o!==e&&(u=await s(t,o))}}if(!u)return 0;let p=u&&"object"==typeof u&&!Array.isArray(u)?u:{};return _(p,a,{provider:t,model:o,...c})}catch(e){return console.error("Error calculating cost:",e),0}}async function p(t,o,s,r){if(!o||!s)return 0;try{let{getPricingForModel:i}=await e.A(605589),c=await i(o,s);if(!c){let e=n(s);e!==s&&(c=await i(o,e))}if(!c)return 0;let _=c;switch(t){case"image":if(!_)return 0;return a(_.output_cost_per_image??_.input_cost_per_image,0)*Math.max(0,Math.floor(a(r.n,0)));case"audio":if(!_)return 0;let u=a(r.seconds,0);if(u>0){let e=a(_.input_cost_per_second??_.output_cost_per_second,0);if(e>0)return e*u}let p=a(r.characters,0);if(p>0){let e=a(_.input_cost_per_character??_.output_cost_per_character,0);if(e>0)return Math.round(e*p*1e10)/1e10}return 0;case"rerank":if(!_)return 0;return a(_.search_unit_cost??_.input_cost_per_query,0)*Math.max(0,a(r.searchUnits,0));case"video":if(!_)return 0;return a(_.output_cost_per_video_per_second??_.input_cost_per_video_per_second,0)*a(r.seconds,0);default:return 0}}catch(e){return console.error("Error calculating modal cost:",e),0}}e.s(["calculateCost",0,u,"calculateModalCost",0,p,"computeCostFromPricing",0,_,"getCodexFastCostMultiplier",0,c,"normalizeModelName",0,n],15844)},662636,e=>{"use strict";e.s(["getAccountDisplayName",0,function(e){if(!e)return"Unknown Account";let t="string"==typeof e.name&&e.name.trim()||"string"==typeof e.displayName&&e.displayName.trim()||"string"==typeof e.email&&e.email.trim();return t||("string"==typeof e.id&&e.id?`Account #${e.id.slice(0,6)}`:"Unknown Account")},"getProviderDisplayName",0,function(e,t){if(t?.name?.trim())return t.name.trim();if(t?.prefix?.trim())return t.prefix.trim();if(!e)return"Unknown Provider";let o=e.match(/^(openai|anthropic)-compatible-(?:chat|responses)-[0-9a-f-]{10,}$/i);return o?`Compatible (${o[1]})`:/^anthropic-compatible-cc-[0-9a-f-]{10,}$/i.test(e)?"CC Compatible":e}])},897114,e=>e.a(async(t,o)=>{try{var n=e.i(899378),s=e.i(125852),a=e.i(27663),r=e.i(662636),i=e.i(15844),c=e.i(918521),_=t([a]);function u(e){return e&&"object"==typeof e&&!Array.isArray(e)?e:{}}function p(e){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let t=Number(e);return Number.isFinite(t)?t:0}return 0}function l(e){return"string"==typeof e?e:""}[a]=_.then?(await _)():_;let E=`
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
`;async function d(e){let t=l(e.provider)||"unknown",o=l(e.model)||"unknown",n=l(e.service_tier)||"standard",s=p(e.stored_cost),a=await (0,i.calculateCost)(t,o,{input:p(e.cost_tokens_input??e.tokens_input),output:p(e.cost_tokens_output??e.tokens_output),cacheRead:p(e.cost_tokens_cache_read??e.tokens_cache_read),cacheCreation:p(e.cost_tokens_cache_creation??e.tokens_cache_creation),reasoning:p(e.cost_tokens_reasoning??e.tokens_reasoning)},{provider:t,serviceTier:n,flatRateAsZero:!0});return s+a}function k(e,t,o,n,s){e.requests+=t,e.promptTokens+=o,e.completionTokens+=n,e.cost+=s}async function m(e,t){if(!e||!t)return{costUsd:0,requests:0};let o=(0,n.getDbInstance)().prepare(`SELECT model,
          COALESCE(SUM(tokens_input), 0) AS input,
          COALESCE(SUM(tokens_output), 0) AS output,
          COALESCE(SUM(tokens_cache_read), 0) AS cacheRead,
          COALESCE(SUM(tokens_cache_creation), 0) AS cacheCreation,
          COALESCE(SUM(tokens_reasoning), 0) AS reasoning,
          COUNT(*) AS requests
       FROM usage_history
       WHERE connection_id = ? AND provider = ? AND success = 1
       GROUP BY model`).all(t,e),s=0,a=0;for(let t of o){a+=Math.max(0,Number(t.requests??0));let o="string"==typeof t.model?t.model:"",n={input:Number(t.input??0),output:Number(t.output??0),cacheRead:Number(t.cacheRead??0),cacheCreation:Number(t.cacheCreation??0),reasoning:Number(t.reasoning??0)};s+=await (0,i.calculateCost)(e,o,n,{provider:e,model:o,flatRateAsZero:!0})}return{costUsd:Math.max(0,s),requests:a}}async function C(){let t=(0,n.getDbInstance)(),o=await (0,c.isAggregationEnabled)(),i=o?await (0,c.getRawDataCutoffDate)():null,_=o?`
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
    `,m=o&&i?[i,i]:[],{getProviderConnections:C}=await e.A(605589),S=[];try{let e=await C();S=Array.isArray(e)?e:[]}catch{}let g={};for(let e of S){let t=u(e),o=l(t.id);o&&(g[o]=l(t.name)||l(t.email)||o)}let f=new Map;try{for(let e of(await (0,s.getApiKeys)()))"string"==typeof e.id&&"string"==typeof e.name&&f.set(e.id,e.name)}catch{}let A=(0,a.getPendingRequests)(),h={totalRequests:0,totalPromptTokens:0,totalCompletionTokens:0,totalCost:0,byProvider:{},byModel:{},byAccount:{},byApiKey:{},last10Minutes:[],pending:A,activeRequests:[]};for(let[e,t]of Object.entries(A.byAccount))for(let[o,n]of Object.entries(t))if(n>0){let t=g[e]||(0,r.getAccountDisplayName)({id:e}),s=o.match(/^(.*) \((.*)\)$/);h.activeRequests.push({model:s?s[1]:o,provider:s?s[2]:"unknown",account:t,count:n})}let y=new Date,O=new Date(6e4*Math.floor(y.getTime()/6e4)),L={};for(let e=0;e<10;e++){let t=new Date(O.getTime()-(9-e)*6e4).getTime();L[t]={requests:0,promptTokens:0,completionTokens:0,cost:0},h.last10Minutes.push(L[t])}let M=new Date(O.getTime()-54e4);for(let e of t.prepare(`
        WITH usage_source AS (${_})
        SELECT provider, model, service_tier, ${E}
        FROM usage_source
        GROUP BY provider, model, service_tier
      `).all(...m)){let t=u(e),o=l(t.provider)||"unknown",n=l(t.model)||"unknown",s=l(t.last_used)||new Date(0).toISOString(),a=p(t.request_count),r=p(t.tokens_input),i=p(t.tokens_output),c=await d(t);h.totalRequests+=a,h.totalPromptTokens+=r,h.totalCompletionTokens+=i,h.totalCost+=c,h.byProvider[o]||(h.byProvider[o]={requests:0,promptTokens:0,completionTokens:0,cost:0}),k(h.byProvider[o],a,r,i,c);let _=`${n} (${o})`;h.byModel[_]||(h.byModel[_]={requests:0,promptTokens:0,completionTokens:0,cost:0,rawModel:n,provider:o,lastUsed:s}),k(h.byModel[_],a,r,i,c),new Date(s)>new Date(h.byModel[_].lastUsed||s)&&(h.byModel[_].lastUsed=s)}for(let e of t.prepare(`
        WITH usage_source AS (${_})
        SELECT provider, model, connection_id, service_tier, ${E}
        FROM usage_source
        WHERE connection_id IS NOT NULL AND connection_id != ''
        GROUP BY provider, model, connection_id, service_tier
      `).all(...m)){let t=u(e),o=l(t.provider)||"unknown",n=l(t.model)||"unknown",s=l(t.last_used)||new Date(0).toISOString(),a=l(t.connection_id),i=p(t.request_count),c=p(t.tokens_input),_=p(t.tokens_output),m=await d(t);if(a){let e=g[a]||(0,r.getAccountDisplayName)({id:a}),t=`${n} (${o} - ${e})`;h.byAccount[t]||(h.byAccount[t]={requests:0,promptTokens:0,completionTokens:0,cost:0,rawModel:n,provider:o,connectionId:a,accountName:e,lastUsed:s}),k(h.byAccount[t],i,c,_,m),new Date(s)>new Date(h.byAccount[t].lastUsed||s)&&(h.byAccount[t].lastUsed=s)}}for(let e of t.prepare(`
        WITH usage_source AS (${_})
        SELECT provider, model, api_key_id, api_key_name, service_tier, ${E}
        FROM usage_source
        WHERE (api_key_id IS NOT NULL AND api_key_id != '')
           OR (api_key_name IS NOT NULL AND api_key_name != '')
        GROUP BY provider, model, api_key_id, api_key_name, service_tier
      `).all(...m)){let t=u(e),o=l(t.last_used)||new Date(0).toISOString(),n=l(t.api_key_id)||null,s=l(t.api_key_name)||null,a=p(t.request_count),r=p(t.tokens_input),i=p(t.tokens_output),c=await d(t);if(n||s){let e=n?`id:${n}`:`name:${s||"unknown"}`,t=(n?f.get(n):void 0)||s||n||"unknown";h.byApiKey[e]||(h.byApiKey[e]={requests:0,promptTokens:0,completionTokens:0,cost:0,apiKeyId:n,apiKeyName:t,historicalApiKeyNames:[],lastUsed:o});let _=h.byApiKey[e];s&&!_.historicalApiKeyNames?.includes(s)&&_.historicalApiKeyNames?.push(s),_.apiKeyName=t,k(_,a,r,i,c),new Date(o)>new Date(_.lastUsed||o)&&(_.lastUsed=o)}}for(let e of t.prepare(`
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
      `).all(M.toISOString(),y.toISOString())){let t=u(e),o=l(t.minute),n=new Date(o).getTime();if(!L[n])continue;let s=p(t.request_count),a=p(t.tokens_input),r=p(t.tokens_output),i=await d(t);k(L[n],s,a,r,i)}return h}e.s(["getConnectionSpendUsdSinceAdded",0,m,"getMonthlyProviderTokensForConnection",0,function(e,t){if(!e||!t)return 0;let o=(0,n.getDbInstance)(),s=new Date,a=new Date(Date.UTC(s.getUTCFullYear(),s.getUTCMonth(),1)).toISOString(),r=o.prepare(`SELECT COALESCE(SUM(tokens_input), 0)
            + COALESCE(SUM(tokens_output), 0)
            + COALESCE(SUM(tokens_cache_read), 0)
            + COALESCE(SUM(tokens_cache_creation), 0)
            + COALESCE(SUM(tokens_reasoning), 0) AS total
       FROM usage_history
       WHERE provider = ? AND connection_id = ? AND timestamp >= ?`).get(e,t,a);return Math.max(0,Number(r?.total??0))},"getUsageStats",0,C]),o()}catch(e){o(e)}},!1)];

//# sourceMappingURL=src_lib_0ncdpv1._.js.map