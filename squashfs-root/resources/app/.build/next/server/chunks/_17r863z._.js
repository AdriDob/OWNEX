module.exports=[15844,e=>{"use strict";var t=e.i(284655);let n=new Set(["minimax","kimi-coding","kimi-coding-apikey","xiaomi-mimo","bailian-coding-plan","glm","glm-cn"]);function o(e){if(!e||!e.includes("/"))return e;let t=e.split("/");return t[t.length-1]}function s(e){let t=e?.cost_in_usd_ticks;return"number"==typeof t&&Number.isFinite(t)&&t>=0?t/1e10:null}function a(e,t=0){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let n=Number(e);return Number.isFinite(n)?n:t}return t}function r(e){return"string"==typeof e?e.trim().toLowerCase():""}function i(e){return e.replace(/-(?:ultra|max|xhigh|high|medium|low|none)$/i,"")}function c(e,t,n){let s=r(e),a=r(n);if("codex"!==s&&"cx"!==s)return 1;if("flex"===a)return .5;if("priority"!==a&&"fast"!==a)return 1;let c=i(o(String(t||"")).toLowerCase()),u=c.replace(/-/g,"");return/^gpt-5\.6-(?:sol|terra|luna)$/.test(c)||/^gpt5\.6(?:sol|terra|luna)$/.test(u)?1.5:"gpt-5.5"===c||"gpt5.5"===u?2.5:"gpt-5.4"===c||"gpt5.4"===u?2:1}function u(e,o,r={}){if(!o)return 0;let i=s(o);if(null!==i)return i;if(!e||r.flatRateAsZero&&function(e){if(!e||"string"!=typeof e)return!1;let o=e.trim().toLowerCase();return!!o&&(!!n.has(o)||Object.prototype.hasOwnProperty.call(t.WEB_COOKIE_PROVIDERS,o))}(r.provider))return 0;let _=a(e.input,0),p=a(e.cached,_),l=a(e.output,0),d=a(e.reasoning,l),k=a(e.cache_creation,_),m=0,E=o.input??o.prompt_tokens??o.input_tokens??0,C=o.cacheRead??o.cached_tokens??o.cache_read_input_tokens??0,S=o.cacheCreation??o.cache_creation_input_tokens??0;m+=_/1e6*Math.max(0,E-C-S),C>0&&(m+=p/1e6*C),m+=l/1e6*(o.output??o.completion_tokens??o.output_tokens??0);let f=o.reasoning??o.reasoning_tokens??0;return f>0&&(m+=d/1e6*f),S>0&&(m+=k/1e6*S),m*c(r.provider,r.model,r.serviceTier)}async function _(t,n,a,c={}){if(!a||!t||!n)return 0;let p=s(a);if(null!==p)return p;try{let{getPricingForModel:s}=await e.A(605589),_=await s(t,n);if(!_){let e=o(n);e!==n&&(_=await s(t,e));let a=r(t);if(!_&&("codex"===a||"cx"===a)){let n=i(e);n!==e&&(_=await s(t,n))}}if(!_)return 0;let p=_&&"object"==typeof _&&!Array.isArray(_)?_:{};return u(p,a,{provider:t,model:n,...c})}catch(e){return console.error("Error calculating cost:",e),0}}async function p(t,n,s,r){if(!n||!s)return 0;try{let{getPricingForModel:i}=await e.A(605589),c=await i(n,s);if(!c){let e=o(s);e!==s&&(c=await i(n,e))}if(!c)return 0;let u=c;switch(t){case"image":if(!u)return 0;return a(u.output_cost_per_image??u.input_cost_per_image,0)*Math.max(0,Math.floor(a(r.n,0)));case"audio":if(!u)return 0;let _=a(r.seconds,0);if(_>0){let e=a(u.input_cost_per_second??u.output_cost_per_second,0);if(e>0)return e*_}let p=a(r.characters,0);if(p>0){let e=a(u.input_cost_per_character??u.output_cost_per_character,0);if(e>0)return Math.round(e*p*1e10)/1e10}return 0;case"rerank":if(!u)return 0;return a(u.search_unit_cost??u.input_cost_per_query,0)*Math.max(0,a(r.searchUnits,0));case"video":if(!u)return 0;return a(u.output_cost_per_video_per_second??u.input_cost_per_video_per_second,0)*a(r.seconds,0);default:return 0}}catch(e){return console.error("Error calculating modal cost:",e),0}}e.s(["calculateCost",0,_,"calculateModalCost",0,p,"computeCostFromPricing",0,u,"getCodexFastCostMultiplier",0,c,"normalizeModelName",0,o],15844)},496727,e=>{"use strict";e.s(["FORMATS",0,{OPENAI:"openai",OPENAI_RESPONSES:"openai-responses",OPENAI_RESPONSE:"openai-response",CLAUDE:"claude",GEMINI:"gemini",CODEX:"codex",ANTIGRAVITY:"antigravity",KIRO:"kiro",CURSOR:"cursor"}])},208896,e=>{"use strict";function t(e,n=""){for(let t of e){let e=function(e,t=3){if(!e)return"";let n=e.trim();return n?n.includes("@")?function(e,t=3){if(!e)return"";if(!e.includes("@"))return e;let n=e.lastIndexOf("@"),o=e.slice(0,n),s=e.slice(n+1);if(o.length<=t)return e;let a=o.slice(0,t)+"*".repeat(o.length-t);if(s.length<=t)return`${a}@${s}`;let r="*".repeat(s.length-t)+s.slice(s.length-t);return`${a}@${r}`}(n,t):n:""}(t);if(e)return e}return n}e.s(["pickDisplayValue",0,function(e,n,o=""){if(n){for(let t of e)if(t?.trim())return t.trim();return o}return t(e,o)},"pickMaskedDisplayValue",0,t])},662636,e=>{"use strict";e.s(["getAccountDisplayName",0,function(e){if(!e)return"Unknown Account";let t="string"==typeof e.name&&e.name.trim()||"string"==typeof e.displayName&&e.displayName.trim()||"string"==typeof e.email&&e.email.trim();return t||("string"==typeof e.id&&e.id?`Account #${e.id.slice(0,6)}`:"Unknown Account")},"getProviderDisplayName",0,function(e,t){if(t?.name?.trim())return t.name.trim();if(t?.prefix?.trim())return t.prefix.trim();if(!e)return"Unknown Provider";let n=e.match(/^(openai|anthropic)-compatible-(?:chat|responses)-[0-9a-f-]{10,}$/i);return n?`Compatible (${n[1]})`:/^anthropic-compatible-cc-[0-9a-f-]{10,}$/i.test(e)?"CC Compatible":e}])},897114,e=>e.a(async(t,n)=>{try{var o=e.i(899378),s=e.i(125852),a=e.i(27663),r=e.i(662636),i=e.i(15844),c=e.i(918521),u=t([a]);function _(e){return e&&"object"==typeof e&&!Array.isArray(e)?e:{}}function p(e){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let t=Number(e);return Number.isFinite(t)?t:0}return 0}function l(e){return"string"==typeof e?e:""}[a]=u.then?(await u)():u;let C=`
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
`;async function d(e){let t=l(e.provider)||"unknown",n=l(e.model)||"unknown",o=l(e.service_tier)||"standard",s=p(e.stored_cost),a=await (0,i.calculateCost)(t,n,{input:p(e.cost_tokens_input??e.tokens_input),output:p(e.cost_tokens_output??e.tokens_output),cacheRead:p(e.cost_tokens_cache_read??e.tokens_cache_read),cacheCreation:p(e.cost_tokens_cache_creation??e.tokens_cache_creation),reasoning:p(e.cost_tokens_reasoning??e.tokens_reasoning)},{provider:t,serviceTier:o,flatRateAsZero:!0});return s+a}function k(e,t,n,o,s){e.requests+=t,e.promptTokens+=n,e.completionTokens+=o,e.cost+=s}async function m(e,t){if(!e||!t)return{costUsd:0,requests:0};let n=(0,o.getDbInstance)().prepare(`SELECT model,
          COALESCE(SUM(tokens_input), 0) AS input,
          COALESCE(SUM(tokens_output), 0) AS output,
          COALESCE(SUM(tokens_cache_read), 0) AS cacheRead,
          COALESCE(SUM(tokens_cache_creation), 0) AS cacheCreation,
          COALESCE(SUM(tokens_reasoning), 0) AS reasoning,
          COUNT(*) AS requests
       FROM usage_history
       WHERE connection_id = ? AND provider = ? AND success = 1
       GROUP BY model`).all(t,e),s=0,a=0;for(let t of n){a+=Math.max(0,Number(t.requests??0));let n="string"==typeof t.model?t.model:"",o={input:Number(t.input??0),output:Number(t.output??0),cacheRead:Number(t.cacheRead??0),cacheCreation:Number(t.cacheCreation??0),reasoning:Number(t.reasoning??0)};s+=await (0,i.calculateCost)(e,n,o,{provider:e,model:n,flatRateAsZero:!0})}return{costUsd:Math.max(0,s),requests:a}}async function E(){let t=(0,o.getDbInstance)(),n=await (0,c.isAggregationEnabled)(),i=n?await (0,c.getRawDataCutoffDate)():null,u=n?`
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
    `,m=n&&i?[i,i]:[],{getProviderConnections:E}=await e.A(605589),S=[];try{let e=await E();S=Array.isArray(e)?e:[]}catch{}let f={};for(let e of S){let t=_(e),n=l(t.id);n&&(f[n]=l(t.name)||l(t.email)||n)}let g=new Map;try{for(let e of(await (0,s.getApiKeys)()))"string"==typeof e.id&&"string"==typeof e.name&&g.set(e.id,e.name)}catch{}let A=(0,a.getPendingRequests)(),h={totalRequests:0,totalPromptTokens:0,totalCompletionTokens:0,totalCost:0,byProvider:{},byModel:{},byAccount:{},byApiKey:{},last10Minutes:[],pending:A,activeRequests:[]};for(let[e,t]of Object.entries(A.byAccount))for(let[n,o]of Object.entries(t))if(o>0){let t=f[e]||(0,r.getAccountDisplayName)({id:e}),s=n.match(/^(.*) \((.*)\)$/);h.activeRequests.push({model:s?s[1]:n,provider:s?s[2]:"unknown",account:t,count:o})}let y=new Date,O=new Date(6e4*Math.floor(y.getTime()/6e4)),L={};for(let e=0;e<10;e++){let t=new Date(O.getTime()-(9-e)*6e4).getTime();L[t]={requests:0,promptTokens:0,completionTokens:0,cost:0},h.last10Minutes.push(L[t])}let M=new Date(O.getTime()-54e4);for(let e of t.prepare(`
        WITH usage_source AS (${u})
        SELECT provider, model, service_tier, ${C}
        FROM usage_source
        GROUP BY provider, model, service_tier
      `).all(...m)){let t=_(e),n=l(t.provider)||"unknown",o=l(t.model)||"unknown",s=l(t.last_used)||new Date(0).toISOString(),a=p(t.request_count),r=p(t.tokens_input),i=p(t.tokens_output),c=await d(t);h.totalRequests+=a,h.totalPromptTokens+=r,h.totalCompletionTokens+=i,h.totalCost+=c,h.byProvider[n]||(h.byProvider[n]={requests:0,promptTokens:0,completionTokens:0,cost:0}),k(h.byProvider[n],a,r,i,c);let u=`${o} (${n})`;h.byModel[u]||(h.byModel[u]={requests:0,promptTokens:0,completionTokens:0,cost:0,rawModel:o,provider:n,lastUsed:s}),k(h.byModel[u],a,r,i,c),new Date(s)>new Date(h.byModel[u].lastUsed||s)&&(h.byModel[u].lastUsed=s)}for(let e of t.prepare(`
        WITH usage_source AS (${u})
        SELECT provider, model, connection_id, service_tier, ${C}
        FROM usage_source
        WHERE connection_id IS NOT NULL AND connection_id != ''
        GROUP BY provider, model, connection_id, service_tier
      `).all(...m)){let t=_(e),n=l(t.provider)||"unknown",o=l(t.model)||"unknown",s=l(t.last_used)||new Date(0).toISOString(),a=l(t.connection_id),i=p(t.request_count),c=p(t.tokens_input),u=p(t.tokens_output),m=await d(t);if(a){let e=f[a]||(0,r.getAccountDisplayName)({id:a}),t=`${o} (${n} - ${e})`;h.byAccount[t]||(h.byAccount[t]={requests:0,promptTokens:0,completionTokens:0,cost:0,rawModel:o,provider:n,connectionId:a,accountName:e,lastUsed:s}),k(h.byAccount[t],i,c,u,m),new Date(s)>new Date(h.byAccount[t].lastUsed||s)&&(h.byAccount[t].lastUsed=s)}}for(let e of t.prepare(`
        WITH usage_source AS (${u})
        SELECT provider, model, api_key_id, api_key_name, service_tier, ${C}
        FROM usage_source
        WHERE (api_key_id IS NOT NULL AND api_key_id != '')
           OR (api_key_name IS NOT NULL AND api_key_name != '')
        GROUP BY provider, model, api_key_id, api_key_name, service_tier
      `).all(...m)){let t=_(e),n=l(t.last_used)||new Date(0).toISOString(),o=l(t.api_key_id)||null,s=l(t.api_key_name)||null,a=p(t.request_count),r=p(t.tokens_input),i=p(t.tokens_output),c=await d(t);if(o||s){let e=o?`id:${o}`:`name:${s||"unknown"}`,t=(o?g.get(o):void 0)||s||o||"unknown";h.byApiKey[e]||(h.byApiKey[e]={requests:0,promptTokens:0,completionTokens:0,cost:0,apiKeyId:o,apiKeyName:t,historicalApiKeyNames:[],lastUsed:n});let u=h.byApiKey[e];s&&!u.historicalApiKeyNames?.includes(s)&&u.historicalApiKeyNames?.push(s),u.apiKeyName=t,k(u,a,r,i,c),new Date(n)>new Date(u.lastUsed||n)&&(u.lastUsed=n)}}for(let e of t.prepare(`
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
      `).all(M.toISOString(),y.toISOString())){let t=_(e),n=l(t.minute),o=new Date(n).getTime();if(!L[o])continue;let s=p(t.request_count),a=p(t.tokens_input),r=p(t.tokens_output),i=await d(t);k(L[o],s,a,r,i)}return h}e.s(["getConnectionSpendUsdSinceAdded",0,m,"getMonthlyProviderTokensForConnection",0,function(e,t){if(!e||!t)return 0;let n=(0,o.getDbInstance)(),s=new Date,a=new Date(Date.UTC(s.getUTCFullYear(),s.getUTCMonth(),1)).toISOString(),r=n.prepare(`SELECT COALESCE(SUM(tokens_input), 0)
            + COALESCE(SUM(tokens_output), 0)
            + COALESCE(SUM(tokens_cache_read), 0)
            + COALESCE(SUM(tokens_cache_creation), 0)
            + COALESCE(SUM(tokens_reasoning), 0) AS total
       FROM usage_history
       WHERE provider = ? AND connection_id = ? AND timestamp >= ?`).get(e,t,a);return Math.max(0,Number(r?.total??0))},"getUsageStats",0,E]),n()}catch(e){n(e)}},!1),312125,e=>e.a(async(t,n)=>{try{var o=e.i(461145),s=e.i(27663);e.i(15844);var a=e.i(897114),r=e.i(397506),i=t([o,s,a,r]);[o,s,a,r]=i.then?(await i)():i,e.s([]),n()}catch(e){n(e)}},!1)];

//# sourceMappingURL=_17r863z._.js.map