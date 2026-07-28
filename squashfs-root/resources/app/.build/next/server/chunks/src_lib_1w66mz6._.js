module.exports=[576992,e=>{"use strict";var t=e.i(446786),r=e.i(814747),a=e.i(785148);let n=()=>r.default.join(r.default.join(t.default.homedir(),".omp","agent"),"agent.db");e.s(["deleteOmpCredentials",0,function(e){let t=n(),r=new a.default(t);r.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(e),r.close()},"getOmpCredentials",0,function(e){let t=n();try{let r=new a.default(t,{readonly:!0}),n=r.prepare("SELECT data FROM auth_credentials WHERE provider = ? AND credential_type = 'api_key'").get(e);if(r.close(),n?.data){let e=JSON.parse(n.data);return{hasOmniRoute:!0,baseUrl:e.baseUrl||null,apiKey:e.apiKey||null}}return{hasOmniRoute:!1,baseUrl:null,apiKey:null}}catch{return{hasOmniRoute:!1,baseUrl:null,apiKey:null}}},"saveOmpCredentials",0,function(e,t,r){let i=n(),s=new a.default(i);s.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(e),s.prepare("INSERT INTO auth_credentials (provider, credential_type, data, disabled_cause, identity_key, created_at, updated_at) VALUES (?, ?, ?, NULL, NULL, ?, ?)").run(e,"api_key",JSON.stringify({apiKey:t,baseUrl:r}),Math.floor(Date.now()/1e3),Math.floor(Date.now()/1e3)),s.close()}])},926554,e=>{"use strict";var t=e.i(666680),r=e.i(899378),a=e.i(529646);function n(e,t,r){return e.prepare(`PRAGMA table_info(${t})`).all().some(e=>e&&"string"==typeof e.name&&e.name===r)}function i(e){e.prepare(`CREATE TABLE IF NOT EXISTS eval_suites (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )`).run(),n(e,"eval_suites","description")||e.prepare("ALTER TABLE eval_suites ADD COLUMN description TEXT").run(),n(e,"eval_suites","created_at")||e.prepare("ALTER TABLE eval_suites ADD COLUMN created_at TEXT NOT NULL DEFAULT ''").run(),n(e,"eval_suites","updated_at")||e.prepare("ALTER TABLE eval_suites ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''").run(),e.prepare(`CREATE TABLE IF NOT EXISTS eval_cases (
      id TEXT PRIMARY KEY,
      suite_id TEXT NOT NULL,
      sort_order INTEGER NOT NULL DEFAULT 0,
      name TEXT NOT NULL,
      model TEXT,
      input_json TEXT NOT NULL,
      expected_strategy TEXT NOT NULL,
      expected_value TEXT,
      tags_json TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )`).run(),n(e,"eval_cases","sort_order")||e.prepare("ALTER TABLE eval_cases ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0").run(),n(e,"eval_cases","model")||e.prepare("ALTER TABLE eval_cases ADD COLUMN model TEXT").run(),n(e,"eval_cases","input_json")||e.prepare("ALTER TABLE eval_cases ADD COLUMN input_json TEXT NOT NULL DEFAULT '{}'").run(),n(e,"eval_cases","expected_strategy")||e.prepare("ALTER TABLE eval_cases ADD COLUMN expected_strategy TEXT NOT NULL DEFAULT 'contains'").run(),n(e,"eval_cases","expected_value")||e.prepare("ALTER TABLE eval_cases ADD COLUMN expected_value TEXT").run(),n(e,"eval_cases","tags_json")||e.prepare("ALTER TABLE eval_cases ADD COLUMN tags_json TEXT").run(),n(e,"eval_cases","created_at")||e.prepare("ALTER TABLE eval_cases ADD COLUMN created_at TEXT NOT NULL DEFAULT ''").run(),n(e,"eval_cases","updated_at")||e.prepare("ALTER TABLE eval_cases ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''").run(),e.prepare("CREATE INDEX IF NOT EXISTS idx_eval_suites_updated_at ON eval_suites(updated_at DESC)").run(),e.prepare("CREATE INDEX IF NOT EXISTS idx_eval_cases_suite_order ON eval_cases(suite_id, sort_order ASC, created_at ASC)").run()}function s(e){if(e&&"object"==typeof e&&!Array.isArray(e))return e;if("string"!=typeof e||0===e.trim().length)return{};try{let t=JSON.parse(e);return t&&"object"==typeof t&&!Array.isArray(t)?t:{}}catch{return{}}}function o(e){let t=Number(e);return Number.isFinite(t)?t:0}function u(e){var t;let r=e&&"object"==typeof e&&!Array.isArray(e)?e:{},a=o(r.max_tokens),n={messages:Array.isArray(t=r.messages)?t.map(e=>{if(!e||"object"!=typeof e||Array.isArray(e))return null;let t="string"==typeof e.role?e.role.trim():"",r="string"==typeof e.content?e.content:"";return t&&r.trim()?{role:t,content:r}:null}).filter(e=>null!==e):[]};return a>0&&(n.max_tokens=Math.floor(a)),n}function l(e){let t=e&&"object"==typeof e&&!Array.isArray(e)?e:{},r="string"==typeof t.strategy?t.strategy.trim():"",a="string"==typeof t.value&&t.value.trim().length>0?t.value:void 0;return{strategy:"exact"===r||"regex"===r||"custom"===r?r:"contains",...a?{value:a}:{}}}function d(e,t){return`${e}:${"string"==typeof t&&t.trim().length>0?t.trim():"__default__"}`}function c(e){let t,r,n,i,u=(0,a.rowToCamel)(e);if(!u)return null;let l=s(u.summary??u.summaryJson),c=Object.fromEntries(Object.entries(s(u.outputs??u.outputsJson)).filter(e=>"string"==typeof e[0]).map(([e,t])=>[e,"string"==typeof t?t:String(t??"")]));return{id:"string"==typeof u.id?u.id:"",runGroupId:"string"==typeof u.runGroupId&&u.runGroupId.trim().length>0?u.runGroupId:null,suiteId:"string"==typeof u.suiteId?u.suiteId:"",suiteName:"string"==typeof u.suiteName?u.suiteName:"",target:(t=u.targetType,n="string"==typeof(r=u.targetId)&&r.trim().length>0?r.trim():null,{type:i="combo"===t||"model"===t||"suite-default"===t?t:"suite-default",id:n,key:d(i,n),label:"string"==typeof u.targetLabel&&u.targetLabel.trim().length>0?u.targetLabel.trim():"combo"===i?`Combo: ${n||"Unknown"}`:"model"===i?`Model: ${n||"Unknown"}`:"Suite defaults"}),apiKeyId:"string"==typeof u.apiKeyId&&u.apiKeyId.trim().length>0?u.apiKeyId:null,avgLatencyMs:o(u.avgLatencyMs),summary:{total:o(l.total??u.total),passed:o(l.passed??u.passed),failed:o(l.failed??u.failed),passRate:o(l.passRate??u.passRate)},results:function(e){if(Array.isArray(e))return e.filter(e=>!!e&&"object"==typeof e&&!Array.isArray(e));if("string"!=typeof e||0===e.trim().length)return[];try{let t=JSON.parse(e);return Array.isArray(t)?t.filter(e=>!!e&&"object"==typeof e&&!Array.isArray(e)):[]}catch{return[]}}(u.results??u.resultsJson),outputs:c,createdAt:"string"==typeof u.createdAt?u.createdAt:""}}function p(e={}){let t=(0,r.getDbInstance)(),a=[],n=[];e.suiteId&&(a.push("suite_id = ?"),n.push(e.suiteId)),e.runGroupId&&(a.push("run_group_id = ?"),n.push(e.runGroupId));let i=Number.isFinite(Number(e.limit))?Math.min(200,Math.max(1,Math.floor(Number(e.limit)))):20;n.push(i);let s=`SELECT *
    FROM eval_runs
    ${a.length>0?`WHERE ${a.join(" AND ")}`:""}
    ORDER BY created_at DESC
    LIMIT ?`;return t.prepare(s).all(...n).map(e=>c(e)).filter(e=>null!==e)}function E(){let e=(0,r.getDbInstance)();i(e);let t=e.prepare("SELECT * FROM eval_suites ORDER BY updated_at DESC, created_at DESC").all(),n=e.prepare("SELECT * FROM eval_cases ORDER BY suite_id ASC, sort_order ASC, created_at ASC, id ASC").all(),d=new Map;for(let e of n){let t=function(e){let t=(0,a.rowToCamel)(e);if(!t)return null;let r=u(s(t.input??t.inputJson)),n=l({strategy:t.expectedStrategy,value:t.expectedValue});return{id:"string"==typeof t.id?t.id:"",suiteId:"string"==typeof t.suiteId?t.suiteId:"",name:"string"==typeof t.name?t.name:"",..."string"==typeof t.model&&t.model.trim().length>0?{model:t.model.trim()}:{},input:r,expected:n,tags:function(e){if(Array.isArray(e))return e.filter(e=>"string"==typeof e).map(e=>e.trim()).filter(e=>e.length>0);if("string"!=typeof e||0===e.trim().length)return[];try{let t=JSON.parse(e);return Array.isArray(t)?t.filter(e=>"string"==typeof e).map(e=>e.trim()).filter(e=>e.length>0):[]}catch{return[]}}(t.tags??t.tagsJson),sortOrder:o(t.sortOrder),createdAt:"string"==typeof t.createdAt?t.createdAt:"",updatedAt:"string"==typeof t.updatedAt?t.updatedAt:""}}(e);if(!t||!t.suiteId)continue;let r=d.get(t.suiteId)||[];r.push(t),d.set(t.suiteId,r)}return t.map(e=>{var t;let r,n=(0,a.rowToCamel)(e),i=n&&"string"==typeof n.id?n.id:"";return t=d.get(i)||[],(r=(0,a.rowToCamel)(e))?{id:"string"==typeof r.id?r.id:"",name:"string"==typeof r.name?r.name:"",..."string"==typeof r.description&&r.description.trim().length>0?{description:r.description}:{},source:"custom",caseCount:t.length,cases:t,createdAt:"string"==typeof r.createdAt?r.createdAt:"",updatedAt:"string"==typeof r.updatedAt?r.updatedAt:""}:null}).filter(e=>null!==e)}function _(e){let t=e.trim();return t&&E().find(e=>e.id===t)||null}e.s(["deleteCustomEvalSuite",0,function(e){let t=(0,r.getDbInstance)();i(t);let a=e.trim();if(!a)return!1;t.prepare("BEGIN").run();try{t.prepare("DELETE FROM eval_cases WHERE suite_id = ?").run(a);let e=t.prepare("DELETE FROM eval_suites WHERE id = ?").run(a);return t.prepare("COMMIT").run(),e.changes>0}catch(e){throw t.prepare("ROLLBACK").run(),e}},"getCustomEvalSuite",0,_,"getEvalScorecard",0,function(e={}){var t;let r,a,n=p({suiteId:e.suiteId,limit:e.limit||50});if(0===n.length)return null;let i=new Map;for(let e of n){let t=`${e.suiteId}:${e.target.key}`;i.has(t)||i.set(t,e)}return r=(t=Array.from(i.values()).map(e=>({suiteId:`${e.suiteId}:${e.target.key}`,suiteName:`${e.suiteName} \xb7 ${e.target.label}`,results:e.results,summary:e.summary}))).reduce((e,t)=>e+t.summary.total,0),a=t.reduce((e,t)=>e+t.summary.passed,0),{suites:t.length,totalCases:r,totalPassed:a,overallPassRate:r>0?Math.round(a/r*100):0,perSuite:t.map(e=>({id:e.suiteId,name:e.suiteName,passRate:e.summary.passRate}))}},"listCustomEvalSuites",0,E,"listEvalRuns",0,p,"listModelEvalRunsForRouting",0,function(e){let t=[...new Set(e.targetIds.map(e=>e.trim()).filter(Boolean))].slice(0,200);if(0===t.length)return[];let a=Array.isArray(e.suiteIds)?[...new Set(e.suiteIds.map(e=>e.trim()).filter(Boolean))].slice(0,50):[],n=(0,r.getDbInstance)(),i=["target_type = 'model'"],s=[];i.push(`target_id IN (${t.map(()=>"?").join(", ")})`),s.push(...t),a.length>0&&(i.push(`suite_id IN (${a.map(()=>"?").join(", ")})`),s.push(...a));let o=Number(e.maxAgeHours);Number.isFinite(o)&&o>0&&(i.push("created_at >= ?"),s.push(new Date(Date.now()-60*o*6e4).toISOString()));let u=Number.isFinite(Number(e.limit))?Math.min(1e3,Math.max(1,Math.floor(Number(e.limit)))):Math.min(1e3,Math.max(50,t.length*Math.max(3,a.length||5)*2));return s.push(u),n.prepare(`SELECT *
       FROM eval_runs
       WHERE ${i.join(" AND ")}
       ORDER BY created_at DESC
       LIMIT ?`).all(...s).map(e=>c(e)).filter(e=>null!==e)},"saveCustomEvalSuite",0,function(e){let a=(0,r.getDbInstance)();i(a);let n=new Date().toISOString(),s="string"==typeof e.id&&e.id.trim().length>0?e.id.trim():(0,t.randomUUID)(),o=e.name.trim(),d="string"==typeof e.description&&e.description.trim().length>0?e.description.trim():null;if(!o)throw Error("Suite name is required");if(!Array.isArray(e.cases)||0===e.cases.length)throw Error("At least one eval case is required");a.prepare("BEGIN").run();try{a.prepare("SELECT id FROM eval_suites WHERE id = ?").get(s)?a.prepare(`UPDATE eval_suites
         SET name = ?, description = ?, updated_at = ?
         WHERE id = ?`).run(o,d,n,s):a.prepare(`INSERT INTO eval_suites (id, name, description, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?)`).run(s,o,d,n,n),a.prepare("DELETE FROM eval_cases WHERE suite_id = ?").run(s),e.cases.forEach((e,r)=>{let i="string"==typeof e.id&&e.id.trim().length>0?e.id.trim():(0,t.randomUUID)(),o=e.name.trim(),d="string"==typeof e.model&&e.model.trim().length>0?e.model.trim():null,c=u(e.input),p=l(e.expected),E=Array.isArray(e.tags)?e.tags.map(e=>e.trim()).filter(e=>e.length>0):[];if(!o)throw Error(`Case ${r+1} is missing a name`);if(0===c.messages.length)throw Error(`Case ${r+1} must include at least one message`);if(("contains"===p.strategy||"exact"===p.strategy||"regex"===p.strategy)&&!p.value)throw Error(`Case ${r+1} must include an expected value`);a.prepare(`INSERT INTO eval_cases
          (id, suite_id, sort_order, name, model, input_json, expected_strategy, expected_value,
           tags_json, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(i,s,r,o,d,JSON.stringify(c),p.strategy,p.value||null,JSON.stringify(E),n,n)}),a.prepare("COMMIT").run()}catch(e){throw a.prepare("ROLLBACK").run(),e}let c=_(s);if(!c)throw Error("Failed to persist eval suite");return c},"saveEvalRun",0,function(e){let a=(0,r.getDbInstance)(),n=e.createdAt||new Date().toISOString(),i=(0,t.randomUUID)(),s="string"==typeof e.target.id&&e.target.id.trim().length>0?e.target.id.trim():null,o=Number.isFinite(Number(e.avgLatencyMs))?Math.max(0,Math.round(Number(e.avgLatencyMs))):0;return a.prepare(`INSERT INTO eval_runs
      (id, run_group_id, suite_id, suite_name, target_type, target_id, target_label, api_key_id,
       pass_rate, total, passed, failed, avg_latency_ms, summary_json, results_json, outputs_json, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(i,e.runGroupId||null,e.suiteId,e.suiteName,e.target.type,s,e.target.label,e.apiKeyId||null,e.summary.passRate,e.summary.total,e.summary.passed,e.summary.failed,o,JSON.stringify(e.summary),JSON.stringify(e.results||[]),JSON.stringify(e.outputs||{}),n),{id:i,runGroupId:e.runGroupId||null,suiteId:e.suiteId,suiteName:e.suiteName,target:{type:e.target.type,id:s,key:d(e.target.type,s),label:e.target.label},apiKeyId:e.apiKeyId||null,avgLatencyMs:o,summary:e.summary,results:e.results||[],outputs:e.outputs||{},createdAt:n}},"serializeEvalTargetKey",0,d])},964183,e=>{"use strict";var t=e.i(899378);let r=new Set(["enabled","mode","updated_at"]);e.s(["updateSkill",0,function(e,a){let n=(0,t.getDbInstance)(),i=[],s=[];for(let[e,t]of Object.entries(a))r.has(e)&&(i.push(`${e} = ?`),s.push(t));return 0===i.length?0:(i.push("updated_at = datetime('now')"),s.push(e),n.prepare(`UPDATE skills SET ${i.join(", ")} WHERE id = ?`).run(...s).changes)}])},583281,e=>{"use strict";var t=e.i(254799),r=e.i(689960),a=e.i(899378),n=e.i(529646);function i(){return new Date().toISOString().slice(0,10)}function s(){return new Date().toISOString().slice(0,13)}function o(e){return e&&"string"==typeof e?(0,t.createHash)("sha256").update(e).digest("hex"):""}function u(e,t,r,a){let n=i(),o=s();e.prepare(`
    UPDATE ${t}
    SET daily_issued = CASE WHEN last_reset_day <> ? THEN 0 ELSE daily_issued END,
        hourly_issued = CASE WHEN last_reset_hour <> ? THEN 0 ELSE hourly_issued END,
        last_reset_day = ?,
        last_reset_hour = ?
    WHERE ${r} = ?
  `).run(n,o,n,o,a)}e.s(["checkQuota",0,function(e="",t=""){let r=(0,a.getDbInstance)();if(i(),s(),e){u(r,"provider_key_limits","provider",e);let t=r.prepare("SELECT * FROM provider_key_limits WHERE provider = ?").get(e);if(t){if(null!==t.hourly_issue_limit&&t.hourly_issued>=t.hourly_issue_limit)return{allowed:!1,errorCode:"PROVIDER_QUOTA_EXCEEDED",errorMessage:`Hourly issue limit (${t.hourly_issue_limit}) reached for provider '${e}'`,provider:e};if(null!==t.daily_issue_limit&&t.daily_issued>=t.daily_issue_limit)return{allowed:!1,errorCode:"PROVIDER_QUOTA_EXCEEDED",errorMessage:`Daily issue limit (${t.daily_issue_limit}) reached for provider '${e}'`,provider:e};if(null!==t.max_active_keys){let{activeCount:a}=r.prepare("SELECT COUNT(*) as activeCount FROM registered_keys WHERE provider = ? AND is_active = 1").get(e);if(a>=t.max_active_keys)return{allowed:!1,errorCode:"MAX_ACTIVE_KEYS_EXCEEDED",errorMessage:`Max active keys (${t.max_active_keys}) reached for provider '${e}'`,provider:e,providerActiveKeys:a}}}}if(t){u(r,"account_key_limits","account_id",t);let e=r.prepare("SELECT * FROM account_key_limits WHERE account_id = ?").get(t);if(e){if(null!==e.hourly_issue_limit&&e.hourly_issued>=e.hourly_issue_limit)return{allowed:!1,errorCode:"ACCOUNT_QUOTA_EXCEEDED",errorMessage:`Hourly issue limit (${e.hourly_issue_limit}) reached for account '${t}'`,accountId:t};if(null!==e.daily_issue_limit&&e.daily_issued>=e.daily_issue_limit)return{allowed:!1,errorCode:"ACCOUNT_QUOTA_EXCEEDED",errorMessage:`Daily issue limit (${e.daily_issue_limit}) reached for account '${t}'`,accountId:t};if(null!==e.max_active_keys){let{activeCount:a}=r.prepare("SELECT COUNT(*) as activeCount FROM registered_keys WHERE account_id = ? AND is_active = 1").get(t);if(a>=e.max_active_keys)return{allowed:!1,errorCode:"MAX_ACTIVE_KEYS_EXCEEDED",errorMessage:`Max active keys (${e.max_active_keys}) reached for account '${t}'`,accountId:t,accountActiveKeys:a}}}}return{allowed:!0}},"getAccountKeyLimit",0,function(e){let t=(0,a.getDbInstance)().prepare("SELECT * FROM account_key_limits WHERE account_id = ?").get(e);return t?(0,n.rowToCamel)(t):null},"getProviderKeyLimit",0,function(e){let t=(0,a.getDbInstance)().prepare("SELECT * FROM provider_key_limits WHERE provider = ?").get(e);return t?(0,n.rowToCamel)(t):null},"getRegisteredKey",0,function(e){let t=(0,a.getDbInstance)().prepare("SELECT * FROM registered_keys WHERE id = ?").get(e);return t?(0,n.rowToCamel)(t):null},"incrementRegisteredKeyUsage",0,function(e){(0,a.getDbInstance)().prepare(`
    UPDATE registered_keys
    SET daily_used = daily_used + 1, hourly_used = hourly_used + 1, updated_at = datetime('now')
    WHERE id = ?
  `).run(e)},"issueRegisteredKey",0,function(e){let l=(0,a.getDbInstance)(),{name:d,provider:c="",accountId:p="",idempotencyKey:E,expiresAt:_,dailyBudget:m,hourlyBudget:y}=e;if(E){let e=l.prepare("SELECT * FROM registered_keys WHERE idempotency_key = ?").get(E);if(e)return{idempotencyConflict:!0,existing:(0,n.rowToCamel)(e)}}let g="ork_"+(0,t.randomBytes)(24).toString("base64url"),T=(0,r.v4)(),S=o(g),f=g.slice(0,12);l.prepare(`
    INSERT INTO registered_keys
      (id, key, key_prefix, name, provider, account_id, idempotency_key, expires_at, daily_budget, hourly_budget, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(T,S,f,d,c,p,E??null,_??null,m??null,y??null,i(),s()),c&&(u(l,"provider_key_limits","provider",c),l.prepare(`
      INSERT INTO provider_key_limits (provider, daily_issued, hourly_issued, last_reset_day, last_reset_hour)
      VALUES (?, 1, 1, ?, ?)
      ON CONFLICT(provider) DO UPDATE SET
        daily_issued = daily_issued + 1,
        hourly_issued = hourly_issued + 1,
        updated_at = datetime('now')
    `).run(c,i(),s())),p&&(u(l,"account_key_limits","account_id",p),l.prepare(`
      INSERT INTO account_key_limits (account_id, daily_issued, hourly_issued, last_reset_day, last_reset_hour)
      VALUES (?, 1, 1, ?, ?)
      ON CONFLICT(account_id) DO UPDATE SET
        daily_issued = daily_issued + 1,
        hourly_issued = hourly_issued + 1,
        updated_at = datetime('now')
    `).run(p,i(),s()));let A=l.prepare("SELECT * FROM registered_keys WHERE id = ?").get(T);return{...(0,n.rowToCamel)(A),rawKey:g}},"listRegisteredKeys",0,function(e={}){let t=(0,a.getDbInstance)(),r="SELECT * FROM registered_keys WHERE 1=1",i=[];return e.provider&&(r+=" AND provider = ?",i.push(e.provider)),e.accountId&&(r+=" AND account_id = ?",i.push(e.accountId)),r+=" ORDER BY created_at DESC LIMIT 500",t.prepare(r).all(...i).map(e=>(0,n.rowToCamel)(e))},"revokeRegisteredKey",0,function(e){return(0,a.getDbInstance)().prepare(`
    UPDATE registered_keys
    SET is_active = 0, revoked_at = datetime('now'), updated_at = datetime('now')
    WHERE id = ? AND is_active = 1
  `).run(e).changes>0},"setAccountKeyLimit",0,function(e,t){(0,a.getDbInstance)().prepare(`
    INSERT INTO account_key_limits (account_id, max_active_keys, daily_issue_limit, hourly_issue_limit, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(account_id) DO UPDATE SET
      max_active_keys = excluded.max_active_keys,
      daily_issue_limit = excluded.daily_issue_limit,
      hourly_issue_limit = excluded.hourly_issue_limit,
      updated_at = datetime('now')
  `).run(e,t.maxActiveKeys??null,t.dailyIssueLimit??null,t.hourlyIssueLimit??null,i(),s())},"setProviderKeyLimit",0,function(e,t){(0,a.getDbInstance)().prepare(`
    INSERT INTO provider_key_limits (provider, max_active_keys, daily_issue_limit, hourly_issue_limit, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(provider) DO UPDATE SET
      max_active_keys = excluded.max_active_keys,
      daily_issue_limit = excluded.daily_issue_limit,
      hourly_issue_limit = excluded.hourly_issue_limit,
      updated_at = datetime('now')
  `).run(e,t.maxActiveKeys??null,t.dailyIssueLimit??null,t.hourlyIssueLimit??null,i(),s())},"validateRegisteredKey",0,function(e){let t=(0,a.getDbInstance)(),r=o(e),u=t.prepare(`
    SELECT * FROM registered_keys
    WHERE key = ? AND is_active = 1
      AND (expires_at IS NULL OR expires_at > datetime('now'))
  `).get(r);if(!u)return null;let l=i(),d=s();return((u.last_reset_day!==l||u.last_reset_hour!==d)&&t.prepare(`
      UPDATE registered_keys
      SET daily_used = CASE WHEN last_reset_day <> ? THEN 0 ELSE daily_used END,
          hourly_used = CASE WHEN last_reset_hour <> ? THEN 0 ELSE hourly_used END,
          last_reset_day = ?, last_reset_hour = ?
      WHERE id = ?
    `).run(l,d,l,d,u.id),null!==u.daily_budget&&u.daily_used>=u.daily_budget||null!==u.hourly_budget&&u.hourly_used>=u.hourly_budget)?null:(0,n.rowToCamel)(u)}])},118739,e=>{"use strict";var t=e.i(899378),r=e.i(529646),a=e.i(689960);let n="id, bytes, created_at, filename, purpose, mime_type, api_key_id, expires_at, deleted_at";function i(e){let a=(0,t.getDbInstance)().prepare(`SELECT ${n} FROM files WHERE id = ? AND deleted_at IS NULL`).get(e);return a?(0,r.rowToCamel)(a):null}e.s(["countFiles",0,function(e={}){let r=(0,t.getDbInstance)(),{apiKeyId:a,purpose:n}=e,i="SELECT COUNT(*) as c FROM files WHERE deleted_at IS NULL",s=[];a&&(i+=" AND api_key_id = ?",s.push(a)),n&&(i+=" AND purpose = ?",s.push(n));let o=r.prepare(i).get(...s);return o?Number(o.c):0},"createFile",0,function(e){let r=(0,t.getDbInstance)(),n="file-"+(0,a.v4)().replaceAll("-","").substring(0,24),i=Math.floor(Date.now()/1e3),s=e.expiresAt;void 0===s&&"batch"===e.purpose&&(s=i+2592e3);let o={id:n,bytes:e.bytes,createdAt:i,filename:e.filename,purpose:e.purpose,content:e.content??null,mimeType:e.mimeType??null,apiKeyId:e.apiKeyId??null,expiresAt:s??null,deletedAt:null};return r.prepare(`
    INSERT INTO files (id, bytes, created_at, filename, purpose, content, mime_type, api_key_id, expires_at, deleted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(o.id,o.bytes,o.createdAt,o.filename,o.purpose,o.content,o.mimeType,o.apiKeyId,o.expiresAt,o.deletedAt),o},"deleteFile",0,function(e){return(0,t.getDbInstance)().prepare("UPDATE files SET deleted_at = ?, content = NULL WHERE id = ?").run(Math.floor(Date.now()/1e3),e).changes>0},"formatFileResponse",0,function(e){let t="number"==typeof e.createdAt&&Number.isFinite(e.createdAt)?e.createdAt:0,r="number"==typeof e.expiresAt&&Number.isFinite(e.expiresAt)?e.expiresAt:null;return{id:e.id,bytes:e.bytes,created_at:t,filename:e.filename,object:"file",purpose:e.purpose,expires_at:r}},"getFile",0,i,"getFileContent",0,function(e){let r=(0,t.getDbInstance)().prepare("SELECT content FROM files WHERE id = ? AND deleted_at IS NULL").get(e);return r?.content?Buffer.isBuffer(r.content)?r.content:Buffer.from(r.content):null},"listFiles",0,function(e={}){let a=(0,t.getDbInstance)(),{apiKeyId:s,purpose:o,limit:u=20,after:l,order:d="desc"}=e,c=`SELECT ${n} FROM files WHERE deleted_at IS NULL`,p=[];if(s&&(c+=" AND api_key_id = ?",p.push(s)),o&&(c+=" AND purpose = ?",p.push(o)),l){let e=i(l);e&&("desc"===d?c+=" AND (created_at < ? OR (created_at = ? AND id < ?))":c+=" AND (created_at > ? OR (created_at = ? AND id > ?))",p.push(e.createdAt,e.createdAt,l))}return c+=` ORDER BY created_at ${"asc"===d?"ASC":"DESC"}, id ${"asc"===d?"ASC":"DESC"} LIMIT ?`,p.push(u),a.prepare(c).all(...p).map(e=>(0,r.rowToCamel)(e))}],118739)},226420,e=>{"use strict";var t=e.i(899378),r=e.i(529646),a=e.i(118739),n=e.i(689960);function i(e){let t=(0,r.rowToCamel)(e);if(t.metadata&&"string"==typeof t.metadata)try{t.metadata=JSON.parse(t.metadata)}catch{t.metadata=null}if(t.errors&&"string"==typeof t.errors)try{t.errors=JSON.parse(t.errors)}catch{t.errors=null}if(t.usage&&"string"==typeof t.usage)try{t.usage=JSON.parse(t.usage)}catch{t.usage=null}let a=e=>{if("number"==typeof e&&Number.isFinite(e))return e;if(null==e)return null;let t=Number(e);return Number.isFinite(t)?t:null};return t.createdAt=a(t.createdAt)??0,t.inProgressAt=a(t.inProgressAt),t.expiresAt=a(t.expiresAt),t.finalizingAt=a(t.finalizingAt),t.completedAt=a(t.completedAt),t.failedAt=a(t.failedAt),t.expiredAt=a(t.expiredAt),t.cancellingAt=a(t.cancellingAt),t.cancelledAt=a(t.cancelledAt),t}function s(e){if(null==e)return null;if("string"!=typeof e)return e;try{return JSON.parse(e)}catch{return null}}function o(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM batches WHERE id = ?").get(e);return r?i(r):null}e.s(["countBatchItemCheckpoints",0,function(e){let r=(0,t.getDbInstance)().prepare("SELECT COUNT(*) AS c FROM batch_item_checkpoints WHERE batch_id = ?").get(e);return r?Number(r.c):0},"countBatches",0,function(e){let r=(0,t.getDbInstance)();if(e){let t=r.prepare("SELECT COUNT(*) as c FROM batches WHERE api_key_id = ?").get(e);return t?Number(t.c):0}{let e=r.prepare("SELECT COUNT(*) as c FROM batches").get();return e?Number(e.c):0}},"createBatch",0,function(e){let a=(0,t.getDbInstance)(),i="batch_"+(0,n.v4)().replaceAll("-","").substring(0,24),s=Math.floor(Date.now()/1e3),o={...e,id:i,createdAt:s,status:e.status||"validating",requestCountsTotal:0,requestCountsCompleted:0,requestCountsFailed:0,errors:e.errors||null,model:e.model||null,usage:e.usage||null,outputExpiresAfterSeconds:e.outputExpiresAfterSeconds||null,outputExpiresAfterAnchor:e.outputExpiresAfterAnchor||null},u=(0,r.objToSnake)({...o,metadata:o.metadata?JSON.stringify(o.metadata):null,errors:o.errors?JSON.stringify(o.errors):null,usage:o.usage?JSON.stringify(o.usage):null}),l=Object.keys(u),d=Object.values(u),c=l.map(()=>"?").join(", ");return a.prepare(`INSERT INTO batches (${l.join(", ")}) VALUES (${c})`).run(...d),o},"deleteBatch",0,function(e){let r=(0,t.getDbInstance)(),n=o(e);if(!n)return!1;if(r.prepare("DELETE FROM batch_item_checkpoints WHERE batch_id = ?").run(e),n.inputFileId)try{(0,a.deleteFile)(n.inputFileId)}catch{}if(n.outputFileId)try{(0,a.deleteFile)(n.outputFileId)}catch{}if(n.errorFileId)try{(0,a.deleteFile)(n.errorFileId)}catch{}return r.prepare("DELETE FROM batches WHERE id = ?").run(e).changes>0},"deleteCompletedBatches",0,function(){let e=(0,t.getDbInstance)(),r=e.prepare("SELECT input_file_id, output_file_id, error_file_id FROM batches WHERE status = 'completed'").all(),n=new Set;for(let e of r)e.input_file_id&&n.add(e.input_file_id),e.output_file_id&&n.add(e.output_file_id),e.error_file_id&&n.add(e.error_file_id);let i=0;for(let e of n)try{(0,a.deleteFile)(e)&&i++}catch{}return e.prepare("DELETE FROM batch_item_checkpoints WHERE batch_id IN (SELECT id FROM batches WHERE status = 'completed')").run(),{deletedBatches:e.prepare("DELETE FROM batches WHERE status = 'completed'").run().changes,deletedFiles:i}},"ensureBatchItemCheckpoints",0,function(e,r){if(0===r.length)return;let a=(0,t.getDbInstance)(),n=Math.floor(Date.now()/1e3),i=a.prepare(`
    INSERT OR IGNORE INTO batch_item_checkpoints (
      batch_id,
      line_number,
      custom_id,
      status,
      result_json,
      error_json,
      created_at,
      updated_at
    )
    VALUES (?, ?, ?, 'pending', NULL, NULL, ?, ?)
  `);a.transaction(()=>{for(let t of r)i.run(e,t.lineNumber,t.customId,n,n)})()},"getBatch",0,o,"getPendingBatches",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM batches WHERE status IN ('validating', 'in_progress', 'finalizing', 'cancelling')").all().map(e=>i(e))},"getTerminalBatches",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM batches WHERE status IN ('completed', 'failed', 'cancelled', 'expired') ORDER BY created_at ASC").all().map(e=>i(e))},"listBatchItemCheckpoints",0,function(e){return(0,t.getDbInstance)().prepare(`
      SELECT batch_id, line_number, custom_id, status, result_json, error_json, created_at, updated_at
      FROM batch_item_checkpoints
      WHERE batch_id = ?
      ORDER BY line_number ASC
    `).all(e).map(e=>({batchId:e.batch_id,lineNumber:Number(e.line_number),customId:e.custom_id??null,status:e.status,result:s(e.result_json),error:s(e.error_json),createdAt:Number(e.created_at),updatedAt:Number(e.updated_at)}))},"listBatches",0,function(e,r=20,a){let n=(0,t.getDbInstance)(),s=a?o(a):null;return(e?s?n.prepare("SELECT * FROM batches WHERE api_key_id = ? AND (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC LIMIT ?").all(e,s.createdAt,s.createdAt,a,r):n.prepare("SELECT * FROM batches WHERE api_key_id = ? ORDER BY created_at DESC, id DESC LIMIT ?").all(e,r):s?n.prepare("SELECT * FROM batches WHERE (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC LIMIT ?").all(s.createdAt,s.createdAt,a,r):n.prepare("SELECT * FROM batches ORDER BY created_at DESC, id DESC LIMIT ?").all(r)).map(e=>i(e))},"markBatchItemError",0,function(e,r,a){let n=(0,t.getDbInstance)(),i=Math.floor(Date.now()/1e3);n.prepare(`
    UPDATE batch_item_checkpoints
    SET custom_id = ?,
        status = 'errored',
        result_json = NULL,
        error_json = ?,
        updated_at = ?
    WHERE batch_id = ? AND line_number = ?
  `).run(r.customId,JSON.stringify(a),i,e,r.lineNumber)},"markBatchItemProcessing",0,function(e,r){let a=(0,t.getDbInstance)(),n=Math.floor(Date.now()/1e3);a.prepare(`
    INSERT INTO batch_item_checkpoints (
      batch_id,
      line_number,
      custom_id,
      status,
      result_json,
      error_json,
      created_at,
      updated_at
    )
    VALUES (?, ?, ?, 'processing', NULL, NULL, ?, ?)
    ON CONFLICT(batch_id, line_number) DO UPDATE SET
      custom_id = excluded.custom_id,
      status = 'processing',
      result_json = NULL,
      error_json = NULL,
      updated_at = excluded.updated_at
  `).run(e,r.lineNumber,r.customId,n,n)},"markBatchItemResult",0,function(e,r,a){let n=(0,t.getDbInstance)(),i=Math.floor(Date.now()/1e3);n.prepare(`
    UPDATE batch_item_checkpoints
    SET custom_id = ?,
        status = 'completed',
        result_json = ?,
        error_json = NULL,
        updated_at = ?
    WHERE batch_id = ? AND line_number = ?
  `).run(r.customId,JSON.stringify(a),i,e,r.lineNumber)},"updateBatch",0,function(e,a){let n=(0,t.getDbInstance)(),i=(0,r.objToSnake)(a);i.metadata&&"string"!=typeof i.metadata&&(i.metadata=JSON.stringify(i.metadata)),i.errors&&"string"!=typeof i.errors&&(i.errors=JSON.stringify(i.errors)),i.usage&&"string"!=typeof i.usage&&(i.usage=JSON.stringify(i.usage));let s=Object.keys(i);if(0===s.length)return!1;let o=s.map(e=>`${e} = ?`).join(", "),u=Object.values(i);return n.prepare(`UPDATE batches SET ${o} WHERE id = ?`).run(...u,e).changes>0}])},783414,e=>{"use strict";var t=e.i(899378);function r(e){let t;if(e.models)try{let r=JSON.parse(e.models);Array.isArray(r)&&(t=r.map(String))}catch{t=void 0}return{id:e.id,providerId:e.provider_id,method:e.method,endpoint:e.endpoint,authType:e.auth_type??"none",models:t,rateLimit:e.rate_limit,feasibility:e.feasibility??0,riskLevel:e.risk_level??"none",status:e.status,notes:e.notes,discoveredAt:e.discovered_at,verifiedAt:e.verified_at}}function a(e){let a=(0,t.getDbInstance)().prepare("SELECT * FROM discovery_results WHERE id = ?").get(e);return a?r(a):null}e.s(["deleteDiscoveryResult",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM discovery_results WHERE id = ?").run(e).changes>0},"getDiscoveryResultById",0,a,"getDiscoveryResults",0,function(e){let a=(0,t.getDbInstance)();return(e?a.prepare("SELECT * FROM discovery_results WHERE provider_id = ? ORDER BY discovered_at DESC, id DESC").all(e):a.prepare("SELECT * FROM discovery_results ORDER BY discovered_at DESC, id DESC").all()).map(r)},"markVerified",0,function(e){return 0===(0,t.getDbInstance)().prepare("UPDATE discovery_results SET status = 'verified', verified_at = datetime('now') WHERE id = ?").run(e).changes?null:a(e)},"upsertDiscoveryResult",0,function(e){let a=(0,t.getDbInstance)(),n=e.models?JSON.stringify(e.models):null;return a.prepare(`INSERT INTO discovery_results
       (provider_id, method, endpoint, auth_type, models, rate_limit, feasibility, risk_level, status, notes)
     VALUES (@provider_id, @method, @endpoint, @auth_type, @models, @rate_limit, @feasibility, @risk_level, @status, @notes)
     ON CONFLICT(provider_id, method, endpoint) DO UPDATE SET
       auth_type = excluded.auth_type,
       models = excluded.models,
       rate_limit = excluded.rate_limit,
       feasibility = excluded.feasibility,
       risk_level = excluded.risk_level,
       status = excluded.status,
       notes = excluded.notes`).run({provider_id:e.providerId,method:e.method,endpoint:e.endpoint??null,auth_type:e.authType,models:n,rate_limit:e.rateLimit??null,feasibility:e.feasibility,risk_level:e.riskLevel,status:e.status,notes:e.notes??null}),r(a.prepare(`SELECT * FROM discovery_results
       WHERE provider_id = ? AND method = ? AND ifnull(endpoint, '') = ifnull(?, '')`).get(e.providerId,e.method,e.endpoint??null))}])},130273,e=>{"use strict";var t=e.i(254799),r=e.i(899378);let a="session_account_affinity",n=null;function i(e){return Number.isFinite(e)&&Number(e)>0?Number(e):0}function s(e,r){let a=(0,t.createHash)("sha256").update(`${r}:${e}`).digest("hex");return`${r}:${a}`}function o(e){return new Date(e).toISOString()}function u(e){if("string"!=typeof e)return null;try{let t=JSON.parse(e);if("string"!=typeof t.connectionId||0===t.connectionId.trim().length||"string"!=typeof t.expiresAt||Number.isNaN(Date.parse(t.expiresAt)))return null;return{connectionId:t.connectionId,createdAt:"string"!=typeof t.createdAt||Number.isNaN(Date.parse(t.createdAt))?t.expiresAt:t.createdAt,lastUsedAt:"string"!=typeof t.lastUsedAt||Number.isNaN(Date.parse(t.lastUsedAt))?t.expiresAt:t.lastUsedAt,expiresAt:t.expiresAt}}catch{return null}}function l(e){(0,r.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(a,e)}function d(e,t,n=0,o=Date.now()){if(!e||!t||0>=i(n))return null;let c=s(e,t),p=(0,r.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(a,c),E=u(p?.value);return E?Date.parse(E.expiresAt)<=o?(l(c),null):E:null}function c(e,t,n,u=Date.now(),l=0){let p=i(l);if(!e||!t||!n||p<=0)return;let E=s(e,t),_=d(e,t,p,u),m=o(u),y={connectionId:n,createdAt:_?.createdAt??m,lastUsedAt:m,expiresAt:o(u+p)};(0,r.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(a,E,JSON.stringify(y))}function p(e=18e5,t=Date.now()){let n=(0,r.getDbInstance)(),i=n.prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(a),s=0;return n.transaction(()=>{for(let e of i){if("string"!=typeof e.key)continue;let r=u(e.value);(!r||Date.parse(r.expiresAt)<=t)&&(n.prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(a,e.key),s++)}})(),s}e.s(["cleanupStaleSessionAccountAffinities",0,p,"deleteSessionAccountAffinity",0,function(e,t){e&&t&&l(s(e,t))},"evictSessionAccountAffinityForConnection",0,function(e,t,n){if(!e||!t||!n)return!1;let i=s(e,t),o=(0,r.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(a,i),d=u(o?.value);return!!d&&d.connectionId===n&&(l(i),!0)},"getSessionAccountAffinity",0,d,"startSessionAccountAffinityCleanup",0,function(){if(!n){try{p()}catch(e){console.warn("[SESSION_AFFINITY] Startup cleanup failed:",e)}"object"==typeof(n=setInterval(()=>{try{p()}catch(e){console.warn("[SESSION_AFFINITY] Periodic cleanup failed:",e)}},3e5))&&"unref"in n&&n.unref?.()}},"stopSessionAccountAffinityCleanupForTests",0,function(){n&&(clearInterval(n),n=null)},"touchSessionAccountAffinity",0,function(e,t,r=Date.now(),a=0){let n=i(a);if(n<=0)return;let s=d(e,t,n,r);s&&c(e,t,s.connectionId,r,n)},"upsertSessionAccountAffinity",0,c])},559339,e=>{"use strict";var t=e.i(689960),r=e.i(899378),a=e.i(529646),n=e.i(935050);function i(e){var t;let r=(t=(0,a.rowToCamel)(e))&&"object"==typeof t&&!Array.isArray(t)?t:{};return"string"!=typeof r.id||"string"!=typeof r.name?null:{id:r.id,name:r.name,tokenHash:"string"==typeof r.tokenHash?r.tokenHash:"",syncApiKeyId:"string"==typeof r.syncApiKeyId?r.syncApiKeyId:null,revokedAt:"string"==typeof r.revokedAt?r.revokedAt:null,lastUsedAt:"string"==typeof r.lastUsedAt?r.lastUsedAt:null,createdAt:"string"==typeof r.createdAt?r.createdAt:new Date().toISOString(),updatedAt:"string"==typeof r.updatedAt?r.updatedAt:new Date().toISOString()}}function s(e){e.exec(`
    CREATE TABLE IF NOT EXISTS sync_tokens (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      token_hash TEXT NOT NULL UNIQUE,
      sync_api_key_id TEXT,
      revoked_at TEXT,
      last_used_at TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_sync_tokens_created_at ON sync_tokens(created_at);
    CREATE INDEX IF NOT EXISTS idx_sync_tokens_last_used_at ON sync_tokens(last_used_at);
    CREATE INDEX IF NOT EXISTS idx_sync_tokens_revoked_at ON sync_tokens(revoked_at);
    CREATE INDEX IF NOT EXISTS idx_sync_tokens_sync_api_key_id ON sync_tokens(sync_api_key_id);
  `)}async function o(){let e=(0,r.getDbInstance)();return s(e),e.prepare("SELECT * FROM sync_tokens ORDER BY datetime(created_at) DESC, name COLLATE NOCASE ASC").all().map(e=>i(e)).filter(e=>null!==e)}async function u(e){let t=(0,r.getDbInstance)();return s(t),i(t.prepare("SELECT * FROM sync_tokens WHERE id = ?").get(e))}async function l(e){let t=(0,r.getDbInstance)();return s(t),i(t.prepare("SELECT * FROM sync_tokens WHERE token_hash = ?").get(e))}async function d(e){let a=(0,r.getDbInstance)();s(a);let i=new Date().toISOString(),o={id:(0,t.v4)(),name:e.name,tokenHash:e.tokenHash,syncApiKeyId:e.syncApiKeyId||null,revokedAt:null,lastUsedAt:null,createdAt:i,updatedAt:i};return a.prepare(`INSERT INTO sync_tokens (
      id, name, token_hash, sync_api_key_id, revoked_at, last_used_at, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(o.id,o.name,o.tokenHash,o.syncApiKeyId,o.revokedAt,o.lastUsedAt,o.createdAt,o.updatedAt),(0,n.backupDbFile)("pre-write"),o}async function c(e){let t=(0,r.getDbInstance)();s(t);let a=await u(e);if(!a)return null;if(a.revokedAt)return a;let i=new Date().toISOString();return t.prepare("UPDATE sync_tokens SET revoked_at = ?, updated_at = ? WHERE id = ?").run(i,i,e),(0,n.backupDbFile)("pre-write"),await u(e)}async function p(e,t=new Date().toISOString()){let a=(0,r.getDbInstance)();return s(a),Number(a.prepare("UPDATE sync_tokens SET last_used_at = ?, updated_at = ? WHERE id = ?").run(t,t,e).changes||0)>0}e.s(["createSyncTokenRecord",0,d,"getSyncTokenByHash",0,l,"getSyncTokenById",0,u,"listSyncTokens",0,o,"revokeSyncToken",0,c,"touchSyncTokenLastUsed",0,p])},870766,e=>{"use strict";var t=e.i(899378);let r="antigravityCreditBalance";function a(e){try{return JSON.parse(e)}catch{return null}}e.s(["getAllPersistedCreditBalances",0,function(){let e=new Map;if(t.isBuildPhase||t.isCloud)return e;for(let n of(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(r)){let t=a(n.value);t&&"number"==typeof t.balance&&e.set(n.key,t.balance)}return e},"getPersistedCreditBalance",0,function(e){if(t.isBuildPhase||t.isCloud)return null;let n=(0,t.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(r,e);if(!n?.value)return null;let i=a(n.value);return i&&"number"==typeof i.balance?i.balance:null},"persistCreditBalance",0,function(e,a){if(t.isBuildPhase||t.isCloud)return;let n=(0,t.getDbInstance)(),i={balance:a,updatedAt:new Date().toISOString()};n.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(r,e,JSON.stringify(i))}])},291823,e=>{"use strict";var t=e.i(254799),r=e.i(899378),a=e.i(935050);function n(e){return e&&"object"==typeof e?e:{}}function i(e){let t=n(e);return{id:"string"==typeof t.id?t.id:"",name:"string"==typeof t.name?t.name:"",type:"string"==typeof t.type?t.type:"http",host:"string"==typeof t.host?t.host:"",port:Number(t.port)||0,region:"string"==typeof t.region?t.region:null,notes:"string"==typeof t.notes?t.notes:null,status:"string"==typeof t.status?t.status:"active",source:"string"==typeof t.source?t.source:"oneproxy",qualityScore:"number"==typeof t.quality_score?t.quality_score:null,latencyMs:"number"==typeof t.latency_ms?t.latency_ms:null,anonymity:"string"==typeof t.anonymity?t.anonymity:null,googleAccess:1===t.google_access||!0===t.google_access,lastValidated:"string"==typeof t.last_validated?t.last_validated:null,countryCode:"string"==typeof t.country_code?t.country_code:null,createdAt:"string"==typeof t.created_at?t.created_at:"",updatedAt:"string"==typeof t.updated_at?t.updated_at:""}}async function s(e){let t=(0,r.getDbInstance)(),a="SELECT * FROM proxy_registry WHERE source = 'oneproxy' AND status = 'active'",n=[];return e?.protocol&&(a+=" AND type = ?",n.push(e.protocol)),e?.countryCode&&(a+=" AND country_code = ?",n.push(e.countryCode)),e?.minQuality!=null&&(a+=" AND quality_score >= ?",n.push(e.minQuality)),a+=" ORDER BY quality_score DESC, last_validated DESC",e?.limit&&(a+=" LIMIT ?",n.push(e.limit)),t.prepare(a).all(...n).map(i)}async function o(){let e,t=(0,r.getDbInstance)(),a={total:Number((e=n(t.prepare(`SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
        AVG(quality_score) as avg_quality,
        MAX(last_validated) as last_validated
       FROM proxy_registry WHERE source = 'oneproxy'`).get())).total)||0,active:Number(e.active)||0,avgQuality:null!==e.avg_quality&&void 0!==e.avg_quality?Math.round(100*Number(e.avg_quality))/100:null,lastValidated:"string"==typeof e.last_validated?e.last_validated:null},i=t.prepare("SELECT type as protocol, COUNT(*) as count FROM proxy_registry WHERE source = 'oneproxy' GROUP BY type ORDER BY count DESC").all(),s=t.prepare("SELECT country_code as countryCode, COUNT(*) as count FROM proxy_registry WHERE source = 'oneproxy' AND country_code IS NOT NULL GROUP BY country_code ORDER BY count DESC LIMIT 20").all();return{...a,byProtocol:i.map(e=>({protocol:String(e.protocol||"unknown"),count:Number(e.count)||0})),byCountry:s.map(e=>({countryCode:String(e.countryCode||"unknown"),count:Number(e.count)||0}))}}async function u(e){let n=(0,r.getDbInstance)(),i=new Date().toISOString(),s=`${e.protocol?.toUpperCase()||"HTTP"} - ${e.countryCode||"Unknown"} - ${e.ip}`,o=n.prepare("SELECT id FROM proxy_registry WHERE host = ? AND port = ? AND source = 'oneproxy'").get(e.ip,e.port);if(o?.id)return n.prepare(`UPDATE proxy_registry
       SET status = ?, quality_score = ?, latency_ms = ?, anonymity = ?,
           google_access = ?, last_validated = ?, country_code = ?, updated_at = ?
       WHERE id = ?`).run("active",e.qualityScore??null,e.latencyMs??null,e.anonymity??null,+!!e.googleAccess,e.lastValidated??i,e.countryCode??null,i,o.id),(0,a.backupDbFile)("pre-write"),{proxy:await l(o.id),action:"updated"};let u=(0,t.randomUUID)();return n.prepare(`INSERT INTO proxy_registry
     (id, name, type, host, port, region, notes, status, source,
      quality_score, latency_ms, anonymity, google_access, last_validated, country_code,
      created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(u,s,e.protocol||"http",e.ip,e.port,e.countryCode??null,null,"active","oneproxy",e.qualityScore??null,e.latencyMs??null,e.anonymity??null,+!!e.googleAccess,e.lastValidated??i,e.countryCode??null,i,i),(0,a.backupDbFile)("pre-write"),{proxy:await l(u),action:"created"}}async function l(e){let t=(0,r.getDbInstance)().prepare("SELECT * FROM proxy_registry WHERE id = ? AND source = 'oneproxy'").get(e);return t?i(t):null}async function d(e){let t=(0,r.getDbInstance)().prepare("DELETE FROM proxy_registry WHERE id = ? AND source = 'oneproxy'").run(e);return(0,a.backupDbFile)("pre-write"),t.changes>0}async function c(){let e=(0,r.getDbInstance)().prepare("DELETE FROM proxy_registry WHERE source = 'oneproxy'").run();return(0,a.backupDbFile)("pre-write"),e.changes}async function p(e){let t=(0,r.getDbInstance)(),a=e?.strategy||"quality",n="SELECT * FROM proxy_registry WHERE source = 'oneproxy' AND status = 'active'";switch(a){case"quality":n+=" ORDER BY quality_score DESC, latency_ms ASC LIMIT 1";break;case"random":n+=" ORDER BY RANDOM() LIMIT 1";break;case"sequential":n+=" ORDER BY last_validated ASC LIMIT 1"}let s=t.prepare(n).get();return s?i(s):null}async function E(e,t){let n=(0,r.getDbInstance)().prepare(`UPDATE proxy_registry
       SET quality_score = MAX(0, COALESCE(quality_score, 50) - 10),
           status = CASE WHEN COALESCE(quality_score, 50) <= 10 THEN 'inactive' ELSE status END,
           updated_at = datetime('now')
       WHERE host = ? AND port = ? AND source = 'oneproxy'`).run(e,t);return(0,a.backupDbFile)("pre-write"),n.changes>0}e.s(["clearAllOneproxyProxies",0,c,"deleteOneproxyProxy",0,d,"getOneproxyProxyById",0,l,"getOneproxyProxyForRotation",0,p,"getOneproxyStats",0,o,"listOneproxyProxies",0,s,"markOneproxyProxyFailed",0,E,"upsertOneproxyProxy",0,u])},992088,e=>{"use strict";var t=e.i(899378);function r(e){return{name:e.name,description:e.description,priority:e.priority,scope:"combo"===e.scope_type&&e.combo_id?{type:"combo",comboId:e.combo_id}:{type:"global"},enabled:1===e.enabled,code:e.code,createdAt:e.created_at,updatedAt:e.updated_at,runCount:e.run_count,lastError:e.last_error||void 0}}function a(e){return{name:e.name,description:e.description,priority:e.priority,scope_type:e.scope.type,combo_id:"combo"===e.scope.type?e.scope.comboId:null,enabled:+!!e.enabled,code:e.code,created_at:e.createdAt||new Date().toISOString(),updated_at:new Date().toISOString(),run_count:e.runCount||0,last_error:e.lastError}}function n(e){let a=(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE name = ?").get(e);return a?r(a):void 0}e.s(["cleanupHookLogs",0,function(e=1e4){return(0,t.getDbInstance)().prepare(`
    DELETE FROM middleware_logs WHERE id NOT IN (
      SELECT id FROM middleware_logs ORDER BY timestamp DESC LIMIT ?
    )
  `).run(e).changes},"createMiddlewareHook",0,function(e){let r=(0,t.getDbInstance)(),i=a(e);return i.created_at=new Date().toISOString(),i.updated_at=i.created_at,r.prepare(`
    INSERT INTO middleware_hooks (name, description, priority, scope_type, combo_id, enabled, code, created_at, updated_at, run_count, last_error)
    VALUES (@name, @description, @priority, @scope_type, @combo_id, @enabled, @code, @created_at, @updated_at, @run_count, @last_error)
  `).run(i),n(e.name)},"deleteMiddlewareHook",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM middleware_hooks WHERE name = ?").run(e).changes>0},"getAllMiddlewareHooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks ORDER BY priority ASC, name ASC").all().map(r)},"getComboMiddlewareHooks",0,function(e){return(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE enabled = 1 AND (scope_type = 'global' OR (scope_type = 'combo' AND combo_id = ?)) ORDER BY priority ASC").all(e).map(r)},"getEnabledMiddlewareHooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE enabled = 1 ORDER BY priority ASC").all().map(r)},"getHookLogs",0,function(e,r=50){let a=(0,t.getDbInstance)();return(e?a.prepare("SELECT * FROM middleware_logs WHERE hook_name = ? ORDER BY timestamp DESC LIMIT ?").all(e,r):a.prepare("SELECT * FROM middleware_logs ORDER BY timestamp DESC LIMIT ?").all(r)).map(e=>({id:e.id,hookName:e.hook_name,requestId:e.request_id,durationMs:e.duration_ms,mutated:1===e.mutated,skipped:1===e.skipped,error:e.error,timestamp:e.timestamp}))},"getMiddlewareHook",0,n,"insertHookLog",0,function(e){(0,t.getDbInstance)().prepare(`
    INSERT INTO middleware_logs (id, hook_name, request_id, duration_ms, mutated, skipped, error, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(e.id,e.hookName,e.requestId,e.durationMs,+!!e.mutated,+!!e.skipped,e.error||null,e.timestamp)},"recordHookExecution",0,function(e,r){let a=(0,t.getDbInstance)();r?a.prepare("UPDATE middleware_hooks SET run_count = run_count + 1, last_error = ?, updated_at = datetime('now') WHERE name = ?").run(r,e):a.prepare("UPDATE middleware_hooks SET run_count = run_count + 1, last_error = NULL, updated_at = datetime('now') WHERE name = ?").run(e)},"updateMiddlewareHook",0,function(e,r){let i=n(e);if(!i)return;let s=a({...i,...r,updatedAt:new Date().toISOString()});return(0,t.getDbInstance)().prepare(`
    UPDATE middleware_hooks SET
      description = @description,
      priority = @priority,
      scope_type = @scope_type,
      combo_id = @combo_id,
      enabled = @enabled,
      code = @code,
      updated_at = @updated_at,
      run_count = @run_count,
      last_error = @last_error
    WHERE name = @name
  `).run(s),n(e)}])},13123,e=>{"use strict";var t=e.i(899378),r=e.i(666680);function a(e){let t={};try{let r=JSON.parse(e.params_json);null===r||"object"!=typeof r||Array.isArray(r)||(t=r)}catch{t={}}return{id:e.id,name:e.name,endpoint:e.endpoint,model:e.model,system:e.system,params:t,created_at:e.created_at}}function n(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM playground_presets WHERE id = ? LIMIT 1").get(e);return r?a(r):null}e.s(["createPlaygroundPreset",0,function(e){let a=(0,t.getDbInstance)(),i=(0,r.randomUUID)(),s=JSON.stringify(e.params??{}),o=e.system??null;return a.prepare("INSERT INTO playground_presets (id, name, endpoint, model, system, params_json) VALUES (?, ?, ?, ?, ?, ?)").run(i,e.name,e.endpoint,e.model,o,s),n(i)},"deletePlaygroundPreset",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM playground_presets WHERE id = ?").run(e).changes>0},"getPlaygroundPreset",0,n,"listPlaygroundPresets",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM playground_presets ORDER BY created_at DESC").all().map(a)},"updatePlaygroundPreset",0,function(e,r){let a=(0,t.getDbInstance)(),i=n(e);if(!i)return null;let s=[],o=[];return(void 0!==r.name&&(s.push("name = ?"),o.push(r.name)),void 0!==r.endpoint&&(s.push("endpoint = ?"),o.push(r.endpoint)),void 0!==r.model&&(s.push("model = ?"),o.push(r.model)),"system"in r&&(s.push("system = ?"),o.push(r.system??null)),void 0!==r.params&&(s.push("params_json = ?"),o.push(JSON.stringify(r.params))),0===s.length)?i:(o.push(e),a.prepare(`UPDATE playground_presets SET ${s.join(", ")} WHERE id = ?`).run(...o),n(e))}])},524630,e=>{"use strict";var t=e.i(899378);function r(){let e=(0,t.getDbInstance)().prepare("SELECT active_dim, embedding_signature, last_reset_at, vec_loaded FROM memory_vec_meta WHERE id = 1").get();return e?{activeDim:e.active_dim,embeddingSignature:e.embedding_signature,lastResetAt:e.last_reset_at,vecLoaded:1===e.vec_loaded}:{activeDim:null,embeddingSignature:null,lastResetAt:null,vecLoaded:!1}}e.s(["countMemoryReindexPending",0,function(){return(0,t.getDbInstance)().prepare("SELECT COUNT(*) AS cnt FROM memories WHERE needs_reindex = 1").get().cnt},"getMemoryReindexQueue",0,function(e){return(0,t.getDbInstance)().prepare(`SELECT id, content, COALESCE(key, '') AS key
       FROM memories
       WHERE needs_reindex = 1
       ORDER BY created_at ASC
       LIMIT ?`).all(e)},"getMemoryVecMeta",0,r,"markAllMemoriesNeedReindex",0,function(){return(0,t.getDbInstance)().prepare("UPDATE memories SET needs_reindex = 1").run().changes},"markMemoryNeedsReindex",0,function(e,r){(0,t.getDbInstance)().prepare("UPDATE memories SET needs_reindex = ? WHERE id = ?").run(+!!r,e)},"setMemoryVecMeta",0,function(e){let a=(0,t.getDbInstance)(),n=r(),i="activeDim"in e?e.activeDim??null:n.activeDim,s="embeddingSignature"in e?e.embeddingSignature??null:n.embeddingSignature,o="lastResetAt"in e?e.lastResetAt??null:n.lastResetAt,u="vecLoaded"in e?+!!e.vecLoaded:+!!n.vecLoaded;a.prepare(`INSERT OR REPLACE INTO memory_vec_meta
       (id, active_dim, embedding_signature, last_reset_at, vec_loaded)
     VALUES (1, ?, ?, ?, ?)`).run(i,s,o,u)}])},365164,e=>{"use strict";var t=e.i(899378);function r(e){return{poolId:e.pool_id,apiKeyId:e.api_key_id,model:e.model,capValue:e.cap_value,capUnit:e.cap_unit}}function a(){return(0,t.getDbInstance)()}e.s(["deleteModelCap",0,function(e,t,r){a().prepare(`DELETE FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ? AND model = ?`).run(e,t,r)},"getModelCap",0,function(e,t,n){let i=a().prepare(`SELECT pool_id, api_key_id, model, cap_value, cap_unit
       FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ? AND model = ?`).get(e,t,n);return i?r(i):null},"listModelCaps",0,function(e,t){return a().prepare(`SELECT pool_id, api_key_id, model, cap_value, cap_unit
       FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ?`).all(e,t).map(r)},"setModelCap",0,function(e){a().prepare(`INSERT INTO quota_allocation_model_caps
         (pool_id, api_key_id, model, cap_value, cap_unit)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(pool_id, api_key_id, model) DO UPDATE SET
         cap_value = excluded.cap_value,
         cap_unit  = excluded.cap_unit`).run(e.poolId,e.apiKeyId,e.model,e.capValue,e.capUnit)}])},489259,e=>{"use strict";var t=e.i(899378);function r(){return(0,t.getDbInstance)()}e.s(["gcOlderThan",0,function(e){return r().prepare("DELETE FROM quota_consumption WHERE updated_at < ?").run(e).changes},"getBucket",0,function(e,t,a){let n=r().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(e,t,a);return n?.consumed??0},"getPair",0,function(e,t,a){let n=r().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(e,t,a),i=r().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(e,t,a-1);return{curr:n?.consumed??0,prev:i?.consumed??0}},"incrementBucket",0,function(e,t,a,n,i){r().prepare(`INSERT INTO quota_consumption (api_key_id, dimension_key, bucket_index, consumed, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(api_key_id, dimension_key, bucket_index)
       DO UPDATE SET
         consumed = consumed + excluded.consumed,
         updated_at = excluded.updated_at`).run(e,t,a,n,i)},"listConsumptionForPool",0,function(e,t){let a=Math.max(1,Math.min(t,500)),n=e.replace(/[%_\\]/g,"\\$&")+":%";return r().prepare(`SELECT api_key_id, dimension_key, bucket_index, consumed, updated_at
       FROM quota_consumption
       WHERE dimension_key LIKE ? ESCAPE '\\'
       ORDER BY updated_at DESC
       LIMIT ?`).all(n,a).map(e=>{let t=e.dimension_key.split(":"),r=t[1]??"",a=t.slice(2).join(":")??"";return{apiKeyId:e.api_key_id,dimensionKey:e.dimension_key,unit:r,window:a,bucketIndex:e.bucket_index,consumed:e.consumed,updatedAt:e.updated_at}})},"sumPoolDimension",0,function(e,t){let a=r().prepare(`SELECT COALESCE(SUM(consumed), 0) AS total
       FROM quota_consumption
       WHERE dimension_key = ? AND bucket_index = ?`).get(e,t),n=r().prepare(`SELECT COALESCE(SUM(consumed), 0) AS total
       FROM quota_consumption
       WHERE dimension_key = ? AND bucket_index = ?`).get(e,t-1);return{currTotal:a?.total??0,prevTotal:n?.total??0}}])},409500,e=>{"use strict";var t=e.i(899378);function r(){return(0,t.getDbInstance)()}function a(e){let t=[];try{t=JSON.parse(e.dimensions_json)}catch{t=[]}return{connectionId:e.connection_id,provider:e.provider,dimensions:t,source:e.source}}e.s(["deletePlan",0,function(e){return r().prepare("DELETE FROM provider_plans WHERE connection_id = ?").run(e).changes>0},"getPlan",0,function(e){let t=r().prepare(`SELECT connection_id, provider, dimensions_json, source, updated_at
       FROM provider_plans WHERE connection_id = ?`).get(e);return t?a(t):null},"listPlans",0,function(){return r().prepare(`SELECT connection_id, provider, dimensions_json, source, updated_at
       FROM provider_plans ORDER BY provider ASC`).all().map(a)},"upsertPlan",0,function(e,t,a,n){let i=new Date().toISOString(),s=JSON.stringify(a);r().prepare(`INSERT INTO provider_plans (connection_id, provider, dimensions_json, source, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(connection_id)
       DO UPDATE SET
         provider = excluded.provider,
         dimensions_json = excluded.dimensions_json,
         source = excluded.source,
         updated_at = excluded.updated_at`).run(e,t,s,n,i)}])},95825,e=>{"use strict";var t=e.i(254799),r=e.i(899378),a=e.i(362225);let n=!1;function i(e){return e&&"object"==typeof e&&!Array.isArray(e)?e:{}}function s(e,t=0){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let r=Number(e);return Number.isFinite(r)?r:t}return t}function o(e){return"model"===e||"provider"===e||"global"===e?e:"global"}function u(e){return"daily"===e||"weekly"===e||"monthly"===e?e:"monthly"}function l(){n||((0,r.getDbInstance)().exec(`
    CREATE TABLE IF NOT EXISTS api_key_token_limits (
      id              TEXT PRIMARY KEY,
      api_key_id      TEXT NOT NULL,
      scope_type      TEXT NOT NULL CHECK (scope_type IN ('model', 'provider', 'global')),
      scope_value     TEXT NOT NULL DEFAULT '',
      token_limit     INTEGER NOT NULL CHECK (token_limit > 0),
      reset_interval  TEXT NOT NULL DEFAULT 'monthly' CHECK (reset_interval IN ('daily', 'weekly', 'monthly')),
      reset_time      TEXT,
      enabled         INTEGER NOT NULL DEFAULT 1,
      created_at      TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
      UNIQUE (api_key_id, scope_type, scope_value)
    );
    CREATE INDEX IF NOT EXISTS idx_aktl_api_key_id ON api_key_token_limits (api_key_id);
    CREATE TABLE IF NOT EXISTS api_key_token_counters (
      limit_id      TEXT NOT NULL,
      window_start  TEXT NOT NULL,
      tokens_used   INTEGER NOT NULL DEFAULT 0,
      updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
      PRIMARY KEY (limit_id, window_start),
      FOREIGN KEY (limit_id) REFERENCES api_key_token_limits (id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS api_key_token_limit_reset_logs (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      limit_id      TEXT NOT NULL,
      reset_at      TEXT NOT NULL DEFAULT (datetime('now')),
      prev_tokens   INTEGER NOT NULL DEFAULT 0,
      window_start  TEXT NOT NULL,
      FOREIGN KEY (limit_id) REFERENCES api_key_token_limits (id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_aktlrl_limit_id ON api_key_token_limit_reset_logs (limit_id);
  `),n=!0)}function d(e){let t=i(e);return{id:"string"==typeof t.id?t.id:"",apiKeyId:"string"==typeof t.api_key_id?t.api_key_id:"",scopeType:o(t.scope_type),scopeValue:"string"==typeof t.scope_value?t.scope_value:"",tokenLimit:s(t.token_limit),resetInterval:u(t.reset_interval),resetTime:"string"==typeof t.reset_time&&t.reset_time?t.reset_time:"00:00",enabled:0!==s(t.enabled,1),createdAt:"string"==typeof t.created_at?t.created_at:"",updatedAt:"string"==typeof t.updated_at?t.updated_at:""}}function c(e,t=Date.now()){let r=(0,a.getBudgetWindow)(e.resetInterval,e.resetTime,t);return{windowStart:String(r.periodStartAt),didReset:!1,periodStartAt:r.periodStartAt,nextResetAt:r.nextResetAt}}e.s(["deleteTokenLimit",0,function(e){l();let t=(0,r.getDbInstance)();return t.prepare("DELETE FROM api_key_token_counters WHERE limit_id = ?").run(e),t.prepare("DELETE FROM api_key_token_limit_reset_logs WHERE limit_id = ?").run(e),t.prepare("DELETE FROM api_key_token_limits WHERE id = ?").run(e).changes>0},"getTokenLimitsForRequest",0,function(e,t,a){return l(),(0,r.getDbInstance)().prepare(`SELECT * FROM api_key_token_limits
       WHERE api_key_id = @apiKeyId
         AND enabled = 1
         AND (
           (scope_type = 'global')
           OR (scope_type = 'model' AND scope_value = @model)
           OR (scope_type = 'provider' AND scope_value = @provider)
         )`).all({apiKeyId:e,model:a||"",provider:t||""}).map(d)},"getWindowUsage",0,function(e,t=Date.now()){l();let a=(0,r.getDbInstance)(),{windowStart:n}=c(e,t);return s(i(a.prepare("SELECT tokens_used FROM api_key_token_counters WHERE limit_id = ? AND window_start = ?").get(e.id,n)).tokens_used)},"incrementWindowTokens",0,function(e,t,a){l();let n=(0,r.getDbInstance)(),o=Math.max(0,Math.floor(s(a)));return s(i(n.prepare(`INSERT INTO api_key_token_counters (limit_id, window_start, tokens_used, updated_at)
       VALUES (@limitId, @windowStart, @tokens, datetime('now'))
       ON CONFLICT(limit_id, window_start)
       DO UPDATE SET tokens_used = tokens_used + excluded.tokens_used,
                     updated_at  = datetime('now')
       RETURNING tokens_used`).get({limitId:e,windowStart:t,tokens:o})).tokens_used)},"listTokenLimits",0,function(e){return l(),(0,r.getDbInstance)().prepare(`SELECT * FROM api_key_token_limits
       WHERE api_key_id = ?
       ORDER BY CASE scope_type WHEN 'model' THEN 0 WHEN 'provider' THEN 1 ELSE 2 END, scope_value`).all(e).map(d)},"logTokenLimitReset",0,function(e,t,a){l(),(0,r.getDbInstance)().prepare(`INSERT INTO api_key_token_limit_reset_logs (limit_id, reset_at, prev_tokens, window_start)
     VALUES (?, datetime('now'), ?, ?)`).run(e,Math.max(0,Math.floor(s(t))),a)},"resetWindowIfElapsed",0,c,"upsertTokenLimit",0,function(e){l();let a=(0,r.getDbInstance)(),n=o(e.scopeType),i="global"===n?"":(e.scopeValue??"").trim(),c=u(e.resetInterval),p="string"==typeof e.resetTime&&e.resetTime?e.resetTime:"00:00",E=+(!1!==e.enabled),_=Math.floor(s(e.tokenLimit)),m=e.id&&e.id.trim()?e.id.trim():(0,t.randomUUID)();return a.prepare(`INSERT INTO api_key_token_limits
       (id, api_key_id, scope_type, scope_value, token_limit, reset_interval, reset_time, enabled, created_at, updated_at)
     VALUES (@id, @apiKeyId, @scopeType, @scopeValue, @tokenLimit, @resetInterval, @resetTime, @enabled, datetime('now'), datetime('now'))
     ON CONFLICT(api_key_id, scope_type, scope_value)
     DO UPDATE SET token_limit    = excluded.token_limit,
                   reset_interval = excluded.reset_interval,
                   reset_time     = excluded.reset_time,
                   enabled        = excluded.enabled,
                   updated_at     = datetime('now')`).run({id:m,apiKeyId:e.apiKeyId,scopeType:n,scopeValue:i,tokenLimit:_,resetInterval:c,resetTime:p,enabled:E}),d(a.prepare("SELECT * FROM api_key_token_limits WHERE api_key_id = ? AND scope_type = ? AND scope_value = ?").get(e.apiKeyId,n,i))}])},224136,e=>{"use strict";var t=e.i(899378);function r(e){return{apiKeyId:e.api_key_id,sourceType:e.source_type,token:e.token,baseUrl:e.base_url,vaultPath:e.vault_path,enabled:1===e.enabled}}e.s(["deleteApiKeyContextSource",0,function(e,r){(0,t.getDbInstance)().prepare("DELETE FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ?").run(e,r)},"getApiKeyContextSource",0,function(e,a){if(!e)return null;let n=(0,t.getDbInstance)().prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ? AND enabled = 1").get(e,a);return n?r(n):null},"listApiKeyContextSources",0,function(e){return(0,t.getDbInstance)().prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ?").all(e).map(r)},"setApiKeyContextSource",0,function(e,r,a){let n=(0,t.getDbInstance)(),i=n.prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ?").get(e,r),s=new Date().toISOString();i?n.prepare(`UPDATE api_key_context_sources SET
        token = COALESCE(?, token),
        base_url = COALESCE(?, base_url),
        vault_path = COALESCE(?, vault_path),
        enabled = COALESCE(?, enabled),
        updated_at = ?
      WHERE api_key_id = ? AND source_type = ?`).run(a.token??null,a.baseUrl??null,a.vaultPath??null,void 0!==a.enabled?+!!a.enabled:null,s,e,r):n.prepare(`INSERT INTO api_key_context_sources
        (api_key_id, source_type, token, base_url, vault_path, enabled, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(e,r,a.token??null,a.baseUrl??null,a.vaultPath??null,void 0!==a.enabled?+!!a.enabled:1,s,s)}])},126603,e=>{"use strict";var t=e.i(899378);e.s(["getAccountCostRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        COALESCE(NULLIF(c.display_name, ''), NULLIF(c.email, ''), NULLIF(c.name, ''), usage_history.connection_id, 'unknown') as account,
        LOWER(usage_history.provider) as provider,
        LOWER(usage_history.model) as model,
        COALESCE(NULLIF(usage_history.service_tier, ''), 'standard') as serviceTier,
        COALESCE(SUM(usage_history.tokens_input), 0) as promptTokens,
        COALESCE(SUM(usage_history.tokens_output), 0) as completionTokens,
        COALESCE(SUM(usage_history.tokens_cache_read), 0) as cacheReadTokens,
        COALESCE(SUM(usage_history.tokens_cache_creation), 0) as cacheCreationTokens,
        COALESCE(SUM(usage_history.tokens_reasoning), 0) as reasoningTokens
      FROM usage_history
      LEFT JOIN provider_connections c ON c.id = usage_history.connection_id
      ${e}
      GROUP BY account, LOWER(usage_history.provider), LOWER(usage_history.model), serviceTier
    `).all(r)},"getAccountUsageRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        COALESCE(NULLIF(c.display_name, ''), NULLIF(c.email, ''), NULLIF(c.name, ''), usage_history.connection_id, 'unknown') as account,
        COUNT(usage_history.id) as requests,
        COALESCE(SUM(usage_history.tokens_input), 0) as promptTokens,
        COALESCE(SUM(usage_history.tokens_output), 0) as completionTokens,
        COALESCE(SUM(usage_history.tokens_input + usage_history.tokens_output), 0) as totalTokens,
        COALESCE(AVG(usage_history.latency_ms), 0) as avgLatencyMs,
        COALESCE(MAX(usage_history.timestamp), '') as lastUsed
      FROM usage_history
      LEFT JOIN provider_connections c ON c.id = usage_history.connection_id
      ${e}
      GROUP BY account
      ORDER BY requests DESC
      LIMIT 50
    `).all(r)},"getAllDomainBudgets",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM domain_budgets").all()},"getAllDomainCostHistory",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM domain_cost_history").all()},"getAllUsageHistory",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM usage_history").all()},"getApiKeyMetadataRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        NULLIF(api_key_id, '') as apiKeyId,
        NULLIF(api_key_name, '') as apiKeyName,
        COALESCE(NULLIF(api_key_id, ''), NULLIF(api_key_name, ''), 'unknown') as apiKeyGroupKey,
        MAX(timestamp) as lastUsed
      FROM usage_history
      ${e}
      GROUP BY NULLIF(api_key_id, ''), NULLIF(api_key_name, '')
      ORDER BY lastUsed DESC
    `).all(r)},"getApiKeyUsageRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        NULLIF(api_key_id, '') as apiKeyId,
        COALESCE(NULLIF(api_key_id, ''), NULLIF(api_key_name, ''), 'unknown') as apiKeyGroupKey,
        LOWER(provider) as provider,
        LOWER(model) as model,
        COALESCE(NULLIF(service_tier, ''), 'standard') as serviceTier,
        COUNT(*) as requests,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_cache_read), 0) as cacheReadTokens,
        COALESCE(SUM(tokens_cache_creation), 0) as cacheCreationTokens,
        COALESCE(SUM(tokens_reasoning), 0) as reasoningTokens,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens
      FROM usage_history
      ${e}
      GROUP BY COALESCE(NULLIF(api_key_id, ''), NULLIF(api_key_name, ''), 'unknown'), NULLIF(api_key_id, ''), LOWER(provider), LOWER(model), serviceTier
    `).all(r)},"getDailyCostRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        DATE(timestamp) as date,
        LOWER(provider) as provider,
        LOWER(model) as model,
        COALESCE(NULLIF(service_tier, ''), 'standard') as serviceTier,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_cache_read), 0) as cacheReadTokens,
        COALESCE(SUM(tokens_cache_creation), 0) as cacheCreationTokens,
        COALESCE(SUM(tokens_reasoning), 0) as reasoningTokens
      FROM ${e} AS _u
      GROUP BY DATE(timestamp), LOWER(provider), LOWER(model), serviceTier
      ORDER BY date ASC
    `).all(r)},"getDailyUsage",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        DATE(timestamp) as date,
        COUNT(*) as requests,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens
      FROM ${e} AS _u
      GROUP BY DATE(timestamp)
      ORDER BY date ASC
    `).all(r)},"getHeatmapRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        DATE(timestamp) as date,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens
      FROM usage_history
      WHERE ${e.join(" AND ")}
      GROUP BY DATE(timestamp)
      ORDER BY date ASC
    `).all(r)},"getModelUsageRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        LOWER(model) as model,
        LOWER(provider) as provider,
        COALESCE(NULLIF(service_tier, ''), 'standard') as serviceTier,
        COUNT(*) as requests,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_cache_read), 0) as cacheReadTokens,
        COALESCE(SUM(tokens_cache_creation), 0) as cacheCreationTokens,
        COALESCE(SUM(tokens_reasoning), 0) as reasoningTokens,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens,
        COALESCE(AVG(latency_ms), 0) as avgLatencyMs,
        COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as successfulRequests,
        COALESCE(MAX(timestamp), '') as lastUsed
      FROM ${e} AS _u
      GROUP BY LOWER(model), LOWER(provider), serviceTier
      ORDER BY requests DESC
    `).all(r)},"getPresetCostModelRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        LOWER(model) as model,
        LOWER(provider) as provider,
        COALESCE(NULLIF(service_tier, ''), 'standard') as serviceTier,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_cache_read), 0) as cacheReadTokens,
        COALESCE(SUM(tokens_cache_creation), 0) as cacheCreationTokens,
        COALESCE(SUM(tokens_reasoning), 0) as reasoningTokens
      FROM ${e} AS _pu
      GROUP BY LOWER(model), LOWER(provider), serviceTier
    `).all(r)},"getProviderCostRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        LOWER(provider) as provider,
        LOWER(model) as model,
        COALESCE(NULLIF(service_tier, ''), 'standard') as serviceTier,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_cache_read), 0) as cacheReadTokens,
        COALESCE(SUM(tokens_cache_creation), 0) as cacheCreationTokens,
        COALESCE(SUM(tokens_reasoning), 0) as reasoningTokens
      FROM ${e} AS _u
      GROUP BY LOWER(provider), LOWER(model), serviceTier
    `).all(r)},"getProviderDailyUsageRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        DATE(timestamp) as date,
        LOWER(provider) as provider,
        COUNT(*) as requests,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens
      FROM ${e} AS _u
      GROUP BY DATE(timestamp), LOWER(provider)
      ORDER BY date DESC, requests DESC
    `).all(r)},"getProviderUsageRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        LOWER(provider) as provider,
        COUNT(*) as requests,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens,
        COALESCE(AVG(latency_ms), 0) as avgLatencyMs,
        COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as successfulRequests
      FROM ${e} AS _u
      GROUP BY LOWER(provider)
      ORDER BY requests DESC
    `).all(r)},"getServiceTierUsageRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        COALESCE(NULLIF(service_tier, ''), 'standard') as serviceTier,
        LOWER(provider) as provider,
        LOWER(model) as model,
        COALESCE(NULLIF(service_tier, ''), 'standard') as serviceTier,
        COUNT(*) as requests,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_cache_read), 0) as cacheReadTokens,
        COALESCE(SUM(tokens_cache_creation), 0) as cacheCreationTokens,
        COALESCE(SUM(tokens_reasoning), 0) as reasoningTokens,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens
      FROM ${e} AS _u
      GROUP BY serviceTier, LOWER(provider), LOWER(model)
    `).all(r)},"getUsageSummary",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        COUNT(*) as totalRequests,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens,
        COUNT(DISTINCT model) as uniqueModels,
        COUNT(DISTINCT connection_id) as uniqueAccounts,
        COUNT(DISTINCT COALESCE(NULLIF(api_key_id, ''), NULLIF(api_key_name, ''))) as uniqueApiKeys,
        COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as successfulRequests,
        COALESCE(AVG(latency_ms), 0) as avgLatencyMs,
        COALESCE(MIN(timestamp), '') as firstRequest,
        COALESCE(MAX(timestamp), '') as lastRequest
      FROM ${e} AS _u
    `).get(r)??{totalRequests:0,promptTokens:0,completionTokens:0,totalTokens:0,uniqueModels:0,uniqueAccounts:0,uniqueApiKeys:0,successfulRequests:0,avgLatencyMs:0,firstRequest:"",lastRequest:""}},"getWeeklyPatternRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
      SELECT
        dayOfWeek,
        COUNT(*) as days,
        COALESCE(SUM(requests), 0) as requests,
        COALESCE(SUM(totalTokens), 0) as totalTokens
      FROM (
        SELECT
          DATE(timestamp) as date,
          strftime('%w', timestamp) as dayOfWeek,
          COUNT(*) as requests,
          COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens
        FROM ${e} AS _u
        GROUP BY DATE(timestamp), strftime('%w', timestamp)
      )
      GROUP BY dayOfWeek
      ORDER BY dayOfWeek ASC
    `).all(r)}])},702826,e=>{"use strict";var t=e.i(899378);e.s(["getAutoRoutingTopProviders",0,function(){return(0,t.getDbInstance)().prepare(`
      SELECT provider, COUNT(*) as count
      FROM usage_logs
      WHERE model = 'auto' OR model LIKE 'auto/%'
      GROUP BY provider
      ORDER BY count DESC
      LIMIT 10
      `).all()},"getAutoRoutingTotalCount",0,function(){return(0,t.getDbInstance)().prepare(`
      SELECT COUNT(*) as count
      FROM usage_logs
      WHERE model = 'auto' OR model LIKE 'auto/%'
    `).get()??{count:0}},"getAutoRoutingVariantBreakdown",0,function(){return(0,t.getDbInstance)().prepare(`
      SELECT
        CASE
          WHEN model = 'auto' THEN 'default'
          WHEN model LIKE 'auto/%' THEN SUBSTR(model, 6)
          ELSE 'other'
        END as variant,
        COUNT(*) as count
      FROM usage_logs
      WHERE model = 'auto' OR model LIKE 'auto/%'
      GROUP BY variant
      ORDER BY count DESC
    `).all()}])},631716,e=>{"use strict";var t=e.i(899378);let r=["created_at","expires_at","hit_count","tokens_saved","model"];e.s(["deleteSemanticCacheByModel",0,function(e){return{deleted:(0,t.getDbInstance)().prepare("DELETE FROM semantic_cache WHERE model = ?").run(e).changes}},"deleteSemanticCacheBySignature",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM semantic_cache WHERE signature = ?").run(e),{deleted:1}},"listSemanticCacheEntries",0,function(e){let a=(0,t.getDbInstance)(),{page:n,limit:i,search:s,model:o,sortBy:u,sortOrder:l}=e,d=[],c=[];s&&(d.push("(signature LIKE ? OR model LIKE ?)"),c.push(`%${s}%`,`%${s}%`)),o&&(d.push("model = ?"),c.push(o));let p=d.length>0?`WHERE ${d.join(" AND ")}`:"",E=r.includes(u)?u:"created_at",_=a.prepare(`SELECT COUNT(*) as total FROM semantic_cache ${p}`).get(...c);return{entries:a.prepare(`SELECT id, signature, model, hit_count, tokens_saved, created_at, expires_at
       FROM semantic_cache ${p}
       ORDER BY ${E} ${"asc"===l?"ASC":"DESC"}
       LIMIT ? OFFSET ?`).all(...c,i,(n-1)*i),total:_?.total||0}}])},683844,e=>{"use strict";var t=e.i(899378);e.s(["exportProxyLogsSince",0,function(e){return(0,t.getDbInstance)().prepare("SELECT * FROM proxy_logs WHERE timestamp >= @since ORDER BY timestamp DESC").all({since:e})}])},575869,e=>{"use strict";var t=e.i(899378);let r="provider_param_filters",a=null,n=0;function i(){n++,a=null}function s(e){return null!==e&&"object"==typeof e&&!Array.isArray(e)}function o(e){return"string"==typeof e&&e.length>0?e:null}function u(e){return Array.isArray(e)?e.filter(e=>"string"==typeof e):[]}function l(){return null===a&&(a=function(){let e=function(e){let r=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(e),a={};for(let e of r)a[e.key]=function(e){if("string"!=typeof e)return e;try{return JSON.parse(e)}catch{return e}}(e.value);return a}(r),a=new Map;for(let[t,r]of Object.entries(e)){let e=function(e){if(!s(e))return null;let t=u(e.block),r=u(e.allow),a=function(e){let t={};if(!s(e))return t;for(let[r,a]of Object.entries(e)){if(!s(a))continue;let e=function(e){let t=u(e.block),r=u(e.allow);if(0===t.length&&0===r.length)return null;let a={};return t.length>0&&(a.block=t),r.length>0&&(a.allow=r),a}(a);e&&(t[r]=e)}return t}(e.models),n="boolean"==typeof e.autoLearn&&e.autoLearn;return{block:t,allow:r,models:Object.keys(a).length>0?a:void 0,autoLearn:n}}(r);e&&a.set(t,e)}return a}()),a}function d(e){return o(e)?l().get(e)??null:null}function c(e,a){if(!o(e))return;let n=(0,t.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)"),s={block:a.block??[],allow:a.allow??[],autoLearn:a.autoLearn??!1,models:a.models&&Object.keys(a.models).length>0?a.models:void 0};n.run(r,e,JSON.stringify(s)),i()}let p="__global__";e.s(["addParamToBlocklist",0,function(e,t,r){if(!o(e)||!o(t))return;let a=d(e)??{block:[],allow:[],autoLearn:!1};if(r){let e=a.models??{},n=e[r]??{};if(Array.isArray(n.block)&&n.block.includes(t))return;let i=[...n.block??[],t];e[r]={...n,block:i},a.models=e}else{if(a.block.includes(t))return;a.block=[...a.block,t]}c(e,a)},"deleteParamFilterConfig",0,function(e){o(e)&&((0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(r,e),i())},"getParamFilterConfig",0,d,"isAutoLearnGloballyEnabled",0,function(){let e=d(p);return e?.autoLearn===!0},"loadParamFilterConfigs",0,l,"setGlobalAutoLearnEnabled",0,function(e){let t=d(p);c(p,{block:t?.block??[],allow:t?.allow??[],autoLearn:e})},"setParamFilterConfig",0,c])},845042,e=>{"use strict";var t=e.i(899378);let r="interception_rules",a=null;function n(e){return null!==e&&"object"==typeof e&&!Array.isArray(e)}function i(e){return"string"==typeof e&&e.trim().length>0?e.trim():null}function s(e){return"boolean"==typeof e?e:void 0}function o(e){return"firecrawl"===e||"jina"===e||"tavily"===e?e:void 0}function u(e){return i(e)?(null===a&&(a=function(){let e=function(e){let r=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(e),a={};for(let e of r)a[e.key]=function(e){if("string"!=typeof e)return e;try{return JSON.parse(e)}catch{return e}}(e.value);return a}(r),a=new Map;for(let[t,r]of Object.entries(e)){let e=function(e){if(!n(e))return null;let t=function(e){let t={};if(!n(e))return t;for(let[r,a]of Object.entries(e)){let e=function(e){if(!n(e))return null;let t={interceptSearch:s(e.interceptSearch),interceptFetch:s(e.interceptFetch),fetchBackend:o(e.fetchBackend),fetchProxyUrl:i(e.fetchProxyUrl)??void 0};return Object.values(t).some(e=>void 0!==e)?t:null}(a);e&&(t[r]=e)}return t}(e.models);return{interceptSearch:s(e.interceptSearch),interceptFetch:s(e.interceptFetch),fetchBackend:o(e.fetchBackend),fetchProxyUrl:i(e.fetchProxyUrl)??void 0,models:Object.keys(t).length>0?t:void 0}}(r);e&&a.set(t,e)}return a}()),a).get(e)??null:null}e.s(["deleteInterceptionRules",0,function(e){let n=i(e);n&&((0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(r,n),a=null)},"getInterceptionRules",0,u,"resolveInterceptSearch",0,function(e,t){let r=i(e);if(!r)return;let a=u(r);if(!a)return;let n=i(t);return n&&a.models?.[n]?.interceptSearch!==void 0?a.models[n].interceptSearch:a.interceptSearch},"setInterceptionRules",0,function(e,n){let s=i(e);if(!s)return;let o=(0,t.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)"),u={interceptSearch:n.interceptSearch,interceptFetch:n.interceptFetch,fetchBackend:n.fetchBackend,fetchProxyUrl:n.fetchProxyUrl,models:n.models&&Object.keys(n.models).length>0?n.models:void 0};o.run(r,s,JSON.stringify(u)),a=null}])},245272,e=>e.a(async(t,r)=>{try{var a=e.i(748648);e.i(186920),e.i(151205),e.i(894278),e.i(926028),e.i(747369),e.i(315963),e.i(125852),e.i(926554);var n=e.i(238521);e.i(167213),e.i(33770),e.i(751183),e.i(935050),e.i(964183),e.i(403122),e.i(583281),e.i(68392),e.i(118739),e.i(226420),e.i(879032),e.i(446908),e.i(783414),e.i(517551),e.i(130273),e.i(188693),e.i(13985),e.i(559339),e.i(790883),e.i(829422),e.i(870766),e.i(983427),e.i(306860),e.i(291823),e.i(850803),e.i(605845),e.i(403098),e.i(992088),e.i(323681),e.i(795769),e.i(54572),e.i(13123),e.i(524630),e.i(343379),e.i(51829),e.i(620457),e.i(682815);var i=e.i(519854);e.i(576992),e.i(446980),e.i(365164),e.i(582109),e.i(489259),e.i(409500),e.i(95825),e.i(131470),e.i(224136),e.i(441273),e.i(469960),e.i(496425),e.i(126603),e.i(702826),e.i(631716),e.i(683844),e.i(575869),e.i(845042);var s=t([a,n,i]);[a,n,i]=s.then?(await s)():s,e.s([]),r()}catch(e){r(e)}},!1)];

//# sourceMappingURL=src_lib_1w66mz6._.js.map