module.exports=[974008,e=>{"use strict";var t=e.i(666680),r=e.i(830471),n=e.i(330485);function a(e,t,r){return e.prepare(`PRAGMA table_info(${t})`).all().some(e=>e&&"string"==typeof e.name&&e.name===r)}function i(e){e.prepare(`CREATE TABLE IF NOT EXISTS eval_suites (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )`).run(),a(e,"eval_suites","description")||e.prepare("ALTER TABLE eval_suites ADD COLUMN description TEXT").run(),a(e,"eval_suites","created_at")||e.prepare("ALTER TABLE eval_suites ADD COLUMN created_at TEXT NOT NULL DEFAULT ''").run(),a(e,"eval_suites","updated_at")||e.prepare("ALTER TABLE eval_suites ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''").run(),e.prepare(`CREATE TABLE IF NOT EXISTS eval_cases (
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
    )`).run(),a(e,"eval_cases","sort_order")||e.prepare("ALTER TABLE eval_cases ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0").run(),a(e,"eval_cases","model")||e.prepare("ALTER TABLE eval_cases ADD COLUMN model TEXT").run(),a(e,"eval_cases","input_json")||e.prepare("ALTER TABLE eval_cases ADD COLUMN input_json TEXT NOT NULL DEFAULT '{}'").run(),a(e,"eval_cases","expected_strategy")||e.prepare("ALTER TABLE eval_cases ADD COLUMN expected_strategy TEXT NOT NULL DEFAULT 'contains'").run(),a(e,"eval_cases","expected_value")||e.prepare("ALTER TABLE eval_cases ADD COLUMN expected_value TEXT").run(),a(e,"eval_cases","tags_json")||e.prepare("ALTER TABLE eval_cases ADD COLUMN tags_json TEXT").run(),a(e,"eval_cases","created_at")||e.prepare("ALTER TABLE eval_cases ADD COLUMN created_at TEXT NOT NULL DEFAULT ''").run(),a(e,"eval_cases","updated_at")||e.prepare("ALTER TABLE eval_cases ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''").run(),e.prepare("CREATE INDEX IF NOT EXISTS idx_eval_suites_updated_at ON eval_suites(updated_at DESC)").run(),e.prepare("CREATE INDEX IF NOT EXISTS idx_eval_cases_suite_order ON eval_cases(suite_id, sort_order ASC, created_at ASC)").run()}function s(e){if(e&&"object"==typeof e&&!Array.isArray(e))return e;if("string"!=typeof e||0===e.trim().length)return{};try{let t=JSON.parse(e);return t&&"object"==typeof t&&!Array.isArray(t)?t:{}}catch{return{}}}function o(e){let t=Number(e);return Number.isFinite(t)?t:0}function l(e){var t;let r=e&&"object"==typeof e&&!Array.isArray(e)?e:{},n=o(r.max_tokens),a={messages:Array.isArray(t=r.messages)?t.map(e=>{if(!e||"object"!=typeof e||Array.isArray(e))return null;let t="string"==typeof e.role?e.role.trim():"",r="string"==typeof e.content?e.content:"";return t&&r.trim()?{role:t,content:r}:null}).filter(e=>null!==e):[]};return n>0&&(a.max_tokens=Math.floor(n)),a}function u(e){let t=e&&"object"==typeof e&&!Array.isArray(e)?e:{},r="string"==typeof t.strategy?t.strategy.trim():"",n="string"==typeof t.value&&t.value.trim().length>0?t.value:void 0;return{strategy:"exact"===r||"regex"===r||"custom"===r?r:"contains",...n?{value:n}:{}}}function d(e,t){return`${e}:${"string"==typeof t&&t.trim().length>0?t.trim():"__default__"}`}function c(e){let t,r,a,i,l=(0,n.rowToCamel)(e);if(!l)return null;let u=s(l.summary??l.summaryJson),c=Object.fromEntries(Object.entries(s(l.outputs??l.outputsJson)).filter(e=>"string"==typeof e[0]).map(([e,t])=>[e,"string"==typeof t?t:String(t??"")]));return{id:"string"==typeof l.id?l.id:"",runGroupId:"string"==typeof l.runGroupId&&l.runGroupId.trim().length>0?l.runGroupId:null,suiteId:"string"==typeof l.suiteId?l.suiteId:"",suiteName:"string"==typeof l.suiteName?l.suiteName:"",target:(t=l.targetType,a="string"==typeof(r=l.targetId)&&r.trim().length>0?r.trim():null,{type:i="combo"===t||"model"===t||"suite-default"===t?t:"suite-default",id:a,key:d(i,a),label:"string"==typeof l.targetLabel&&l.targetLabel.trim().length>0?l.targetLabel.trim():"combo"===i?`Combo: ${a||"Unknown"}`:"model"===i?`Model: ${a||"Unknown"}`:"Suite defaults"}),apiKeyId:"string"==typeof l.apiKeyId&&l.apiKeyId.trim().length>0?l.apiKeyId:null,avgLatencyMs:o(l.avgLatencyMs),summary:{total:o(u.total??l.total),passed:o(u.passed??l.passed),failed:o(u.failed??l.failed),passRate:o(u.passRate??l.passRate)},results:function(e){if(Array.isArray(e))return e.filter(e=>!!e&&"object"==typeof e&&!Array.isArray(e));if("string"!=typeof e||0===e.trim().length)return[];try{let t=JSON.parse(e);return Array.isArray(t)?t.filter(e=>!!e&&"object"==typeof e&&!Array.isArray(e)):[]}catch{return[]}}(l.results??l.resultsJson),outputs:c,createdAt:"string"==typeof l.createdAt?l.createdAt:""}}function p(e={}){let t=(0,r.getDbInstance)(),n=[],a=[];e.suiteId&&(n.push("suite_id = ?"),a.push(e.suiteId)),e.runGroupId&&(n.push("run_group_id = ?"),a.push(e.runGroupId));let i=Number.isFinite(Number(e.limit))?Math.min(200,Math.max(1,Math.floor(Number(e.limit)))):20;a.push(i);let s=`SELECT *
    FROM eval_runs
    ${n.length>0?`WHERE ${n.join(" AND ")}`:""}
    ORDER BY created_at DESC
    LIMIT ?`;return t.prepare(s).all(...a).map(e=>c(e)).filter(e=>null!==e)}function E(){let e=(0,r.getDbInstance)();i(e);let t=e.prepare("SELECT * FROM eval_suites ORDER BY updated_at DESC, created_at DESC").all(),a=e.prepare("SELECT * FROM eval_cases ORDER BY suite_id ASC, sort_order ASC, created_at ASC, id ASC").all(),d=new Map;for(let e of a){let t=function(e){let t=(0,n.rowToCamel)(e);if(!t)return null;let r=l(s(t.input??t.inputJson)),a=u({strategy:t.expectedStrategy,value:t.expectedValue});return{id:"string"==typeof t.id?t.id:"",suiteId:"string"==typeof t.suiteId?t.suiteId:"",name:"string"==typeof t.name?t.name:"",..."string"==typeof t.model&&t.model.trim().length>0?{model:t.model.trim()}:{},input:r,expected:a,tags:function(e){if(Array.isArray(e))return e.filter(e=>"string"==typeof e).map(e=>e.trim()).filter(e=>e.length>0);if("string"!=typeof e||0===e.trim().length)return[];try{let t=JSON.parse(e);return Array.isArray(t)?t.filter(e=>"string"==typeof e).map(e=>e.trim()).filter(e=>e.length>0):[]}catch{return[]}}(t.tags??t.tagsJson),sortOrder:o(t.sortOrder),createdAt:"string"==typeof t.createdAt?t.createdAt:"",updatedAt:"string"==typeof t.updatedAt?t.updatedAt:""}}(e);if(!t||!t.suiteId)continue;let r=d.get(t.suiteId)||[];r.push(t),d.set(t.suiteId,r)}return t.map(e=>{var t;let r,a=(0,n.rowToCamel)(e),i=a&&"string"==typeof a.id?a.id:"";return t=d.get(i)||[],(r=(0,n.rowToCamel)(e))?{id:"string"==typeof r.id?r.id:"",name:"string"==typeof r.name?r.name:"",..."string"==typeof r.description&&r.description.trim().length>0?{description:r.description}:{},source:"custom",caseCount:t.length,cases:t,createdAt:"string"==typeof r.createdAt?r.createdAt:"",updatedAt:"string"==typeof r.updatedAt?r.updatedAt:""}:null}).filter(e=>null!==e)}function _(e){let t=e.trim();return t&&E().find(e=>e.id===t)||null}e.s(["deleteCustomEvalSuite",0,function(e){let t=(0,r.getDbInstance)();i(t);let n=e.trim();if(!n)return!1;t.prepare("BEGIN").run();try{t.prepare("DELETE FROM eval_cases WHERE suite_id = ?").run(n);let e=t.prepare("DELETE FROM eval_suites WHERE id = ?").run(n);return t.prepare("COMMIT").run(),e.changes>0}catch(e){throw t.prepare("ROLLBACK").run(),e}},"getCustomEvalSuite",0,_,"getEvalScorecard",0,function(e={}){var t;let r,n,a=p({suiteId:e.suiteId,limit:e.limit||50});if(0===a.length)return null;let i=new Map;for(let e of a){let t=`${e.suiteId}:${e.target.key}`;i.has(t)||i.set(t,e)}return r=(t=Array.from(i.values()).map(e=>({suiteId:`${e.suiteId}:${e.target.key}`,suiteName:`${e.suiteName} \xb7 ${e.target.label}`,results:e.results,summary:e.summary}))).reduce((e,t)=>e+t.summary.total,0),n=t.reduce((e,t)=>e+t.summary.passed,0),{suites:t.length,totalCases:r,totalPassed:n,overallPassRate:r>0?Math.round(n/r*100):0,perSuite:t.map(e=>({id:e.suiteId,name:e.suiteName,passRate:e.summary.passRate}))}},"listCustomEvalSuites",0,E,"listEvalRuns",0,p,"listModelEvalRunsForRouting",0,function(e){let t=[...new Set(e.targetIds.map(e=>e.trim()).filter(Boolean))].slice(0,200);if(0===t.length)return[];let n=Array.isArray(e.suiteIds)?[...new Set(e.suiteIds.map(e=>e.trim()).filter(Boolean))].slice(0,50):[],a=(0,r.getDbInstance)(),i=["target_type = 'model'"],s=[];i.push(`target_id IN (${t.map(()=>"?").join(", ")})`),s.push(...t),n.length>0&&(i.push(`suite_id IN (${n.map(()=>"?").join(", ")})`),s.push(...n));let o=Number(e.maxAgeHours);Number.isFinite(o)&&o>0&&(i.push("created_at >= ?"),s.push(new Date(Date.now()-60*o*6e4).toISOString()));let l=Number.isFinite(Number(e.limit))?Math.min(1e3,Math.max(1,Math.floor(Number(e.limit)))):Math.min(1e3,Math.max(50,t.length*Math.max(3,n.length||5)*2));return s.push(l),a.prepare(`SELECT *
       FROM eval_runs
       WHERE ${i.join(" AND ")}
       ORDER BY created_at DESC
       LIMIT ?`).all(...s).map(e=>c(e)).filter(e=>null!==e)},"saveCustomEvalSuite",0,function(e){let n=(0,r.getDbInstance)();i(n);let a=new Date().toISOString(),s="string"==typeof e.id&&e.id.trim().length>0?e.id.trim():(0,t.randomUUID)(),o=e.name.trim(),d="string"==typeof e.description&&e.description.trim().length>0?e.description.trim():null;if(!o)throw Error("Suite name is required");if(!Array.isArray(e.cases)||0===e.cases.length)throw Error("At least one eval case is required");n.prepare("BEGIN").run();try{n.prepare("SELECT id FROM eval_suites WHERE id = ?").get(s)?n.prepare(`UPDATE eval_suites
         SET name = ?, description = ?, updated_at = ?
         WHERE id = ?`).run(o,d,a,s):n.prepare(`INSERT INTO eval_suites (id, name, description, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?)`).run(s,o,d,a,a),n.prepare("DELETE FROM eval_cases WHERE suite_id = ?").run(s),e.cases.forEach((e,r)=>{let i="string"==typeof e.id&&e.id.trim().length>0?e.id.trim():(0,t.randomUUID)(),o=e.name.trim(),d="string"==typeof e.model&&e.model.trim().length>0?e.model.trim():null,c=l(e.input),p=u(e.expected),E=Array.isArray(e.tags)?e.tags.map(e=>e.trim()).filter(e=>e.length>0):[];if(!o)throw Error(`Case ${r+1} is missing a name`);if(0===c.messages.length)throw Error(`Case ${r+1} must include at least one message`);if(("contains"===p.strategy||"exact"===p.strategy||"regex"===p.strategy)&&!p.value)throw Error(`Case ${r+1} must include an expected value`);n.prepare(`INSERT INTO eval_cases
          (id, suite_id, sort_order, name, model, input_json, expected_strategy, expected_value,
           tags_json, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(i,s,r,o,d,JSON.stringify(c),p.strategy,p.value||null,JSON.stringify(E),a,a)}),n.prepare("COMMIT").run()}catch(e){throw n.prepare("ROLLBACK").run(),e}let c=_(s);if(!c)throw Error("Failed to persist eval suite");return c},"saveEvalRun",0,function(e){let n=(0,r.getDbInstance)(),a=e.createdAt||new Date().toISOString(),i=(0,t.randomUUID)(),s="string"==typeof e.target.id&&e.target.id.trim().length>0?e.target.id.trim():null,o=Number.isFinite(Number(e.avgLatencyMs))?Math.max(0,Math.round(Number(e.avgLatencyMs))):0;return n.prepare(`INSERT INTO eval_runs
      (id, run_group_id, suite_id, suite_name, target_type, target_id, target_label, api_key_id,
       pass_rate, total, passed, failed, avg_latency_ms, summary_json, results_json, outputs_json, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(i,e.runGroupId||null,e.suiteId,e.suiteName,e.target.type,s,e.target.label,e.apiKeyId||null,e.summary.passRate,e.summary.total,e.summary.passed,e.summary.failed,o,JSON.stringify(e.summary),JSON.stringify(e.results||[]),JSON.stringify(e.outputs||{}),a),{id:i,runGroupId:e.runGroupId||null,suiteId:e.suiteId,suiteName:e.suiteName,target:{type:e.target.type,id:s,key:d(e.target.type,s),label:e.target.label},apiKeyId:e.apiKeyId||null,avgLatencyMs:o,summary:e.summary,results:e.results||[],outputs:e.outputs||{},createdAt:a}},"serializeEvalTargetKey",0,d])},709287,e=>{"use strict";var t=e.i(830471);let r=new Set(["enabled","mode","updated_at"]);e.s(["updateSkill",0,function(e,n){let a=(0,t.getDbInstance)(),i=[],s=[];for(let[e,t]of Object.entries(n))r.has(e)&&(i.push(`${e} = ?`),s.push(t));return 0===i.length?0:(i.push("updated_at = datetime('now')"),s.push(e),a.prepare(`UPDATE skills SET ${i.join(", ")} WHERE id = ?`).run(...s).changes)}])},707708,e=>{"use strict";var t=e.i(254799),r=e.i(995031),n=e.i(830471),a=e.i(330485);function i(){return new Date().toISOString().slice(0,10)}function s(){return new Date().toISOString().slice(0,13)}function o(e){return e&&"string"==typeof e?(0,t.createHash)("sha256").update(e).digest("hex"):""}function l(e,t,r,n){let a=i(),o=s();e.prepare(`
    UPDATE ${t}
    SET daily_issued = CASE WHEN last_reset_day <> ? THEN 0 ELSE daily_issued END,
        hourly_issued = CASE WHEN last_reset_hour <> ? THEN 0 ELSE hourly_issued END,
        last_reset_day = ?,
        last_reset_hour = ?
    WHERE ${r} = ?
  `).run(a,o,a,o,n)}e.s(["checkQuota",0,function(e="",t=""){let r=(0,n.getDbInstance)();if(i(),s(),e){l(r,"provider_key_limits","provider",e);let t=r.prepare("SELECT * FROM provider_key_limits WHERE provider = ?").get(e);if(t){if(null!==t.hourly_issue_limit&&t.hourly_issued>=t.hourly_issue_limit)return{allowed:!1,errorCode:"PROVIDER_QUOTA_EXCEEDED",errorMessage:`Hourly issue limit (${t.hourly_issue_limit}) reached for provider '${e}'`,provider:e};if(null!==t.daily_issue_limit&&t.daily_issued>=t.daily_issue_limit)return{allowed:!1,errorCode:"PROVIDER_QUOTA_EXCEEDED",errorMessage:`Daily issue limit (${t.daily_issue_limit}) reached for provider '${e}'`,provider:e};if(null!==t.max_active_keys){let{activeCount:n}=r.prepare("SELECT COUNT(*) as activeCount FROM registered_keys WHERE provider = ? AND is_active = 1").get(e);if(n>=t.max_active_keys)return{allowed:!1,errorCode:"MAX_ACTIVE_KEYS_EXCEEDED",errorMessage:`Max active keys (${t.max_active_keys}) reached for provider '${e}'`,provider:e,providerActiveKeys:n}}}}if(t){l(r,"account_key_limits","account_id",t);let e=r.prepare("SELECT * FROM account_key_limits WHERE account_id = ?").get(t);if(e){if(null!==e.hourly_issue_limit&&e.hourly_issued>=e.hourly_issue_limit)return{allowed:!1,errorCode:"ACCOUNT_QUOTA_EXCEEDED",errorMessage:`Hourly issue limit (${e.hourly_issue_limit}) reached for account '${t}'`,accountId:t};if(null!==e.daily_issue_limit&&e.daily_issued>=e.daily_issue_limit)return{allowed:!1,errorCode:"ACCOUNT_QUOTA_EXCEEDED",errorMessage:`Daily issue limit (${e.daily_issue_limit}) reached for account '${t}'`,accountId:t};if(null!==e.max_active_keys){let{activeCount:n}=r.prepare("SELECT COUNT(*) as activeCount FROM registered_keys WHERE account_id = ? AND is_active = 1").get(t);if(n>=e.max_active_keys)return{allowed:!1,errorCode:"MAX_ACTIVE_KEYS_EXCEEDED",errorMessage:`Max active keys (${e.max_active_keys}) reached for account '${t}'`,accountId:t,accountActiveKeys:n}}}}return{allowed:!0}},"getAccountKeyLimit",0,function(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM account_key_limits WHERE account_id = ?").get(e);return t?(0,a.rowToCamel)(t):null},"getProviderKeyLimit",0,function(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM provider_key_limits WHERE provider = ?").get(e);return t?(0,a.rowToCamel)(t):null},"getRegisteredKey",0,function(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM registered_keys WHERE id = ?").get(e);return t?(0,a.rowToCamel)(t):null},"incrementRegisteredKeyUsage",0,function(e){(0,n.getDbInstance)().prepare(`
    UPDATE registered_keys
    SET daily_used = daily_used + 1, hourly_used = hourly_used + 1, updated_at = datetime('now')
    WHERE id = ?
  `).run(e)},"issueRegisteredKey",0,function(e){let u=(0,n.getDbInstance)(),{name:d,provider:c="",accountId:p="",idempotencyKey:E,expiresAt:_,dailyBudget:m,hourlyBudget:y}=e;if(E){let e=u.prepare("SELECT * FROM registered_keys WHERE idempotency_key = ?").get(E);if(e)return{idempotencyConflict:!0,existing:(0,a.rowToCamel)(e)}}let g="ork_"+(0,t.randomBytes)(24).toString("base64url"),S=(0,r.v4)(),T=o(g),R=g.slice(0,12);u.prepare(`
    INSERT INTO registered_keys
      (id, key, key_prefix, name, provider, account_id, idempotency_key, expires_at, daily_budget, hourly_budget, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(S,T,R,d,c,p,E??null,_??null,m??null,y??null,i(),s()),c&&(l(u,"provider_key_limits","provider",c),u.prepare(`
      INSERT INTO provider_key_limits (provider, daily_issued, hourly_issued, last_reset_day, last_reset_hour)
      VALUES (?, 1, 1, ?, ?)
      ON CONFLICT(provider) DO UPDATE SET
        daily_issued = daily_issued + 1,
        hourly_issued = hourly_issued + 1,
        updated_at = datetime('now')
    `).run(c,i(),s())),p&&(l(u,"account_key_limits","account_id",p),u.prepare(`
      INSERT INTO account_key_limits (account_id, daily_issued, hourly_issued, last_reset_day, last_reset_hour)
      VALUES (?, 1, 1, ?, ?)
      ON CONFLICT(account_id) DO UPDATE SET
        daily_issued = daily_issued + 1,
        hourly_issued = hourly_issued + 1,
        updated_at = datetime('now')
    `).run(p,i(),s()));let f=u.prepare("SELECT * FROM registered_keys WHERE id = ?").get(S);return{...(0,a.rowToCamel)(f),rawKey:g}},"listRegisteredKeys",0,function(e={}){let t=(0,n.getDbInstance)(),r="SELECT * FROM registered_keys WHERE 1=1",i=[];return e.provider&&(r+=" AND provider = ?",i.push(e.provider)),e.accountId&&(r+=" AND account_id = ?",i.push(e.accountId)),r+=" ORDER BY created_at DESC LIMIT 500",t.prepare(r).all(...i).map(e=>(0,a.rowToCamel)(e))},"revokeRegisteredKey",0,function(e){return(0,n.getDbInstance)().prepare(`
    UPDATE registered_keys
    SET is_active = 0, revoked_at = datetime('now'), updated_at = datetime('now')
    WHERE id = ? AND is_active = 1
  `).run(e).changes>0},"setAccountKeyLimit",0,function(e,t){(0,n.getDbInstance)().prepare(`
    INSERT INTO account_key_limits (account_id, max_active_keys, daily_issue_limit, hourly_issue_limit, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(account_id) DO UPDATE SET
      max_active_keys = excluded.max_active_keys,
      daily_issue_limit = excluded.daily_issue_limit,
      hourly_issue_limit = excluded.hourly_issue_limit,
      updated_at = datetime('now')
  `).run(e,t.maxActiveKeys??null,t.dailyIssueLimit??null,t.hourlyIssueLimit??null,i(),s())},"setProviderKeyLimit",0,function(e,t){(0,n.getDbInstance)().prepare(`
    INSERT INTO provider_key_limits (provider, max_active_keys, daily_issue_limit, hourly_issue_limit, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(provider) DO UPDATE SET
      max_active_keys = excluded.max_active_keys,
      daily_issue_limit = excluded.daily_issue_limit,
      hourly_issue_limit = excluded.hourly_issue_limit,
      updated_at = datetime('now')
  `).run(e,t.maxActiveKeys??null,t.dailyIssueLimit??null,t.hourlyIssueLimit??null,i(),s())},"validateRegisteredKey",0,function(e){let t=(0,n.getDbInstance)(),r=o(e),l=t.prepare(`
    SELECT * FROM registered_keys
    WHERE key = ? AND is_active = 1
      AND (expires_at IS NULL OR expires_at > datetime('now'))
  `).get(r);if(!l)return null;let u=i(),d=s();return((l.last_reset_day!==u||l.last_reset_hour!==d)&&t.prepare(`
      UPDATE registered_keys
      SET daily_used = CASE WHEN last_reset_day <> ? THEN 0 ELSE daily_used END,
          hourly_used = CASE WHEN last_reset_hour <> ? THEN 0 ELSE hourly_used END,
          last_reset_day = ?, last_reset_hour = ?
      WHERE id = ?
    `).run(u,d,u,d,l.id),null!==l.daily_budget&&l.daily_used>=l.daily_budget||null!==l.hourly_budget&&l.hourly_used>=l.hourly_budget)?null:(0,a.rowToCamel)(l)}])},138435,e=>{"use strict";e.s(["DEFAULT_BATCH_EXPIRATION_SECONDS",0,2592e3])},773412,e=>{"use strict";var t=e.i(830471),r=e.i(330485),n=e.i(995031),a=e.i(138435);let i="id, bytes, created_at, filename, purpose, mime_type, api_key_id, expires_at, deleted_at";function s(e){let n=(0,t.getDbInstance)().prepare(`SELECT ${i} FROM files WHERE id = ? AND deleted_at IS NULL`).get(e);return n?(0,r.rowToCamel)(n):null}e.s(["countFiles",0,function(e={}){let r=(0,t.getDbInstance)(),{apiKeyId:n,purpose:a}=e,i="SELECT COUNT(*) as c FROM files WHERE deleted_at IS NULL",s=[];n&&(i+=" AND api_key_id = ?",s.push(n)),a&&(i+=" AND purpose = ?",s.push(a));let o=r.prepare(i).get(...s);return o?Number(o.c):0},"createFile",0,function(e){let r=(0,t.getDbInstance)(),i="file-"+(0,n.v4)().replaceAll("-","").substring(0,24),s=Math.floor(Date.now()/1e3),o=e.expiresAt;void 0===o&&"batch"===e.purpose&&(o=s+a.DEFAULT_BATCH_EXPIRATION_SECONDS);let l={id:i,bytes:e.bytes,createdAt:s,filename:e.filename,purpose:e.purpose,content:e.content??null,mimeType:e.mimeType??null,apiKeyId:e.apiKeyId??null,expiresAt:o??null,deletedAt:null};return r.prepare(`
    INSERT INTO files (id, bytes, created_at, filename, purpose, content, mime_type, api_key_id, expires_at, deleted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(l.id,l.bytes,l.createdAt,l.filename,l.purpose,l.content,l.mimeType,l.apiKeyId,l.expiresAt,l.deletedAt),l},"deleteFile",0,function(e){return(0,t.getDbInstance)().prepare("UPDATE files SET deleted_at = ?, content = NULL WHERE id = ?").run(Math.floor(Date.now()/1e3),e).changes>0},"formatFileResponse",0,function(e){let t="number"==typeof e.createdAt&&Number.isFinite(e.createdAt)?e.createdAt:0,r="number"==typeof e.expiresAt&&Number.isFinite(e.expiresAt)?e.expiresAt:null;return{id:e.id,bytes:e.bytes,created_at:t,filename:e.filename,object:"file",purpose:e.purpose,expires_at:r}},"getFile",0,s,"getFileContent",0,function(e){let r=(0,t.getDbInstance)().prepare("SELECT content FROM files WHERE id = ? AND deleted_at IS NULL").get(e);return r?.content?Buffer.isBuffer(r.content)?r.content:Buffer.from(r.content):null},"listFiles",0,function(e={}){let n=(0,t.getDbInstance)(),{apiKeyId:a,purpose:o,limit:l=20,after:u,order:d="desc"}=e,c=`SELECT ${i} FROM files WHERE deleted_at IS NULL`,p=[];if(a&&(c+=" AND api_key_id = ?",p.push(a)),o&&(c+=" AND purpose = ?",p.push(o)),u){let e=s(u);e&&("desc"===d?c+=" AND (created_at < ? OR (created_at = ? AND id < ?))":c+=" AND (created_at > ? OR (created_at = ? AND id > ?))",p.push(e.createdAt,e.createdAt,u))}return c+=` ORDER BY created_at ${"asc"===d?"ASC":"DESC"}, id ${"asc"===d?"ASC":"DESC"} LIMIT ?`,p.push(l),n.prepare(c).all(...p).map(e=>(0,r.rowToCamel)(e))}])},301435,e=>{"use strict";var t=e.i(830471),r=e.i(330485),n=e.i(773412),a=e.i(995031);function i(e){let t=(0,r.rowToCamel)(e);if(t.metadata&&"string"==typeof t.metadata)try{t.metadata=JSON.parse(t.metadata)}catch{t.metadata=null}if(t.errors&&"string"==typeof t.errors)try{t.errors=JSON.parse(t.errors)}catch{t.errors=null}if(t.usage&&"string"==typeof t.usage)try{t.usage=JSON.parse(t.usage)}catch{t.usage=null}let n=e=>{if("number"==typeof e&&Number.isFinite(e))return e;if(null==e)return null;let t=Number(e);return Number.isFinite(t)?t:null};return t.createdAt=n(t.createdAt)??0,t.inProgressAt=n(t.inProgressAt),t.expiresAt=n(t.expiresAt),t.finalizingAt=n(t.finalizingAt),t.completedAt=n(t.completedAt),t.failedAt=n(t.failedAt),t.expiredAt=n(t.expiredAt),t.cancellingAt=n(t.cancellingAt),t.cancelledAt=n(t.cancelledAt),t}function s(e){if(null==e)return null;if("string"!=typeof e)return e;try{return JSON.parse(e)}catch{return null}}function o(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM batches WHERE id = ?").get(e);return r?i(r):null}e.s(["countBatchItemCheckpoints",0,function(e){let r=(0,t.getDbInstance)().prepare("SELECT COUNT(*) AS c FROM batch_item_checkpoints WHERE batch_id = ?").get(e);return r?Number(r.c):0},"countBatches",0,function(e){let r=(0,t.getDbInstance)();if(e){let t=r.prepare("SELECT COUNT(*) as c FROM batches WHERE api_key_id = ?").get(e);return t?Number(t.c):0}{let e=r.prepare("SELECT COUNT(*) as c FROM batches").get();return e?Number(e.c):0}},"createBatch",0,function(e){let n=(0,t.getDbInstance)(),i="batch_"+(0,a.v4)().replaceAll("-","").substring(0,24),s=Math.floor(Date.now()/1e3),o={...e,id:i,createdAt:s,status:e.status||"validating",requestCountsTotal:0,requestCountsCompleted:0,requestCountsFailed:0,errors:e.errors||null,model:e.model||null,usage:e.usage||null,outputExpiresAfterSeconds:e.outputExpiresAfterSeconds||null,outputExpiresAfterAnchor:e.outputExpiresAfterAnchor||null},l=(0,r.objToSnake)({...o,metadata:o.metadata?JSON.stringify(o.metadata):null,errors:o.errors?JSON.stringify(o.errors):null,usage:o.usage?JSON.stringify(o.usage):null}),u=Object.keys(l),d=Object.values(l),c=u.map(()=>"?").join(", ");return n.prepare(`INSERT INTO batches (${u.join(", ")}) VALUES (${c})`).run(...d),o},"deleteBatch",0,function(e){let r=(0,t.getDbInstance)(),a=o(e);if(!a)return!1;if(r.prepare("DELETE FROM batch_item_checkpoints WHERE batch_id = ?").run(e),a.inputFileId)try{(0,n.deleteFile)(a.inputFileId)}catch{}if(a.outputFileId)try{(0,n.deleteFile)(a.outputFileId)}catch{}if(a.errorFileId)try{(0,n.deleteFile)(a.errorFileId)}catch{}return r.prepare("DELETE FROM batches WHERE id = ?").run(e).changes>0},"deleteCompletedBatches",0,function(){let e=(0,t.getDbInstance)(),r=e.prepare("SELECT input_file_id, output_file_id, error_file_id FROM batches WHERE status = 'completed'").all(),a=new Set;for(let e of r)e.input_file_id&&a.add(e.input_file_id),e.output_file_id&&a.add(e.output_file_id),e.error_file_id&&a.add(e.error_file_id);let i=0;for(let e of a)try{(0,n.deleteFile)(e)&&i++}catch{}return e.prepare("DELETE FROM batch_item_checkpoints WHERE batch_id IN (SELECT id FROM batches WHERE status = 'completed')").run(),{deletedBatches:e.prepare("DELETE FROM batches WHERE status = 'completed'").run().changes,deletedFiles:i}},"ensureBatchItemCheckpoints",0,function(e,r){if(0===r.length)return;let n=(0,t.getDbInstance)(),a=Math.floor(Date.now()/1e3),i=n.prepare(`
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
  `);n.transaction(()=>{for(let t of r)i.run(e,t.lineNumber,t.customId,a,a)})()},"getBatch",0,o,"getPendingBatches",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM batches WHERE status IN ('validating', 'in_progress', 'finalizing', 'cancelling')").all().map(e=>i(e))},"getTerminalBatches",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM batches WHERE status IN ('completed', 'failed', 'cancelled', 'expired') ORDER BY created_at ASC").all().map(e=>i(e))},"listBatchItemCheckpoints",0,function(e){return(0,t.getDbInstance)().prepare(`
      SELECT batch_id, line_number, custom_id, status, result_json, error_json, created_at, updated_at
      FROM batch_item_checkpoints
      WHERE batch_id = ?
      ORDER BY line_number ASC
    `).all(e).map(e=>({batchId:e.batch_id,lineNumber:Number(e.line_number),customId:e.custom_id??null,status:e.status,result:s(e.result_json),error:s(e.error_json),createdAt:Number(e.created_at),updatedAt:Number(e.updated_at)}))},"listBatches",0,function(e,r=20,n){let a=(0,t.getDbInstance)(),s=n?o(n):null;return(e?s?a.prepare("SELECT * FROM batches WHERE api_key_id = ? AND (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC LIMIT ?").all(e,s.createdAt,s.createdAt,n,r):a.prepare("SELECT * FROM batches WHERE api_key_id = ? ORDER BY created_at DESC, id DESC LIMIT ?").all(e,r):s?a.prepare("SELECT * FROM batches WHERE (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC LIMIT ?").all(s.createdAt,s.createdAt,n,r):a.prepare("SELECT * FROM batches ORDER BY created_at DESC, id DESC LIMIT ?").all(r)).map(e=>i(e))},"markBatchItemError",0,function(e,r,n){let a=(0,t.getDbInstance)(),i=Math.floor(Date.now()/1e3);a.prepare(`
    UPDATE batch_item_checkpoints
    SET custom_id = ?,
        status = 'errored',
        result_json = NULL,
        error_json = ?,
        updated_at = ?
    WHERE batch_id = ? AND line_number = ?
  `).run(r.customId,JSON.stringify(n),i,e,r.lineNumber)},"markBatchItemProcessing",0,function(e,r){let n=(0,t.getDbInstance)(),a=Math.floor(Date.now()/1e3);n.prepare(`
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
  `).run(e,r.lineNumber,r.customId,a,a)},"markBatchItemResult",0,function(e,r,n){let a=(0,t.getDbInstance)(),i=Math.floor(Date.now()/1e3);a.prepare(`
    UPDATE batch_item_checkpoints
    SET custom_id = ?,
        status = 'completed',
        result_json = ?,
        error_json = NULL,
        updated_at = ?
    WHERE batch_id = ? AND line_number = ?
  `).run(r.customId,JSON.stringify(n),i,e,r.lineNumber)},"updateBatch",0,function(e,n){let a=(0,t.getDbInstance)(),i=(0,r.objToSnake)(n);i.metadata&&"string"!=typeof i.metadata&&(i.metadata=JSON.stringify(i.metadata)),i.errors&&"string"!=typeof i.errors&&(i.errors=JSON.stringify(i.errors)),i.usage&&"string"!=typeof i.usage&&(i.usage=JSON.stringify(i.usage));let s=Object.keys(i);if(0===s.length)return!1;let o=s.map(e=>`${e} = ?`).join(", "),l=Object.values(i);return a.prepare(`UPDATE batches SET ${o} WHERE id = ?`).run(...l,e).changes>0}])},993053,e=>{"use strict";var t=e.i(830471);function r(e){let t;if(e.models)try{let r=JSON.parse(e.models);Array.isArray(r)&&(t=r.map(String))}catch{t=void 0}return{id:e.id,providerId:e.provider_id,method:e.method,endpoint:e.endpoint,authType:e.auth_type??"none",models:t,rateLimit:e.rate_limit,feasibility:e.feasibility??0,riskLevel:e.risk_level??"none",status:e.status,notes:e.notes,discoveredAt:e.discovered_at,verifiedAt:e.verified_at}}function n(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM discovery_results WHERE id = ?").get(e);return n?r(n):null}e.s(["deleteDiscoveryResult",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM discovery_results WHERE id = ?").run(e).changes>0},"getDiscoveryResultById",0,n,"getDiscoveryResults",0,function(e){let n=(0,t.getDbInstance)();return(e?n.prepare("SELECT * FROM discovery_results WHERE provider_id = ? ORDER BY discovered_at DESC, id DESC").all(e):n.prepare("SELECT * FROM discovery_results ORDER BY discovered_at DESC, id DESC").all()).map(r)},"markVerified",0,function(e){return 0===(0,t.getDbInstance)().prepare("UPDATE discovery_results SET status = 'verified', verified_at = datetime('now') WHERE id = ?").run(e).changes?null:n(e)},"upsertDiscoveryResult",0,function(e){let n=(0,t.getDbInstance)(),a=e.models?JSON.stringify(e.models):null;return n.prepare(`INSERT INTO discovery_results
       (provider_id, method, endpoint, auth_type, models, rate_limit, feasibility, risk_level, status, notes)
     VALUES (@provider_id, @method, @endpoint, @auth_type, @models, @rate_limit, @feasibility, @risk_level, @status, @notes)
     ON CONFLICT(provider_id, method, endpoint) DO UPDATE SET
       auth_type = excluded.auth_type,
       models = excluded.models,
       rate_limit = excluded.rate_limit,
       feasibility = excluded.feasibility,
       risk_level = excluded.risk_level,
       status = excluded.status,
       notes = excluded.notes`).run({provider_id:e.providerId,method:e.method,endpoint:e.endpoint??null,auth_type:e.authType,models:a,rate_limit:e.rateLimit??null,feasibility:e.feasibility,risk_level:e.riskLevel,status:e.status,notes:e.notes??null}),r(n.prepare(`SELECT * FROM discovery_results
       WHERE provider_id = ? AND method = ? AND ifnull(endpoint, '') = ifnull(?, '')`).get(e.providerId,e.method,e.endpoint??null))}])},556826,e=>{"use strict";var t=e.i(830471),r=e.i(330485);let n=0;e.s(["cleanupOldSnapshots",0,function(e=90){let r=Date.now();if(r-n<216e5)return 0;let a=(0,t.getDbInstance)(),i=new Date(Date.now()-24*e*36e5).toISOString();try{let e=a.prepare("DELETE FROM quota_snapshots WHERE created_at < ?").run(i);return n=r,e.changes}catch(e){if(e?.message?.includes("no such table"))return 0;throw e}},"getAggregatedSnapshots",0,function(e){let r=(0,t.getDbInstance)(),n=["created_at >= ?"],a=[e.since];e.provider&&(n.push("provider = ?"),a.push(e.provider)),e.until&&(n.push("created_at <= ?"),a.push(e.until));let i=60*Number(e.bucketMinutes);if(!Number.isFinite(i)||i<=0)throw Error("Invalid bucket size");let s="connection"===e.aggregateBy?"bucket, provider, connection_id, window_key":"bucket, provider, window_key",o="connection"===e.aggregateBy?"provider || ':' || connection_id as provider":"provider";try{let e=`
      SELECT
        datetime((strftime('%s', created_at) / ${i}) * ${i}, 'unixepoch') as bucket,
        ${o},
        AVG(remaining_percentage) as remainingPct,
        MAX(is_exhausted) as isExhausted,
        window_key
      FROM quota_snapshots
      WHERE ${n.join(" AND ")}
      GROUP BY ${s}
      ORDER BY bucket ASC
    `;return r.prepare(e).all(...a).map(e=>({timestamp:e.bucket,provider:e.provider,remainingPct:e.remainingPct??0,isExhausted:1===e.isExhausted,windowKey:e.windowKey}))}catch(e){if(e?.message?.includes("no such table"))return[];throw e}},"getLatestQuotaSnapshotsForConnection",0,function(e){let n=(0,t.getDbInstance)();try{let t=n.prepare(`SELECT * FROM quota_snapshots
         WHERE connection_id = ?
         ORDER BY created_at DESC
         LIMIT 200`).all(e),a=new Map;for(let e of t){let t=(0,r.rowToCamel)(e),n=t.windowKey??t.window_key;!n||a.has(n)||a.set(n,t)}return[...a.values()]}catch(e){if(e?.message?.includes("no such table"))return[];throw e}},"getQuotaSnapshots",0,function(e){let n=(0,t.getDbInstance)(),a=["created_at >= ?"],i=[e.since];e.provider&&(a.push("provider = ?"),i.push(e.provider)),e.connectionId&&(a.push("connection_id = ?"),i.push(e.connectionId)),e.until&&(a.push("created_at <= ?"),i.push(e.until));try{let e=`SELECT * FROM quota_snapshots WHERE ${a.join(" AND ")} ORDER BY created_at ASC`;return n.prepare(e).all(...i).map(e=>(0,r.rowToCamel)(e))}catch(e){if(e?.message?.includes("no such table"))return[];throw e}},"saveQuotaSnapshot",0,function(e){let r=(0,t.getDbInstance)(),n=new Date().toISOString();try{r.prepare(`INSERT INTO quota_snapshots
       (provider, connection_id, window_key, remaining_percentage, is_exhausted,
        next_reset_at, window_duration_ms, raw_data, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(e.provider,e.connection_id,e.window_key,e.remaining_percentage,e.is_exhausted,e.next_reset_at,e.window_duration_ms,e.raw_data,n)}catch(e){if(e?.message?.includes("no such table"))return void console.warn("[QuotaSnapshots] Skipping save: quota_snapshots table not found. Awaiting migration.");throw e}}])},520700,e=>{"use strict";var t=e.i(995031),r=e.i(830471),n=e.i(330485),a=e.i(335273);function i(e){var t;let r=(t=(0,n.rowToCamel)(e))&&"object"==typeof t&&!Array.isArray(t)?t:{};return"string"!=typeof r.id||"string"!=typeof r.name?null:{id:r.id,name:r.name,tokenHash:"string"==typeof r.tokenHash?r.tokenHash:"",syncApiKeyId:"string"==typeof r.syncApiKeyId?r.syncApiKeyId:null,revokedAt:"string"==typeof r.revokedAt?r.revokedAt:null,lastUsedAt:"string"==typeof r.lastUsedAt?r.lastUsedAt:null,createdAt:"string"==typeof r.createdAt?r.createdAt:new Date().toISOString(),updatedAt:"string"==typeof r.updatedAt?r.updatedAt:new Date().toISOString()}}function s(e){e.exec(`
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
  `)}async function o(){let e=(0,r.getDbInstance)();return s(e),e.prepare("SELECT * FROM sync_tokens ORDER BY datetime(created_at) DESC, name COLLATE NOCASE ASC").all().map(e=>i(e)).filter(e=>null!==e)}async function l(e){let t=(0,r.getDbInstance)();return s(t),i(t.prepare("SELECT * FROM sync_tokens WHERE id = ?").get(e))}async function u(e){let t=(0,r.getDbInstance)();return s(t),i(t.prepare("SELECT * FROM sync_tokens WHERE token_hash = ?").get(e))}async function d(e){let n=(0,r.getDbInstance)();s(n);let i=new Date().toISOString(),o={id:(0,t.v4)(),name:e.name,tokenHash:e.tokenHash,syncApiKeyId:e.syncApiKeyId||null,revokedAt:null,lastUsedAt:null,createdAt:i,updatedAt:i};return n.prepare(`INSERT INTO sync_tokens (
      id, name, token_hash, sync_api_key_id, revoked_at, last_used_at, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(o.id,o.name,o.tokenHash,o.syncApiKeyId,o.revokedAt,o.lastUsedAt,o.createdAt,o.updatedAt),(0,a.backupDbFile)("pre-write"),o}async function c(e){let t=(0,r.getDbInstance)();s(t);let n=await l(e);if(!n)return null;if(n.revokedAt)return n;let i=new Date().toISOString();return t.prepare("UPDATE sync_tokens SET revoked_at = ?, updated_at = ? WHERE id = ?").run(i,i,e),(0,a.backupDbFile)("pre-write"),await l(e)}async function p(e,t=new Date().toISOString()){let n=(0,r.getDbInstance)();return s(n),Number(n.prepare("UPDATE sync_tokens SET last_used_at = ?, updated_at = ? WHERE id = ?").run(t,t,e).changes||0)>0}e.s(["createSyncTokenRecord",0,d,"getSyncTokenByHash",0,u,"getSyncTokenById",0,l,"listSyncTokens",0,o,"revokeSyncToken",0,c,"touchSyncTokenLastUsed",0,p])},675292,e=>{"use strict";var t=e.i(830471);function r(e){return e&&"object"==typeof e?e:{}}let n=["metadata.google.internal","169.254.169.254","metadata.aws.internal"];function a(e){let t=null;if(e.cliproxyapi_model_mapping&&"string"==typeof e.cliproxyapi_model_mapping)try{t=JSON.parse(e.cliproxyapi_model_mapping)}catch{t=null}return{id:e.id,providerId:e.provider_id,mode:e.mode,cliproxyapiModelMapping:t,nativePriority:e.native_priority,cliproxyapiPriority:e.cliproxyapi_priority,enabled:1===e.enabled||!0===e.enabled,family:"string"==typeof e.family?e.family:"auto",createdAt:e.created_at,updatedAt:e.updated_at}}async function i(){return(0,t.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config ORDER BY provider_id").all().map(e=>a(r(e)))}async function s(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config WHERE provider_id = ?").get(e);return n?a(r(n)):null}async function o(e){let r=(0,t.getDbInstance)(),n=e.mode??"native",a=void 0!==e.cliproxyapiModelMapping?JSON.stringify(e.cliproxyapiModelMapping):null,i=e.nativePriority??1,o=e.cliproxyapiPriority??2,l=+(!1!==e.enabled),u=e.family??"auto";return r.prepare(`INSERT INTO upstream_proxy_config
     (provider_id, mode, cliproxyapi_model_mapping, native_priority, cliproxyapi_priority, enabled, family, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
     ON CONFLICT(provider_id) DO UPDATE SET
       mode = excluded.mode,
       cliproxyapi_model_mapping = excluded.cliproxyapi_model_mapping,
       native_priority = excluded.native_priority,
       cliproxyapi_priority = excluded.cliproxyapi_priority,
       enabled = excluded.enabled,
       family = excluded.family,
       updated_at = datetime('now')`).run(e.providerId,n,a,i,o,l,u),s(e.providerId)}async function l(e,r){let n=(0,t.getDbInstance)();if(!await s(e))throw Error(`Provider ${e} not found`);let a=["updated_at = datetime('now')"],i=[];return void 0!==r.mode&&(a.push("mode = ?"),i.push(r.mode)),void 0!==r.cliproxyapiModelMapping&&(a.push("cliproxyapi_model_mapping = ?"),i.push(null===r.cliproxyapiModelMapping?null:JSON.stringify(r.cliproxyapiModelMapping))),void 0!==r.nativePriority&&(a.push("native_priority = ?"),i.push(r.nativePriority)),void 0!==r.cliproxyapiPriority&&(a.push("cliproxyapi_priority = ?"),i.push(r.cliproxyapiPriority)),void 0!==r.enabled&&(a.push("enabled = ?"),i.push(+(!0===r.enabled))),void 0!==r.family&&(a.push("family = ?"),i.push(r.family)),i.push(e),n.prepare(`UPDATE upstream_proxy_config SET ${a.join(", ")} WHERE provider_id = ?`).run(...i),s(e)}async function u(e){return(0,t.getDbInstance)().prepare("DELETE FROM upstream_proxy_config WHERE provider_id = ?").run(e).changes>0}async function d(e){return(0,t.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config WHERE mode = ? AND enabled = 1 ORDER BY provider_id").all(e).map(e=>a(r(e)))}async function c(e){let t=await s(e);if(!t)return[];let r=[];return t.enabled&&(r.push({executor:"native",priority:t.nativePriority}),("cliproxyapi"===t.mode||"fallback"===t.mode)&&r.push({executor:"cliproxyapi",priority:t.cliproxyapiPriority})),r.sort((e,t)=>e.priority-t.priority),r}e.s(["deleteUpstreamProxyConfig",0,u,"getFallbackChainForProvider",0,c,"getProvidersByMode",0,d,"getUpstreamProxyConfig",0,s,"getUpstreamProxyConfigs",0,i,"updateUpstreamProxyConfig",0,l,"upsertUpstreamProxyConfig",0,o,"validateProxyUrl",0,function(e){try{var t;let r=new URL(e);if(!["http:","https:"].includes(r.protocol))return{valid:!1,error:`Unsupported protocol "${r.protocol}" — use http or https`};if(t=r.hostname,"localhost"!==t&&"127.0.0.1"!==t&&"::1"!==t&&(n.includes(t)||/^10\./.test(t)||/^172\.(1[6-9]|2\d|3[01])\./.test(t)||/^192\.168\./.test(t)||/^0\./.test(t)||/^127\./.test(t)||/^224\./.test(t)||/^169\.254\./.test(t)||0))return{valid:!1,error:`Proxy URL cannot point to private/internal address "${r.hostname}"`};return{valid:!0,url:e}}catch{return{valid:!1,error:`Invalid URL: "${e}"`}}}])},224002,e=>{"use strict";var t=e.i(830471);let r="antigravityCreditBalance";function n(e){try{return JSON.parse(e)}catch{return null}}e.s(["getAllPersistedCreditBalances",0,function(){let e=new Map;if(t.isBuildPhase||t.isCloud)return e;for(let a of(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(r)){let t=n(a.value);t&&"number"==typeof t.balance&&e.set(a.key,t.balance)}return e},"getPersistedCreditBalance",0,function(e){if(t.isBuildPhase||t.isCloud)return null;let a=(0,t.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(r,e);if(!a?.value)return null;let i=n(a.value);return i&&"number"==typeof i.balance?i.balance:null},"persistCreditBalance",0,function(e,n){if(t.isBuildPhase||t.isCloud)return;let a=(0,t.getDbInstance)(),i={balance:n,updatedAt:new Date().toISOString()};a.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(r,e,JSON.stringify(i))}])},61499,e=>{"use strict";var t=e.i(254799),r=e.i(830471),n=e.i(335273);function a(e){return e&&"object"==typeof e?e:{}}function i(e){let t=a(e);return{id:"string"==typeof t.id?t.id:"",name:"string"==typeof t.name?t.name:"",type:"string"==typeof t.type?t.type:"http",host:"string"==typeof t.host?t.host:"",port:Number(t.port)||0,region:"string"==typeof t.region?t.region:null,notes:"string"==typeof t.notes?t.notes:null,status:"string"==typeof t.status?t.status:"active",source:"string"==typeof t.source?t.source:"oneproxy",qualityScore:"number"==typeof t.quality_score?t.quality_score:null,latencyMs:"number"==typeof t.latency_ms?t.latency_ms:null,anonymity:"string"==typeof t.anonymity?t.anonymity:null,googleAccess:1===t.google_access||!0===t.google_access,lastValidated:"string"==typeof t.last_validated?t.last_validated:null,countryCode:"string"==typeof t.country_code?t.country_code:null,createdAt:"string"==typeof t.created_at?t.created_at:"",updatedAt:"string"==typeof t.updated_at?t.updated_at:""}}async function s(e){let t=(0,r.getDbInstance)(),n="SELECT * FROM proxy_registry WHERE source = 'oneproxy' AND status = 'active'",a=[];return e?.protocol&&(n+=" AND type = ?",a.push(e.protocol)),e?.countryCode&&(n+=" AND country_code = ?",a.push(e.countryCode)),e?.minQuality!=null&&(n+=" AND quality_score >= ?",a.push(e.minQuality)),n+=" ORDER BY quality_score DESC, last_validated DESC",e?.limit&&(n+=" LIMIT ?",a.push(e.limit)),t.prepare(n).all(...a).map(i)}async function o(){let e,t=(0,r.getDbInstance)(),n={total:Number((e=a(t.prepare(`SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
        AVG(quality_score) as avg_quality,
        MAX(last_validated) as last_validated
       FROM proxy_registry WHERE source = 'oneproxy'`).get())).total)||0,active:Number(e.active)||0,avgQuality:null!==e.avg_quality&&void 0!==e.avg_quality?Math.round(100*Number(e.avg_quality))/100:null,lastValidated:"string"==typeof e.last_validated?e.last_validated:null},i=t.prepare("SELECT type as protocol, COUNT(*) as count FROM proxy_registry WHERE source = 'oneproxy' GROUP BY type ORDER BY count DESC").all(),s=t.prepare("SELECT country_code as countryCode, COUNT(*) as count FROM proxy_registry WHERE source = 'oneproxy' AND country_code IS NOT NULL GROUP BY country_code ORDER BY count DESC LIMIT 20").all();return{...n,byProtocol:i.map(e=>({protocol:String(e.protocol||"unknown"),count:Number(e.count)||0})),byCountry:s.map(e=>({countryCode:String(e.countryCode||"unknown"),count:Number(e.count)||0}))}}async function l(e){let a=(0,r.getDbInstance)(),i=new Date().toISOString(),s=`${e.protocol?.toUpperCase()||"HTTP"} - ${e.countryCode||"Unknown"} - ${e.ip}`,o=a.prepare("SELECT id FROM proxy_registry WHERE host = ? AND port = ? AND source = 'oneproxy'").get(e.ip,e.port);if(o?.id)return a.prepare(`UPDATE proxy_registry
       SET status = ?, quality_score = ?, latency_ms = ?, anonymity = ?,
           google_access = ?, last_validated = ?, country_code = ?, updated_at = ?
       WHERE id = ?`).run("active",e.qualityScore??null,e.latencyMs??null,e.anonymity??null,+!!e.googleAccess,e.lastValidated??i,e.countryCode??null,i,o.id),(0,n.backupDbFile)("pre-write"),{proxy:await u(o.id),action:"updated"};let l=(0,t.randomUUID)();return a.prepare(`INSERT INTO proxy_registry
     (id, name, type, host, port, region, notes, status, source,
      quality_score, latency_ms, anonymity, google_access, last_validated, country_code,
      created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(l,s,e.protocol||"http",e.ip,e.port,e.countryCode??null,null,"active","oneproxy",e.qualityScore??null,e.latencyMs??null,e.anonymity??null,+!!e.googleAccess,e.lastValidated??i,e.countryCode??null,i,i),(0,n.backupDbFile)("pre-write"),{proxy:await u(l),action:"created"}}async function u(e){let t=(0,r.getDbInstance)().prepare("SELECT * FROM proxy_registry WHERE id = ? AND source = 'oneproxy'").get(e);return t?i(t):null}async function d(e){let t=(0,r.getDbInstance)().prepare("DELETE FROM proxy_registry WHERE id = ? AND source = 'oneproxy'").run(e);return(0,n.backupDbFile)("pre-write"),t.changes>0}async function c(){let e=(0,r.getDbInstance)().prepare("DELETE FROM proxy_registry WHERE source = 'oneproxy'").run();return(0,n.backupDbFile)("pre-write"),e.changes}async function p(e){let t=(0,r.getDbInstance)(),n=e?.strategy||"quality",a="SELECT * FROM proxy_registry WHERE source = 'oneproxy' AND status = 'active'";switch(n){case"quality":a+=" ORDER BY quality_score DESC, latency_ms ASC LIMIT 1";break;case"random":a+=" ORDER BY RANDOM() LIMIT 1";break;case"sequential":a+=" ORDER BY last_validated ASC LIMIT 1"}let s=t.prepare(a).get();return s?i(s):null}async function E(e,t){let a=(0,r.getDbInstance)().prepare(`UPDATE proxy_registry
       SET quality_score = MAX(0, COALESCE(quality_score, 50) - 10),
           status = CASE WHEN COALESCE(quality_score, 50) <= 10 THEN 'inactive' ELSE status END,
           updated_at = datetime('now')
       WHERE host = ? AND port = ? AND source = 'oneproxy'`).run(e,t);return(0,n.backupDbFile)("pre-write"),a.changes>0}e.s(["clearAllOneproxyProxies",0,c,"deleteOneproxyProxy",0,d,"getOneproxyProxyById",0,u,"getOneproxyProxyForRotation",0,p,"getOneproxyStats",0,o,"listOneproxyProxies",0,s,"markOneproxyProxyFailed",0,E,"upsertOneproxyProxy",0,l])},639015,e=>{"use strict";var t=e.i(830471);function r(e){return{name:e.name,description:e.description,priority:e.priority,scope:"combo"===e.scope_type&&e.combo_id?{type:"combo",comboId:e.combo_id}:{type:"global"},enabled:1===e.enabled,code:e.code,createdAt:e.created_at,updatedAt:e.updated_at,runCount:e.run_count,lastError:e.last_error||void 0}}function n(e){return{name:e.name,description:e.description,priority:e.priority,scope_type:e.scope.type,combo_id:"combo"===e.scope.type?e.scope.comboId:null,enabled:+!!e.enabled,code:e.code,created_at:e.createdAt||new Date().toISOString(),updated_at:new Date().toISOString(),run_count:e.runCount||0,last_error:e.lastError}}function a(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE name = ?").get(e);return n?r(n):void 0}e.s(["cleanupHookLogs",0,function(e=1e4){return(0,t.getDbInstance)().prepare(`
    DELETE FROM middleware_logs WHERE id NOT IN (
      SELECT id FROM middleware_logs ORDER BY timestamp DESC LIMIT ?
    )
  `).run(e).changes},"createMiddlewareHook",0,function(e){let r=(0,t.getDbInstance)(),i=n(e);return i.created_at=new Date().toISOString(),i.updated_at=i.created_at,r.prepare(`
    INSERT INTO middleware_hooks (name, description, priority, scope_type, combo_id, enabled, code, created_at, updated_at, run_count, last_error)
    VALUES (@name, @description, @priority, @scope_type, @combo_id, @enabled, @code, @created_at, @updated_at, @run_count, @last_error)
  `).run(i),a(e.name)},"deleteMiddlewareHook",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM middleware_hooks WHERE name = ?").run(e).changes>0},"getAllMiddlewareHooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks ORDER BY priority ASC, name ASC").all().map(r)},"getComboMiddlewareHooks",0,function(e){return(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE enabled = 1 AND (scope_type = 'global' OR (scope_type = 'combo' AND combo_id = ?)) ORDER BY priority ASC").all(e).map(r)},"getEnabledMiddlewareHooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE enabled = 1 ORDER BY priority ASC").all().map(r)},"getHookLogs",0,function(e,r=50){let n=(0,t.getDbInstance)();return(e?n.prepare("SELECT * FROM middleware_logs WHERE hook_name = ? ORDER BY timestamp DESC LIMIT ?").all(e,r):n.prepare("SELECT * FROM middleware_logs ORDER BY timestamp DESC LIMIT ?").all(r)).map(e=>({id:e.id,hookName:e.hook_name,requestId:e.request_id,durationMs:e.duration_ms,mutated:1===e.mutated,skipped:1===e.skipped,error:e.error,timestamp:e.timestamp}))},"getMiddlewareHook",0,a,"insertHookLog",0,function(e){(0,t.getDbInstance)().prepare(`
    INSERT INTO middleware_logs (id, hook_name, request_id, duration_ms, mutated, skipped, error, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(e.id,e.hookName,e.requestId,e.durationMs,+!!e.mutated,+!!e.skipped,e.error||null,e.timestamp)},"recordHookExecution",0,function(e,r){let n=(0,t.getDbInstance)();r?n.prepare("UPDATE middleware_hooks SET run_count = run_count + 1, last_error = ?, updated_at = datetime('now') WHERE name = ?").run(r,e):n.prepare("UPDATE middleware_hooks SET run_count = run_count + 1, last_error = NULL, updated_at = datetime('now') WHERE name = ?").run(e)},"updateMiddlewareHook",0,function(e,r){let i=a(e);if(!i)return;let s=n({...i,...r,updatedAt:new Date().toISOString()});return(0,t.getDbInstance)().prepare(`
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
  `).run(s),a(e)}])},324074,e=>{"use strict";var t=e.i(666680),r=e.i(830471),n=e.i(330485);function a(e){let t=(0,r.getDbInstance)().prepare("SELECT * FROM relay_tokens WHERE id = ?").get(e);return t?{...(0,n.rowToCamel)(t),enabled:1===t.enabled}:null}e.s(["checkRateLimit",0,function(e,t){let a=(0,r.getDbInstance)(),i=t;if(!i){let t=a.prepare("SELECT * FROM relay_tokens WHERE id = ?").get(e);if(!t)return{allowed:!1,remaining:0,resetIn:0};i=(0,n.rowToCamel)(t)}let s=Math.floor(Date.now()/1e3),o=60*Math.floor(s/60),l=86400*Math.floor(s/86400),u=a.prepare("SELECT request_count, cost FROM relay_rate_limits WHERE token_id = ? AND window_start = ?").get(e,o),d=u?.request_count||0;if(d>=i.maxRequestsPerMinute)return{allowed:!1,remaining:0,resetIn:60-s%60};let c=a.prepare("SELECT SUM(request_count) as total FROM relay_rate_limits WHERE token_id = ? AND window_start >= ?").get(e,l),p=c?.total||0;return p>=i.maxRequestsPerDay?{allowed:!1,remaining:0,resetIn:86400-s%86400}:{allowed:!0,remaining:Math.min(i.maxRequestsPerMinute-d,i.maxRequestsPerDay-p),resetIn:60-s%60}},"createRelayToken",0,function(a){let i=(0,r.getDbInstance)(),s="rl_"+(0,t.randomBytes)(16).toString("hex"),o="relay_"+(0,t.randomBytes)(24).toString("hex"),l=function(t){let{createHash:r}=e.r(666680);return r("sha256").update(t).digest("hex")}(o),u=Math.floor(Date.now()/1e3),d="rl_"+o.slice(6,14);i.prepare(`
    INSERT INTO relay_tokens (id, name, token_hash, token_prefix, description, combo_id, allowed_models,
      max_tokens_per_request, max_requests_per_minute, max_requests_per_day, max_cost_per_day,
      enabled, created_at, updated_at, expires_at, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
  `).run(s,a.name,l,d,a.description||"",a.comboId||null,JSON.stringify(a.allowedModels||["*"]),a.maxTokensPerRequest||128e3,a.maxRequestsPerMinute||60,a.maxRequestsPerDay||1e4,a.maxCostPerDay||0,u,u,a.expiresAt||null,JSON.stringify(a.metadata||{}));let c=i.prepare("SELECT * FROM relay_tokens WHERE id = ?").get(s);return{...(0,n.rowToCamel)(c),rawToken:o}},"deleteRelayToken",0,function(e){(0,r.getDbInstance)().prepare("DELETE FROM relay_tokens WHERE id = ?").run(e)},"getRelayLogs",0,function(e,t=50){let n=(0,r.getDbInstance)();return e?n.prepare("SELECT * FROM relay_logs WHERE token_id = ? ORDER BY created_at DESC LIMIT ?").all(e,t):n.prepare("SELECT * FROM relay_logs ORDER BY created_at DESC LIMIT ?").all(t)},"getRelayToken",0,a,"getRelayTokenByHash",0,function(e){let t=(0,r.getDbInstance)().prepare("SELECT * FROM relay_tokens WHERE token_hash = ? AND enabled = 1").get(e);return t?{...(0,n.rowToCamel)(t),enabled:1===t.enabled}:null},"getRelayTokens",0,function(){return(0,r.getDbInstance)().prepare("SELECT * FROM relay_tokens ORDER BY created_at DESC").all().map(e=>({...(0,n.rowToCamel)(e),enabled:1===e.enabled}))},"getRelayUsage",0,function(e,t){let n=(0,r.getDbInstance)().prepare("SELECT COUNT(*) as request_count, COALESCE(SUM(cost), 0) as total_cost FROM relay_logs WHERE token_id = ? AND created_at >= ?").get(e,t);return{requestCount:n.request_count,totalCost:n.total_cost}},"recordRelayUsage",0,function(e,t){let n=(0,r.getDbInstance)(),a=Math.floor(Date.now()/1e3),i=60*Math.floor(a/60);n.prepare(`
    INSERT INTO relay_rate_limits (token_id, window_start, request_count, cost)
    VALUES (?, ?, 1, ?)
    ON CONFLICT(token_id, window_start) DO UPDATE SET
      request_count = request_count + 1,
      cost = cost + ?
  `).run(e,i,t.cost||0,t.cost||0),n.prepare("UPDATE relay_tokens SET last_used_at = ? WHERE id = ?").run(a,e),n.prepare(`
    INSERT INTO relay_logs (token_id, request_id, model, prompt_tokens, completion_tokens, cost,
      status, status_code, latency_ms, client_ip, user_agent, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(e,t.requestId||null,t.model||null,t.promptTokens||0,t.completionTokens||0,t.cost||0,t.status||"success",t.statusCode||200,t.latencyMs||0,t.clientIp||null,t.userAgent||null,a)},"toggleRelayToken",0,function(e,t){let n=(0,r.getDbInstance)(),i=Math.floor(Date.now()/1e3);return n.prepare("UPDATE relay_tokens SET enabled = ?, updated_at = ? WHERE id = ?").run(+!!t,i,e),a(e)},"updateRelayToken",0,function(e,t){let n=(0,r.getDbInstance)(),i=Math.floor(Date.now()/1e3),s=["updated_at = ?"],o=[i];return void 0!==t.name&&(s.push("name = ?"),o.push(t.name)),void 0!==t.description&&(s.push("description = ?"),o.push(t.description)),void 0!==t.comboId&&(s.push("combo_id = ?"),o.push(t.comboId)),void 0!==t.allowedModels&&(s.push("allowed_models = ?"),o.push(JSON.stringify(t.allowedModels))),void 0!==t.maxTokensPerRequest&&(s.push("max_tokens_per_request = ?"),o.push(t.maxTokensPerRequest)),void 0!==t.maxRequestsPerMinute&&(s.push("max_requests_per_minute = ?"),o.push(t.maxRequestsPerMinute)),void 0!==t.maxRequestsPerDay&&(s.push("max_requests_per_day = ?"),o.push(t.maxRequestsPerDay)),void 0!==t.maxCostPerDay&&(s.push("max_cost_per_day = ?"),o.push(t.maxCostPerDay)),o.push(e),n.prepare(`UPDATE relay_tokens SET ${s.join(", ")} WHERE id = ?`).run(...o),a(e)}])},169730,e=>{"use strict";var t=e.i(254799),r=e.i(830471),n=e.i(335273);function a(e){return{id:String(e.id??""),source:String(e.source??"1proxy"),host:String(e.host??""),port:Number(e.port)||0,type:String(e.type??"http"),countryCode:null!=e.country_code?String(e.country_code):null,qualityScore:null!=e.quality_score?Number(e.quality_score):null,latencyMs:null!=e.latency_ms?Number(e.latency_ms):null,anonymity:null!=e.anonymity?String(e.anonymity):null,lastValidated:null!=e.last_validated?String(e.last_validated):null,inPool:1===e.in_pool||!0===e.in_pool,poolProxyId:null!=e.pool_proxy_id?String(e.pool_proxy_id):null,createdAt:String(e.created_at??""),updatedAt:String(e.updated_at??"")}}async function i(e){let n=(0,r.getDbInstance)(),a=new Date().toISOString(),i=n.prepare("SELECT id FROM free_proxies WHERE source = ? AND host = ? AND port = ?").get(e.source,e.host,e.port);if(i?.id)return n.prepare(`UPDATE free_proxies
       SET type = ?, country_code = ?, quality_score = ?, latency_ms = ?,
           anonymity = ?, last_validated = ?, updated_at = ?
       WHERE id = ?`).run(e.type,e.countryCode??null,e.qualityScore??null,e.latencyMs??null,e.anonymity??null,e.lastValidated??a,a,i.id),{id:i.id,action:"updated"};let s=(0,t.randomUUID)();return n.prepare(`INSERT INTO free_proxies
     (id, source, host, port, type, country_code, quality_score, latency_ms,
      anonymity, last_validated, in_pool, pool_proxy_id, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)`).run(s,e.source,e.host,e.port,e.type,e.countryCode??null,e.qualityScore??null,e.latencyMs??null,e.anonymity??null,e.lastValidated??a,a,a),{id:s,action:"created"}}async function s(e){let t=(0,r.getDbInstance)(),n=[],i="SELECT * FROM free_proxies WHERE 1=1";e?.sources?.length&&(i+=` AND source IN (${e.sources.map(()=>"?").join(",")})`,n.push(...e.sources)),e?.protocol&&(i+=" AND type = ?",n.push(e.protocol)),e?.country&&(i+=" AND country_code = ?",n.push(e.country.toUpperCase())),e?.minQuality!=null&&(i+=" AND quality_score >= ?",n.push(e.minQuality)),e?.onlyInPool&&(i+=" AND in_pool = 1"),e?.onlyNotInPool&&(i+=" AND in_pool = 0"),e?.search&&(i+=" AND host LIKE ?",n.push(`%${e.search}%`));let s=e?.sortBy==="latency"?"ORDER BY latency_ms IS NULL, latency_ms ASC":e?.sortBy==="recent"?"ORDER BY last_validated DESC":"ORDER BY quality_score DESC, last_validated DESC";return i+=` ${s}`,e?.limit&&(i+=" LIMIT ?",n.push(e.limit),e?.offset&&(i+=" OFFSET ?",n.push(e.offset))),t.prepare(i).all(...n).map(a)}async function o(e){let t=(0,r.getDbInstance)(),n=[],a="SELECT COUNT(*) AS count FROM free_proxies WHERE 1=1";e?.sources?.length&&(a+=` AND source IN (${e.sources.map(()=>"?").join(",")})`,n.push(...e.sources)),e?.protocol&&(a+=" AND type = ?",n.push(e.protocol)),e?.country&&(a+=" AND country_code = ?",n.push(e.country.toUpperCase())),e?.minQuality!=null&&(a+=" AND quality_score >= ?",n.push(e.minQuality)),e?.onlyInPool&&(a+=" AND in_pool = 1"),e?.onlyNotInPool&&(a+=" AND in_pool = 0"),e?.search&&(a+=" AND host LIKE ?",n.push(`%${e.search}%`));let i=t.prepare(a).get(...n),s=i?.count;return"number"==typeof s?s:Number(s??0)}async function l(e,t){return(await s({sources:[e],protocol:t.protocol,country:t.country,minQuality:t.minQuality,limit:t.limit})).map(e=>({source:e.source,host:e.host,port:e.port,type:e.type,countryCode:e.countryCode,qualityScore:e.qualityScore,latencyMs:e.latencyMs,anonymity:e.anonymity,lastValidated:e.lastValidated}))}async function u(e){let t=(0,r.getDbInstance)().prepare("SELECT * FROM free_proxies WHERE id = ?").get(e);return t?a(t):null}async function d(e,t){let a=(0,r.getDbInstance)(),i=new Date().toISOString();a.prepare("UPDATE free_proxies SET in_pool = 1, pool_proxy_id = ?, updated_at = ? WHERE id = ?").run(t,i,e),(0,n.backupDbFile)("pre-write")}async function c(e,a){let i=(0,r.getDbInstance)(),s=new Date().toISOString(),o=(0,t.randomUUID)(),l=i.transaction(()=>{let t=i.prepare("SELECT id, in_pool FROM free_proxies WHERE id = ? LIMIT 1").get(e);return t?.id?(i.prepare(`INSERT INTO proxy_registry
        (id, name, type, host, port, username, password, region, notes, status, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, '', '', NULL, NULL, 'active', ?, ?, ?)`).run(o,a.name,a.type,a.host,Number(a.port),a.source,s,s),i.prepare("UPDATE free_proxies SET in_pool = 1, pool_proxy_id = ?, updated_at = ? WHERE id = ?").run(o,s,e),o):null})();return l&&(0,n.backupDbFile)("pre-write"),l}async function p(e){let t=(0,r.getDbInstance)().prepare("DELETE FROM free_proxies WHERE id = ?").run(e);return(0,n.backupDbFile)("pre-write"),t.changes>0}async function E(e){let t=(0,r.getDbInstance)().prepare("DELETE FROM free_proxies WHERE source = ? AND in_pool = 0").run(e);return(0,n.backupDbFile)("pre-write"),t.changes}async function _(e,t){let a=(0,r.getDbInstance)(),i=a.prepare("SELECT id, host, port FROM free_proxies WHERE source = ? AND in_pool = 0").all(e).filter(e=>!t.has(`${e.host}:${e.port}`)).map(e=>e.id);if(0===i.length)return 0;let s=i.map(()=>"?").join(","),o=a.prepare(`DELETE FROM free_proxies WHERE id IN (${s})`).run(...i);return(0,n.backupDbFile)("pre-write"),o.changes}let m="free_proxies",y="last_sync_at";async function g(e){let t=(0,r.getDbInstance)(),a=e??new Date().toISOString();return t.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(m,y,a),(0,n.backupDbFile)("pre-write"),a}async function S(){let e,t=(0,r.getDbInstance)(),n=t.prepare(`SELECT COUNT(*) as total,
              SUM(CASE WHEN in_pool = 1 THEN 1 ELSE 0 END) as in_pool_count,
              AVG(quality_score) as avg_quality,
              MAX(last_validated) as last_sync_at
       FROM free_proxies`).get(),a=t.prepare("SELECT source, COUNT(*) as count FROM free_proxies GROUP BY source ORDER BY count DESC").all(),i=(e=t.prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(m,y),e?.value!=null?String(e.value):null),s=null!=n.last_sync_at?String(n.last_sync_at):null;return{total:Number(n.total)||0,inPool:Number(n.in_pool_count)||0,avgQuality:null!=n.avg_quality?Math.round(Number(n.avg_quality)):null,bySource:a.map(e=>({source:String(e.source),count:Number(e.count)})),lastSyncAt:i??s}}async function T(e,t){let a=(0,r.getDbInstance)(),i=new Date().toISOString();a.prepare("INSERT OR REPLACE INTO free_proxy_sync_errors (source, errors, updated_at) VALUES (?, ?, ?)").run(e,JSON.stringify(t),i),(0,n.backupDbFile)("pre-write")}async function R(e){(0,r.getDbInstance)().prepare("DELETE FROM free_proxy_sync_errors WHERE source = ?").run(e),(0,n.backupDbFile)("pre-write")}async function f(){let e=(0,r.getDbInstance)().prepare("SELECT source, errors FROM free_proxy_sync_errors").all(),t={};for(let r of e)if(r.source)try{let e=JSON.parse(r.errors);t[r.source]=Array.isArray(e)?e.map(String):[String(r.errors)]}catch{t[r.source]=[String(r.errors)]}return t}e.s(["clearFreeProxiesBySource",0,E,"clearFreeProxySyncErrors",0,R,"countFreeProxies",0,o,"deleteFreeProxy",0,p,"getFreeProxyById",0,u,"getFreeProxyStats",0,S,"getFreeProxySyncErrors",0,f,"listFreeProxies",0,s,"listFreeProxiesBySource",0,l,"markFreeProxyInPool",0,d,"promoteFreeProxyToPool",0,c,"pruneStaleFreeProxies",0,_,"recordFreeProxySync",0,g,"recordFreeProxySyncErrors",0,T,"upsertFreeProxy",0,i])},767382,e=>{"use strict";var t=e.i(830471),r=e.i(666680);function n(e){let t={};try{let r=JSON.parse(e.params_json);null===r||"object"!=typeof r||Array.isArray(r)||(t=r)}catch{t={}}return{id:e.id,name:e.name,endpoint:e.endpoint,model:e.model,system:e.system,params:t,created_at:e.created_at}}function a(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM playground_presets WHERE id = ? LIMIT 1").get(e);return r?n(r):null}e.s(["createPlaygroundPreset",0,function(e){let n=(0,t.getDbInstance)(),i=(0,r.randomUUID)(),s=JSON.stringify(e.params??{}),o=e.system??null;return n.prepare("INSERT INTO playground_presets (id, name, endpoint, model, system, params_json) VALUES (?, ?, ?, ?, ?, ?)").run(i,e.name,e.endpoint,e.model,o,s),a(i)},"deletePlaygroundPreset",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM playground_presets WHERE id = ?").run(e).changes>0},"getPlaygroundPreset",0,a,"listPlaygroundPresets",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM playground_presets ORDER BY created_at DESC").all().map(n)},"updatePlaygroundPreset",0,function(e,r){let n=(0,t.getDbInstance)(),i=a(e);if(!i)return null;let s=[],o=[];return(void 0!==r.name&&(s.push("name = ?"),o.push(r.name)),void 0!==r.endpoint&&(s.push("endpoint = ?"),o.push(r.endpoint)),void 0!==r.model&&(s.push("model = ?"),o.push(r.model)),"system"in r&&(s.push("system = ?"),o.push(r.system??null)),void 0!==r.params&&(s.push("params_json = ?"),o.push(JSON.stringify(r.params))),0===s.length)?i:(o.push(e),n.prepare(`UPDATE playground_presets SET ${s.join(", ")} WHERE id = ?`).run(...o),a(e))}])},697387,e=>{"use strict";var t=e.i(830471);function r(){let e=(0,t.getDbInstance)().prepare("SELECT active_dim, embedding_signature, last_reset_at, vec_loaded FROM memory_vec_meta WHERE id = 1").get();return e?{activeDim:e.active_dim,embeddingSignature:e.embedding_signature,lastResetAt:e.last_reset_at,vecLoaded:1===e.vec_loaded}:{activeDim:null,embeddingSignature:null,lastResetAt:null,vecLoaded:!1}}e.s(["countMemoryReindexPending",0,function(){return(0,t.getDbInstance)().prepare("SELECT COUNT(*) AS cnt FROM memories WHERE needs_reindex = 1").get().cnt},"getMemoryReindexQueue",0,function(e){return(0,t.getDbInstance)().prepare(`SELECT id, content, COALESCE(key, '') AS key
       FROM memories
       WHERE needs_reindex = 1
       ORDER BY created_at ASC
       LIMIT ?`).all(e)},"getMemoryVecMeta",0,r,"markAllMemoriesNeedReindex",0,function(){return(0,t.getDbInstance)().prepare("UPDATE memories SET needs_reindex = 1").run().changes},"markMemoryNeedsReindex",0,function(e,r){(0,t.getDbInstance)().prepare("UPDATE memories SET needs_reindex = ? WHERE id = ?").run(+!!r,e)},"setMemoryVecMeta",0,function(e){let n=(0,t.getDbInstance)(),a=r(),i="activeDim"in e?e.activeDim??null:a.activeDim,s="embeddingSignature"in e?e.embeddingSignature??null:a.embeddingSignature,o="lastResetAt"in e?e.lastResetAt??null:a.lastResetAt,l="vecLoaded"in e?+!!e.vecLoaded:+!!a.vecLoaded;n.prepare(`INSERT OR REPLACE INTO memory_vec_meta
       (id, active_dim, embedding_signature, last_reset_at, vec_loaded)
     VALUES (1, ?, ?, ?, ?)`).run(i,s,o,l)}])},326151,e=>{"use strict";var t=e.i(830471);function r(e){return{agent_id:e.agent_id,dns_enabled:1===e.dns_enabled,cert_trusted:1===e.cert_trusted,setup_completed:1===e.setup_completed,last_started_at:e.last_started_at,last_error:e.last_error}}function n(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM agent_bridge_state WHERE agent_id = ?").get(e);return n?r(n):null}e.s(["getAgentBridgeState",0,n,"getAllAgentBridgeStates",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM agent_bridge_state ORDER BY agent_id ASC").all().map(r)},"setLastError",0,function(e,r){(0,t.getDbInstance)().prepare(`INSERT INTO agent_bridge_state (agent_id, last_error)
     VALUES (?, ?)
     ON CONFLICT(agent_id) DO UPDATE SET last_error = excluded.last_error`).run(e,r)},"setLastStarted",0,function(e,r){(0,t.getDbInstance)().prepare(`INSERT INTO agent_bridge_state (agent_id, last_started_at)
     VALUES (?, ?)
     ON CONFLICT(agent_id) DO UPDATE SET last_started_at = excluded.last_started_at`).run(e,r)},"upsertAgentBridgeState",0,function(e){let r=(0,t.getDbInstance)();if(n(e.agent_id)){let t=[],n=[];if(void 0!==e.dns_enabled&&(t.push("dns_enabled = ?"),n.push(+!!e.dns_enabled)),void 0!==e.cert_trusted&&(t.push("cert_trusted = ?"),n.push(+!!e.cert_trusted)),void 0!==e.setup_completed&&(t.push("setup_completed = ?"),n.push(+!!e.setup_completed)),void 0!==e.last_started_at&&(t.push("last_started_at = ?"),n.push(e.last_started_at)),void 0!==e.last_error&&(t.push("last_error = ?"),n.push(e.last_error)),0===t.length)return;n.push(e.agent_id),r.prepare(`UPDATE agent_bridge_state SET ${t.join(", ")} WHERE agent_id = ?`).run(...n)}else r.prepare(`INSERT INTO agent_bridge_state
         (agent_id, dns_enabled, cert_trusted, setup_completed, last_started_at, last_error)
       VALUES (?, ?, ?, ?, ?, ?)`).run(e.agent_id,void 0!==e.dns_enabled?+!!e.dns_enabled:0,void 0!==e.cert_trusted?+!!e.cert_trusted:0,void 0!==e.setup_completed?+!!e.setup_completed:0,e.last_started_at??null,e.last_error??null)}])},758677,e=>{"use strict";var t=e.i(830471);e.s(["deleteMapping",0,function(e,r){(0,t.getDbInstance)().prepare("DELETE FROM agent_bridge_mappings WHERE agent_id = ? AND source_model = ?").run(e,r)},"getMappingsForAgent",0,function(e){return(0,t.getDbInstance)().prepare("SELECT agent_id, source_model, target_model, updated_at FROM agent_bridge_mappings WHERE agent_id = ? ORDER BY source_model ASC").all(e)},"setMappings",0,function(e,r){let n=(0,t.getDbInstance)(),a=new Date().toISOString(),i=n.prepare("DELETE FROM agent_bridge_mappings WHERE agent_id = ?"),s=n.prepare(`INSERT INTO agent_bridge_mappings (agent_id, source_model, target_model, updated_at)
     VALUES (?, ?, ?, ?)`);n.transaction(()=>{for(let t of(i.run(e),r))s.run(e,t.source,t.target,a)})()}])},452415,e=>{"use strict";var t=e.i(830471);function r(e){return{pattern:e.pattern,source:e.source,created_at:e.created_at}}e.s(["getAllBypassPatterns",0,function(){return(0,t.getDbInstance)().prepare("SELECT pattern, source, created_at FROM agent_bridge_bypass ORDER BY source ASC, pattern ASC").all().map(r)},"getUserBypassPatterns",0,function(){return(0,t.getDbInstance)().prepare("SELECT pattern FROM agent_bridge_bypass WHERE source = 'user' ORDER BY pattern ASC").all().map(e=>e.pattern)},"replaceUserBypassPatterns",0,function(e){let r=(0,t.getDbInstance)(),n=new Date().toISOString(),a=r.prepare("DELETE FROM agent_bridge_bypass WHERE source = 'user'"),i=r.prepare("INSERT INTO agent_bridge_bypass (pattern, source, created_at) VALUES (?, 'user', ?)");r.transaction(()=>{for(let t of(a.run(),e))i.run(t,n)})()},"seedDefaultBypassPatterns",0,function(e){let r=(0,t.getDbInstance)(),n=new Date().toISOString(),a=r.prepare("INSERT OR IGNORE INTO agent_bridge_bypass (pattern, source, created_at) VALUES (?, 'default', ?)");r.transaction(()=>{for(let t of e)a.run(t,n)})()}])},339176,e=>{"use strict";var t=e.i(830471);function r(e){return{host:e.host,enabled:1===e.enabled,label:e.label,kind:e.kind,added_at:e.added_at,last_seen_at:e.last_seen_at}}e.s(["addCustomHost",0,function(e,r="custom",n){let a=(0,t.getDbInstance)(),i=new Date().toISOString();a.prepare(`INSERT OR IGNORE INTO inspector_custom_hosts (host, enabled, label, kind, added_at)
     VALUES (?, 1, ?, ?, ?)`).run(e,n??null,r,i)},"isCustomHost",0,function(e){return void 0!==(0,t.getDbInstance)().prepare("SELECT 1 AS found FROM inspector_custom_hosts WHERE host = ? AND enabled = 1").get(e)},"listCustomHosts",0,function(e){let n=(0,t.getDbInstance)();return(e?.enabledOnly===!0?n.prepare("SELECT * FROM inspector_custom_hosts WHERE enabled = 1 ORDER BY host ASC").all():n.prepare("SELECT * FROM inspector_custom_hosts ORDER BY host ASC").all()).map(r)},"removeCustomHost",0,function(e){(0,t.getDbInstance)().prepare("DELETE FROM inspector_custom_hosts WHERE host = ?").run(e)},"toggleCustomHost",0,function(e,r){(0,t.getDbInstance)().prepare("UPDATE inspector_custom_hosts SET enabled = ? WHERE host = ?").run(+!!r,e)},"touchLastSeen",0,function(e){let r=(0,t.getDbInstance)(),n=new Date().toISOString();r.prepare("UPDATE inspector_custom_hosts SET last_seen_at = ? WHERE host = ?").run(n,e)}])},942598,e=>e.a(async(t,r)=>{try{var n=e.i(677850),a=t([n]);[n]=a.then?(await a)():a;let i=n.z.object({id:n.z.string().uuid(),source:n.z.enum(["agent-bridge","custom-host","http-proxy","system-proxy","tproxy"]),agent:n.z.string().optional(),timestamp:n.z.string().datetime(),method:n.z.string(),host:n.z.string(),path:n.z.string(),requestHeaders:n.z.record(n.z.string(),n.z.string()),requestBody:n.z.string().nullable(),requestSize:n.z.number().int().nonnegative(),responseHeaders:n.z.record(n.z.string(),n.z.string()),responseBody:n.z.string().nullable(),responseSize:n.z.number().int().nonnegative(),status:n.z.union([n.z.number().int(),n.z.literal("in-flight"),n.z.literal("error")]),proxyLatencyMs:n.z.number().nonnegative().optional(),upstreamLatencyMs:n.z.number().nonnegative().optional(),totalLatencyMs:n.z.number().nonnegative().optional(),error:n.z.string().optional(),sourceModel:n.z.string().nullable().optional(),mappedModel:n.z.string().nullable().optional(),detectedKind:n.z.enum(["llm","app","unknown"]).optional(),contextKey:n.z.string().optional(),annotation:n.z.string().optional(),sessionId:n.z.string().uuid().optional(),note:n.z.string().optional(),pid:n.z.number().int().nonnegative().optional(),processName:n.z.string().optional()});e.s(["InterceptedRequestSchema",0,i]),r()}catch(e){r(e)}},!1),839713,e=>e.a(async(t,r)=>{try{var n=e.i(254799),a=e.i(830471),i=e.i(942598),s=t([i]);function o(e){return{id:e.id,name:e.name,started_at:e.started_at,ended_at:e.ended_at,request_count:e.request_count,profile:e.profile}}function l(e){let t=(0,a.getDbInstance)().prepare("SELECT * FROM inspector_sessions WHERE id = ?").get(e);return t?o(t):null}function u(e){return(0,a.getDbInstance)().prepare("SELECT seq, payload FROM inspector_session_requests WHERE session_id = ? ORDER BY seq ASC").all(e).map(e=>({seq:e.seq,payload:e.payload}))}[i]=s.then?(await s)():s,e.s(["appendSessionRequest",0,function(e,t){let r=(0,a.getDbInstance)(),n=0;return r.transaction(()=>{let a=r.prepare("SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM inspector_session_requests WHERE session_id = ?").get(e).next_seq;r.prepare("INSERT INTO inspector_session_requests (session_id, seq, payload) VALUES (?, ?, ?)").run(e,a,t),r.prepare("UPDATE inspector_sessions SET request_count = request_count + 1 WHERE id = ?").run(e),n=a})(),n},"createSession",0,function(e){let t=(0,a.getDbInstance)(),r=(0,n.randomUUID)(),i=new Date().toISOString();return t.prepare("INSERT INTO inspector_sessions (id, name, started_at, profile) VALUES (?, ?, ?, ?)").run(r,e?.name??null,i,e?.profile??null),{id:r,started_at:i}},"deleteSession",0,function(e){(0,a.getDbInstance)().prepare("DELETE FROM inspector_sessions WHERE id = ?").run(e)},"getSession",0,l,"getSessionRequests",0,u,"listSessions",0,function(){return(0,a.getDbInstance)().prepare("SELECT * FROM inspector_sessions ORDER BY started_at DESC").all().map(o)},"renameSession",0,function(e,t){(0,a.getDbInstance)().prepare("UPDATE inspector_sessions SET name = ? WHERE id = ?").run(t,e)},"snapshotSession",0,function(e){let t=l(e);if(null===t)return null;let r=u(e),n=[];for(let e of r){let t;try{t=JSON.parse(e.payload)}catch{continue}let r=i.InterceptedRequestSchema.safeParse(t);r.success&&n.push(r.data)}return n},"stopSession",0,function(e){let t=(0,a.getDbInstance)(),r=new Date().toISOString();t.prepare("UPDATE inspector_sessions SET ended_at = ? WHERE id = ?").run(r,e)}]),r()}catch(e){r(e)}},!1),896326,e=>{"use strict";var t=e.i(446786),r=e.i(814747),n=e.i(785148);let a=()=>r.default.join(r.default.join(t.default.homedir(),".omp","agent"),"agent.db");e.s(["deleteOmpCredentials",0,function(e){let t=a(),r=new n.default(t);r.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(e),r.close()},"getOmpCredentials",0,function(e){let t=a();try{let r=new n.default(t,{readonly:!0}),a=r.prepare("SELECT data FROM auth_credentials WHERE provider = ? AND credential_type = 'api_key'").get(e);if(r.close(),a?.data){let e=JSON.parse(a.data);return{hasOmniRoute:!0,baseUrl:e.baseUrl||null,apiKey:e.apiKey||null}}return{hasOmniRoute:!1,baseUrl:null,apiKey:null}}catch{return{hasOmniRoute:!1,baseUrl:null,apiKey:null}}},"saveOmpCredentials",0,function(e,t,r){let i=a(),s=new n.default(i);s.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(e),s.prepare("INSERT INTO auth_credentials (provider, credential_type, data, disabled_cause, identity_key, created_at, updated_at) VALUES (?, ?, ?, NULL, NULL, ?, ?)").run(e,"api_key",JSON.stringify({apiKey:t,baseUrl:r}),Math.floor(Date.now()/1e3),Math.floor(Date.now()/1e3)),s.close()}])},160769,e=>{"use strict";var t=e.i(830471);function r(e){return{poolId:e.pool_id,apiKeyId:e.api_key_id,model:e.model,capValue:e.cap_value,capUnit:e.cap_unit}}function n(){return(0,t.getDbInstance)()}e.s(["deleteModelCap",0,function(e,t,r){n().prepare(`DELETE FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ? AND model = ?`).run(e,t,r)},"getModelCap",0,function(e,t,a){let i=n().prepare(`SELECT pool_id, api_key_id, model, cap_value, cap_unit
       FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ? AND model = ?`).get(e,t,a);return i?r(i):null},"listModelCaps",0,function(e,t){return n().prepare(`SELECT pool_id, api_key_id, model, cap_value, cap_unit
       FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ?`).all(e,t).map(r)},"setModelCap",0,function(e){n().prepare(`INSERT INTO quota_allocation_model_caps
         (pool_id, api_key_id, model, cap_value, cap_unit)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(pool_id, api_key_id, model) DO UPDATE SET
         cap_value = excluded.cap_value,
         cap_unit  = excluded.cap_unit`).run(e.poolId,e.apiKeyId,e.model,e.capValue,e.capUnit)}])},913184,e=>{"use strict";var t=e.i(830471);function r(){return(0,t.getDbInstance)()}e.s(["gcOlderThan",0,function(e){return r().prepare("DELETE FROM quota_consumption WHERE updated_at < ?").run(e).changes},"getBucket",0,function(e,t,n){let a=r().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(e,t,n);return a?.consumed??0},"getPair",0,function(e,t,n){let a=r().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(e,t,n),i=r().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(e,t,n-1);return{curr:a?.consumed??0,prev:i?.consumed??0}},"incrementBucket",0,function(e,t,n,a,i){r().prepare(`INSERT INTO quota_consumption (api_key_id, dimension_key, bucket_index, consumed, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(api_key_id, dimension_key, bucket_index)
       DO UPDATE SET
         consumed = consumed + excluded.consumed,
         updated_at = excluded.updated_at`).run(e,t,n,a,i)},"sumPoolDimension",0,function(e,t){let n=r().prepare(`SELECT COALESCE(SUM(consumed), 0) AS total
       FROM quota_consumption
       WHERE dimension_key = ? AND bucket_index = ?`).get(e,t),a=r().prepare(`SELECT COALESCE(SUM(consumed), 0) AS total
       FROM quota_consumption
       WHERE dimension_key = ? AND bucket_index = ?`).get(e,t-1);return{currTotal:n?.total??0,prevTotal:a?.total??0}}])},954147,e=>{"use strict";var t=e.i(830471);function r(){return(0,t.getDbInstance)()}function n(e){let t=[];try{t=JSON.parse(e.dimensions_json)}catch{t=[]}return{connectionId:e.connection_id,provider:e.provider,dimensions:t,source:e.source}}e.s(["deletePlan",0,function(e){return r().prepare("DELETE FROM provider_plans WHERE connection_id = ?").run(e).changes>0},"getPlan",0,function(e){let t=r().prepare(`SELECT connection_id, provider, dimensions_json, source, updated_at
       FROM provider_plans WHERE connection_id = ?`).get(e);return t?n(t):null},"listPlans",0,function(){return r().prepare(`SELECT connection_id, provider, dimensions_json, source, updated_at
       FROM provider_plans ORDER BY provider ASC`).all().map(n)},"upsertPlan",0,function(e,t,n,a){let i=new Date().toISOString(),s=JSON.stringify(n);r().prepare(`INSERT INTO provider_plans (connection_id, provider, dimensions_json, source, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(connection_id)
       DO UPDATE SET
         provider = excluded.provider,
         dimensions_json = excluded.dimensions_json,
         source = excluded.source,
         updated_at = excluded.updated_at`).run(e,t,s,a,i)}])},10947,e=>{"use strict";var t=e.i(991110),r=e.i(471801);let n=new Set(["daily","weekly","monthly"]),a=/^(\d{2}):(\d{2})$/,i=new Map;function s(e,t=0){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let r=Number(e);return Number.isFinite(r)?r:t}return t}function o(e){if("string"==typeof e){let t=e.trim().match(a);if(t){let e=Math.min(Math.max(parseInt(t[1],10),0),23),r=Math.min(Math.max(parseInt(t[2],10),0),59);return`${String(e).padStart(2,"0")}:${String(r).padStart(2,"0")}`}}return"00:00"}function l(e){let t=s(e,NaN);return Number.isFinite(t)&&t>0?t:null}function u(e,t,r,n,a){return Date.UTC(e,t,r,n,a,0,0)}function d(e,t="00:00",r=Date.now()){let n,i=new Date(r),[s,l]=(n=o(t).match(a))?[parseInt(n[1],10),parseInt(n[2],10)]:[0,0],c=i.getUTCFullYear(),p=i.getUTCMonth(),E=i.getUTCDate();if("weekly"===e){let e=(i.getUTCDay()+6)%7,t=u(c,p,E-e,s,l);return r>=t?{periodStartAt:t,nextResetAt:u(c,p,E-e+7,s,l)}:{periodStartAt:u(c,p,E-e-7,s,l),nextResetAt:t}}if("monthly"===e){let e=u(c,p,1,s,l);return r>=e?{periodStartAt:e,nextResetAt:u(c,p+1,1,s,l)}:{periodStartAt:u(c,p-1,1,s,l),nextResetAt:e}}let _=u(c,p,E,s,l);return r>=_?{periodStartAt:_,nextResetAt:u(c,p,E+1,s,l)}:{periodStartAt:u(c,p,E-1,s,l),nextResetAt:_}}function c(e,a,u=Date.now(),p={}){let E={dailyLimitUsd:Math.max(0,s(a.dailyLimitUsd)),weeklyLimitUsd:Math.max(0,s(a.weeklyLimitUsd)),monthlyLimitUsd:Math.max(0,s(a.monthlyLimitUsd)),warningThreshold:Math.min(Math.max(s(a.warningThreshold,.8),0),1),resetInterval:function(e){if("string"==typeof e){let t=e.trim().toLowerCase();if(n.has(t))return t}return"daily"}(a.resetInterval),resetTime:o(a.resetTime),budgetResetAt:l(a.budgetResetAt),lastBudgetResetAt:l(a.lastBudgetResetAt),warningEmittedAt:l(a.warningEmittedAt),warningPeriodStart:l(a.warningPeriodStart)},_=d(E.resetInterval,E.resetTime,u),m=null!==E.lastBudgetResetAt&&_.periodStartAt>E.lastBudgetResetAt;if(m&&!1!==p.logReset){let n=function(e,n,a){try{return(function(e){if(!Array.isArray(e))return[];let t=[];for(let r of e){if(!r||"object"!=typeof r||Array.isArray(r))continue;let e=s(r.cost,NaN),n=s(r.timestamp,NaN);Number.isFinite(e)&&Number.isFinite(n)&&t.push({cost:e,timestamp:n})}return t})((0,t.loadCostEntriesInRange)(e,n,a)).reduce((e,t)=>e+t.cost,0)+r.spendBatchWriter.getPendingCostTotal(e,n,a)}catch{return 0}}(e,E.lastBudgetResetAt,_.periodStartAt);try{(0,t.saveBudgetResetLog)({apiKeyId:e,resetInterval:E.resetInterval,previousSpend:n,resetAt:_.periodStartAt,nextResetAt:_.nextResetAt,periodStart:_.periodStartAt,periodEnd:_.nextResetAt})}catch{}}let y={...E,budgetResetAt:_.nextResetAt,lastBudgetResetAt:_.periodStartAt,warningEmittedAt:m?null:E.warningEmittedAt,warningPeriodStart:m?null:E.warningPeriodStart};if((E.budgetResetAt!==y.budgetResetAt||E.lastBudgetResetAt!==y.lastBudgetResetAt||E.warningEmittedAt!==y.warningEmittedAt||E.warningPeriodStart!==y.warningPeriodStart||E.dailyLimitUsd!==y.dailyLimitUsd||E.weeklyLimitUsd!==y.weeklyLimitUsd||E.monthlyLimitUsd!==y.monthlyLimitUsd||E.warningThreshold!==y.warningThreshold||E.resetInterval!==y.resetInterval||E.resetTime!==y.resetTime)&&!1!==p.persist)try{(0,t.saveBudget)(e,y)}catch{}return i.set(e,y),y}e.s(["checkBudget",0,function(e,n=0){var a;let s=function(e){let r=i.get(e);if(r)return c(e,r);try{let r=(0,t.loadBudget)(e);if(r)return c(e,r)}catch{}return null}(e);if(!s)return{allowed:!0,dailyUsed:0,dailyLimit:0,warningReached:!1,remaining:0,periodUsed:0,activeLimitUsd:0,resetInterval:null,resetTime:null,budgetResetAt:null,lastBudgetResetAt:null,periodStartAt:null};let o=d(s.resetInterval,s.resetTime),l=function(e,n){try{return(0,t.loadCostTotal)(e,n)+r.spendBatchWriter.getPendingCostTotal(e,n)}catch{return 0}}(e,o.periodStartAt),u=l+n,p="monthly"===s.resetInterval?s.monthlyLimitUsd>0?s.monthlyLimitUsd:s.dailyLimitUsd:"weekly"===s.resetInterval&&s.weeklyLimitUsd>0?s.weeklyLimitUsd:s.dailyLimitUsd,E=p>0&&u>=p*s.warningThreshold,_=Math.max(p-u,0);if(E&&s.warningPeriodStart!==o.periodStartAt){let r={...s,warningEmittedAt:Date.now(),warningPeriodStart:o.periodStartAt};i.set(e,r);try{let n;(0,t.saveBudget)(e,r),a=o.nextResetAt,n=p>0?(u/p*100).toFixed(1):"0.0",console.warn(`[BudgetWarning] ${e} reached ${n}% of ${r.resetInterval} budget ($${u.toFixed(4)} / $${p.toFixed(2)}) — next reset ${new Date(a).toISOString()}`)}catch{}}return p>0&&u>p?{allowed:!1,reason:`${s.resetInterval[0].toUpperCase()}${s.resetInterval.slice(1)} budget exceeded: $${u.toFixed(4)} / $${p.toFixed(2)}`,dailyUsed:l,dailyLimit:p,warningReached:!0,remaining:_,periodUsed:l,activeLimitUsd:p,resetInterval:s.resetInterval,resetTime:s.resetTime,budgetResetAt:o.nextResetAt,lastBudgetResetAt:o.periodStartAt,periodStartAt:o.periodStartAt}:{allowed:!0,dailyUsed:l,dailyLimit:p,warningReached:E,remaining:_,periodUsed:l,activeLimitUsd:p,resetInterval:s.resetInterval,resetTime:s.resetTime,budgetResetAt:o.nextResetAt,lastBudgetResetAt:o.periodStartAt,periodStartAt:o.periodStartAt}},"getBudgetWindow",0,d,"recordCost",0,function(e,t){try{r.spendBatchWriter.increment(e,t,Date.now())}catch{}},"syncAllBudgetSchedules",0,function(e=Date.now()){let r=0,n=0;try{let a=(0,t.loadAllBudgets)();for(let[t,i]of Object.entries(a)){r+=1;let a=c(t,i,e,{logReset:!0,persist:!0});i.lastBudgetResetAt!==a.lastBudgetResetAt&&(n+=1)}}catch{}return{processed:r,resetCount:n}}])},65124,e=>{"use strict";var t=e.i(254799),r=e.i(830471),n=e.i(10947);let a=!1;function i(e){return e&&"object"==typeof e&&!Array.isArray(e)?e:{}}function s(e,t=0){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let r=Number(e);return Number.isFinite(r)?r:t}return t}function o(e){return"model"===e||"provider"===e||"global"===e?e:"global"}function l(e){return"daily"===e||"weekly"===e||"monthly"===e?e:"monthly"}function u(){a||((0,r.getDbInstance)().exec(`
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
  `),a=!0)}function d(e){let t=i(e);return{id:"string"==typeof t.id?t.id:"",apiKeyId:"string"==typeof t.api_key_id?t.api_key_id:"",scopeType:o(t.scope_type),scopeValue:"string"==typeof t.scope_value?t.scope_value:"",tokenLimit:s(t.token_limit),resetInterval:l(t.reset_interval),resetTime:"string"==typeof t.reset_time&&t.reset_time?t.reset_time:"00:00",enabled:0!==s(t.enabled,1),createdAt:"string"==typeof t.created_at?t.created_at:"",updatedAt:"string"==typeof t.updated_at?t.updated_at:""}}function c(e,t=Date.now()){let r=(0,n.getBudgetWindow)(e.resetInterval,e.resetTime,t);return{windowStart:String(r.periodStartAt),didReset:!1,periodStartAt:r.periodStartAt,nextResetAt:r.nextResetAt}}e.s(["deleteTokenLimit",0,function(e){u();let t=(0,r.getDbInstance)();return t.prepare("DELETE FROM api_key_token_counters WHERE limit_id = ?").run(e),t.prepare("DELETE FROM api_key_token_limit_reset_logs WHERE limit_id = ?").run(e),t.prepare("DELETE FROM api_key_token_limits WHERE id = ?").run(e).changes>0},"getTokenLimitsForRequest",0,function(e,t,n){return u(),(0,r.getDbInstance)().prepare(`SELECT * FROM api_key_token_limits
       WHERE api_key_id = @apiKeyId
         AND enabled = 1
         AND (
           (scope_type = 'global')
           OR (scope_type = 'model' AND scope_value = @model)
           OR (scope_type = 'provider' AND scope_value = @provider)
         )`).all({apiKeyId:e,model:n||"",provider:t||""}).map(d)},"getWindowUsage",0,function(e,t=Date.now()){u();let n=(0,r.getDbInstance)(),{windowStart:a}=c(e,t);return s(i(n.prepare("SELECT tokens_used FROM api_key_token_counters WHERE limit_id = ? AND window_start = ?").get(e.id,a)).tokens_used)},"incrementWindowTokens",0,function(e,t,n){u();let a=(0,r.getDbInstance)(),o=Math.max(0,Math.floor(s(n)));return s(i(a.prepare(`INSERT INTO api_key_token_counters (limit_id, window_start, tokens_used, updated_at)
       VALUES (@limitId, @windowStart, @tokens, datetime('now'))
       ON CONFLICT(limit_id, window_start)
       DO UPDATE SET tokens_used = tokens_used + excluded.tokens_used,
                     updated_at  = datetime('now')
       RETURNING tokens_used`).get({limitId:e,windowStart:t,tokens:o})).tokens_used)},"listTokenLimits",0,function(e){return u(),(0,r.getDbInstance)().prepare(`SELECT * FROM api_key_token_limits
       WHERE api_key_id = ?
       ORDER BY CASE scope_type WHEN 'model' THEN 0 WHEN 'provider' THEN 1 ELSE 2 END, scope_value`).all(e).map(d)},"logTokenLimitReset",0,function(e,t,n){u(),(0,r.getDbInstance)().prepare(`INSERT INTO api_key_token_limit_reset_logs (limit_id, reset_at, prev_tokens, window_start)
     VALUES (?, datetime('now'), ?, ?)`).run(e,Math.max(0,Math.floor(s(t))),n)},"resetWindowIfElapsed",0,c,"upsertTokenLimit",0,function(e){u();let n=(0,r.getDbInstance)(),a=o(e.scopeType),i="global"===a?"":(e.scopeValue??"").trim(),c=l(e.resetInterval),p="string"==typeof e.resetTime&&e.resetTime?e.resetTime:"00:00",E=+(!1!==e.enabled),_=Math.floor(s(e.tokenLimit)),m=e.id&&e.id.trim()?e.id.trim():(0,t.randomUUID)();return n.prepare(`INSERT INTO api_key_token_limits
       (id, api_key_id, scope_type, scope_value, token_limit, reset_interval, reset_time, enabled, created_at, updated_at)
     VALUES (@id, @apiKeyId, @scopeType, @scopeValue, @tokenLimit, @resetInterval, @resetTime, @enabled, datetime('now'), datetime('now'))
     ON CONFLICT(api_key_id, scope_type, scope_value)
     DO UPDATE SET token_limit    = excluded.token_limit,
                   reset_interval = excluded.reset_interval,
                   reset_time     = excluded.reset_time,
                   enabled        = excluded.enabled,
                   updated_at     = datetime('now')`).run({id:m,apiKeyId:e.apiKeyId,scopeType:a,scopeValue:i,tokenLimit:_,resetInterval:c,resetTime:p,enabled:E}),d(n.prepare("SELECT * FROM api_key_token_limits WHERE api_key_id = ? AND scope_type = ? AND scope_value = ?").get(e.apiKeyId,a,i))}])},430508,e=>{"use strict";var t=e.i(830471);let r=(0,e.i(403380).logger)("DB_PLUGINS");function n(e){return{id:e.id,name:e.name,version:e.version,description:e.description,author:e.author,license:e.license,main:e.main,source:e.source,tags:e.tags,status:e.status,enabled:e.enabled,manifest:e.manifest,config:e.config,configSchema:e.config_schema,hooks:e.hooks,permissions:e.permissions,pluginDir:e.plugin_dir,errorMessage:e.error_message,installedAt:e.installed_at,updatedAt:e.updated_at,activatedAt:e.activated_at}}function a(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM plugins WHERE name = ?").get(e);return r?n(r):null}e.s(["deletePlugin",0,function(e){let n=(0,t.getDbInstance)().prepare("DELETE FROM plugins WHERE name = ?").run(e);return n.changes>0&&r.info("plugin.deleted",{name:e}),n.changes>0},"getPluginById",0,function(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM plugins WHERE id = ?").get(e);return r?n(r):null},"getPluginByName",0,a,"insertPlugin",0,function(e){let n=(0,t.getDbInstance)(),i=new Date().toISOString();n.prepare(`INSERT INTO plugins (
      id, name, version, description, author, license, main, source, tags,
      status, enabled, manifest, config, config_schema, hooks, permissions,
      plugin_dir, installed_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(e.id,e.name,e.version,e.description??null,e.author??null,e.license??"MIT",e.main,e.source??"local",JSON.stringify(e.tags??[]),e.status??"installed",+!!e.enabled,JSON.stringify(e.manifest),JSON.stringify(e.config??{}),JSON.stringify(e.configSchema??{}),JSON.stringify(e.hooks??[]),JSON.stringify(e.permissions??[]),e.pluginDir,i,i),r.info("plugin.inserted",{id:e.id,name:e.name});let s=a(e.name);if(!s)throw Error(`Failed to retrieve plugin '${e.name}' after insertion`);return s},"listPlugins",0,function(e){let r=(0,t.getDbInstance)();return(e?r.prepare("SELECT * FROM plugins WHERE status = ? ORDER BY name").all(e):r.prepare("SELECT * FROM plugins ORDER BY name").all()).map(n)},"pluginExists",0,function(e){return!!(0,t.getDbInstance)().prepare("SELECT 1 FROM plugins WHERE name = ?").get(e)},"updatePluginConfig",0,function(e,r){let n=(0,t.getDbInstance)(),a=new Date().toISOString();return n.prepare("UPDATE plugins SET config = ?, updated_at = ? WHERE name = ?").run(JSON.stringify(r),a,e).changes>0},"updatePluginStatus",0,function(e,n,a){let i=(0,t.getDbInstance)(),s=new Date().toISOString(),o="active"===n?s:null,l=i.prepare(`UPDATE plugins SET status = ?, enabled = ?, error_message = ?,
       updated_at = ?, activated_at = COALESCE(?, activated_at)
       WHERE name = ?`).run(n,+("active"===n),a??null,s,o,e);return l.changes>0&&r.info("plugin.status_updated",{name:e,status:n}),l.changes>0}])},204366,e=>{"use strict";var t=e.i(830471);function r(e){return{apiKeyId:e.api_key_id,sourceType:e.source_type,token:e.token,baseUrl:e.base_url,vaultPath:e.vault_path,enabled:1===e.enabled}}e.s(["deleteApiKeyContextSource",0,function(e,r){(0,t.getDbInstance)().prepare("DELETE FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ?").run(e,r)},"getApiKeyContextSource",0,function(e,n){if(!e)return null;let a=(0,t.getDbInstance)().prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ? AND enabled = 1").get(e,n);return a?r(a):null},"listApiKeyContextSources",0,function(e){return(0,t.getDbInstance)().prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ?").all(e).map(r)},"setApiKeyContextSource",0,function(e,r,n){let a=(0,t.getDbInstance)(),i=a.prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ?").get(e,r),s=new Date().toISOString();i?a.prepare(`UPDATE api_key_context_sources SET
        token = COALESCE(?, token),
        base_url = COALESCE(?, base_url),
        vault_path = COALESCE(?, vault_path),
        enabled = COALESCE(?, enabled),
        updated_at = ?
      WHERE api_key_id = ? AND source_type = ?`).run(n.token??null,n.baseUrl??null,n.vaultPath??null,void 0!==n.enabled?+!!n.enabled:null,s,e,r):a.prepare(`INSERT INTO api_key_context_sources
        (api_key_id, source_type, token, base_url, vault_path, enabled, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(e,r,n.token??null,n.baseUrl??null,n.vaultPath??null,void 0!==n.enabled?+!!n.enabled:1,s,s)}])},197374,e=>{"use strict";var t=e.i(830471);e.s(["sumUsageTokensThisMonth",0,function(e=(0,t.getDbInstance)()){try{let t=e.prepare(`SELECT COALESCE(SUM(total_input_tokens + total_output_tokens), 0) AS used
         FROM daily_usage_summary
         WHERE date >= strftime('%Y-%m-01','now')`).get();return t?.used??0}catch{return 0}}])},734252,e=>{"use strict";var t=e.i(830471);e.s(["getFallbackStats",0,function(e,r){return(0,t.getDbInstance)().prepare(`
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
    `).get(r)??{total:0,with_requested:0,fallback_eligible:0,fallbacks:0}},"getProviderMetrics",0,function(){return(0,t.getDbInstance)().prepare(`SELECT
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
      `).all()}])},741017,e=>{"use strict";var t=e.i(830471);e.s(["getAccountCostRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
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
    `).all(r)}])},670440,e=>{"use strict";var t=e.i(830471);e.s(["getAutoRoutingTopProviders",0,function(){return(0,t.getDbInstance)().prepare(`
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
    `).all()}])},494330,e=>{"use strict";var t=e.i(830471);let r=["created_at","expires_at","hit_count","tokens_saved","model"];e.s(["deleteSemanticCacheByModel",0,function(e){return{deleted:(0,t.getDbInstance)().prepare("DELETE FROM semantic_cache WHERE model = ?").run(e).changes}},"deleteSemanticCacheBySignature",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM semantic_cache WHERE signature = ?").run(e),{deleted:1}},"listSemanticCacheEntries",0,function(e){let n=(0,t.getDbInstance)(),{page:a,limit:i,search:s,model:o,sortBy:l,sortOrder:u}=e,d=[],c=[];s&&(d.push("(signature LIKE ? OR model LIKE ?)"),c.push(`%${s}%`,`%${s}%`)),o&&(d.push("model = ?"),c.push(o));let p=d.length>0?`WHERE ${d.join(" AND ")}`:"",E=r.includes(l)?l:"created_at",_=n.prepare(`SELECT COUNT(*) as total FROM semantic_cache ${p}`).get(...c);return{entries:n.prepare(`SELECT id, signature, model, hit_count, tokens_saved, created_at, expires_at
       FROM semantic_cache ${p}
       ORDER BY ${E} ${"asc"===u?"ASC":"DESC"}
       LIMIT ? OFFSET ?`).all(...c,i,(a-1)*i),total:_?.total||0}}])},407417,e=>{"use strict";var t=e.i(830471);e.s(["exportProxyLogsSince",0,function(e){return(0,t.getDbInstance)().prepare("SELECT * FROM proxy_logs WHERE timestamp >= @since ORDER BY timestamp DESC").all({since:e})}])},5497,e=>{"use strict";var t=e.i(830471);let r="provider_param_filters",n=null,a=0;function i(){a++,n=null}function s(e){return null!==e&&"object"==typeof e&&!Array.isArray(e)}function o(e){return"string"==typeof e&&e.length>0?e:null}function l(e){return Array.isArray(e)?e.filter(e=>"string"==typeof e):[]}function u(){return null===n&&(n=function(){let e=function(e){let r=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(e),n={};for(let e of r)n[e.key]=function(e){if("string"!=typeof e)return e;try{return JSON.parse(e)}catch{return e}}(e.value);return n}(r),n=new Map;for(let[t,r]of Object.entries(e)){let e=function(e){if(!s(e))return null;let t=l(e.block),r=l(e.allow),n=function(e){let t={};if(!s(e))return t;for(let[r,n]of Object.entries(e)){if(!s(n))continue;let e=function(e){let t=l(e.block),r=l(e.allow);if(0===t.length&&0===r.length)return null;let n={};return t.length>0&&(n.block=t),r.length>0&&(n.allow=r),n}(n);e&&(t[r]=e)}return t}(e.models),a="boolean"==typeof e.autoLearn&&e.autoLearn;return{block:t,allow:r,models:Object.keys(n).length>0?n:void 0,autoLearn:a}}(r);e&&n.set(t,e)}return n}()),n}function d(e){return o(e)?u().get(e)??null:null}function c(e,n){if(!o(e))return;let a=(0,t.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)"),s={block:n.block??[],allow:n.allow??[],autoLearn:n.autoLearn??!1,models:n.models&&Object.keys(n.models).length>0?n.models:void 0};a.run(r,e,JSON.stringify(s)),i()}let p="__global__";e.s(["addParamToBlocklist",0,function(e,t,r){if(!o(e)||!o(t))return;let n=d(e)??{block:[],allow:[],autoLearn:!1};if(r){let e=n.models??{},a=e[r]??{};if(Array.isArray(a.block)&&a.block.includes(t))return;let i=[...a.block??[],t];e[r]={...a,block:i},n.models=e}else{if(n.block.includes(t))return;n.block=[...n.block,t]}c(e,n)},"deleteParamFilterConfig",0,function(e){o(e)&&((0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(r,e),i())},"getParamFilterConfig",0,d,"isAutoLearnGloballyEnabled",0,function(){let e=d(p);return e?.autoLearn===!0},"loadParamFilterConfigs",0,u,"setGlobalAutoLearnEnabled",0,function(e){let t=d(p);c(p,{block:t?.block??[],allow:t?.allow??[],autoLearn:e})},"setParamFilterConfig",0,c])},680516,e=>{"use strict";var t=e.i(830471);let r="interception_rules",n=null;function a(e){return null!==e&&"object"==typeof e&&!Array.isArray(e)}function i(e){return"string"==typeof e&&e.trim().length>0?e.trim():null}function s(e){return"boolean"==typeof e?e:void 0}function o(e){return"firecrawl"===e||"jina"===e||"tavily"===e?e:void 0}function l(e){return i(e)?(null===n&&(n=function(){let e=function(e){let r=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(e),n={};for(let e of r)n[e.key]=function(e){if("string"!=typeof e)return e;try{return JSON.parse(e)}catch{return e}}(e.value);return n}(r),n=new Map;for(let[t,r]of Object.entries(e)){let e=function(e){if(!a(e))return null;let t=function(e){let t={};if(!a(e))return t;for(let[r,n]of Object.entries(e)){let e=function(e){if(!a(e))return null;let t={interceptSearch:s(e.interceptSearch),interceptFetch:s(e.interceptFetch),fetchBackend:o(e.fetchBackend),fetchProxyUrl:i(e.fetchProxyUrl)??void 0};return Object.values(t).some(e=>void 0!==e)?t:null}(n);e&&(t[r]=e)}return t}(e.models);return{interceptSearch:s(e.interceptSearch),interceptFetch:s(e.interceptFetch),fetchBackend:o(e.fetchBackend),fetchProxyUrl:i(e.fetchProxyUrl)??void 0,models:Object.keys(t).length>0?t:void 0}}(r);e&&n.set(t,e)}return n}()),n).get(e)??null:null}e.s(["deleteInterceptionRules",0,function(e){let a=i(e);a&&((0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(r,a),n=null)},"getInterceptionRules",0,l,"resolveInterceptSearch",0,function(e,t){let r=i(e);if(!r)return;let n=l(r);if(!n)return;let a=i(t);return a&&n.models?.[a]?.interceptSearch!==void 0?n.models[a].interceptSearch:n.interceptSearch},"setInterceptionRules",0,function(e,a){let s=i(e);if(!s)return;let o=(0,t.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)"),l={interceptSearch:a.interceptSearch,interceptFetch:a.interceptFetch,fetchBackend:a.fetchBackend,fetchProxyUrl:a.fetchProxyUrl,models:a.models&&Object.keys(a.models).length>0?a.models:void 0};o.run(r,s,JSON.stringify(l)),n=null}])},13572,e=>e.a(async(t,r)=>{try{var n=e.i(648830);e.i(248084),e.i(413618),e.i(488608),e.i(381581),e.i(865498),e.i(363685),e.i(950412),e.i(974008);var a=e.i(754140);e.i(417358),e.i(132446),e.i(986039),e.i(335273),e.i(709287),e.i(687267),e.i(707708),e.i(884344),e.i(773412),e.i(301435),e.i(595357),e.i(8011),e.i(993053),e.i(556826),e.i(756045),e.i(690915),e.i(998715),e.i(520700),e.i(675292),e.i(874957),e.i(224002),e.i(704553),e.i(719686),e.i(61499),e.i(616118),e.i(682611),e.i(822071),e.i(639015),e.i(528682),e.i(324074),e.i(169730),e.i(767382),e.i(697387),e.i(326151),e.i(758677),e.i(452415),e.i(339176);var i=e.i(839713);e.i(896326),e.i(858013),e.i(160769),e.i(608455),e.i(913184),e.i(954147),e.i(65124),e.i(430508),e.i(204366),e.i(197374),e.i(31792),e.i(734252),e.i(741017),e.i(670440),e.i(494330),e.i(407417),e.i(5497),e.i(680516);var s=t([n,a,i]);[n,a,i]=s.then?(await s)():s,e.s([]),r()}catch(e){r(e)}},!1)];

//# sourceMappingURL=src_0q32v-8._.js.map