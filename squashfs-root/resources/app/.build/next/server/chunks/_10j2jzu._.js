module.exports=[710876,e=>{"use strict";let r,i=process.env.REDIS_URL?.trim()||"";i||console.warn("[REDIS] REDIS_URL is not set in production. Using in-memory rate limiting.");let n=null;function t(){return i.length>0}let o=(r=null,{shouldLog:e=>e!==r&&(r=e,!0),reset(){r=null}});function l(){if(!t())throw Error("Redis is not configured");return n||(n=(async()=>{let r=await e.A(906538),n=new(r.default??r)(i,{maxRetriesPerRequest:3,enableReadyCheck:!1,retryStrategy:e=>Math.min(50*e,2e3)});return n.on("error",e=>{o.shouldLog(e.message)&&console.error("[REDIS] Error:",e.message)}),n.on("ready",()=>o.reset()),n})()),n}let s=`
local key_prefix = KEYS[1]
local current_time = tonumber(ARGV[1])

local rules = {}
for i = 2, #ARGV, 2 do
  table.insert(rules, {
    limit = tonumber(ARGV[i]),
    window = tonumber(ARGV[i+1])
  })
end

-- First pass: check if any limit is exceeded
for i, rule in ipairs(rules) do
  local current_window = math.floor(current_time / rule.window)
  local window_key = key_prefix .. ":" .. rule.window .. ":" .. current_window

  local count = tonumber(redis.call("GET", window_key) or "0")
  if count >= rule.limit then
    return { 0, rule.window } -- Reject, return which window failed
  end
end

-- Second pass: increment all rules
for i, rule in ipairs(rules) do
  local current_window = math.floor(current_time / rule.window)
  local window_key = key_prefix .. ":" .. rule.window .. ":" .. current_window

  local count = redis.call("INCR", window_key)
  if count == 1 then
    -- TTL is twice the window size to ensure it covers the current window safely
    redis.call("EXPIRE", window_key, rule.window * 2)
  end
end

return { 1, 0 } -- Accepted
`,u=new Map,a=new Map;function d(e,r,i){let n=Math.floor(Date.now()/1e3);for(let t of(e.size>50&&function(e,r){for(let i of e.keys()){let n=i.lastIndexOf(":");if(-1===n)continue;let t=i.lastIndexOf(":",n-1);if(-1===t)continue;let o=Number(i.slice(n+1)),l=Number(i.slice(t+1,n));Number.isFinite(o)&&Number.isFinite(l)&&!(l<=0)&&(o+1)*l<=r&&e.delete(i)}}(e,n),i)){let i=Math.floor(n/t.window),o=`rl:api_key:${r}:${t.window}:${i}`;if((e.get(o)||0)>=t.limit)return{allowed:!1,failedWindow:t.window}}for(let t of i){let i=Math.floor(n/t.window),o=`rl:api_key:${r}:${t.window}:${i}`;e.set(o,(e.get(o)||0)+1)}return{allowed:!0}}async function w(e,r){if(!r||0===r.length)return{allowed:!0};if("true"===process.env.DISABLE_SQLITE_AUTO_BACKUP)return d(u,e,r);if(!t())return d(a,e,r);let i=await l(),n=[Math.floor(Date.now()/1e3)];for(let e of r)n.push(e.limit,e.window);try{let r=await i.eval(s,1,`rl:api_key:${e}`,...n);if(0===r[0])return{allowed:!1,failedWindow:r[1]};return{allowed:!0}}catch(e){return console.error("[RATE_LIMITER] Redis eval failed, bypassing rate limit:",e),{allowed:!0}}}e.s(["checkRateLimit",0,w,"getRedisClient",0,l,"isRedisConfigured",0,t])},906538,e=>{e.v(r=>Promise.all(["server/chunks/[externals]__0b7vdvs._.js","server/chunks/node_modules_217wseu._.js"].map(r=>e.l(r))).then(()=>r(842512)))}];

//# sourceMappingURL=_10j2jzu._.js.map