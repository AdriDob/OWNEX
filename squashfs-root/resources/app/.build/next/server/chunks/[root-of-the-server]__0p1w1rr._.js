module.exports=[13985,e=>{"use strict";var t=e.i(899378);function n(e){if(null===e)return null;try{return JSON.stringify(e)}catch{return null}}function r(e){let t=e&&"object"==typeof e?e:{};return{id:"number"==typeof t.id?t.id:0,tool:"string"==typeof t.tool?t.tool:"",currentVersion:null===t.current_version?null:"string"==typeof t.current_version?t.current_version:null,installedVersion:null===t.installed_version?null:"string"==typeof t.installed_version?t.installed_version:null,pinnedVersion:null===t.pinned_version?null:"string"==typeof t.pinned_version?t.pinned_version:null,binaryPath:null===t.binary_path?null:"string"==typeof t.binary_path?t.binary_path:null,status:"string"==typeof t.status?t.status:"not_installed",pid:null===t.pid?null:"number"==typeof t.pid?t.pid:null,port:"number"==typeof t.port?t.port:8317,apiKey:null===t.api_key?null:"string"==typeof t.api_key?t.api_key:null,managementKey:null===t.management_key?null:"string"==typeof t.management_key?t.management_key:null,autoUpdate:1===t.auto_update||!0===t.auto_update||"1"===t.auto_update,autoStart:1===t.auto_start||!0===t.auto_start||"1"===t.auto_start,lastHealthCheck:null===t.last_health_check?null:"string"==typeof t.last_health_check?t.last_health_check:null,lastUpdateCheck:null===t.last_update_check?null:"string"==typeof t.last_update_check?t.last_update_check:null,healthStatus:"string"==typeof t.health_status?t.health_status:"unknown",configOverrides:function(e){if(!e||"string"!=typeof e||""===e.trim())return null;try{let t=JSON.parse(e);return"object"==typeof t&&null!==t?t:null}catch{return null}}(t.config_overrides),errorMessage:null===t.error_message?null:"string"==typeof t.error_message?t.error_message:null,createdAt:"string"==typeof t.created_at?t.created_at:"",updatedAt:"string"==typeof t.updated_at?t.updated_at:"",logsBufferPath:null===t.logs_buffer_path?null:"string"==typeof t.logs_buffer_path?t.logs_buffer_path:null,providerExpose:1===t.provider_expose||!0===t.provider_expose||"1"===t.provider_expose,lastSyncAt:null===t.last_sync_at?null:"string"==typeof t.last_sync_at?t.last_sync_at:null}}async function a(){return(0,t.getDbInstance)().prepare("SELECT * FROM version_manager").all().map(r)}async function o(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM version_manager WHERE tool = ?").get(e);return n?r(n):null}async function s(e){(0,t.getDbInstance)().prepare(`
    INSERT INTO version_manager (
      tool, current_version, installed_version, pinned_version, binary_path,
      status, pid, port, api_key, management_key, auto_update, auto_start,
      health_status, config_overrides, error_message, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    ON CONFLICT(tool) DO UPDATE SET
      current_version = excluded.current_version,
      installed_version = excluded.installed_version,
      pinned_version = excluded.pinned_version,
      binary_path = excluded.binary_path,
      status = excluded.status,
      pid = excluded.pid,
      port = excluded.port,
      api_key = excluded.api_key,
      management_key = excluded.management_key,
      auto_update = excluded.auto_update,
      auto_start = excluded.auto_start,
      health_status = excluded.health_status,
      config_overrides = excluded.config_overrides,
      error_message = excluded.error_message,
      updated_at = datetime('now')
  `).run(e.tool,e.currentVersion??null,e.installedVersion??null,e.pinnedVersion??null,e.binaryPath??null,e.status??"not_installed",e.pid??null,e.port??8317,e.apiKey??null,e.managementKey??null,void 0!==e.autoUpdate?+!!e.autoUpdate:1,void 0!==e.autoStart?+!!e.autoStart:0,e.healthStatus??"unknown",n(e.configOverrides??null),e.errorMessage??null);let r=await o(e.tool);if(!r)throw Error("Failed to retrieve inserted version manager tool");return r}async function i(e,r){let a=(0,t.getDbInstance)();if(!await o(e))return null;let s=new Set(["currentVersion","installedVersion","pinnedVersion","binaryPath","status","pid","port","apiKey","managementKey","autoUpdate","autoStart","healthStatus","configOverrides","errorMessage","logsBufferPath","providerExpose","lastSyncAt"]),i=["updated_at = datetime('now')"],l={tool:e};for(let[e,t]of Object.entries(r)){if(!s.has(e))continue;let r=e.replace(/([A-Z])/g,"_$1").toLowerCase();"configOverrides"===e?(i.push("config_overrides = @configOverrides"),l.configOverrides=n(t)):"autoUpdate"===e||"autoStart"===e||"providerExpose"===e?(i.push(`${r} = @${e}`),l[e]=+(!0===t)):null===t?i.push(`${r} = null`):(i.push(`${r} = @${e}`),l[e]=t)}return a.prepare(`UPDATE version_manager SET ${i.join(", ")} WHERE tool = @tool`).run(l),o(e)}async function l(e){return(0,t.getDbInstance)().prepare("DELETE FROM version_manager WHERE tool = ?").run(e).changes>0}async function u(e,n){return(0,t.getDbInstance)().prepare("UPDATE version_manager SET health_status = ?, last_health_check = datetime('now') WHERE tool = ?").run(n,e).changes>0}async function c(e,n,r){return(0,t.getDbInstance)().prepare(`UPDATE version_manager SET ${n} = ?, updated_at = datetime('now') WHERE tool = ?`).run(r,e).changes>0}async function p(e,n,r,a){return(0,t.getDbInstance)().prepare(void 0!==r?"UPDATE version_manager SET status = ?, pid = ?, error_message = ?, updated_at = datetime('now') WHERE tool = ?":"UPDATE version_manager SET status = ?, error_message = ?, updated_at = datetime('now') WHERE tool = ?").run(...void 0!==r?[n,r,a??null,e]:[n,a??null,e]).changes>0}async function d(e){return o(e)}let _=new Set(["logsBufferPath","providerExpose","lastSyncAt","status","pid","port","apiKey","autoStart","autoUpdate","healthStatus","errorMessage","currentVersion","installedVersion","binaryPath"]);async function E(e,t,n){if(!_.has(t))throw Error(`updateServiceField: field "${t}" is not in the allowed list`);return i(e,{[t]:n})}e.s(["deleteVersionManagerTool",0,l,"getServiceRow",0,d,"getVersionManagerStatus",0,a,"getVersionManagerTool",0,o,"setToolStatus",0,p,"updateServiceField",0,E,"updateToolHealth",0,u,"updateToolVersion",0,c,"updateVersionManagerTool",0,i,"upsertVersionManagerTool",0,s])},97793,e=>{"use strict";let t=new Set(["host","connection","content-length","keep-alive","proxy-connection","transfer-encoding","te","trailer","upgrade"].map(e=>e.toLowerCase()));function n(e){return t.has(String(e).trim().toLowerCase())}let r=new Set(["authorization","x-api-key","x-goog-api-key","api-key","cookie"].map(e=>e.toLowerCase()));e.s(["isForbiddenCustomHeaderName",0,function(e){let t=String(e).trim().toLowerCase();return n(t)||r.has(t)},"isForbiddenUpstreamHeaderName",0,n])},95638,684076,730901,e=>{"use strict";let t=new Uint8Array(16);e.s(["default",0,function(){return crypto.getRandomValues(t)}],95638);let n=/^(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/i;e.s(["default",0,function(e){return"string"==typeof e&&n.test(e)}],684076);let r=[];for(let e=0;e<256;++e)r.push((e+256).toString(16).slice(1));e.s(["unsafeStringify",0,function(e,t=0){return(r[e[t+0]]+r[e[t+1]]+r[e[t+2]]+r[e[t+3]]+"-"+r[e[t+4]]+r[e[t+5]]+"-"+r[e[t+6]]+r[e[t+7]]+"-"+r[e[t+8]]+r[e[t+9]]+"-"+r[e[t+10]]+r[e[t+11]]+r[e[t+12]]+r[e[t+13]]+r[e[t+14]]+r[e[t+15]]).toLowerCase()}],730901)},689960,e=>{"use strict";var t=e.i(95638),n=e.i(730901);e.s(["v4",0,function(e,r,a){return r||e||!crypto.randomUUID?function(e,r,a){let o=(e=e||{}).random??e.rng?.()??(0,t.default)();if(o.length<16)throw Error("Random bytes length must be >= 16");if(o[6]=15&o[6]|64,o[8]=63&o[8]|128,r){if((a=a||0)<0||a+16>r.length)throw RangeError(`UUID byte range ${a}:${a+15} is out of buffer bounds`);for(let e=0;e<16;++e)r[a+e]=o[e];return r}return(0,n.unsafeStringify)(o)}(e,r,a):crypto.randomUUID()}],689960)},705765,e=>{"use strict";let t={"gemini-pro":"gemini-2.5-pro","gemini-pro-vision":"gemini-2.5-pro","gemini-1.5-pro":"gemini-2.5-pro","gemini-1.5-flash":"gemini-2.5-flash","gemini-1.0-pro":"gemini-2.5-pro","gemini-2.0-flash":"gemini-2.5-flash","gemini-2.0-flash-lite":"gemini-3.1-flash-lite","gemini-3.1-flash-lite-preview":"gemini-3.1-flash-lite","gemini-3-pro-high":"gemini-3.1-pro-high","gemini-3-pro-low":"gemini-3.1-pro-low","gemma-4":"gemini-3.1-flash-lite","claude-3-opus-20240229":"claude-opus-4-20250514","claude-3-sonnet-20240229":"claude-sonnet-4-20250514","claude-3-haiku-20240307":"claude-3-5-sonnet-20241022","claude-3-5-sonnet-latest":"claude-sonnet-4-20250514","claude-3-5-haiku-latest":"claude-3-5-sonnet-20241022","gpt-4-turbo-preview":"gpt-4-turbo","gpt-4-0125-preview":"gpt-4-turbo","gpt-4-1106-preview":"gpt-4-turbo","gpt-3.5-turbo-0125":"gpt-3.5-turbo","accounts/fireworks/models/kimi-k2p5":"moonshotai/Kimi-K2.5","fireworks/accounts/fireworks/models/kimi-k2p5":"moonshotai/Kimi-K2.5","kimi-k2p5":"moonshotai/Kimi-K2.5","accounts/fireworks/models/kimi-k2":"moonshotai/Kimi-K2","fireworks/accounts/fireworks/models/kimi-k2":"moonshotai/Kimi-K2","kimi-k2":"moonshotai/Kimi-K2","mistral-large":"mistral-large-latest","mistral-small":"mistral-small-latest",codestral:"codestral-latest","codestral-2405":"codestral-2508","llama-3.3":"llama-3.3-70b-versatile","llama-3-70b":"llama-3.3-70b-versatile","llama-3-8b":"llama3-8b-8192"},n="__omniroute_customAliases__",r=globalThis;function a(){return r[n]||(r[n]={}),r[n]}e.s(["addCustomAlias",0,function(e,t){a()[e]=t},"getAllAliases",0,function(){return{...t,...a()}},"getBuiltInAliases",0,function(){return{...t}},"getCustomAliases",0,function(){return{...a()}},"removeCustomAlias",0,function(e){let t=a();return!!t[e]&&(delete t[e],!0)},"resolveModelAlias",0,function(e){if(!e)return e;let n=a();return n[e]?n[e]:t[e]?t[e]:e},"setCustomAliases",0,function(e){r[n]={...e}}])},677850,e=>e.a(async(t,n)=>{try{let t=await e.y("zod-dcb22c6336e0bc69");e.n(t),n()}catch(e){n(e)}},!0),666680,(e,t,n)=>{t.exports=e.x("node:crypto",()=>require("node:crypto"))},343379,e=>{"use strict";var t=e.i(899378);function n(e){return{agent_id:e.agent_id,dns_enabled:1===e.dns_enabled,cert_trusted:1===e.cert_trusted,setup_completed:1===e.setup_completed,last_started_at:e.last_started_at,last_error:e.last_error}}function r(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM agent_bridge_state WHERE agent_id = ?").get(e);return r?n(r):null}e.s(["getAgentBridgeState",0,r,"getAllAgentBridgeStates",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM agent_bridge_state ORDER BY agent_id ASC").all().map(n)},"setLastError",0,function(e,n){(0,t.getDbInstance)().prepare(`INSERT INTO agent_bridge_state (agent_id, last_error)
     VALUES (?, ?)
     ON CONFLICT(agent_id) DO UPDATE SET last_error = excluded.last_error`).run(e,n)},"setLastStarted",0,function(e,n){(0,t.getDbInstance)().prepare(`INSERT INTO agent_bridge_state (agent_id, last_started_at)
     VALUES (?, ?)
     ON CONFLICT(agent_id) DO UPDATE SET last_started_at = excluded.last_started_at`).run(e,n)},"upsertAgentBridgeState",0,function(e){let n=(0,t.getDbInstance)();if(r(e.agent_id)){let t=[],r=[];if(void 0!==e.dns_enabled&&(t.push("dns_enabled = ?"),r.push(+!!e.dns_enabled)),void 0!==e.cert_trusted&&(t.push("cert_trusted = ?"),r.push(+!!e.cert_trusted)),void 0!==e.setup_completed&&(t.push("setup_completed = ?"),r.push(+!!e.setup_completed)),void 0!==e.last_started_at&&(t.push("last_started_at = ?"),r.push(e.last_started_at)),void 0!==e.last_error&&(t.push("last_error = ?"),r.push(e.last_error)),0===t.length)return;r.push(e.agent_id),n.prepare(`UPDATE agent_bridge_state SET ${t.join(", ")} WHERE agent_id = ?`).run(...r)}else n.prepare(`INSERT INTO agent_bridge_state
         (agent_id, dns_enabled, cert_trusted, setup_completed, last_started_at, last_error)
       VALUES (?, ?, ?, ?, ?, ?)`).run(e.agent_id,void 0!==e.dns_enabled?+!!e.dns_enabled:0,void 0!==e.cert_trusted?+!!e.cert_trusted:0,void 0!==e.setup_completed?+!!e.setup_completed:0,e.last_started_at??null,e.last_error??null)}])},682815,e=>{"use strict";var t=e.i(899378);function n(e){return{host:e.host,enabled:1===e.enabled,label:e.label,kind:e.kind,added_at:e.added_at,last_seen_at:e.last_seen_at}}e.s(["addCustomHost",0,function(e,n="custom",r){let a=(0,t.getDbInstance)(),o=new Date().toISOString();a.prepare(`INSERT OR IGNORE INTO inspector_custom_hosts (host, enabled, label, kind, added_at)
     VALUES (?, 1, ?, ?, ?)`).run(e,r??null,n,o)},"isCustomHost",0,function(e){return void 0!==(0,t.getDbInstance)().prepare("SELECT 1 AS found FROM inspector_custom_hosts WHERE host = ? AND enabled = 1").get(e)},"listCustomHosts",0,function(e){let r=(0,t.getDbInstance)();return(e?.enabledOnly===!0?r.prepare("SELECT * FROM inspector_custom_hosts WHERE enabled = 1 ORDER BY host ASC").all():r.prepare("SELECT * FROM inspector_custom_hosts ORDER BY host ASC").all()).map(n)},"removeCustomHost",0,function(e){(0,t.getDbInstance)().prepare("DELETE FROM inspector_custom_hosts WHERE host = ?").run(e)},"toggleCustomHost",0,function(e,n){(0,t.getDbInstance)().prepare("UPDATE inspector_custom_hosts SET enabled = ? WHERE host = ?").run(+!!n,e)},"touchLastSeen",0,function(e){let n=(0,t.getDbInstance)(),r=new Date().toISOString();n.prepare("UPDATE inspector_custom_hosts SET last_seen_at = ? WHERE host = ?").run(r,e)}])},620457,e=>{"use strict";var t=e.i(899378);function n(e){return{pattern:e.pattern,source:e.source,created_at:e.created_at}}e.s(["getAllBypassPatterns",0,function(){return(0,t.getDbInstance)().prepare("SELECT pattern, source, created_at FROM agent_bridge_bypass ORDER BY source ASC, pattern ASC").all().map(n)},"getUserBypassPatterns",0,function(){return(0,t.getDbInstance)().prepare("SELECT pattern FROM agent_bridge_bypass WHERE source = 'user' ORDER BY pattern ASC").all().map(e=>e.pattern)},"replaceUserBypassPatterns",0,function(e){let n=(0,t.getDbInstance)(),r=new Date().toISOString(),a=n.prepare("DELETE FROM agent_bridge_bypass WHERE source = 'user'"),o=n.prepare("INSERT INTO agent_bridge_bypass (pattern, source, created_at) VALUES (?, 'user', ?)");n.transaction(()=>{for(let t of(a.run(),e))o.run(t,r)})()},"seedDefaultBypassPatterns",0,function(e){let n=(0,t.getDbInstance)(),r=new Date().toISOString(),a=n.prepare("INSERT OR IGNORE INTO agent_bridge_bypass (pattern, source, created_at) VALUES (?, 'default', ?)");n.transaction(()=>{for(let t of e)a.run(t,r)})()}])},686174,e=>e.a(async(t,n)=>{try{var r=e.i(677850),a=t([r]);[r]=a.then?(await a)():a;let o=r.z.object({id:r.z.string().uuid(),source:r.z.enum(["agent-bridge","custom-host","http-proxy","system-proxy","tproxy"]),agent:r.z.string().optional(),timestamp:r.z.string().datetime(),method:r.z.string(),host:r.z.string(),path:r.z.string(),requestHeaders:r.z.record(r.z.string(),r.z.string()),requestBody:r.z.string().nullable(),requestSize:r.z.number().int().nonnegative(),responseHeaders:r.z.record(r.z.string(),r.z.string()),responseBody:r.z.string().nullable(),responseSize:r.z.number().int().nonnegative(),status:r.z.union([r.z.number().int(),r.z.literal("in-flight"),r.z.literal("error")]),proxyLatencyMs:r.z.number().nonnegative().optional(),upstreamLatencyMs:r.z.number().nonnegative().optional(),totalLatencyMs:r.z.number().nonnegative().optional(),error:r.z.string().optional(),sourceModel:r.z.string().nullable().optional(),mappedModel:r.z.string().nullable().optional(),detectedKind:r.z.enum(["llm","app","unknown"]).optional(),contextKey:r.z.string().optional(),annotation:r.z.string().optional(),sessionId:r.z.string().uuid().optional(),note:r.z.string().optional(),pid:r.z.number().int().nonnegative().optional(),processName:r.z.string().optional()});e.s(["InterceptedRequestSchema",0,o]),n()}catch(e){n(e)}},!1),519854,e=>e.a(async(t,n)=>{try{var r=e.i(254799),a=e.i(899378),o=e.i(686174),s=t([o]);function i(e){return{id:e.id,name:e.name,started_at:e.started_at,ended_at:e.ended_at,request_count:e.request_count,profile:e.profile}}function l(e){let t=(0,a.getDbInstance)().prepare("SELECT * FROM inspector_sessions WHERE id = ?").get(e);return t?i(t):null}function u(e){return(0,a.getDbInstance)().prepare("SELECT seq, payload FROM inspector_session_requests WHERE session_id = ? ORDER BY seq ASC").all(e).map(e=>({seq:e.seq,payload:e.payload}))}[o]=s.then?(await s)():s,e.s(["appendSessionRequest",0,function(e,t){let n=(0,a.getDbInstance)(),r=0;return n.transaction(()=>{let a=n.prepare("SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM inspector_session_requests WHERE session_id = ?").get(e).next_seq;n.prepare("INSERT INTO inspector_session_requests (session_id, seq, payload) VALUES (?, ?, ?)").run(e,a,t),n.prepare("UPDATE inspector_sessions SET request_count = request_count + 1 WHERE id = ?").run(e),r=a})(),r},"createSession",0,function(e){let t=(0,a.getDbInstance)(),n=(0,r.randomUUID)(),o=new Date().toISOString();return t.prepare("INSERT INTO inspector_sessions (id, name, started_at, profile) VALUES (?, ?, ?, ?)").run(n,e?.name??null,o,e?.profile??null),{id:n,started_at:o}},"deleteSession",0,function(e){(0,a.getDbInstance)().prepare("DELETE FROM inspector_sessions WHERE id = ?").run(e)},"getSession",0,l,"getSessionRequests",0,u,"listSessions",0,function(){return(0,a.getDbInstance)().prepare("SELECT * FROM inspector_sessions ORDER BY started_at DESC").all().map(i)},"renameSession",0,function(e,t){(0,a.getDbInstance)().prepare("UPDATE inspector_sessions SET name = ? WHERE id = ?").run(t,e)},"snapshotSession",0,function(e){let t=l(e);if(null===t)return null;let n=u(e),r=[];for(let e of n){let t;try{t=JSON.parse(e.payload)}catch{continue}let n=o.InterceptedRequestSchema.safeParse(t);n.success&&r.push(n.data)}return r},"stopSession",0,function(e){let t=(0,a.getDbInstance)(),n=new Date().toISOString();t.prepare("UPDATE inspector_sessions SET ended_at = ? WHERE id = ?").run(n,e)}]),n()}catch(e){n(e)}},!1),436231,e=>{"use strict";e.s(["calculateLevel",0,function(e){return e<=0?1:Math.max(1,Math.floor(Math.pow(2.5*e/100,.4)))},"getLevelTier",0,function(e){return e>=76?"diamond":e>=51?"platinum":e>=26?"gold":e>=11?"silver":"bronze"},"getLevelTitle",0,function(e){return e>=76?"Legend":e>=51?"Master":e>=26?"Expert":e>=11?"Explorer":"Beginner"}])},850803,e=>{"use strict";var t=e.i(899378),n=e.i(436231);function r(){return(0,t.getDbInstance)()}function a(e){let t=r().prepare("SELECT COALESCE(SUM(amount), 0) AS total FROM token_ledger WHERE to_api_key_id = ?").get(e),n=r().prepare("SELECT COALESCE(SUM(amount), 0) AS total FROM token_ledger WHERE from_api_key_id = ?").get(e);return t.total-n.total}e.s(["addXp",0,function(e,t,a,o){r().prepare(`INSERT INTO xp_audit_log (api_key_id, action, xp_earned, metadata)
     VALUES (?, ?, ?, ?)`).run(e,t,a,o??null),r().prepare(`INSERT INTO user_levels (api_key_id, total_xp, current_level, updated_at)
     VALUES (?, ?, ?, datetime('now'))
     ON CONFLICT(api_key_id)
     DO UPDATE SET total_xp = total_xp + excluded.total_xp, updated_at = datetime('now')`).run(e,a,(0,n.calculateLevel)(a))},"connectServer",0,function(e,t,n,a){r().prepare(`INSERT OR REPLACE INTO community_servers (id, name, url, api_key_hash)
     VALUES (?, ?, ?, ?)`).run(e,t,n,a)},"createInviteToken",0,function(e,t,n,a,o,s){r().prepare(`INSERT INTO invite_tokens (id, code, token_hash, created_by, server_url, max_uses)
     VALUES (?, ?, ?, ?, ?, ?)`).run(e,t,n,a,o??null,s??1)},"disconnectServer",0,function(e){r().prepare("UPDATE community_servers SET status = 'disconnected' WHERE id = ?").run(e)},"getAggregateXp",0,function(){let e=r().prepare(`SELECT COALESCE(SUM(total_xp), 0) AS total_xp,
              COALESCE(MAX(current_level), 1) AS current_level,
              MAX(updated_at) AS updated_at
       FROM user_levels`).get();return{apiKeyId:"*",totalXp:e?.total_xp??0,currentLevel:e?.current_level??1,updatedAt:e?.updated_at??""}},"getAllEarnedBadges",0,function(){return r().prepare(`SELECT ub.badge_id, MIN(ub.unlocked_at) AS unlocked_at,
              bd.name, bd.description, bd.icon, bd.category, bd.rarity
       FROM user_badges ub
       JOIN badge_definitions bd ON bd.id = ub.badge_id
       GROUP BY ub.badge_id`).all().map(e=>({apiKeyId:"*",badgeId:e.badge_id,unlockedAt:e.unlocked_at,badgeName:e.name,badgeDescription:e.description,badgeIcon:e.icon,badgeCategory:e.category,badgeRarity:e.rarity}))},"getBadgeDefinitions",0,function(e){let t=e?"SELECT * FROM badge_definitions WHERE category = ?":"SELECT * FROM badge_definitions";return(e?r().prepare(t).all(e):r().prepare(t).all()).map(e=>({id:e.id,name:e.name,description:e.description,icon:e.icon,category:e.category,rarity:e.rarity,criteria:e.criteria,hidden:e.hidden,createdAt:e.created_at}))},"getBadges",0,function(e){return r().prepare(`SELECT ub.api_key_id, ub.badge_id, ub.unlocked_at,
            bd.name, bd.description, bd.icon, bd.category, bd.rarity
     FROM user_badges ub
     JOIN badge_definitions bd ON bd.id = ub.badge_id
     WHERE ub.api_key_id = ?`).all(e).map(e=>({apiKeyId:e.api_key_id,badgeId:e.badge_id,unlockedAt:e.unlocked_at,badgeName:e.name,badgeDescription:e.description,badgeIcon:e.icon,badgeCategory:e.category,badgeRarity:e.rarity}))},"getBalance",0,a,"getConnectedServerByKeyHash",0,function(e){return r().prepare("SELECT id FROM community_servers WHERE api_key_hash = ? AND status = 'connected'").get(e)},"getHistory",0,function(e,t){return r().prepare(`SELECT * FROM token_ledger
     WHERE from_api_key_id = ? OR to_api_key_id = ?
     ORDER BY created_at DESC LIMIT ?`).all(e,e,t).map(e=>({id:e.id,fromApiKeyId:e.from_api_key_id,toApiKeyId:e.to_api_key_id,amount:e.amount,reason:e.reason,idempotencyKey:e.idempotency_key,createdAt:e.created_at}))},"getInviteByCode",0,function(e){let t=r().prepare("SELECT * FROM invite_tokens WHERE code = ?").get(e);return t?{id:t.id,code:t.code,tokenHash:t.token_hash,createdBy:t.created_by,usedBy:t.used_by,serverUrl:t.server_url,maxUses:t.max_uses,useCount:t.use_count,expiresAt:t.expires_at,revokedAt:t.revoked_at,createdAt:t.created_at}:null},"getLeaderboardNeighbors",0,function(e,t,n=5){let a=r(),o=a.prepare("SELECT score FROM leaderboard WHERE api_key_id = ? AND scope = ?").get(e,t);if(!o)return{above:[],below:[]};let s=a.prepare(`SELECT api_key_id, score FROM leaderboard
       WHERE scope = ? AND score > ?
       ORDER BY score ASC LIMIT ?`).all(t,o.score,n),i=a.prepare(`SELECT api_key_id, score FROM leaderboard
       WHERE scope = ? AND score < ?
       ORDER BY score DESC LIMIT ?`).all(t,o.score,n);return{above:s.reverse().map(e=>({apiKeyId:e.api_key_id,score:e.score})),below:i.map(e=>({apiKeyId:e.api_key_id,score:e.score}))}},"getRank",0,function(e,t){let n=r().prepare("SELECT score FROM leaderboard WHERE api_key_id = ? AND scope = ?").get(e,t);return n?r().prepare("SELECT COUNT(*) + 1 AS rank FROM leaderboard WHERE scope = ? AND score > ?").get(t,n.score).rank:0},"getTopN",0,function(e,t,n=0){return r().prepare(`SELECT api_key_id, scope, score, updated_at FROM leaderboard
     WHERE scope = ? ORDER BY score DESC LIMIT ? OFFSET ?`).all(e,t,n).map(e=>({apiKeyId:e.api_key_id,scope:e.scope,score:e.score,updatedAt:e.updated_at}))},"getXp",0,function(e){let t=r().prepare("SELECT api_key_id, total_xp, current_level, updated_at FROM user_levels WHERE api_key_id = ?").get(e);return t?{apiKeyId:t.api_key_id,totalXp:t.total_xp,currentLevel:t.current_level,updatedAt:t.updated_at}:null},"hasBadge",0,function(e,t){return!!r().prepare("SELECT 1 FROM user_badges WHERE api_key_id = ? AND badge_id = ? LIMIT 1").get(e,t)},"listServers",0,function(){return r().prepare("SELECT id, name, url, connected_at, last_sync_at, status, error_message FROM community_servers").all().map(e=>({id:e.id,name:e.name,url:e.url,connectedAt:e.connected_at,lastSyncAt:e.last_sync_at,status:e.status,errorMessage:e.error_message}))},"redeemInvite",0,function(e,t){return r().prepare(`UPDATE invite_tokens
     SET use_count = use_count + 1, used_by = ?
     WHERE code = ? AND revoked_at IS NULL
       AND use_count < max_uses
       AND (expires_at IS NULL OR expires_at > datetime('now'))`).run(t,e).changes>0},"revokeInvite",0,function(e){r().prepare("UPDATE invite_tokens SET revoked_at = datetime('now') WHERE id = ?").run(e)},"rotateLeaderboardScope",0,function(e){let t=r(),n="weekly"===e?`week_${new Date().toISOString().slice(0,10)}`:`month_${new Date().toISOString().slice(0,7)}`;if(t.prepare("SELECT COUNT(*) AS cnt FROM leaderboard WHERE scope = ?").get(n).cnt>0)return;let a=t.prepare("SELECT api_key_id, score, updated_at FROM leaderboard WHERE scope = ?").all(e);if(a.length>0){let e=t.prepare("INSERT OR IGNORE INTO leaderboard (api_key_id, scope, score, updated_at) VALUES (?, ?, ?, ?)");for(let t of a)e.run(t.api_key_id,n,t.score,t.updated_at)}t.prepare("DELETE FROM leaderboard WHERE scope = ?").run(e)},"transferTokens",0,function(e,n,r,o,s){let i=(0,t.getDbInstance)();return i.transaction(()=>i.prepare("SELECT id FROM token_ledger WHERE idempotency_key = ?").get(s)?{success:!0}:a(e)<r?{success:!1,error:"insufficient_balance"}:(i.prepare(`INSERT INTO token_ledger (from_api_key_id, to_api_key_id, amount, reason, idempotency_key)
         VALUES (?, ?, ?, ?, ?)`).run(e,n,r,o,s),{success:!0}))()},"unlockBadge",0,function(e,t){r().prepare("INSERT OR IGNORE INTO user_badges (api_key_id, badge_id) VALUES (?, ?)").run(e,t)},"updateLevel",0,function(e,t){r().prepare(`INSERT INTO user_levels (api_key_id, total_xp, current_level, updated_at)
     VALUES (?, 0, ?, datetime('now'))
     ON CONFLICT(api_key_id)
     DO UPDATE SET current_level = ?, updated_at = datetime('now')`).run(e,t,t)},"updateScore",0,function(e,t,n){r().prepare(`INSERT INTO leaderboard (api_key_id, scope, score, updated_at)
     VALUES (?, ?, ?, datetime('now'))
     ON CONFLICT(api_key_id, scope)
     DO UPDATE SET score = score + excluded.score, updated_at = datetime('now')`).run(e,t,n)}])},795769,e=>{"use strict";var t=e.i(666680),n=e.i(899378),r=e.i(529646);function a(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM relay_tokens WHERE id = ?").get(e);return t?{...(0,r.rowToCamel)(t),enabled:1===t.enabled}:null}e.s(["checkRateLimit",0,function(e,t){let a=(0,n.getDbInstance)(),o=t;if(!o){let t=a.prepare("SELECT * FROM relay_tokens WHERE id = ?").get(e);if(!t)return{allowed:!1,remaining:0,resetIn:0};o=(0,r.rowToCamel)(t)}let s=Math.floor(Date.now()/1e3),i=60*Math.floor(s/60),l=86400*Math.floor(s/86400),u=a.prepare("SELECT request_count, cost FROM relay_rate_limits WHERE token_id = ? AND window_start = ?").get(e,i),c=u?.request_count||0;if(c>=o.maxRequestsPerMinute)return{allowed:!1,remaining:0,resetIn:60-s%60};let p=a.prepare("SELECT SUM(request_count) as total FROM relay_rate_limits WHERE token_id = ? AND window_start >= ?").get(e,l),d=p?.total||0;return d>=o.maxRequestsPerDay?{allowed:!1,remaining:0,resetIn:86400-s%86400}:{allowed:!0,remaining:Math.min(o.maxRequestsPerMinute-c,o.maxRequestsPerDay-d),resetIn:60-s%60}},"createRelayToken",0,function(a){let o=(0,n.getDbInstance)(),s="rl_"+(0,t.randomBytes)(16).toString("hex"),i="relay_"+(0,t.randomBytes)(24).toString("hex"),l=function(t){let{createHash:n}=e.r(666680);return n("sha256").update(t).digest("hex")}(i),u=Math.floor(Date.now()/1e3),c="rl_"+i.slice(6,14);o.prepare(`
    INSERT INTO relay_tokens (id, name, token_hash, token_prefix, description, combo_id, allowed_models,
      max_tokens_per_request, max_requests_per_minute, max_requests_per_day, max_cost_per_day,
      enabled, created_at, updated_at, expires_at, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
  `).run(s,a.name,l,c,a.description||"",a.comboId||null,JSON.stringify(a.allowedModels||["*"]),a.maxTokensPerRequest||128e3,a.maxRequestsPerMinute||60,a.maxRequestsPerDay||1e4,a.maxCostPerDay||0,u,u,a.expiresAt||null,JSON.stringify(a.metadata||{}));let p=o.prepare("SELECT * FROM relay_tokens WHERE id = ?").get(s);return{...(0,r.rowToCamel)(p),rawToken:i}},"deleteRelayToken",0,function(e){(0,n.getDbInstance)().prepare("DELETE FROM relay_tokens WHERE id = ?").run(e)},"getRelayLogs",0,function(e,t=50){let r=(0,n.getDbInstance)();return e?r.prepare("SELECT * FROM relay_logs WHERE token_id = ? ORDER BY created_at DESC LIMIT ?").all(e,t):r.prepare("SELECT * FROM relay_logs ORDER BY created_at DESC LIMIT ?").all(t)},"getRelayToken",0,a,"getRelayTokenByHash",0,function(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM relay_tokens WHERE token_hash = ? AND enabled = 1").get(e);return t?{...(0,r.rowToCamel)(t),enabled:1===t.enabled}:null},"getRelayTokens",0,function(){return(0,n.getDbInstance)().prepare("SELECT * FROM relay_tokens ORDER BY created_at DESC").all().map(e=>({...(0,r.rowToCamel)(e),enabled:1===e.enabled}))},"getRelayUsage",0,function(e,t){let r=(0,n.getDbInstance)().prepare("SELECT COUNT(*) as request_count, COALESCE(SUM(cost), 0) as total_cost FROM relay_logs WHERE token_id = ? AND created_at >= ?").get(e,t);return{requestCount:r.request_count,totalCost:r.total_cost}},"recordRelayUsage",0,function(e,t){let r=(0,n.getDbInstance)(),a=Math.floor(Date.now()/1e3),o=60*Math.floor(a/60);r.prepare(`
    INSERT INTO relay_rate_limits (token_id, window_start, request_count, cost)
    VALUES (?, ?, 1, ?)
    ON CONFLICT(token_id, window_start) DO UPDATE SET
      request_count = request_count + 1,
      cost = cost + ?
  `).run(e,o,t.cost||0,t.cost||0),r.prepare("UPDATE relay_tokens SET last_used_at = ? WHERE id = ?").run(a,e),r.prepare(`
    INSERT INTO relay_logs (token_id, request_id, model, prompt_tokens, completion_tokens, cost,
      status, status_code, latency_ms, client_ip, user_agent, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(e,t.requestId||null,t.model||null,t.promptTokens||0,t.completionTokens||0,t.cost||0,t.status||"success",t.statusCode||200,t.latencyMs||0,t.clientIp||null,t.userAgent||null,a)},"toggleRelayToken",0,function(e,t){let r=(0,n.getDbInstance)(),o=Math.floor(Date.now()/1e3);return r.prepare("UPDATE relay_tokens SET enabled = ?, updated_at = ? WHERE id = ?").run(+!!t,o,e),a(e)},"updateRelayToken",0,function(e,t){let r=(0,n.getDbInstance)(),o=Math.floor(Date.now()/1e3),s=["updated_at = ?"],i=[o];return void 0!==t.name&&(s.push("name = ?"),i.push(t.name)),void 0!==t.description&&(s.push("description = ?"),i.push(t.description)),void 0!==t.comboId&&(s.push("combo_id = ?"),i.push(t.comboId)),void 0!==t.allowedModels&&(s.push("allowed_models = ?"),i.push(JSON.stringify(t.allowedModels))),void 0!==t.maxTokensPerRequest&&(s.push("max_tokens_per_request = ?"),i.push(t.maxTokensPerRequest)),void 0!==t.maxRequestsPerMinute&&(s.push("max_requests_per_minute = ?"),i.push(t.maxRequestsPerMinute)),void 0!==t.maxRequestsPerDay&&(s.push("max_requests_per_day = ?"),i.push(t.maxRequestsPerDay)),void 0!==t.maxCostPerDay&&(s.push("max_cost_per_day = ?"),i.push(t.maxCostPerDay)),i.push(e),r.prepare(`UPDATE relay_tokens SET ${s.join(", ")} WHERE id = ?`).run(...i),a(e)}])},926028,e=>{"use strict";var t=e.i(689960),n=e.i(935050),r=e.i(899378),a=e.i(529646);let o="default-caveman",s="Standard Savings",i="Default RTK + Caveman compression pipeline";function l(){return[{engine:"rtk",intensity:"standard"},{engine:"caveman",intensity:"full"}]}function u(e,t){if(Array.isArray(e))return e;if("string"!=typeof e)return t;try{let n=JSON.parse(e);return Array.isArray(n)?n:t}catch{return t}}let c=["lite","caveman","aggressive","ultra","rtk","headroom","session-dedup","ccr","llmlingua","relevance"];function p(e){return u(e,[]).filter(e=>e&&"object"==typeof e&&c.includes(String(e.engine)))}function d(){let e=(0,r.getDbInstance)();e.exec(`
    CREATE TABLE IF NOT EXISTS compression_combos (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT DEFAULT '',
      pipeline TEXT NOT NULL DEFAULT '[]',
      language_packs TEXT DEFAULT '["en"]',
      output_mode INTEGER DEFAULT 0,
      output_mode_intensity TEXT DEFAULT 'full',
      is_default INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS compression_combo_assignments (
      id TEXT PRIMARY KEY,
      compression_combo_id TEXT NOT NULL REFERENCES compression_combos(id) ON DELETE CASCADE,
      routing_combo_id TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now')),
      UNIQUE(routing_combo_id)
    );

    CREATE INDEX IF NOT EXISTS idx_compression_combos_default
      ON compression_combos(is_default);
    CREATE INDEX IF NOT EXISTS idx_compression_combo_assignments_combo
      ON compression_combo_assignments(compression_combo_id);
    CREATE INDEX IF NOT EXISTS idx_compression_combo_assignments_routing
      ON compression_combo_assignments(routing_combo_id);
  `),e.prepare(`
    INSERT OR IGNORE INTO compression_combos (
      id, name, description, pipeline, language_packs, output_mode, output_mode_intensity, is_default
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(o,s,i,JSON.stringify(l()),JSON.stringify(["en"]),0,"full",1),function(){let e=(0,r.getDbInstance)(),t=e.prepare("SELECT name, description, pipeline FROM compression_combos WHERE id = ?").get(o);if(!t)return;let n=String(t.description??"");String(t.name??"")===s&&("Default Caveman compression pipeline"===n||n===i)&&function(e){if(1!==e.length)return!1;let[t]=e;return"caveman"===t.engine&&(void 0===t.intensity||"full"===t.intensity)}(p(t.pipeline))&&e.prepare(`
    UPDATE compression_combos
    SET description = ?, pipeline = ?, updated_at = ?
    WHERE id = ?
  `).run(i,JSON.stringify(l()),new Date().toISOString(),o)}()}function _(e){let t;if(!e)return null;let n=(0,a.rowToCamel)(e);return{id:String(n.id),name:String(n.name??""),description:String(n.description??""),pipeline:p(n.pipeline),languagePacks:[...new Set((t=u(n.languagePacks,["en"]).filter(e=>"string"==typeof e&&e.trim().length>0)).length>0?t.map(e=>e.trim()):["en"])],outputMode:!!n.outputMode,outputModeIntensity:String(n.outputModeIntensity??"full"),isDefault:!!n.isDefault,createdAt:String(n.createdAt??""),updatedAt:String(n.updatedAt??"")}}function E(e){if(!e)return null;let t=(0,a.rowToCamel)(e);return{id:String(t.id),compressionComboId:String(t.compressionComboId),routingComboId:String(t.routingComboId),createdAt:String(t.createdAt??"")}}function g(e,n){let r=new Date().toISOString();return{id:n?.id??e.id??(0,t.v4)(),name:e.name?.trim()||n?.name||"Compression Combo",description:e.description??n?.description??"",pipeline:e.pipeline&&e.pipeline.length>0?e.pipeline:n?.pipeline&&n.pipeline.length>0?n.pipeline:l(),languagePacks:e.languagePacks&&e.languagePacks.length>0?e.languagePacks:n?.languagePacks&&n.languagePacks.length>0?n.languagePacks:["en"],outputMode:e.outputMode??n?.outputMode??!1,outputModeIntensity:e.outputModeIntensity??n?.outputModeIntensity??"full",isDefault:e.isDefault??n?.isDefault??!1,createdAt:n?.createdAt??r,updatedAt:r}}function m(e){return d(),_((0,r.getDbInstance)().prepare("SELECT * FROM compression_combos WHERE id = ?").get(e))}function S(){return d(),_((0,r.getDbInstance)().prepare("SELECT * FROM compression_combos WHERE is_default = 1 ORDER BY updated_at DESC LIMIT 1").get())}let f={"session-dedup":3,ccr:4,lite:5,rtk:10,headroom:15,caveman:20,aggressive:30,llmlingua:35,ultra:40};e.s(["assignRoutingCombo",0,function(e,a){return d(),!!m(e)&&!!a.trim()&&((0,r.getDbInstance)().prepare(`
      INSERT OR REPLACE INTO compression_combo_assignments (
        id, compression_combo_id, routing_combo_id, created_at
      )
      VALUES (?, ?, ?, ?)
    `).run((0,t.v4)(),e,a.trim(),new Date().toISOString()),(0,n.backupDbFile)("pre-write"),!0)},"createCompressionCombo",0,function(e){d();let t=(0,r.getDbInstance)(),a=g(e);return t.transaction(()=>{a.isDefault&&t.prepare("UPDATE compression_combos SET is_default = 0").run(),t.prepare(`
      INSERT INTO compression_combos (
        id, name, description, pipeline, language_packs, output_mode, output_mode_intensity,
        is_default, created_at, updated_at
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(a.id,a.name,a.description,JSON.stringify(a.pipeline),JSON.stringify(a.languagePacks),+!!a.outputMode,a.outputModeIntensity,+!!a.isDefault,a.createdAt,a.updatedAt)})(),(0,n.backupDbFile)("pre-write"),m(a.id)},"deleteCompressionCombo",0,function(e){d();let t=m(e);if(!t||t.isDefault)return!1;let a=(0,r.getDbInstance)().prepare("DELETE FROM compression_combos WHERE id = ?").run(e);return a.changes>0&&(0,n.backupDbFile)("pre-write"),a.changes>0},"getAssignmentsForCompressionCombo",0,function(e){return d(),(0,r.getDbInstance)().prepare("SELECT * FROM compression_combo_assignments WHERE compression_combo_id = ? ORDER BY routing_combo_id").all(e).map(E).filter(e=>null!==e)},"getCompressionCombo",0,m,"getCompressionComboForRoutingCombo",0,function(e){return d(),_((0,r.getDbInstance)().prepare(`
      SELECT c.*
      FROM compression_combos c
      JOIN compression_combo_assignments a ON a.compression_combo_id = c.id
      WHERE a.routing_combo_id = ?
      LIMIT 1
    `).get(e))},"getDefaultCompressionCombo",0,S,"listCompressionCombos",0,function(){return d(),(0,r.getDbInstance)().prepare("SELECT * FROM compression_combos ORDER BY is_default DESC, name COLLATE NOCASE ASC").all().map(_).filter(e=>null!==e)},"setDefaultCompressionCombo",0,function(e){if(d(),!m(e))return!1;let t=(0,r.getDbInstance)(),a=new Date().toISOString();return t.transaction(()=>{t.prepare("UPDATE compression_combos SET is_default = 0").run(),t.prepare("UPDATE compression_combos SET is_default = 1, updated_at = ? WHERE id = ?").run(a,e)})(),(0,n.backupDbFile)("pre-write"),!0},"setEngineInDefaultCombo",0,function(e,t,a){if(!c.includes(e))return null;d();let o=S();if(!o)return null;let s=[...o.pipeline];if(t){let t=s.findIndex(t=>t.engine===e);t>=0?void 0!==a&&(s[t]={...s[t],config:a}):s.push({engine:e,...a?{config:a}:{}}),s.sort((e,t)=>(f[e.engine]??50)-(f[t.engine]??50))}else s=s.filter(t=>t.engine!==e);let i=(0,r.getDbInstance)(),l=new Date().toISOString();return i.prepare("UPDATE compression_combos SET pipeline = ?, updated_at = ? WHERE id = ?").run(JSON.stringify(s),l,o.id),(0,n.backupDbFile)("pre-write"),m(o.id)},"unassignRoutingCombo",0,function(e,t){d();let a=(0,r.getDbInstance)().prepare("DELETE FROM compression_combo_assignments WHERE compression_combo_id = ? AND routing_combo_id = ?").run(e,t);return a.changes>0&&(0,n.backupDbFile)("pre-write"),a.changes>0},"updateAssignments",0,function(e,a){if(d(),!m(e))return!1;let o=[...new Set(a.map(e=>e.trim()).filter(Boolean))],s=(0,r.getDbInstance)();return s.transaction(()=>{if(s.prepare("DELETE FROM compression_combo_assignments WHERE compression_combo_id = ?").run(e),o.length>0){let n=s.prepare("DELETE FROM compression_combo_assignments WHERE routing_combo_id = ?"),r=s.prepare(`
        INSERT INTO compression_combo_assignments (
          id, compression_combo_id, routing_combo_id, created_at
        )
        VALUES (?, ?, ?, ?)
      `);for(let a of o)n.run(a),r.run((0,t.v4)(),e,a,new Date().toISOString())}})(),(0,n.backupDbFile)("pre-write"),!0},"updateCompressionCombo",0,function(e,t){d();let a=m(e);if(!a)return null;let o=g(t,a),s=(0,r.getDbInstance)();return s.transaction(()=>{o.isDefault&&s.prepare("UPDATE compression_combos SET is_default = 0").run(),s.prepare(`
      UPDATE compression_combos
      SET name = ?, description = ?, pipeline = ?, language_packs = ?, output_mode = ?,
          output_mode_intensity = ?, is_default = ?, updated_at = ?
      WHERE id = ?
    `).run(o.name,o.description,JSON.stringify(o.pipeline),JSON.stringify(o.languagePacks),+!!o.outputMode,o.outputModeIntensity,+!!o.isDefault,o.updatedAt,e)})(),(0,n.backupDbFile)("pre-write"),m(e)}])},188693,e=>{"use strict";var t=e.i(899378);function n(e){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim()){let t=Number(e);return Number.isFinite(t)?t:null}return null}function r(e){return null!==e&&Number.isFinite(e)?Math.max(0,Math.min(100,e)):null}function a(e){let t=r(e);return null===t?null:Math.max(0,Math.min(100,100-t))}function o(e,t){return null!==e&&(t<=1&&e>t||e-t>=5)}function s(e){if(!e)return null;let t=Date.parse(e);return Number.isFinite(t)?new Date(t).toISOString():null}function i(e){let t=s(e);return t?t.slice(0,10):null}function l(e,n,u=Date.now()){let c=function(e,n,r=Date.now()){if(!e||!n)return null;let a=i(n);if(!a)return null;let o=(0,t.getDbInstance)(),l=new Date(r).toISOString();try{for(let t of o.prepare(`
        SELECT
          window_started_at as windowStartedAt,
          window_resets_at as windowResetsAt,
          observed_at as observedAt
        FROM provider_quota_reset_events
        WHERE connection_id = @connectionId
          AND LOWER(window_key) LIKE '%weekly%'
          AND LOWER(window_key) NOT LIKE '%sonnet%'
          AND observed_at <= @nowIso
        ORDER BY observed_at DESC, id DESC
      `).all({connectionId:e,nowIso:l}))if(i(t.windowResetsAt)===a)return s(t.windowStartedAt);return null}catch(e){if(e instanceof Error&&e.message.includes("no such table"))return null;throw e}}(e,n,u),p=function(e,n,l=Date.now()){if(!e||!n)return null;let u=i(n);if(!u)return null;let c=(0,t.getDbInstance)(),p=new Date(l).toISOString();try{let t=c.prepare(`
        SELECT
          next_reset_at as nextResetAt,
          remaining_percentage as remainingPercentage,
          created_at as createdAt
        FROM quota_snapshots
        WHERE connection_id = @connectionId
          AND LOWER(window_key) LIKE '%weekly%'
          AND LOWER(window_key) NOT LIKE '%sonnet%'
          AND created_at <= @nowIso
        ORDER BY created_at ASC, id ASC
      `).all({connectionId:e,nowIso:p}),n=null,l=null,d=null;for(let e of t){let t=s(e.createdAt);if(!t||i(e.nextResetAt)!==u)continue;n||(n=t);let c=a(r(e.remainingPercentage));null!==c&&(o(d,c)&&(l=t),d=c)}if(l)return{windowStartIso:l,resetDrop:!0};if(n)return{windowStartIso:n,resetDrop:!1};return null}catch(e){if(e instanceof Error&&e.message.includes("no such table"))return null;throw e}}(e,n,u);if(!c&&!p)return null;if(!c&&p)return{windowStartIso:p.windowStartIso,source:"observed_snapshot_reset"};if(c&&!p)return{windowStartIso:c,source:"recorded_reset_event"};let d=Date.parse(c),_=Date.parse(p.windowStartIso);return p.resetDrop&&Number.isFinite(d)&&Number.isFinite(_)&&_>d?{windowStartIso:p.windowStartIso,source:"observed_snapshot_reset"}:{windowStartIso:c,source:"recorded_reset_event"}}e.s(["getProviderQuotaWindowStart",0,l,"getProviderQuotaWindowStartIso",0,function(e,t,n=Date.now()){return l(e,t,n)?.windowStartIso??null},"recordProviderQuotaResetEventIfChanged",0,function(e){let l;if(!e.connectionId||!e.windowKey||!(((l=e.windowKey.toLowerCase().replace(/[^a-z0-9]+/g," ").trim()).includes("weekly")||l.includes("7d"))&&!l.includes("sonnet")))return;let u=s(e.currentResetAt);if(!u)return;let c=e.previousObservation??function(e,r){let a=(0,t.getDbInstance)();try{let t=a.prepare(`
        SELECT
          next_reset_at as nextResetAt,
          remaining_percentage as remainingPercentage
        FROM quota_snapshots
        WHERE connection_id = ?
          AND LOWER(window_key) = LOWER(?)
          AND next_reset_at IS NOT NULL
        ORDER BY created_at DESC, id DESC
        LIMIT 1
      `).get(e,r);if(!t)return null;return{resetAt:t.nextResetAt,remainingPercentage:n(t.remainingPercentage)}}catch(e){if(e instanceof Error&&e.message.includes("no such table"))return null;throw e}}(e.connectionId,e.windowKey),p=s(c?.resetAt??null);if(!p)return;let d=Date.parse(p),_=Date.parse(u);if(!Number.isFinite(d)||!Number.isFinite(_))return;let E=r(n(c?.remainingPercentage)),g=r(n(e.currentRemainingPercentage)),m=s(e.observedAt??null)??new Date().toISOString(),S=a(E),f=a(g),y=_>d&&i(p)!==i(u),b=i(p)===i(u)&&null!==f&&o(S,f);if(!y&&!b)return;let R=y?p:m;try{(0,t.getDbInstance)().prepare(`
      INSERT OR IGNORE INTO provider_quota_reset_events
        (provider, connection_id, window_key, window_started_at, window_resets_at,
         observed_at, previous_remaining_percentage, new_remaining_percentage,
         previous_used_percentage, new_used_percentage, raw_data)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(e.provider,e.connectionId,e.windowKey,R,u,m,E,g,S,f,null)}catch(e){if(e instanceof Error&&e.message.includes("no such table"))return;throw e}}])},315963,e=>{"use strict";var t=e.i(899378);function n(e,t){let n="string"==typeof e?e.trim():"",r="string"==typeof t?t.trim():"";return n&&r?{provider:n,modelId:r}:null}function r(e){return{provider:e.provider,modelId:e.model_id,realContext:e.real_context,source:"auto:discovery"===e.source?"auto:discovery":"manual",refreshedAt:e.refreshed_at}}function a(e,a){let o=n(e,a);if(!o)return null;try{let e=(0,t.getDbInstance)().prepare("SELECT provider, model_id, real_context, source, refreshed_at FROM model_context_overrides WHERE provider = ? AND model_id = ?").get(o.provider,o.modelId);return e?r(e):null}catch{return null}}e.s(["getModelContextOverride",0,function(e,t){let n=a(e,t);return n?n.realContext:null},"getModelContextOverrideRecord",0,a,"listModelContextOverrides",0,function(){try{return(0,t.getDbInstance)().prepare("SELECT provider, model_id, real_context, source, refreshed_at FROM model_context_overrides ORDER BY refreshed_at DESC").all().map(r)}catch{return[]}},"removeModelContextOverride",0,function(e,r){let a=n(e,r);return!!a&&(0,t.getDbInstance)().prepare("DELETE FROM model_context_overrides WHERE provider = ? AND model_id = ?").run(a.provider,a.modelId).changes>0},"setModelContextOverride",0,function(e,r,a,o="manual"){let s=n(e,r);return!!s&&!!("number"==typeof a&&Number.isInteger(a)&&a>0)&&((0,t.getDbInstance)().prepare("INSERT OR REPLACE INTO model_context_overrides (provider, model_id, real_context, source, refreshed_at) VALUES (?, ?, ?, ?, datetime('now'))").run(s.provider,s.modelId,a,"auto:discovery"===o?"auto:discovery":"manual"),!0)}])},306860,e=>{"use strict";var t=e.i(899378);let n=`COALESCE(
  CASE
    WHEN typeof(expires_at) IN ('integer', 'real') THEN CAST(expires_at AS INTEGER)
    WHEN typeof(expires_at) = 'text' AND expires_at <> '' AND expires_at NOT GLOB '*[^0-9]*'
      THEN CAST(expires_at AS INTEGER)
    ELSE unixepoch(expires_at)
  END,
  0
)`;e.s(["cleanupExpiredReasoning",0,function(){return(0,t.getDbInstance)().prepare(`DELETE FROM reasoning_cache WHERE ${n} <= unixepoch('now')`).run().changes},"clearAllReasoningCache",0,function(e){let n=(0,t.getDbInstance)();return e?n.prepare("DELETE FROM reasoning_cache WHERE provider = ?").run(e).changes:n.prepare("DELETE FROM reasoning_cache").run().changes},"deleteReasoningCache",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM reasoning_cache WHERE tool_call_id = ?").run(e).changes},"getReasoningCache",0,function(e){return(0,t.getDbInstance)().prepare(`SELECT reasoning, provider, model FROM reasoning_cache
       WHERE tool_call_id = ? AND ${n} > unixepoch('now')`).get(e)??null},"getReasoningCacheEntries",0,function(e={}){let r=(0,t.getDbInstance)(),a=Math.min(e.limit??50,200),o=e.offset??0,s=[`${n} > unixepoch('now')`],i=[];e.provider&&(s.push("provider = ?"),i.push(e.provider)),e.model&&(s.push("model = ?"),i.push(e.model));let l=s.length>0?`WHERE ${s.join(" AND ")}`:"";return r.prepare(`SELECT tool_call_id, provider, model, reasoning, char_count, created_at, expires_at
       FROM reasoning_cache ${l}
       ORDER BY created_at DESC
       LIMIT ? OFFSET ?`).all(...i,a,o).map(e=>({toolCallId:e.tool_call_id,provider:e.provider,model:e.model,reasoning:e.reasoning,charCount:e.char_count,createdAt:e.created_at,expiresAt:function(e){let t=String(e),n="number"!=typeof e&&(""===t||/[^0-9]/.test(t))?NaN:Number.parseInt(t,10);if(Number.isFinite(n)&&n>0)return new Date(1e3*n).toISOString();let r=Date.parse(t);return Number.isFinite(r)?new Date(r).toISOString():String(e)}(e.expires_at)}))},"getReasoningCacheStats",0,function(){let e=(0,t.getDbInstance)(),r=e.prepare(`SELECT COUNT(*) as total_entries, COALESCE(SUM(char_count), 0) as total_chars
       FROM reasoning_cache WHERE ${n} > unixepoch('now')`).get(),a=e.prepare(`SELECT provider, COUNT(*) as entries, COALESCE(SUM(char_count), 0) as chars
       FROM reasoning_cache WHERE ${n} > unixepoch('now')
       GROUP BY provider ORDER BY entries DESC`).all(),o={};for(let e of a)o[e.provider]={entries:e.entries,chars:e.chars};let s=e.prepare(`SELECT model, COUNT(*) as entries, COALESCE(SUM(char_count), 0) as chars
       FROM reasoning_cache WHERE ${n} > unixepoch('now')
       GROUP BY model ORDER BY entries DESC`).all(),i={};for(let e of s)i[e.model]={entries:e.entries,chars:e.chars};let l=e.prepare(`SELECT created_at FROM reasoning_cache
       WHERE ${n} > unixepoch('now') ORDER BY created_at ASC LIMIT 1`).get(),u=e.prepare(`SELECT created_at FROM reasoning_cache
       WHERE ${n} > unixepoch('now') ORDER BY created_at DESC LIMIT 1`).get();return{totalEntries:r.total_entries,totalChars:r.total_chars,byProvider:o,byModel:i,oldestEntry:l?.created_at??null,newestEntry:u?.created_at??null}},"setReasoningCache",0,function(e,n,r,a,o=72e5){a.length>1e4&&(a=a.slice(0,1e4));let s=(0,t.getDbInstance)(),i=Math.floor((Date.now()+o)/1e3),l=a.length;s.prepare(`INSERT OR REPLACE INTO reasoning_cache
       (tool_call_id, provider, model, reasoning, char_count, created_at, expires_at)
     VALUES (?, ?, ?, ?, ?, datetime('now'), ?)`).run(e,n,r,a,l,i)}])},469960,e=>{"use strict";var t=e.i(899378),n=e.i(529646);function r(e){let t=(0,n.rowToCamel)(e)??{};return{model:String(t.model??""),source:String(t.source??""),category:String(t.category??""),score:"number"==typeof t.score?t.score:0,eloRaw:"number"==typeof t.eloRaw?t.eloRaw:null,confidence:"string"==typeof t.confidence?t.confidence:null,syncedAt:String(t.syncedAt??""),expiresAt:"string"==typeof t.expiresAt?t.expiresAt:null}}function a(e,n){let a=(0,t.getDbInstance)().prepare(`SELECT * FROM model_intelligence
       WHERE model = ? AND category = ?
         AND source IN ('user_override', 'arena_elo', 'models_dev_tier')
         AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))
       ORDER BY CASE source
         WHEN 'user_override' THEN 1
         WHEN 'arena_elo' THEN 2
         WHEN 'models_dev_tier' THEN 3
       END
       LIMIT 1`).get(e,n);return a?r(a):null}function o(e){(0,t.getDbInstance)().prepare(`INSERT OR REPLACE INTO model_intelligence
       (model, source, category, score, elo_raw, confidence, synced_at, expires_at)
     VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)`).run(e.model,e.source,e.category,e.score,e.eloRaw??null,e.confidence??null,e.expiresAt??null)}function s(e,n,r){return((0,t.getDbInstance)().prepare(`DELETE FROM model_intelligence
       WHERE model = ? AND source = ? AND category = ?`).run(e,n,r).changes??0)>0}e.s(["bulkUpsertModelIntelligence",0,function(e){if(0===e.length)return 0;let n=(0,t.getDbInstance)(),r=n.prepare(`INSERT OR REPLACE INTO model_intelligence
       (model, source, category, score, elo_raw, confidence, synced_at, expires_at)
     VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)`);return n.transaction(()=>{let t=0;for(let n of e)r.run(n.model,n.source,n.category,n.score,n.eloRaw??null,n.confidence??null,n.expiresAt??null),t++;return t})()},"deleteExpiredIntelligence",0,function(e){let n=(0,t.getDbInstance)(),r=["expires_at IS NOT NULL","datetime(expires_at) < datetime('now')"],a=[];e&&(r.push("source = ?"),a.push(e));let o=r.join(" AND ");return n.prepare(`DELETE FROM model_intelligence WHERE ${o}`).run(...a).changes??0},"deleteModelIntelligence",0,s,"deleteModelIntelligenceBySource",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM model_intelligence WHERE source = ?").run(e).changes??0},"deleteUserFitnessOverrideEntry",0,function(e,t){return s(e.toLowerCase(),"user_override",t.toLowerCase())},"getModelIntelligence",0,a,"getModelIntelligenceBySource",0,function(e,n,a){let o=(0,t.getDbInstance)().prepare(`SELECT * FROM model_intelligence
       WHERE model = ? AND source = ? AND category = ?
         AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))`).get(e,n,a);return o?r(o):null},"getResolvedTaskFitness",0,function(e,t){let n=a(e,t);return n?n.score:null},"listModelIntelligence",0,function(e){let n=(0,t.getDbInstance)(),a=[],o=[];e?.source&&(a.push("source = ?"),o.push(e.source)),e?.category&&(a.push("category = ?"),o.push(e.category));let s=a.length>0?`WHERE ${a.join(" AND ")}`:"",i=`SELECT * FROM model_intelligence ${s} ORDER BY model ASC, source ASC, category ASC`;return n.prepare(i).all(...o).map(r)},"setUserFitnessOverrideEntry",0,function(e,t,n){o({model:e.toLowerCase(),source:"user_override",category:t.toLowerCase(),score:Math.max(0,Math.min(1,n)),eloRaw:null,confidence:null,expiresAt:null})},"upsertModelIntelligence",0,o])},51829,e=>{"use strict";var t=e.i(899378);e.s(["deleteMapping",0,function(e,n){(0,t.getDbInstance)().prepare("DELETE FROM agent_bridge_mappings WHERE agent_id = ? AND source_model = ?").run(e,n)},"getMappingsForAgent",0,function(e){return(0,t.getDbInstance)().prepare("SELECT agent_id, source_model, target_model, updated_at FROM agent_bridge_mappings WHERE agent_id = ? ORDER BY source_model ASC").all(e)},"setMappings",0,function(e,n){let r=(0,t.getDbInstance)(),a=new Date().toISOString(),o=r.prepare("DELETE FROM agent_bridge_mappings WHERE agent_id = ?"),s=r.prepare(`INSERT INTO agent_bridge_mappings (agent_id, source_model, target_model, updated_at)
     VALUES (?, ?, ?, ?)`);r.transaction(()=>{for(let t of(o.run(e),n))s.run(e,t.source,t.target,a)})()}])},983427,e=>{"use strict";var t=e.i(899378);let n=null,r=[["actual_prompt_tokens","INTEGER"],["actual_completion_tokens","INTEGER"],["actual_total_tokens","INTEGER"],["actual_cache_read_tokens","INTEGER"],["actual_cache_write_tokens","INTEGER"],["estimated_usd_saved","REAL"],["mcp_description_tokens_saved","INTEGER DEFAULT 0"],["multimodal_skip_count","INTEGER DEFAULT 0"],["receipt_source","TEXT"],["validation_fallback","INTEGER DEFAULT 0"],["output_mode","TEXT"],["compression_combo_id","TEXT"],["engine","TEXT"],["rtk_raw_output_pointer","TEXT"],["rtk_raw_output_bytes","INTEGER"],["rtk_raw_output_pointers","TEXT"],["rtk_raw_output_total_bytes","INTEGER"],["skip_reason","TEXT"]];function a(){let e=(0,t.getDbInstance)();if(n===e)return;let a=new Set(e.prepare("PRAGMA table_info(compression_analytics)").all().map(e=>e.name));for(let[t,n]of r)a.has(t)||e.exec(`ALTER TABLE compression_analytics ADD COLUMN ${t} ${n}`);n=e}function o(e){let n=(0,t.getDbInstance)();a(),n.prepare(`
    INSERT INTO compression_analytics (
      timestamp, combo_id, compression_combo_id, engine, provider, mode, original_tokens, compressed_tokens, tokens_saved,
      duration_ms, request_id, actual_prompt_tokens, actual_completion_tokens,
      actual_total_tokens, actual_cache_read_tokens, actual_cache_write_tokens,
      estimated_usd_saved, mcp_description_tokens_saved, multimodal_skip_count,
      receipt_source, validation_fallback, output_mode, rtk_raw_output_pointer, rtk_raw_output_bytes,
      rtk_raw_output_pointers, rtk_raw_output_total_bytes, skip_reason
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(e.timestamp,e.combo_id??null,e.compression_combo_id??null,e.engine??e.mode,e.provider??null,e.mode,e.original_tokens,e.compressed_tokens,e.tokens_saved,e.duration_ms??null,e.request_id??null,e.actual_prompt_tokens??null,e.actual_completion_tokens??null,e.actual_total_tokens??null,e.actual_cache_read_tokens??null,e.actual_cache_write_tokens??null,e.estimated_usd_saved??null,e.mcp_description_tokens_saved??0,e.multimodal_skip_count??0,e.receipt_source??null,+!!e.validation_fallback,e.output_mode??null,e.rtk_raw_output_pointer??null,e.rtk_raw_output_bytes??null,e.rtk_raw_output_pointers??null,e.rtk_raw_output_total_bytes??null,e.skip_reason??null)}let s=null;function i(){let e=(0,t.getDbInstance)();s!==e&&(e.exec(`
    CREATE TABLE IF NOT EXISTS compression_engine_breakdown (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT NOT NULL,
      request_id TEXT,
      engine TEXT NOT NULL,
      original_tokens INTEGER NOT NULL DEFAULT 0,
      compressed_tokens INTEGER NOT NULL DEFAULT 0,
      tokens_saved INTEGER NOT NULL DEFAULT 0,
      duration_ms INTEGER
    );
    CREATE INDEX IF NOT EXISTS idx_ceb_engine_ts ON compression_engine_breakdown(engine, timestamp);
    CREATE INDEX IF NOT EXISTS idx_ceb_request ON compression_engine_breakdown(request_id);
  `),s=e)}function l(e){if("number"==typeof e&&Number.isFinite(e))return Math.max(0,Math.floor(e));if("string"==typeof e&&e.trim()){let t=Number(e);if(Number.isFinite(t))return Math.max(0,Math.floor(t))}return null}function u(e,t){return e?`${e} AND ${t}`:`WHERE ${t}`}e.s(["attachCompressionUsageReceipt",0,function(e,n,r="provider"){if(!e||!n||"object"!=typeof n)return;let o=l(n.prompt_tokens),s=l(n.completion_tokens),i=l(n.total_tokens)??(o??0)+(s??0),u=n.prompt_tokens_details&&"object"==typeof n.prompt_tokens_details?n.prompt_tokens_details:{},c=l(n.cache_read_input_tokens??n.cached_tokens??u.cached_tokens),p=l(n.cache_creation_input_tokens??u.cache_creation_tokens);if(null===o&&null===s&&i<=0)return;let d=(0,t.getDbInstance)();a(),d.prepare(`
    UPDATE compression_analytics
    SET actual_prompt_tokens = ?,
        actual_completion_tokens = ?,
        actual_total_tokens = ?,
        actual_cache_read_tokens = ?,
        actual_cache_write_tokens = ?,
        receipt_source = ?
    WHERE request_id = ?
      AND id = (
        SELECT id FROM compression_analytics
        WHERE request_id = ?
        ORDER BY id DESC
        LIMIT 1
      )
  `).run(o,s,i,c,p,r,e,e)},"getCompressionAnalyticsSummary",0,function(e){let n=(0,t.getDbInstance)();a();let r=null;"24h"===e?r=new Date(Date.now()-864e5).toISOString():"7d"===e?r=new Date(Date.now()-6048e5).toISOString():"30d"===e&&(r=new Date(Date.now()-2592e6).toISOString());let o=r?"WHERE timestamp >= ?":"",s=r?[r]:[],i=u(o,"skip_reason IS NULL"),l=n.prepare(`
    SELECT
      COUNT(*) as total,
      COALESCE(SUM(tokens_saved), 0) as totalSaved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct,
      COALESCE(AVG(duration_ms), 0) as avgDur
    FROM compression_analytics ${i}
  `).get(...s),c=n.prepare(`
    SELECT mode, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct
    FROM compression_analytics ${i}
    GROUP BY mode
  `).all(...s),p=n.prepare(`
    SELECT mode, COUNT(*) as cnt
    FROM compression_analytics ${u(o,"skip_reason IS NOT NULL")}
    GROUP BY mode
  `).all(...s),d={};for(let e of c)d[e.mode]={count:e.cnt,tokensSaved:e.saved,avgSavingsPct:Math.round(e.avgPct),skipped:0};for(let e of p)d[e.mode]?d[e.mode].skipped=e.cnt:d[e.mode]={count:0,tokensSaved:0,avgSavingsPct:0,skipped:e.cnt};let _=n.prepare(`
    SELECT COALESCE(engine, mode) as engine, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct
    FROM compression_analytics ${i}
    GROUP BY COALESCE(engine, mode)
  `).all(...s),E={};for(let e of _)E[e.engine]={count:e.cnt,tokensSaved:e.saved,avgSavingsPct:Math.round(e.avgPct)};let g=n.prepare(`
    SELECT compression_combo_id as compressionComboId, COUNT(*) as cnt,
      COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics ${u(i,"compression_combo_id IS NOT NULL")}
    GROUP BY compression_combo_id ORDER BY cnt DESC
  `).all(...s),m={};for(let e of g)m[e.compressionComboId??"unknown"]={count:e.cnt,tokensSaved:e.saved};let S=n.prepare(`
    SELECT provider, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics ${i}
    GROUP BY provider ORDER BY cnt DESC
  `).all(...s),f={};for(let e of S)f[e.provider??"unknown"]={count:e.cnt,tokensSaved:e.saved};let y=new Map,b=new Date;for(let e=23;e>=0;e--){let t=new Date(b.getTime()-60*e*6e4).toISOString().substring(0,14)+"00:00Z";y.set(t,{hour:t,count:0,tokensSaved:0})}for(let e of n.prepare(`
    SELECT strftime('%Y-%m-%dT%H:00:00Z', timestamp) as hour,
      COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics
    WHERE timestamp >= ? AND skip_reason IS NULL
    GROUP BY hour ORDER BY hour ASC
  `).all(new Date(b.getTime()-864e5).toISOString()))y.has(e.hour)&&y.set(e.hour,{hour:e.hour,count:e.cnt,tokensSaved:e.saved});let R=Array.from(y.values()),T=n.prepare(`
    SELECT receipt_source as source, COUNT(*) as cnt,
      COALESCE(SUM(actual_prompt_tokens), 0) as prompt,
      COALESCE(SUM(actual_completion_tokens), 0) as completion,
      COALESCE(SUM(actual_total_tokens), 0) as total,
      COALESCE(SUM(actual_cache_read_tokens), 0) as cacheRead,
      COALESCE(SUM(actual_cache_write_tokens), 0) as cacheWrite,
      COALESCE(SUM(estimated_usd_saved), 0) as usdSaved
    FROM compression_analytics ${u(i,"receipt_source IS NOT NULL")}
    GROUP BY receipt_source
  `).all(...s),h={requestsWithReceipts:0,promptTokens:0,completionTokens:0,totalTokens:0,cacheReadTokens:0,cacheWriteTokens:0,estimatedUsdSaved:0,bySource:{}};for(let e of T){let t=e.source??"unknown";h.requestsWithReceipts+=e.cnt,h.promptTokens+=e.prompt,h.completionTokens+=e.completion,h.totalTokens+=e.total,h.cacheReadTokens+=e.cacheRead,h.cacheWriteTokens+=e.cacheWrite,h.estimatedUsdSaved+=e.usdSaved,h.bySource[t]=e.cnt}let I=n.prepare(`
    SELECT COUNT(*) as cnt
    FROM compression_analytics ${u(i,"validation_fallback = 1")}
  `).get(...s),O=n.prepare(`
    SELECT COUNT(*) as cnt, COALESCE(SUM(mcp_description_tokens_saved), 0) as saved
    FROM compression_analytics ${u(i,"mcp_description_tokens_saved > 0")}
  `).get(...s),D=n.prepare(`
    SELECT skip_reason as reason, COUNT(*) as cnt
    FROM compression_analytics ${u(o,"skip_reason IS NOT NULL")}
    GROUP BY skip_reason
  `).all(...s),N={},v=0;for(let e of D)N[e.reason??"unknown"]=e.cnt,v+=e.cnt;return{totalRequests:l?.total??0,totalTokensSaved:l?.totalSaved??0,avgSavingsPct:Math.round(l?.avgPct??0),avgDurationMs:Math.round(l?.avgDur??0),byMode:d,byEngine:E,byCompressionCombo:m,byProvider:f,last24h:R,totalSkipped:v,bySkipReason:N,validationFallbacks:I?.cnt??0,realUsage:h,mcpDescriptionCompression:{snapshots:O?.cnt??0,estimatedTokensSaved:O?.saved??0}}},"getPerEngineAnalytics",0,function(e,n=7){let r=(0,t.getDbInstance)();a(),i();let o=new Date(Date.now()-864e5*n).toISOString(),s=r.prepare(`SELECT COUNT(*) AS runs,
              COALESCE(SUM(original_tokens), 0) AS original,
              COALESCE(SUM(compressed_tokens), 0) AS compressed,
              COALESCE(SUM(tokens_saved), 0) AS saved
       FROM compression_engine_breakdown
       WHERE engine = ? AND timestamp >= ?`).get(e,o),l=r.prepare(`SELECT COUNT(*) AS runs,
              COALESCE(SUM(original_tokens), 0) AS original,
              COALESCE(SUM(compressed_tokens), 0) AS compressed,
              COALESCE(SUM(tokens_saved), 0) AS saved
       FROM compression_analytics
       WHERE COALESCE(engine, mode) = ? AND timestamp >= ?
         AND (
           request_id IS NULL
           OR request_id NOT IN (
             SELECT request_id FROM compression_engine_breakdown WHERE request_id IS NOT NULL
           )
         )`).get(e,o),u=s.runs+l.runs,c=s.original+l.original,p=s.compressed+l.compressed;return{engineId:e,runs:u,tokensSaved:Math.max(0,s.saved+l.saved),avgSavingsPercent:c>0?Math.round((c-p)/c*1e3)/10:0,days:n}},"insertCompressionAnalyticsRow",0,o,"insertCompressionEngineBreakdown",0,function(e){if(!e.length)return;let n=(0,t.getDbInstance)();i();let r=n.prepare(`INSERT INTO compression_engine_breakdown
       (timestamp, request_id, engine, original_tokens, compressed_tokens, tokens_saved, duration_ms)
     VALUES (?, ?, ?, ?, ?, ?, ?)`);n.transaction(e=>{for(let t of e)r.run(t.timestamp,t.request_id??null,t.engine,t.original_tokens,t.compressed_tokens,t.tokens_saved,t.duration_ms??null)})(e)},"recordContextEditingTelemetry",0,function(e,t,n="claude"){let r=t?.clearedInputTokens??0;Number.isFinite(r)&&!(r<=0)&&o({timestamp:new Date().toISOString(),provider:n,mode:"context-editing",engine:"context-editing",original_tokens:r,compressed_tokens:0,tokens_saved:r,request_id:e?`${e}::context-editing`:null})}])},751183,e=>{"use strict";var t=e.i(899378),n=e.i(403122),r=e.i(935050);let a=["litellm"],o=parseInt(process.env.PRICING_SYNC_INTERVAL||"86400",10),s=Number.isFinite(o)&&o>0?1e3*o:864e5,i=(process.env.PRICING_SYNC_SOURCES||"litellm").split(",").map(e=>e.trim()).filter(e=>a.includes(e)),l={openai:["openai","cx"],anthropic:["anthropic","cc"],vertex_ai:["gemini"],"vertex_ai-anthropic_models":["anthropic"],google:["gemini"],deepseek:["if"],groq:["groq"],together_ai:["openrouter"],bedrock:["kiro"],fireworks_ai:["fireworks"],cerebras:["cerebras"],nvidia_nim:["nvidia"],siliconflow:["siliconflow"],"vertex_ai-language_models":["gemini"],"vertex_ai-mistral_models":["mistral"],gemini:["gemini"],bedrock_converse:["kiro"],cloudflare:["cloudflare-ai"],stability:["stability-ai"]},u=null,c=null,p=0,d=s;async function _(){let e=await fetch("https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",{signal:AbortSignal.timeout(3e4)});if(!e.ok)throw Error(`LiteLLM fetch failed [${e.status}]: ${e.statusText}`);let t=await e.text();try{return JSON.parse(t)}catch{throw Error(`LiteLLM returned invalid JSON (${t.slice(0,100)}...)`)}}function E(e){return e&&"object"==typeof e?e:{}}function g(e){let a=(0,t.getDbInstance)(),o=a.prepare("DELETE FROM key_value WHERE namespace = 'pricing_synced'"),s=a.prepare("INSERT INTO key_value (namespace, key, value) VALUES ('pricing_synced', ?, ?)");a.transaction(()=>{for(let[t,n]of(o.run(),Object.entries(e)))s.run(t,JSON.stringify(n))})(),(0,r.backupDbFile)("pre-write"),(0,n.invalidateDbCache)("pricing")}let m="pricing_sync_status",S="last_sync";async function f(e){let n=e?.sources||i,r=e?.dryRun??!1,o=n.filter(e=>a.includes(e)),s=n.filter(e=>!a.includes(e));if(0===o.length){let e=a.join(", ");return{success:!1,modelCount:0,providerCount:0,source:n.join(","),dryRun:r,error:`No valid sources provided. Supported: ${e}. Invalid: ${s.join(", ")}`}}try{let e={};for(let t of o)if("litellm"===t){let t=await _(),n=function(e){let t={};for(let[n,r]of Object.entries(e)){let e=["input_cost_per_second","output_cost_per_second","input_cost_per_image","output_cost_per_image","input_cost_per_pixel","output_cost_per_pixel","input_cost_per_character","output_cost_per_character","input_cost_per_video_per_second","output_cost_per_video_per_second","search_unit_cost","ocr_cost_per_page"],a=null!=r.input_cost_per_token||null!=r.output_cost_per_token,o=e.some(e=>null!=r[e]);if(!a&&!o)continue;let s=1e6*(r.input_cost_per_token||0),i={input:Math.round(1e3*s)/1e3,output:Math.round(1e3*(1e6*(r.output_cost_per_token||0)))/1e3};for(let t of(r.mode&&(i.mode=r.mode),null!=r.cache_read_input_token_cost&&(i.cached=Math.round(1e6*r.cache_read_input_token_cost*1e3)/1e3),null!=r.cache_creation_input_token_cost&&(i.cache_creation=Math.round(1e6*r.cache_creation_input_token_cost*1e3)/1e3),e)){let e=r[t];"number"==typeof e&&Number.isFinite(e)&&(i[t]=e)}let u=n.indexOf("/"),c=u>=0?n.slice(u+1):n,p=r.litellm_provider||"",d=l[p];if(d)for(let e of d)t[e]||(t[e]={}),t[e][c]=i;else p&&(t[p]||(t[p]={}),t[p][c]=i)}return t}(t);for(let[t,r]of Object.entries(n))e[t]||(e[t]={}),Object.assign(e[t],r)}let n=Object.values(e).reduce((e,t)=>e+Object.keys(t).length,0),a=Object.keys(e).length;if(!r){var u;g(e),c=new Date().toISOString(),p=n,u=c,(0,t.getDbInstance)().prepare("INSERT INTO key_value (namespace, key, value) VALUES (?, ?, ?) ON CONFLICT(namespace, key) DO UPDATE SET value = excluded.value").run(m,S,JSON.stringify({lastSyncTime:u,lastSyncModelCount:n}))}return{success:!0,modelCount:n,providerCount:a,source:o.join(","),dryRun:r,...s.length>0?{warnings:[`Unknown sources ignored: ${s.join(", ")}`]}:{},...r?{data:e}:{}}}catch(t){let e=t instanceof Error?t.message:String(t);return console.warn("[PRICING_SYNC] Sync failed:",e),{success:!1,modelCount:0,providerCount:0,source:n.join(","),dryRun:r,error:e}}}function y(e){if(u)return;let t=e??s;d=t,console.log(`[PRICING_SYNC] Starting periodic sync every ${t/1e3}s`),f().then(e=>{e.success&&console.log(`[PRICING_SYNC] Initial sync complete: ${e.modelCount} models from ${e.providerCount} providers`)}).catch(e=>{console.warn("[PRICING_SYNC] Initial sync error:",e instanceof Error?e.message:e)}),(u=setInterval(()=>{f().then(e=>{e.success&&console.log(`[PRICING_SYNC] Periodic sync complete: ${e.modelCount} models`)}).catch(e=>{console.warn("[PRICING_SYNC] Periodic sync error:",e instanceof Error?e.message:e)})},t))&&"object"==typeof u&&"unref"in u&&u.unref?.()}async function b(){"true"!==process.env.PRICING_SYNC_ENABLED?console.log("[PRICING_SYNC] Disabled (set PRICING_SYNC_ENABLED=true to enable)"):y()}e.s(["clearSyncedPricing",0,function(){(0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = 'pricing_synced'").run(),(0,r.backupDbFile)("pre-write"),(0,n.invalidateDbCache)("pricing")},"getSyncStatus",0,function(){let e="true"===process.env.PRICING_SYNC_ENABLED,n=null===c?function(){let e=E((0,t.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(m,S)),n="string"==typeof e.value?e.value:null;if(!n)return null;try{let e=JSON.parse(n);if("string"!=typeof e.lastSyncTime)return null;return{lastSyncTime:e.lastSyncTime,lastSyncModelCount:"number"==typeof e.lastSyncModelCount?e.lastSyncModelCount:0}}catch{return null}}():null,r=c??n?.lastSyncTime??null;return{enabled:e,lastSync:r,lastSyncModelCount:null!==c?p:n?.lastSyncModelCount??0,nextSync:r?new Date(new Date(r).getTime()+d).toISOString():null,intervalMs:d,sources:i}},"getSyncedPricing",0,function(){let e=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = 'pricing_synced'").all(),n={};for(let t of e){let e=E(t),r="string"==typeof e.key?e.key:null,a="string"==typeof e.value?e.value:null;if(r&&null!==a)try{n[r]=JSON.parse(a)}catch{console.warn(`[PRICING_SYNC] Corrupted data for provider "${r}", skipping`)}}return n},"initPricingSync",0,b,"saveSyncedPricing",0,g,"startPeriodicSync",0,y,"stopPeriodicSync",0,function(){u&&(clearInterval(u),u=null,console.log("[PRICING_SYNC] Periodic sync stopped"))},"syncPricingFromSources",0,f])},758303,e=>{"use strict";var t=e.i(979464);let n={debug:0,info:1,warn:2,error:3},r=(0,t.getAppLogLevel)("info").toLowerCase(),a=Object.prototype.hasOwnProperty.call(n,r)?n[r]:n.info,o="json"===(0,t.getAppLogFormat)("text");function s(e){switch(e){case"debug":return console.debug;case"warn":return console.warn;case"error":return console.error;default:return console.log}}function i(e){if(!e||"object"!=typeof e)return"";let t={};for(let[n,r]of Object.entries(e))null!=r&&(t[n]=r);return Object.keys(t).length>0?` ${JSON.stringify(t)}`:""}let l=function(e=null){let t=(t,r,l,u)=>{if(n[t]<a)return;let c=s(t);if(o){let n={ts:new Date().toISOString(),level:t,tag:r,msg:l};e&&(n.reqId=e),u&&"object"==typeof u&&Object.keys(u).length>0&&(n.data=u),c(JSON.stringify(n))}else{let t=new Date().toISOString().slice(11,23),n=e?`[${e}]`:"",a=i(u);c(`${t} ${n}[${r}] ${l}${a}`)}};return{debug:(e,n,r)=>t("debug",e,n,r),info:(e,n,r)=>t("info",e,n,r),warn:(e,n,r)=>t("warn",e,n,r),error:(e,n,r)=>t("error",e,n,r)}}();e.s(["defaultLogger",0,l,"logger",0,function(e){let t=(t,r,l)=>{if(n[t]<a)return;let u=s(t);if(o){let n={ts:new Date().toISOString(),level:t,tag:e,msg:r};l&&"object"==typeof l&&Object.keys(l).length>0&&(n.data=l),u(JSON.stringify(n))}else u(`[${t.toUpperCase()}] [${e}] ${r}${i(l)}`)};return{debug:(e,n)=>t("debug",e,n),info:(e,n)=>t("info",e,n),warn:(e,n)=>t("warn",e,n),error:(e,n)=>t("error",e,n)}}])},131470,e=>{"use strict";var t=e.i(899378);let n=(0,e.i(758303).logger)("DB_PLUGINS");function r(e){return{id:e.id,name:e.name,version:e.version,description:e.description,author:e.author,license:e.license,main:e.main,source:e.source,tags:e.tags,status:e.status,enabled:e.enabled,manifest:e.manifest,config:e.config,configSchema:e.config_schema,hooks:e.hooks,permissions:e.permissions,pluginDir:e.plugin_dir,errorMessage:e.error_message,installedAt:e.installed_at,updatedAt:e.updated_at,activatedAt:e.activated_at}}function a(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM plugins WHERE name = ?").get(e);return n?r(n):null}e.s(["deletePlugin",0,function(e){let r=(0,t.getDbInstance)().prepare("DELETE FROM plugins WHERE name = ?").run(e);return r.changes>0&&n.info("plugin.deleted",{name:e}),r.changes>0},"getPluginAnalytics",0,function(e){return(0,t.getDbInstance)().prepare(`SELECT plugin_name, hook, duration_ms, success, error_message, created_at
       FROM plugin_analytics
       WHERE plugin_name = ?
       ORDER BY created_at DESC`).all(e).map(e=>({pluginName:e.plugin_name,hook:e.hook,durationMs:e.duration_ms,success:1===e.success,errorMessage:e.error_message,createdAt:e.created_at}))},"getPluginAnalyticsSummary",0,function(e){let n=(0,t.getDbInstance)().prepare(`SELECT
         COUNT(*) AS total,
         SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS successes,
         SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS failures,
         AVG(duration_ms) AS avg_duration
       FROM plugin_analytics
       WHERE plugin_name = ?`).get(e);return{totalCalls:n?.total??0,successCount:n?.successes??0,failureCount:n?.failures??0,avgDurationMs:n?.avg_duration??0}},"getPluginById",0,function(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM plugins WHERE id = ?").get(e);return n?r(n):null},"getPluginByName",0,a,"insertPlugin",0,function(e){let r=(0,t.getDbInstance)(),o=new Date().toISOString();r.prepare(`INSERT INTO plugins (
      id, name, version, description, author, license, main, source, tags,
      status, enabled, manifest, config, config_schema, hooks, permissions,
      plugin_dir, installed_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(e.id,e.name,e.version,e.description??null,e.author??null,e.license??"MIT",e.main,e.source??"local",JSON.stringify(e.tags??[]),e.status??"installed",+!!e.enabled,JSON.stringify(e.manifest),JSON.stringify(e.config??{}),JSON.stringify(e.configSchema??{}),JSON.stringify(e.hooks??[]),JSON.stringify(e.permissions??[]),e.pluginDir,o,o),n.info("plugin.inserted",{id:e.id,name:e.name});let s=a(e.name);if(!s)throw Error(`Failed to retrieve plugin '${e.name}' after insertion`);return s},"listPlugins",0,function(e){let n=(0,t.getDbInstance)();return(e?n.prepare("SELECT * FROM plugins WHERE status = ? ORDER BY name").all(e):n.prepare("SELECT * FROM plugins ORDER BY name").all()).map(r)},"pluginExists",0,function(e){return!!(0,t.getDbInstance)().prepare("SELECT 1 FROM plugins WHERE name = ?").get(e)},"updatePluginConfig",0,function(e,n){let r=(0,t.getDbInstance)(),a=new Date().toISOString();return r.prepare("UPDATE plugins SET config = ?, updated_at = ? WHERE name = ?").run(JSON.stringify(n),a,e).changes>0},"updatePluginStatus",0,function(e,r,a){let o=(0,t.getDbInstance)(),s=new Date().toISOString(),i="active"===r?s:null,l=o.prepare(`UPDATE plugins SET status = ?, enabled = ?, error_message = ?,
       updated_at = ?, activated_at = COALESCE(?, activated_at)
       WHERE name = ?`).run(r,+("active"===r),a??null,s,i,e);return l.changes>0&&n.info("plugin.status_updated",{name:e,status:r}),l.changes>0}])},54572,e=>{"use strict";var t=e.i(254799),n=e.i(899378),r=e.i(935050);function a(e){return{id:String(e.id??""),source:String(e.source??"1proxy"),host:String(e.host??""),port:Number(e.port)||0,type:String(e.type??"http"),countryCode:null!=e.country_code?String(e.country_code):null,qualityScore:null!=e.quality_score?Number(e.quality_score):null,latencyMs:null!=e.latency_ms?Number(e.latency_ms):null,anonymity:null!=e.anonymity?String(e.anonymity):null,lastValidated:null!=e.last_validated?String(e.last_validated):null,inPool:1===e.in_pool||!0===e.in_pool,poolProxyId:null!=e.pool_proxy_id?String(e.pool_proxy_id):null,createdAt:String(e.created_at??""),updatedAt:String(e.updated_at??"")}}async function o(e){let r=(0,n.getDbInstance)(),a=new Date().toISOString(),o=r.prepare("SELECT id FROM free_proxies WHERE source = ? AND host = ? AND port = ?").get(e.source,e.host,e.port);if(o?.id)return r.prepare(`UPDATE free_proxies
       SET type = ?, country_code = ?, quality_score = ?, latency_ms = ?,
           anonymity = ?, last_validated = ?, updated_at = ?
       WHERE id = ?`).run(e.type,e.countryCode??null,e.qualityScore??null,e.latencyMs??null,e.anonymity??null,e.lastValidated??a,a,o.id),{id:o.id,action:"updated"};let s=(0,t.randomUUID)();return r.prepare(`INSERT INTO free_proxies
     (id, source, host, port, type, country_code, quality_score, latency_ms,
      anonymity, last_validated, in_pool, pool_proxy_id, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)`).run(s,e.source,e.host,e.port,e.type,e.countryCode??null,e.qualityScore??null,e.latencyMs??null,e.anonymity??null,e.lastValidated??a,a,a),{id:s,action:"created"}}async function s(e){let t=(0,n.getDbInstance)(),r=[],o="SELECT * FROM free_proxies WHERE 1=1";e?.sources?.length&&(o+=` AND source IN (${e.sources.map(()=>"?").join(",")})`,r.push(...e.sources)),e?.protocol&&(o+=" AND type = ?",r.push(e.protocol)),e?.country&&(o+=" AND country_code = ?",r.push(e.country.toUpperCase())),e?.minQuality!=null&&(o+=" AND quality_score >= ?",r.push(e.minQuality)),e?.onlyInPool&&(o+=" AND in_pool = 1"),e?.onlyNotInPool&&(o+=" AND in_pool = 0"),e?.search&&(o+=" AND host LIKE ?",r.push(`%${e.search}%`));let s=e?.sortBy==="latency"?"ORDER BY latency_ms IS NULL, latency_ms ASC":e?.sortBy==="recent"?"ORDER BY last_validated DESC":"ORDER BY quality_score DESC, last_validated DESC";return o+=` ${s}`,e?.limit&&(o+=" LIMIT ?",r.push(e.limit),e?.offset&&(o+=" OFFSET ?",r.push(e.offset))),t.prepare(o).all(...r).map(a)}async function i(e){let t=(0,n.getDbInstance)(),r=[],a="SELECT COUNT(*) AS count FROM free_proxies WHERE 1=1";e?.sources?.length&&(a+=` AND source IN (${e.sources.map(()=>"?").join(",")})`,r.push(...e.sources)),e?.protocol&&(a+=" AND type = ?",r.push(e.protocol)),e?.country&&(a+=" AND country_code = ?",r.push(e.country.toUpperCase())),e?.minQuality!=null&&(a+=" AND quality_score >= ?",r.push(e.minQuality)),e?.onlyInPool&&(a+=" AND in_pool = 1"),e?.onlyNotInPool&&(a+=" AND in_pool = 0"),e?.search&&(a+=" AND host LIKE ?",r.push(`%${e.search}%`));let o=t.prepare(a).get(...r),s=o?.count;return"number"==typeof s?s:Number(s??0)}async function l(e,t){return(await s({sources:[e],protocol:t.protocol,country:t.country,minQuality:t.minQuality,limit:t.limit})).map(e=>({source:e.source,host:e.host,port:e.port,type:e.type,countryCode:e.countryCode,qualityScore:e.qualityScore,latencyMs:e.latencyMs,anonymity:e.anonymity,lastValidated:e.lastValidated}))}async function u(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM free_proxies WHERE id = ?").get(e);return t?a(t):null}async function c(e,t){let a=(0,n.getDbInstance)(),o=new Date().toISOString();a.prepare("UPDATE free_proxies SET in_pool = 1, pool_proxy_id = ?, updated_at = ? WHERE id = ?").run(t,o,e),(0,r.backupDbFile)("pre-write")}async function p(e,a){let o=(0,n.getDbInstance)(),s=new Date().toISOString(),i=(0,t.randomUUID)(),l=o.transaction(()=>{let t=o.prepare("SELECT id, in_pool FROM free_proxies WHERE id = ? LIMIT 1").get(e);return t?.id?(o.prepare(`INSERT INTO proxy_registry
        (id, name, type, host, port, username, password, region, notes, status, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, '', '', NULL, NULL, 'active', ?, ?, ?)`).run(i,a.name,a.type,a.host,Number(a.port),a.source,s,s),o.prepare("UPDATE free_proxies SET in_pool = 1, pool_proxy_id = ?, updated_at = ? WHERE id = ?").run(i,s,e),i):null})();return l&&(0,r.backupDbFile)("pre-write"),l}async function d(e){let t=(0,n.getDbInstance)().prepare("DELETE FROM free_proxies WHERE id = ?").run(e);return(0,r.backupDbFile)("pre-write"),t.changes>0}async function _(e){let t=(0,n.getDbInstance)().prepare("DELETE FROM free_proxies WHERE source = ? AND in_pool = 0").run(e);return(0,r.backupDbFile)("pre-write"),t.changes}async function E(e,t){let a=(0,n.getDbInstance)(),o=a.prepare("SELECT id, host, port FROM free_proxies WHERE source = ? AND in_pool = 0").all(e).filter(e=>!t.has(`${e.host}:${e.port}`)).map(e=>e.id);if(0===o.length)return 0;let s=o.map(()=>"?").join(","),i=a.prepare(`DELETE FROM free_proxies WHERE id IN (${s})`).run(...o);return(0,r.backupDbFile)("pre-write"),i.changes}let g="free_proxies",m="last_sync_at";async function S(e){let t=(0,n.getDbInstance)(),a=e??new Date().toISOString();return t.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(g,m,a),(0,r.backupDbFile)("pre-write"),a}async function f(){let e,t=(0,n.getDbInstance)(),r=t.prepare(`SELECT COUNT(*) as total,
              SUM(CASE WHEN in_pool = 1 THEN 1 ELSE 0 END) as in_pool_count,
              AVG(quality_score) as avg_quality,
              MAX(last_validated) as last_sync_at
       FROM free_proxies`).get(),a=t.prepare("SELECT source, COUNT(*) as count FROM free_proxies GROUP BY source ORDER BY count DESC").all(),o=(e=t.prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(g,m),e?.value!=null?String(e.value):null),s=null!=r.last_sync_at?String(r.last_sync_at):null;return{total:Number(r.total)||0,inPool:Number(r.in_pool_count)||0,avgQuality:null!=r.avg_quality?Math.round(Number(r.avg_quality)):null,bySource:a.map(e=>({source:String(e.source),count:Number(e.count)})),lastSyncAt:o??s}}async function y(e,t){let a=(0,n.getDbInstance)(),o=new Date().toISOString();a.prepare("INSERT OR REPLACE INTO free_proxy_sync_errors (source, errors, updated_at) VALUES (?, ?, ?)").run(e,JSON.stringify(t),o),(0,r.backupDbFile)("pre-write")}async function b(e){(0,n.getDbInstance)().prepare("DELETE FROM free_proxy_sync_errors WHERE source = ?").run(e),(0,r.backupDbFile)("pre-write")}async function R(){let e=(0,n.getDbInstance)().prepare("SELECT source, errors FROM free_proxy_sync_errors").all(),t={};for(let n of e)if(n.source)try{let e=JSON.parse(n.errors);t[n.source]=Array.isArray(e)?e.map(String):[String(n.errors)]}catch{t[n.source]=[String(n.errors)]}return t}e.s(["clearFreeProxiesBySource",0,_,"clearFreeProxySyncErrors",0,b,"countFreeProxies",0,i,"deleteFreeProxy",0,d,"getFreeProxyById",0,u,"getFreeProxyStats",0,f,"getFreeProxySyncErrors",0,R,"listFreeProxies",0,s,"listFreeProxiesBySource",0,l,"markFreeProxyInPool",0,c,"promoteFreeProxyToPool",0,p,"pruneStaleFreeProxies",0,E,"recordFreeProxySync",0,S,"recordFreeProxySyncErrors",0,y,"upsertFreeProxy",0,o])},790883,e=>{"use strict";var t=e.i(899378);function n(e){return e&&"object"==typeof e?e:{}}let r=["metadata.google.internal","169.254.169.254","metadata.aws.internal"];function a(e){let t=null;if(e.cliproxyapi_model_mapping&&"string"==typeof e.cliproxyapi_model_mapping)try{t=JSON.parse(e.cliproxyapi_model_mapping)}catch{t=null}return{id:e.id,providerId:e.provider_id,mode:e.mode,cliproxyapiModelMapping:t,nativePriority:e.native_priority,cliproxyapiPriority:e.cliproxyapi_priority,enabled:1===e.enabled||!0===e.enabled,family:"string"==typeof e.family?e.family:"auto",createdAt:e.created_at,updatedAt:e.updated_at}}async function o(){return(0,t.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config ORDER BY provider_id").all().map(e=>a(n(e)))}async function s(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config WHERE provider_id = ?").get(e);return r?a(n(r)):null}async function i(e){let n=(0,t.getDbInstance)(),r=e.mode??"native",a=void 0!==e.cliproxyapiModelMapping?JSON.stringify(e.cliproxyapiModelMapping):null,o=e.nativePriority??1,i=e.cliproxyapiPriority??2,l=+(!1!==e.enabled),u=e.family??"auto";return n.prepare(`INSERT INTO upstream_proxy_config
     (provider_id, mode, cliproxyapi_model_mapping, native_priority, cliproxyapi_priority, enabled, family, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
     ON CONFLICT(provider_id) DO UPDATE SET
       mode = excluded.mode,
       cliproxyapi_model_mapping = excluded.cliproxyapi_model_mapping,
       native_priority = excluded.native_priority,
       cliproxyapi_priority = excluded.cliproxyapi_priority,
       enabled = excluded.enabled,
       family = excluded.family,
       updated_at = datetime('now')`).run(e.providerId,r,a,o,i,l,u),s(e.providerId)}async function l(e,n){let r=(0,t.getDbInstance)();if(!await s(e))throw Error(`Provider ${e} not found`);let a=["updated_at = datetime('now')"],o=[];return void 0!==n.mode&&(a.push("mode = ?"),o.push(n.mode)),void 0!==n.cliproxyapiModelMapping&&(a.push("cliproxyapi_model_mapping = ?"),o.push(null===n.cliproxyapiModelMapping?null:JSON.stringify(n.cliproxyapiModelMapping))),void 0!==n.nativePriority&&(a.push("native_priority = ?"),o.push(n.nativePriority)),void 0!==n.cliproxyapiPriority&&(a.push("cliproxyapi_priority = ?"),o.push(n.cliproxyapiPriority)),void 0!==n.enabled&&(a.push("enabled = ?"),o.push(+(!0===n.enabled))),void 0!==n.family&&(a.push("family = ?"),o.push(n.family)),o.push(e),r.prepare(`UPDATE upstream_proxy_config SET ${a.join(", ")} WHERE provider_id = ?`).run(...o),s(e)}async function u(e){return(0,t.getDbInstance)().prepare("DELETE FROM upstream_proxy_config WHERE provider_id = ?").run(e).changes>0}async function c(e){return(0,t.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config WHERE mode = ? AND enabled = 1 ORDER BY provider_id").all(e).map(e=>a(n(e)))}async function p(e){let t=await s(e);if(!t)return[];let n=[];return t.enabled&&(n.push({executor:"native",priority:t.nativePriority}),("cliproxyapi"===t.mode||"fallback"===t.mode)&&n.push({executor:"cliproxyapi",priority:t.cliproxyapiPriority})),n.sort((e,t)=>e.priority-t.priority),n}e.s(["deleteUpstreamProxyConfig",0,u,"getFallbackChainForProvider",0,p,"getProvidersByMode",0,c,"getUpstreamProxyConfig",0,s,"getUpstreamProxyConfigs",0,o,"updateUpstreamProxyConfig",0,l,"upsertUpstreamProxyConfig",0,i,"validateProxyUrl",0,function(e){try{var t;let n=new URL(e);if(!["http:","https:"].includes(n.protocol))return{valid:!1,error:`Unsupported protocol "${n.protocol}" — use http or https`};if(t=n.hostname,"localhost"!==t&&"127.0.0.1"!==t&&"::1"!==t&&(r.includes(t)||/^10\./.test(t)||/^172\.(1[6-9]|2\d|3[01])\./.test(t)||/^192\.168\./.test(t)||/^0\./.test(t)||/^127\./.test(t)||/^224\./.test(t)||/^169\.254\./.test(t)||0))return{valid:!1,error:`Proxy URL cannot point to private/internal address "${n.hostname}"`};return{valid:!0,url:e}}catch{return{valid:!1,error:`Invalid URL: "${e}"`}}}])},517551,e=>{"use strict";var t=e.i(899378),n=e.i(529646);let r=0;e.s(["cleanupOldSnapshots",0,function(e=90){let n=Date.now();if(n-r<216e5)return 0;let a=(0,t.getDbInstance)(),o=new Date(Date.now()-24*e*36e5).toISOString();try{let e=a.prepare("DELETE FROM quota_snapshots WHERE created_at < ?").run(o);return r=n,e.changes}catch(e){if(e?.message?.includes("no such table"))return 0;throw e}},"getAggregatedSnapshots",0,function(e){let n=(0,t.getDbInstance)(),r=["created_at >= ?"],a=[e.since];e.provider&&(r.push("provider = ?"),a.push(e.provider)),e.until&&(r.push("created_at <= ?"),a.push(e.until));let o=60*Number(e.bucketMinutes);if(!Number.isFinite(o)||o<=0)throw Error("Invalid bucket size");let s="connection"===e.aggregateBy?"bucket, provider, connection_id, window_key":"bucket, provider, window_key",i="connection"===e.aggregateBy?"provider || ':' || connection_id as provider":"provider";try{let e=`
      SELECT
        datetime((strftime('%s', created_at) / ${o}) * ${o}, 'unixepoch') as bucket,
        ${i},
        AVG(remaining_percentage) as remainingPct,
        MAX(is_exhausted) as isExhausted,
        window_key
      FROM quota_snapshots
      WHERE ${r.join(" AND ")}
      GROUP BY ${s}
      ORDER BY bucket ASC
    `;return n.prepare(e).all(...a).map(e=>({timestamp:e.bucket,provider:e.provider,remainingPct:e.remainingPct??0,isExhausted:1===e.isExhausted,windowKey:e.windowKey}))}catch(e){if(e?.message?.includes("no such table"))return[];throw e}},"getLatestQuotaSnapshotsForConnection",0,function(e){let r=(0,t.getDbInstance)();try{let t=r.prepare(`SELECT * FROM quota_snapshots
         WHERE connection_id = ?
         ORDER BY created_at DESC
         LIMIT 200`).all(e),a=new Map;for(let e of t){let t=(0,n.rowToCamel)(e),r=t.windowKey??t.window_key;!r||a.has(r)||a.set(r,t)}return[...a.values()]}catch(e){if(e?.message?.includes("no such table"))return[];throw e}},"getQuotaSnapshots",0,function(e){let r=(0,t.getDbInstance)(),a=["created_at >= ?"],o=[e.since];e.provider&&(a.push("provider = ?"),o.push(e.provider)),e.connectionId&&(a.push("connection_id = ?"),o.push(e.connectionId)),e.until&&(a.push("created_at <= ?"),o.push(e.until));try{let e=`SELECT * FROM quota_snapshots WHERE ${a.join(" AND ")} ORDER BY created_at ASC`;return r.prepare(e).all(...o).map(e=>(0,n.rowToCamel)(e))}catch(e){if(e?.message?.includes("no such table"))return[];throw e}},"saveQuotaSnapshot",0,function(e){let n=(0,t.getDbInstance)(),r=new Date().toISOString();try{n.prepare(`INSERT INTO quota_snapshots
       (provider, connection_id, window_key, remaining_percentage, is_exhausted,
        next_reset_at, window_duration_ms, raw_data, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(e.provider,e.connection_id,e.window_key,e.remaining_percentage,e.is_exhausted,e.next_reset_at,e.window_duration_ms,e.raw_data,r)}catch(e){if(e?.message?.includes("no such table"))return void console.warn("[QuotaSnapshots] Skipping save: quota_snapshots table not found. Awaiting migration.");throw e}}])},68392,e=>{"use strict";var t=e.i(689960),n=e.i(899378);function r(e){return{id:e.id,pattern:e.pattern,comboId:e.combo_id,comboName:e.combo_name||void 0,priority:e.priority,enabled:1===e.enabled,description:e.description||"",createdAt:e.created_at,updatedAt:e.updated_at}}async function a(){return(0,n.getDbInstance)().prepare(`SELECT m.id, m.pattern, m.combo_id, c.name AS combo_name,
              m.priority, m.enabled, m.description,
              m.created_at, m.updated_at
       FROM model_combo_mappings m
       LEFT JOIN combos c ON c.id = m.combo_id
       ORDER BY m.priority DESC, m.created_at ASC`).all().map(r)}async function o(e){let t=(0,n.getDbInstance)().prepare(`SELECT m.id, m.pattern, m.combo_id, c.name AS combo_name,
              m.priority, m.enabled, m.description,
              m.created_at, m.updated_at
       FROM model_combo_mappings m
       LEFT JOIN combos c ON c.id = m.combo_id
       WHERE m.id = ?`).get(e);return t?r(t):null}async function s(e){let r=(0,n.getDbInstance)(),a=new Date().toISOString(),o=(0,t.v4)();return r.prepare(`INSERT INTO model_combo_mappings
     (id, pattern, combo_id, priority, enabled, description, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(o,e.pattern,e.comboId,e.priority??0,+(!1!==e.enabled),e.description||"",a,a),{id:o,pattern:e.pattern,comboId:e.comboId,priority:e.priority??0,enabled:!1!==e.enabled,description:e.description||"",createdAt:a,updatedAt:a}}async function i(e,t){let r=await o(e);if(!r)return null;let a=(0,n.getDbInstance)(),s=new Date().toISOString(),i={pattern:t.pattern??r.pattern,combo_id:t.comboId??r.comboId,priority:t.priority??r.priority,enabled:void 0!==t.enabled?+!!t.enabled:+!!r.enabled,description:t.description??r.description};return a.prepare(`UPDATE model_combo_mappings
     SET pattern = ?, combo_id = ?, priority = ?, enabled = ?,
         description = ?, updated_at = ?
     WHERE id = ?`).run(i.pattern,i.combo_id,i.priority,i.enabled,i.description,s,e),o(e)}async function l(e){return((0,n.getDbInstance)().prepare("DELETE FROM model_combo_mappings WHERE id = ?").run(e).changes??0)>0}async function u(e){for(let t of(0,n.getDbInstance)().prepare(`SELECT m.pattern, m.combo_id, c.data AS combo_data
       FROM model_combo_mappings m
       JOIN combos c ON c.id = m.combo_id
       WHERE m.enabled = 1
       ORDER BY m.priority DESC, m.created_at ASC`).all())if((function(e){let t=e.replace(/[.+^${}()|[\]\\]/g,"\\$&").replace(/\*/g,".*").replace(/\?/g,".");return RegExp(`^${t}$`,"i")})(t.pattern).test(e))try{let e=JSON.parse(t.combo_data);if(!1===e.isActive)continue;return e}catch{continue}return null}e.s(["createModelComboMapping",0,s,"deleteModelComboMapping",0,l,"getModelComboMappingById",0,o,"getModelComboMappings",0,a,"resolveComboForModel",0,u,"updateModelComboMapping",0,i])},496425,e=>{"use strict";var t=e.i(899378);e.s(["getFallbackStats",0,function(e,n){return(0,t.getDbInstance)().prepare(`
      SELECT
        SUM(CASE WHEN (combo_name IS NULL OR combo_name = '') THEN 1 ELSE 0 END) as total,
        SUM(CASE WHEN requested_model IS NOT NULL AND requested_model != '' AND (combo_name IS NULL OR combo_name = '') THEN 1 ELSE 0 END) as with_requested,
        SUM(CASE
          WHEN (combo_name IS NULL OR combo_name = '')
           AND requested_model IS NOT NULL
           AND requested_model != ''
           AND model IS NOT NULL
           AND model != ''
          THEN 1 ELSE 0 END
        ) as fallback_eligible,
        SUM(CASE
          WHEN (combo_name IS NULL OR combo_name = '')
           AND requested_model IS NOT NULL
           AND requested_model != ''
           AND model IS NOT NULL
           AND model != ''
           AND LOWER(CASE WHEN instr(requested_model, '/') > 0 THEN substr(requested_model, instr(requested_model, '/') + 1) ELSE requested_model END) != LOWER(model)
          THEN 1 ELSE 0 END
        ) as fallbacks
      FROM call_logs
      ${e}
    `).get(n)??{total:0,with_requested:0,fallback_eligible:0,fallbacks:0}},"getProviderMetrics",0,function(){return(0,t.getDbInstance)().prepare(`SELECT
          c.provider,
          COUNT(*) as totalRequests,
          SUM(CASE WHEN status >= 200 AND status < 400 THEN 1 ELSE 0 END) as totalSuccesses,
          ROUND(AVG(duration)) as avgLatencyMs,
          MAX(timestamp) as lastRequestAt,
          MAX(
            CASE
              WHEN (status IS NOT NULL AND (status < 200 OR status >= 400))
                OR error_summary IS NOT NULL
              THEN timestamp
              ELSE NULL
            END
          ) as lastErrorAt,
          (
            SELECT c2.status
            FROM call_logs c2
            WHERE c2.provider = c.provider
            ORDER BY c2.timestamp DESC, c2.id DESC
            LIMIT 1
          ) as lastStatus,
          (
            SELECT c3.status
            FROM call_logs c3
            WHERE c3.provider = c.provider
              AND (
                (c3.status IS NOT NULL AND (c3.status < 200 OR c3.status >= 400))
                OR c3.error_summary IS NOT NULL
              )
            ORDER BY c3.timestamp DESC, c3.id DESC
            LIMIT 1
          ) as lastErrorStatus
        FROM call_logs c
        WHERE c.provider IS NOT NULL AND c.provider != '-'
        GROUP BY c.provider`).all()},"getRecentSearchLogs",0,function(){return(0,t.getDbInstance)().prepare(`
        SELECT request_summary, provider, timestamp
        FROM call_logs
        WHERE request_type = 'search'
        ORDER BY timestamp DESC
        LIMIT 10
      `).all()},"getSearchAggregateStats",0,function(e){return(0,t.getDbInstance)().prepare(`SELECT
          COUNT(*) as total,
          COALESCE(SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END), 0) as today,
          COALESCE(SUM(CASE WHEN status >= 400 OR error_summary IS NOT NULL THEN 1 ELSE 0 END), 0) as errors,
          AVG(CASE WHEN duration > 0 THEN duration END) as avg_duration,
          COALESCE(SUM(CASE WHEN duration > 0 AND duration < 5 THEN 1 ELSE 0 END), 0) as cached
         FROM call_logs
         WHERE request_type = 'search'`).get(e)??{total:0,today:0,errors:0,avg_duration:null,cached:0}},"getSearchProviderCounts",0,function(){return(0,t.getDbInstance)().prepare(`SELECT provider, COUNT(*) as cnt
         FROM call_logs WHERE request_type = 'search'
         GROUP BY provider ORDER BY cnt DESC`).all()},"getSearchProviderStats",0,function(){return(0,t.getDbInstance)().prepare(`
        SELECT provider, COUNT(*) as requests,
          CAST(AVG(duration) AS INTEGER) as avg_latency_ms
        FROM call_logs
        WHERE request_type = 'search'
        GROUP BY provider
      `).all()}])},879032,e=>{"use strict";var t=e.i(899378),n=e.i(254799);function r(e){return{...e,kind:e.kind||"custom",events:JSON.parse(e.events||'["*"]'),enabled:1===e.enabled}}function a(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM webhooks WHERE id = ?").get(e);return n?r(n):null}e.s(["createWebhook",0,function(e){let r=(0,t.getDbInstance)(),o=n.default.randomUUID(),s=e.secret||`whsec_${n.default.randomBytes(24).toString("hex")}`,i=e.kind||"custom";return r.prepare(`INSERT INTO webhooks (id, url, events, secret, description, kind, metadata_encrypted)
       VALUES (?, ?, ?, ?, ?, ?, ?)`).run(o,e.url,JSON.stringify(e.events||["*"]),s,e.description||"",i,e.metadataEncrypted??null),a(o)},"deleteWebhook",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM webhooks WHERE id = ?").run(e).changes>0},"disableWebhooksWithHighFailures",0,function(e=10){return(0,t.getDbInstance)().prepare("UPDATE webhooks SET enabled = 0 WHERE failure_count >= ? AND enabled = 1").run(e).changes},"getEnabledWebhooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM webhooks WHERE enabled = 1").all().map(r)},"getWebhook",0,a,"getWebhooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM webhooks ORDER BY created_at DESC").all().map(r)},"recordWebhookDelivery",0,function(e,n,r){let a=(0,t.getDbInstance)();r?a.prepare("UPDATE webhooks SET last_triggered_at = datetime('now'), last_status = ?, failure_count = 0 WHERE id = ?").run(n,e):a.prepare("UPDATE webhooks SET last_triggered_at = datetime('now'), last_status = ?, failure_count = failure_count + 1 WHERE id = ?").run(n,e)},"updateWebhook",0,function(e,n){let r=(0,t.getDbInstance)(),o=a(e);if(!o)return null;let s=[],i=[];return(void 0!==n.url&&(s.push("url = ?"),i.push(n.url)),void 0!==n.events&&(s.push("events = ?"),i.push(JSON.stringify(n.events))),void 0!==n.secret&&(s.push("secret = ?"),i.push(n.secret)),void 0!==n.enabled&&(s.push("enabled = ?"),i.push(+!!n.enabled)),void 0!==n.description&&(s.push("description = ?"),i.push(n.description)),void 0!==n.kind&&(s.push("kind = ?"),i.push(n.kind)),void 0!==n.metadataEncrypted&&(s.push("metadata_encrypted = ?"),i.push(n.metadataEncrypted)),0===s.length)?o:(i.push(e),r.prepare(`UPDATE webhooks SET ${s.join(", ")} WHERE id = ?`).run(...i),a(e))}])},829422,e=>{"use strict";var t=e.i(899378);let n="providerLimitsCache";function r(e){try{return JSON.parse(e)}catch{return null}}function a(e){return e&&"object"==typeof e&&!Array.isArray(e)?e:null}function o(e){let t=a(e);if(!t)return null;let n="string"==typeof t.fetchedAt&&t.fetchedAt.trim()?t.fetchedAt:null;if(!n)return null;let r=Number(t.bankedResetCredits);return{quotas:a(t.quotas),plan:t.plan??null,message:"string"==typeof t.message?t.message:null,fetchedAt:n,source:"string"==typeof t.source?t.source:null,...Number.isFinite(r)?{bankedResetCredits:r}:{}}}e.s(["deleteProviderLimitsCache",0,function(e){t.isBuildPhase||t.isCloud||(0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(n,e)},"getAllProviderLimitsCache",0,function(){if(t.isBuildPhase||t.isCloud)return{};let e=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(n),a={};for(let t of e){let e=o(r(t.value));e&&(a[t.key]=e)}return a},"getProviderLimitsCache",0,function(e){if(t.isBuildPhase||t.isCloud)return null;let a=(0,t.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(n,e);return a?.value?o(r(a.value)):null},"setProviderLimitsCache",0,function(e,r){return t.isBuildPhase||t.isCloud||(0,t.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(n,e,JSON.stringify(r)),r},"setProviderLimitsCacheBatch",0,function(e){if(t.isBuildPhase||t.isCloud||0===e.length)return 0;let r=(0,t.getDbInstance)(),a=r.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)");return r.transaction(e=>{for(let t of e)a.run(n,t.connectionId,JSON.stringify(t.entry))})(e),e.length}])},894278,e=>{"use strict";var t=e.i(899378);e.s(["getCacheStatsSummary",0,function(e){let n=(0,t.getDbInstance)();e&&e.toISOString();let r=e?n.prepare("SELECT COUNT(*) as totalRequests, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats WHERE created_at >= ?").get(e.toISOString()):n.prepare("SELECT COUNT(*) as totalRequests, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats").get();if(!r||0===r.totalRequests)return{totalRequests:0,avgNetSavings:0,cacheHitRate:0,byProvider:{}};let a=e?n.prepare("SELECT provider, COUNT(*) as count, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats WHERE created_at >= ? GROUP BY provider").all(e.toISOString()):n.prepare("SELECT provider, COUNT(*) as count, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats GROUP BY provider").all(),o={};for(let e of a)o[e.provider]={count:e.count,avgNetSavings:e.avgNetSavings,cacheHitRate:e.cacheHitRate};return{totalRequests:r.totalRequests,avgNetSavings:r.avgNetSavings??0,cacheHitRate:r.cacheHitRate??0,byProvider:o}},"recordCacheStats",0,function(e){let n=(0,t.getDbInstance)(),r=`INSERT INTO compression_cache_stats (
    provider, 
    model, 
    compression_mode, 
    cache_control_present, 
    estimated_cache_hit, 
    tokens_saved_compression, 
    tokens_saved_caching, 
    net_savings
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;n.prepare(r).run(e.provider,e.model??"",e.compressionMode,+!!e.cacheControlPresent,+!!e.estimatedCacheHit,e.tokensSavedCompression,e.tokensSavedCaching,e.netSavings)}])},747369,e=>{"use strict";var t=e.i(899378);function n(){(0,t.getDbInstance)().exec(`
    CREATE TABLE IF NOT EXISTS compression_run_telemetry (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp INTEGER NOT NULL,
      request_id TEXT,
      model TEXT,
      provider TEXT,
      source TEXT,
      tokens_before INTEGER NOT NULL,
      tokens_after INTEGER NOT NULL,
      ratio REAL,
      cost_delta REAL,
      output_styles TEXT,
      output_style_bypass TEXT,
      output_tokens INTEGER
    )
  `)}e.s(["getCompressionRunTelemetrySummary",0,function(){let e=(0,t.getDbInstance)();n();let r=e.prepare(`SELECT tokens_before, tokens_after, output_styles, output_style_bypass, output_tokens
       FROM compression_run_telemetry`).all(),a={totalRuns:r.length,totalTokensSaved:0,runsWithStyles:0,bypassCount:0,totalOutputTokens:0,appliedStyleCounts:{}};for(let e of r)if(a.totalTokensSaved+=Math.max(0,e.tokens_before-e.tokens_after),a.totalOutputTokens+=e.output_tokens??0,e.output_style_bypass&&(a.bypassCount+=1),e.output_styles){a.runsWithStyles+=1;try{for(let t of JSON.parse(e.output_styles))a.appliedStyleCounts[t.id]=(a.appliedStyleCounts[t.id]??0)+1}catch{}}return a},"insertCompressionRunTelemetryRow",0,function(e){try{let r=(0,t.getDbInstance)();n(),r.prepare(`INSERT INTO compression_run_telemetry (
        timestamp, request_id, model, provider, source,
        tokens_before, tokens_after, ratio, cost_delta,
        output_styles, output_style_bypass, output_tokens
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(Date.now(),e.requestId??null,e.model??null,e.provider??null,e.source??null,e.tokensBefore,e.tokensAfter,e.ratio,e.costDelta??null,e.outputStyles&&e.outputStyles.length>0?JSON.stringify(e.outputStyles):null,e.outputStyleBypass??null,e.outputTokens??null)}catch{}}])},441273,e=>{"use strict";var t=e.i(899378);e.s(["sumUsageTokensThisMonth",0,function(e=(0,t.getDbInstance)()){try{let t=e.prepare(`SELECT COALESCE(SUM(total_input_tokens + total_output_tokens), 0) AS used
         FROM daily_usage_summary
         WHERE date >= strftime('%Y-%m-01','now')`).get();return t?.used??0}catch{return 0}}])},446908,e=>{"use strict";var t=e.i(899378),n=e.i(719201);e.s(["getDeliveries",0,function(e,n){return(0,t.getDbInstance)().prepare(`SELECT id, webhook_id, event_type, status, http_status, latency_ms, error, created_at
       FROM webhook_deliveries
       WHERE webhook_id = ?
       ORDER BY created_at DESC, id DESC
       LIMIT ?`).all(e,n)},"insertDelivery",0,function(e){let r=(0,t.getDbInstance)(),a=r.prepare(`INSERT INTO webhook_deliveries
       (webhook_id, event_type, status, http_status, latency_ms, error, payload_snapshot)
     VALUES (?, ?, ?, ?, ?, ?, ?)`),o=r.prepare(`DELETE FROM webhook_deliveries
     WHERE webhook_id = ?
       AND id NOT IN (
         SELECT id FROM webhook_deliveries
         WHERE webhook_id = ?
         ORDER BY created_at DESC, id DESC
         LIMIT ?
       )`),s=null!=e.error&&(0,n.sanitizeErrorMessage)(e.error)||null;r.transaction(()=>{a.run(e.webhookId,e.eventType,e.status,e.httpStatus??null,e.latencyMs??null,s,e.payloadSnapshot??null),o.run(e.webhookId,e.webhookId,100)})()}])}];

//# sourceMappingURL=%5Broot-of-the-server%5D__0p1w1rr._.js.map