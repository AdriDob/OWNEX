module.exports=[839193,e=>{"use strict";var t=e.i(504208);e.s(["getCacheStatsSummary",0,function(e){let r=(0,t.getDbInstance)();e&&e.toISOString();let n=e?r.prepare("SELECT COUNT(*) as totalRequests, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats WHERE created_at >= ?").get(e.toISOString()):r.prepare("SELECT COUNT(*) as totalRequests, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats").get();if(!n||0===n.totalRequests)return{totalRequests:0,avgNetSavings:0,cacheHitRate:0,byProvider:{}};let a=e?r.prepare("SELECT provider, COUNT(*) as count, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats WHERE created_at >= ? GROUP BY provider").all(e.toISOString()):r.prepare("SELECT provider, COUNT(*) as count, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats GROUP BY provider").all(),o={};for(let e of a)o[e.provider]={count:e.count,avgNetSavings:e.avgNetSavings,cacheHitRate:e.cacheHitRate};return{totalRequests:n.totalRequests,avgNetSavings:n.avgNetSavings??0,cacheHitRate:n.cacheHitRate??0,byProvider:o}},"recordCacheStats",0,function(e){let r=(0,t.getDbInstance)(),n=`INSERT INTO compression_cache_stats (
    provider, 
    model, 
    compression_mode, 
    cache_control_present, 
    estimated_cache_hit, 
    tokens_saved_compression, 
    tokens_saved_caching, 
    net_savings
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;r.prepare(n).run(e.provider,e.model??"",e.compressionMode,+!!e.cacheControlPresent,+!!e.estimatedCacheHit,e.tokensSavedCompression,e.tokensSavedCaching,e.netSavings)}])},660623,e=>{"use strict";var t=e.i(886588),r=e.i(223194),n=e.i(504208),a=e.i(446202);let o="default-caveman",i="Standard Savings",s="Default RTK + Caveman compression pipeline";function u(){return[{engine:"rtk",intensity:"standard"},{engine:"caveman",intensity:"full"}]}function l(e,t){if(Array.isArray(e))return e;if("string"!=typeof e)return t;try{let r=JSON.parse(e);return Array.isArray(r)?r:t}catch{return t}}let c=["lite","caveman","aggressive","ultra","rtk","headroom","session-dedup","ccr","llmlingua","relevance"];function d(e){return l(e,[]).filter(e=>e&&"object"==typeof e&&c.includes(String(e.engine)))}function p(){let e=(0,n.getDbInstance)();e.exec(`
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
  `).run(o,i,s,JSON.stringify(u()),JSON.stringify(["en"]),0,"full",1),function(){let e=(0,n.getDbInstance)(),t=e.prepare("SELECT name, description, pipeline FROM compression_combos WHERE id = ?").get(o);if(!t)return;let r=String(t.description??"");String(t.name??"")===i&&("Default Caveman compression pipeline"===r||r===s)&&function(e){if(1!==e.length)return!1;let[t]=e;return"caveman"===t.engine&&(void 0===t.intensity||"full"===t.intensity)}(d(t.pipeline))&&e.prepare(`
    UPDATE compression_combos
    SET description = ?, pipeline = ?, updated_at = ?
    WHERE id = ?
  `).run(s,JSON.stringify(u()),new Date().toISOString(),o)}()}function _(e){let t;if(!e)return null;let r=(0,a.rowToCamel)(e);return{id:String(r.id),name:String(r.name??""),description:String(r.description??""),pipeline:d(r.pipeline),languagePacks:[...new Set((t=l(r.languagePacks,["en"]).filter(e=>"string"==typeof e&&e.trim().length>0)).length>0?t.map(e=>e.trim()):["en"])],outputMode:!!r.outputMode,outputModeIntensity:String(r.outputModeIntensity??"full"),isDefault:!!r.isDefault,createdAt:String(r.createdAt??""),updatedAt:String(r.updatedAt??"")}}function E(e){if(!e)return null;let t=(0,a.rowToCamel)(e);return{id:String(t.id),compressionComboId:String(t.compressionComboId),routingComboId:String(t.routingComboId),createdAt:String(t.createdAt??"")}}function m(e,r){let n=new Date().toISOString();return{id:r?.id??e.id??(0,t.v4)(),name:e.name?.trim()||r?.name||"Compression Combo",description:e.description??r?.description??"",pipeline:e.pipeline&&e.pipeline.length>0?e.pipeline:r?.pipeline&&r.pipeline.length>0?r.pipeline:u(),languagePacks:e.languagePacks&&e.languagePacks.length>0?e.languagePacks:r?.languagePacks&&r.languagePacks.length>0?r.languagePacks:["en"],outputMode:e.outputMode??r?.outputMode??!1,outputModeIntensity:e.outputModeIntensity??r?.outputModeIntensity??"full",isDefault:e.isDefault??r?.isDefault??!1,createdAt:r?.createdAt??n,updatedAt:n}}function g(e){return p(),_((0,n.getDbInstance)().prepare("SELECT * FROM compression_combos WHERE id = ?").get(e))}function y(){return p(),_((0,n.getDbInstance)().prepare("SELECT * FROM compression_combos WHERE is_default = 1 ORDER BY updated_at DESC LIMIT 1").get())}let S={"session-dedup":3,ccr:4,lite:5,rtk:10,headroom:15,caveman:20,aggressive:30,llmlingua:35,ultra:40};e.s(["assignRoutingCombo",0,function(e,a){return p(),!!g(e)&&!!a.trim()&&((0,n.getDbInstance)().prepare(`
      INSERT OR REPLACE INTO compression_combo_assignments (
        id, compression_combo_id, routing_combo_id, created_at
      )
      VALUES (?, ?, ?, ?)
    `).run((0,t.v4)(),e,a.trim(),new Date().toISOString()),(0,r.backupDbFile)("pre-write"),!0)},"createCompressionCombo",0,function(e){p();let t=(0,n.getDbInstance)(),a=m(e);return t.transaction(()=>{a.isDefault&&t.prepare("UPDATE compression_combos SET is_default = 0").run(),t.prepare(`
      INSERT INTO compression_combos (
        id, name, description, pipeline, language_packs, output_mode, output_mode_intensity,
        is_default, created_at, updated_at
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(a.id,a.name,a.description,JSON.stringify(a.pipeline),JSON.stringify(a.languagePacks),+!!a.outputMode,a.outputModeIntensity,+!!a.isDefault,a.createdAt,a.updatedAt)})(),(0,r.backupDbFile)("pre-write"),g(a.id)},"deleteCompressionCombo",0,function(e){p();let t=g(e);if(!t||t.isDefault)return!1;let a=(0,n.getDbInstance)().prepare("DELETE FROM compression_combos WHERE id = ?").run(e);return a.changes>0&&(0,r.backupDbFile)("pre-write"),a.changes>0},"getAssignmentsForCompressionCombo",0,function(e){return p(),(0,n.getDbInstance)().prepare("SELECT * FROM compression_combo_assignments WHERE compression_combo_id = ? ORDER BY routing_combo_id").all(e).map(E).filter(e=>null!==e)},"getCompressionCombo",0,g,"getCompressionComboForRoutingCombo",0,function(e){return p(),_((0,n.getDbInstance)().prepare(`
      SELECT c.*
      FROM compression_combos c
      JOIN compression_combo_assignments a ON a.compression_combo_id = c.id
      WHERE a.routing_combo_id = ?
      LIMIT 1
    `).get(e))},"getDefaultCompressionCombo",0,y,"listCompressionCombos",0,function(){return p(),(0,n.getDbInstance)().prepare("SELECT * FROM compression_combos ORDER BY is_default DESC, name COLLATE NOCASE ASC").all().map(_).filter(e=>null!==e)},"setDefaultCompressionCombo",0,function(e){if(p(),!g(e))return!1;let t=(0,n.getDbInstance)(),a=new Date().toISOString();return t.transaction(()=>{t.prepare("UPDATE compression_combos SET is_default = 0").run(),t.prepare("UPDATE compression_combos SET is_default = 1, updated_at = ? WHERE id = ?").run(a,e)})(),(0,r.backupDbFile)("pre-write"),!0},"setEngineInDefaultCombo",0,function(e,t,a){if(!c.includes(e))return null;p();let o=y();if(!o)return null;let i=[...o.pipeline];if(t){let t=i.findIndex(t=>t.engine===e);t>=0?void 0!==a&&(i[t]={...i[t],config:a}):i.push({engine:e,...a?{config:a}:{}}),i.sort((e,t)=>(S[e.engine]??50)-(S[t.engine]??50))}else i=i.filter(t=>t.engine!==e);let s=(0,n.getDbInstance)(),u=new Date().toISOString();return s.prepare("UPDATE compression_combos SET pipeline = ?, updated_at = ? WHERE id = ?").run(JSON.stringify(i),u,o.id),(0,r.backupDbFile)("pre-write"),g(o.id)},"unassignRoutingCombo",0,function(e,t){p();let a=(0,n.getDbInstance)().prepare("DELETE FROM compression_combo_assignments WHERE compression_combo_id = ? AND routing_combo_id = ?").run(e,t);return a.changes>0&&(0,r.backupDbFile)("pre-write"),a.changes>0},"updateAssignments",0,function(e,a){if(p(),!g(e))return!1;let o=[...new Set(a.map(e=>e.trim()).filter(Boolean))],i=(0,n.getDbInstance)();return i.transaction(()=>{if(i.prepare("DELETE FROM compression_combo_assignments WHERE compression_combo_id = ?").run(e),o.length>0){let r=i.prepare("DELETE FROM compression_combo_assignments WHERE routing_combo_id = ?"),n=i.prepare(`
        INSERT INTO compression_combo_assignments (
          id, compression_combo_id, routing_combo_id, created_at
        )
        VALUES (?, ?, ?, ?)
      `);for(let a of o)r.run(a),n.run((0,t.v4)(),e,a,new Date().toISOString())}})(),(0,r.backupDbFile)("pre-write"),!0},"updateCompressionCombo",0,function(e,t){p();let a=g(e);if(!a)return null;let o=m(t,a),i=(0,n.getDbInstance)();return i.transaction(()=>{o.isDefault&&i.prepare("UPDATE compression_combos SET is_default = 0").run(),i.prepare(`
      UPDATE compression_combos
      SET name = ?, description = ?, pipeline = ?, language_packs = ?, output_mode = ?,
          output_mode_intensity = ?, is_default = ?, updated_at = ?
      WHERE id = ?
    `).run(o.name,o.description,JSON.stringify(o.pipeline),JSON.stringify(o.languagePacks),+!!o.outputMode,o.outputModeIntensity,+!!o.isDefault,o.updatedAt,e)})(),(0,r.backupDbFile)("pre-write"),g(e)}])},53671,e=>{"use strict";var t=e.i(504208);function r(){(0,t.getDbInstance)().exec(`
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
  `)}e.s(["getCompressionRunTelemetrySummary",0,function(){let e=(0,t.getDbInstance)();r();let n=e.prepare(`SELECT tokens_before, tokens_after, output_styles, output_style_bypass, output_tokens
       FROM compression_run_telemetry`).all(),a={totalRuns:n.length,totalTokensSaved:0,runsWithStyles:0,bypassCount:0,totalOutputTokens:0,appliedStyleCounts:{}};for(let e of n)if(a.totalTokensSaved+=Math.max(0,e.tokens_before-e.tokens_after),a.totalOutputTokens+=e.output_tokens??0,e.output_style_bypass&&(a.bypassCount+=1),e.output_styles){a.runsWithStyles+=1;try{for(let t of JSON.parse(e.output_styles))a.appliedStyleCounts[t.id]=(a.appliedStyleCounts[t.id]??0)+1}catch{}}return a},"insertCompressionRunTelemetryRow",0,function(e){try{let n=(0,t.getDbInstance)();r(),n.prepare(`INSERT INTO compression_run_telemetry (
        timestamp, request_id, model, provider, source,
        tokens_before, tokens_after, ratio, cost_delta,
        output_styles, output_style_bypass, output_tokens
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(Date.now(),e.requestId??null,e.model??null,e.provider??null,e.source??null,e.tokensBefore,e.tokensAfter,e.ratio,e.costDelta??null,e.outputStyles&&e.outputStyles.length>0?JSON.stringify(e.outputStyles):null,e.outputStyleBypass??null,e.outputTokens??null)}catch{}}])},376369,e=>{"use strict";var t=e.i(666680),r=e.i(504208),n=e.i(446202);function a(e,t,r){return e.prepare(`PRAGMA table_info(${t})`).all().some(e=>e&&"string"==typeof e.name&&e.name===r)}function o(e){e.prepare(`CREATE TABLE IF NOT EXISTS eval_suites (
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
    )`).run(),a(e,"eval_cases","sort_order")||e.prepare("ALTER TABLE eval_cases ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0").run(),a(e,"eval_cases","model")||e.prepare("ALTER TABLE eval_cases ADD COLUMN model TEXT").run(),a(e,"eval_cases","input_json")||e.prepare("ALTER TABLE eval_cases ADD COLUMN input_json TEXT NOT NULL DEFAULT '{}'").run(),a(e,"eval_cases","expected_strategy")||e.prepare("ALTER TABLE eval_cases ADD COLUMN expected_strategy TEXT NOT NULL DEFAULT 'contains'").run(),a(e,"eval_cases","expected_value")||e.prepare("ALTER TABLE eval_cases ADD COLUMN expected_value TEXT").run(),a(e,"eval_cases","tags_json")||e.prepare("ALTER TABLE eval_cases ADD COLUMN tags_json TEXT").run(),a(e,"eval_cases","created_at")||e.prepare("ALTER TABLE eval_cases ADD COLUMN created_at TEXT NOT NULL DEFAULT ''").run(),a(e,"eval_cases","updated_at")||e.prepare("ALTER TABLE eval_cases ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''").run(),e.prepare("CREATE INDEX IF NOT EXISTS idx_eval_suites_updated_at ON eval_suites(updated_at DESC)").run(),e.prepare("CREATE INDEX IF NOT EXISTS idx_eval_cases_suite_order ON eval_cases(suite_id, sort_order ASC, created_at ASC)").run()}function i(e){if(e&&"object"==typeof e&&!Array.isArray(e))return e;if("string"!=typeof e||0===e.trim().length)return{};try{let t=JSON.parse(e);return t&&"object"==typeof t&&!Array.isArray(t)?t:{}}catch{return{}}}function s(e){let t=Number(e);return Number.isFinite(t)?t:0}function u(e){var t;let r=e&&"object"==typeof e&&!Array.isArray(e)?e:{},n=s(r.max_tokens),a={messages:Array.isArray(t=r.messages)?t.map(e=>{if(!e||"object"!=typeof e||Array.isArray(e))return null;let t="string"==typeof e.role?e.role.trim():"",r="string"==typeof e.content?e.content:"";return t&&r.trim()?{role:t,content:r}:null}).filter(e=>null!==e):[]};return n>0&&(a.max_tokens=Math.floor(n)),a}function l(e){let t=e&&"object"==typeof e&&!Array.isArray(e)?e:{},r="string"==typeof t.strategy?t.strategy.trim():"",n="string"==typeof t.value&&t.value.trim().length>0?t.value:void 0;return{strategy:"exact"===r||"regex"===r||"custom"===r?r:"contains",...n?{value:n}:{}}}function c(e,t){return`${e}:${"string"==typeof t&&t.trim().length>0?t.trim():"__default__"}`}function d(e={}){let t=(0,r.getDbInstance)(),a=[],o=[];e.suiteId&&(a.push("suite_id = ?"),o.push(e.suiteId)),e.runGroupId&&(a.push("run_group_id = ?"),o.push(e.runGroupId));let u=Number.isFinite(Number(e.limit))?Math.min(200,Math.max(1,Math.floor(Number(e.limit)))):20;o.push(u);let l=`SELECT *
    FROM eval_runs
    ${a.length>0?`WHERE ${a.join(" AND ")}`:""}
    ORDER BY created_at DESC
    LIMIT ?`;return t.prepare(l).all(...o).map(e=>(function(e){let t,r,a,o,u=(0,n.rowToCamel)(e);if(!u)return null;let l=i(u.summary??u.summaryJson),d=Object.fromEntries(Object.entries(i(u.outputs??u.outputsJson)).filter(e=>"string"==typeof e[0]).map(([e,t])=>[e,"string"==typeof t?t:String(t??"")]));return{id:"string"==typeof u.id?u.id:"",runGroupId:"string"==typeof u.runGroupId&&u.runGroupId.trim().length>0?u.runGroupId:null,suiteId:"string"==typeof u.suiteId?u.suiteId:"",suiteName:"string"==typeof u.suiteName?u.suiteName:"",target:(t=u.targetType,a="string"==typeof(r=u.targetId)&&r.trim().length>0?r.trim():null,{type:o="combo"===t||"model"===t||"suite-default"===t?t:"suite-default",id:a,key:c(o,a),label:"string"==typeof u.targetLabel&&u.targetLabel.trim().length>0?u.targetLabel.trim():"combo"===o?`Combo: ${a||"Unknown"}`:"model"===o?`Model: ${a||"Unknown"}`:"Suite defaults"}),apiKeyId:"string"==typeof u.apiKeyId&&u.apiKeyId.trim().length>0?u.apiKeyId:null,avgLatencyMs:s(u.avgLatencyMs),summary:{total:s(l.total??u.total),passed:s(l.passed??u.passed),failed:s(l.failed??u.failed),passRate:s(l.passRate??u.passRate)},results:function(e){if(Array.isArray(e))return e.filter(e=>!!e&&"object"==typeof e&&!Array.isArray(e));if("string"!=typeof e||0===e.trim().length)return[];try{let t=JSON.parse(e);return Array.isArray(t)?t.filter(e=>!!e&&"object"==typeof e&&!Array.isArray(e)):[]}catch{return[]}}(u.results??u.resultsJson),outputs:d,createdAt:"string"==typeof u.createdAt?u.createdAt:""}})(e)).filter(e=>null!==e)}function p(){let e=(0,r.getDbInstance)();o(e);let t=e.prepare("SELECT * FROM eval_suites ORDER BY updated_at DESC, created_at DESC").all(),a=e.prepare("SELECT * FROM eval_cases ORDER BY suite_id ASC, sort_order ASC, created_at ASC, id ASC").all(),c=new Map;for(let e of a){let t=function(e){let t=(0,n.rowToCamel)(e);if(!t)return null;let r=u(i(t.input??t.inputJson)),a=l({strategy:t.expectedStrategy,value:t.expectedValue});return{id:"string"==typeof t.id?t.id:"",suiteId:"string"==typeof t.suiteId?t.suiteId:"",name:"string"==typeof t.name?t.name:"",..."string"==typeof t.model&&t.model.trim().length>0?{model:t.model.trim()}:{},input:r,expected:a,tags:function(e){if(Array.isArray(e))return e.filter(e=>"string"==typeof e).map(e=>e.trim()).filter(e=>e.length>0);if("string"!=typeof e||0===e.trim().length)return[];try{let t=JSON.parse(e);return Array.isArray(t)?t.filter(e=>"string"==typeof e).map(e=>e.trim()).filter(e=>e.length>0):[]}catch{return[]}}(t.tags??t.tagsJson),sortOrder:s(t.sortOrder),createdAt:"string"==typeof t.createdAt?t.createdAt:"",updatedAt:"string"==typeof t.updatedAt?t.updatedAt:""}}(e);if(!t||!t.suiteId)continue;let r=c.get(t.suiteId)||[];r.push(t),c.set(t.suiteId,r)}return t.map(e=>{var t;let r,a=(0,n.rowToCamel)(e),o=a&&"string"==typeof a.id?a.id:"";return t=c.get(o)||[],(r=(0,n.rowToCamel)(e))?{id:"string"==typeof r.id?r.id:"",name:"string"==typeof r.name?r.name:"",..."string"==typeof r.description&&r.description.trim().length>0?{description:r.description}:{},source:"custom",caseCount:t.length,cases:t,createdAt:"string"==typeof r.createdAt?r.createdAt:"",updatedAt:"string"==typeof r.updatedAt?r.updatedAt:""}:null}).filter(e=>null!==e)}function _(e){let t=e.trim();return t&&p().find(e=>e.id===t)||null}e.s(["deleteCustomEvalSuite",0,function(e){let t=(0,r.getDbInstance)();o(t);let n=e.trim();if(!n)return!1;t.prepare("BEGIN").run();try{t.prepare("DELETE FROM eval_cases WHERE suite_id = ?").run(n);let e=t.prepare("DELETE FROM eval_suites WHERE id = ?").run(n);return t.prepare("COMMIT").run(),e.changes>0}catch(e){throw t.prepare("ROLLBACK").run(),e}},"getCustomEvalSuite",0,_,"getEvalScorecard",0,function(e={}){var t;let r,n,a=d({suiteId:e.suiteId,limit:e.limit||50});if(0===a.length)return null;let o=new Map;for(let e of a){let t=`${e.suiteId}:${e.target.key}`;o.has(t)||o.set(t,e)}return r=(t=Array.from(o.values()).map(e=>({suiteId:`${e.suiteId}:${e.target.key}`,suiteName:`${e.suiteName} \xb7 ${e.target.label}`,results:e.results,summary:e.summary}))).reduce((e,t)=>e+t.summary.total,0),n=t.reduce((e,t)=>e+t.summary.passed,0),{suites:t.length,totalCases:r,totalPassed:n,overallPassRate:r>0?Math.round(n/r*100):0,perSuite:t.map(e=>({id:e.suiteId,name:e.suiteName,passRate:e.summary.passRate}))}},"listCustomEvalSuites",0,p,"listEvalRuns",0,d,"saveCustomEvalSuite",0,function(e){let n=(0,r.getDbInstance)();o(n);let a=new Date().toISOString(),i="string"==typeof e.id&&e.id.trim().length>0?e.id.trim():(0,t.randomUUID)(),s=e.name.trim(),c="string"==typeof e.description&&e.description.trim().length>0?e.description.trim():null;if(!s)throw Error("Suite name is required");if(!Array.isArray(e.cases)||0===e.cases.length)throw Error("At least one eval case is required");n.prepare("BEGIN").run();try{n.prepare("SELECT id FROM eval_suites WHERE id = ?").get(i)?n.prepare(`UPDATE eval_suites
         SET name = ?, description = ?, updated_at = ?
         WHERE id = ?`).run(s,c,a,i):n.prepare(`INSERT INTO eval_suites (id, name, description, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?)`).run(i,s,c,a,a),n.prepare("DELETE FROM eval_cases WHERE suite_id = ?").run(i),e.cases.forEach((e,r)=>{let o="string"==typeof e.id&&e.id.trim().length>0?e.id.trim():(0,t.randomUUID)(),s=e.name.trim(),c="string"==typeof e.model&&e.model.trim().length>0?e.model.trim():null,d=u(e.input),p=l(e.expected),_=Array.isArray(e.tags)?e.tags.map(e=>e.trim()).filter(e=>e.length>0):[];if(!s)throw Error(`Case ${r+1} is missing a name`);if(0===d.messages.length)throw Error(`Case ${r+1} must include at least one message`);if(("contains"===p.strategy||"exact"===p.strategy||"regex"===p.strategy)&&!p.value)throw Error(`Case ${r+1} must include an expected value`);n.prepare(`INSERT INTO eval_cases
          (id, suite_id, sort_order, name, model, input_json, expected_strategy, expected_value,
           tags_json, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(o,i,r,s,c,JSON.stringify(d),p.strategy,p.value||null,JSON.stringify(_),a,a)}),n.prepare("COMMIT").run()}catch(e){throw n.prepare("ROLLBACK").run(),e}let d=_(i);if(!d)throw Error("Failed to persist eval suite");return d},"saveEvalRun",0,function(e){let n=(0,r.getDbInstance)(),a=e.createdAt||new Date().toISOString(),o=(0,t.randomUUID)(),i="string"==typeof e.target.id&&e.target.id.trim().length>0?e.target.id.trim():null,s=Number.isFinite(Number(e.avgLatencyMs))?Math.max(0,Math.round(Number(e.avgLatencyMs))):0;return n.prepare(`INSERT INTO eval_runs
      (id, run_group_id, suite_id, suite_name, target_type, target_id, target_label, api_key_id,
       pass_rate, total, passed, failed, avg_latency_ms, summary_json, results_json, outputs_json, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(o,e.runGroupId||null,e.suiteId,e.suiteName,e.target.type,i,e.target.label,e.apiKeyId||null,e.summary.passRate,e.summary.total,e.summary.passed,e.summary.failed,s,JSON.stringify(e.summary),JSON.stringify(e.results||[]),JSON.stringify(e.outputs||{}),a),{id:o,runGroupId:e.runGroupId||null,suiteId:e.suiteId,suiteName:e.suiteName,target:{type:e.target.type,id:i,key:c(e.target.type,i),label:e.target.label},apiKeyId:e.apiKeyId||null,avgLatencyMs:s,summary:e.summary,results:e.results||[],outputs:e.outputs||{},createdAt:a}},"serializeEvalTargetKey",0,c])},825538,e=>{"use strict";var t=e.i(504208),r=e.i(655734),n=e.i(223194);let a=["litellm"],o=parseInt(process.env.PRICING_SYNC_INTERVAL||"86400",10),i=Number.isFinite(o)&&o>0?1e3*o:864e5,s=(process.env.PRICING_SYNC_SOURCES||"litellm").split(",").map(e=>e.trim()).filter(e=>a.includes(e)),u={openai:["openai","cx"],anthropic:["anthropic","cc"],vertex_ai:["gemini"],"vertex_ai-anthropic_models":["anthropic"],google:["gemini"],deepseek:["if"],groq:["groq"],together_ai:["openrouter"],bedrock:["kiro"],fireworks_ai:["fireworks"],cerebras:["cerebras"],nvidia_nim:["nvidia"],siliconflow:["siliconflow"],"vertex_ai-language_models":["gemini"],"vertex_ai-mistral_models":["mistral"],gemini:["gemini"],bedrock_converse:["kiro"],cloudflare:["cloudflare-ai"],stability:["stability-ai"]},l=null,c=null,d=0,p=i;async function _(){let e=await fetch("https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",{signal:AbortSignal.timeout(3e4)});if(!e.ok)throw Error(`LiteLLM fetch failed [${e.status}]: ${e.statusText}`);let t=await e.text();try{return JSON.parse(t)}catch{throw Error(`LiteLLM returned invalid JSON (${t.slice(0,100)}...)`)}}function E(e){return e&&"object"==typeof e?e:{}}function m(e){let a=(0,t.getDbInstance)(),o=a.prepare("DELETE FROM key_value WHERE namespace = 'pricing_synced'"),i=a.prepare("INSERT INTO key_value (namespace, key, value) VALUES ('pricing_synced', ?, ?)");a.transaction(()=>{for(let[t,r]of(o.run(),Object.entries(e)))i.run(t,JSON.stringify(r))})(),(0,n.backupDbFile)("pre-write"),(0,r.invalidateDbCache)("pricing")}let g="pricing_sync_status",y="last_sync";async function S(e){let r=e?.sources||s,n=e?.dryRun??!1,o=r.filter(e=>a.includes(e)),i=r.filter(e=>!a.includes(e));if(0===o.length){let e=a.join(", ");return{success:!1,modelCount:0,providerCount:0,source:r.join(","),dryRun:n,error:`No valid sources provided. Supported: ${e}. Invalid: ${i.join(", ")}`}}try{let e={};for(let t of o)if("litellm"===t){let t=await _(),r=function(e){let t={};for(let[r,n]of Object.entries(e)){let e=["input_cost_per_second","output_cost_per_second","input_cost_per_image","output_cost_per_image","input_cost_per_pixel","output_cost_per_pixel","input_cost_per_character","output_cost_per_character","input_cost_per_video_per_second","output_cost_per_video_per_second","search_unit_cost","ocr_cost_per_page"],a=null!=n.input_cost_per_token||null!=n.output_cost_per_token,o=e.some(e=>null!=n[e]);if(!a&&!o)continue;let i=1e6*(n.input_cost_per_token||0),s={input:Math.round(1e3*i)/1e3,output:Math.round(1e3*(1e6*(n.output_cost_per_token||0)))/1e3};for(let t of(n.mode&&(s.mode=n.mode),null!=n.cache_read_input_token_cost&&(s.cached=Math.round(1e6*n.cache_read_input_token_cost*1e3)/1e3),null!=n.cache_creation_input_token_cost&&(s.cache_creation=Math.round(1e6*n.cache_creation_input_token_cost*1e3)/1e3),e)){let e=n[t];"number"==typeof e&&Number.isFinite(e)&&(s[t]=e)}let l=r.indexOf("/"),c=l>=0?r.slice(l+1):r,d=n.litellm_provider||"",p=u[d];if(p)for(let e of p)t[e]||(t[e]={}),t[e][c]=s;else d&&(t[d]||(t[d]={}),t[d][c]=s)}return t}(t);for(let[t,n]of Object.entries(r))e[t]||(e[t]={}),Object.assign(e[t],n)}let r=Object.values(e).reduce((e,t)=>e+Object.keys(t).length,0),a=Object.keys(e).length;if(!n){var l;m(e),c=new Date().toISOString(),d=r,l=c,(0,t.getDbInstance)().prepare("INSERT INTO key_value (namespace, key, value) VALUES (?, ?, ?) ON CONFLICT(namespace, key) DO UPDATE SET value = excluded.value").run(g,y,JSON.stringify({lastSyncTime:l,lastSyncModelCount:r}))}return{success:!0,modelCount:r,providerCount:a,source:o.join(","),dryRun:n,...i.length>0?{warnings:[`Unknown sources ignored: ${i.join(", ")}`]}:{},...n?{data:e}:{}}}catch(t){let e=t instanceof Error?t.message:String(t);return console.warn("[PRICING_SYNC] Sync failed:",e),{success:!1,modelCount:0,providerCount:0,source:r.join(","),dryRun:n,error:e}}}function f(e){if(l)return;let t=e??i;p=t,console.log(`[PRICING_SYNC] Starting periodic sync every ${t/1e3}s`),S().then(e=>{e.success&&console.log(`[PRICING_SYNC] Initial sync complete: ${e.modelCount} models from ${e.providerCount} providers`)}).catch(e=>{console.warn("[PRICING_SYNC] Initial sync error:",e instanceof Error?e.message:e)}),(l=setInterval(()=>{S().then(e=>{e.success&&console.log(`[PRICING_SYNC] Periodic sync complete: ${e.modelCount} models`)}).catch(e=>{console.warn("[PRICING_SYNC] Periodic sync error:",e instanceof Error?e.message:e)})},t))&&"object"==typeof l&&"unref"in l&&l.unref?.()}async function T(){"true"!==process.env.PRICING_SYNC_ENABLED?console.log("[PRICING_SYNC] Disabled (set PRICING_SYNC_ENABLED=true to enable)"):f()}e.s(["clearSyncedPricing",0,function(){(0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = 'pricing_synced'").run(),(0,n.backupDbFile)("pre-write"),(0,r.invalidateDbCache)("pricing")},"getSyncStatus",0,function(){let e="true"===process.env.PRICING_SYNC_ENABLED,r=null===c?function(){let e=E((0,t.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(g,y)),r="string"==typeof e.value?e.value:null;if(!r)return null;try{let e=JSON.parse(r);if("string"!=typeof e.lastSyncTime)return null;return{lastSyncTime:e.lastSyncTime,lastSyncModelCount:"number"==typeof e.lastSyncModelCount?e.lastSyncModelCount:0}}catch{return null}}():null,n=c??r?.lastSyncTime??null;return{enabled:e,lastSync:n,lastSyncModelCount:null!==c?d:r?.lastSyncModelCount??0,nextSync:n?new Date(new Date(n).getTime()+p).toISOString():null,intervalMs:p,sources:s}},"getSyncedPricing",0,function(){let e=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = 'pricing_synced'").all(),r={};for(let t of e){let e=E(t),n="string"==typeof e.key?e.key:null,a="string"==typeof e.value?e.value:null;if(n&&null!==a)try{r[n]=JSON.parse(a)}catch{console.warn(`[PRICING_SYNC] Corrupted data for provider "${n}", skipping`)}}return r},"initPricingSync",0,T,"saveSyncedPricing",0,m,"startPeriodicSync",0,f,"stopPeriodicSync",0,function(){l&&(clearInterval(l),l=null,console.log("[PRICING_SYNC] Periodic sync stopped"))},"syncPricingFromSources",0,S])},109536,e=>{"use strict";var t=e.i(504208);let r=new Set(["enabled","mode","updated_at"]);e.s(["updateSkill",0,function(e,n){let a=(0,t.getDbInstance)(),o=[],i=[];for(let[e,t]of Object.entries(n))r.has(e)&&(o.push(`${e} = ?`),i.push(t));return 0===o.length?0:(o.push("updated_at = datetime('now')"),i.push(e),a.prepare(`UPDATE skills SET ${o.join(", ")} WHERE id = ?`).run(...i).changes)}])},130521,e=>{"use strict";var t=e.i(254799),r=e.i(886588),n=e.i(504208),a=e.i(446202);function o(){return new Date().toISOString().slice(0,10)}function i(){return new Date().toISOString().slice(0,13)}function s(e){return e&&"string"==typeof e?(0,t.createHash)("sha256").update(e).digest("hex"):""}function u(e,t,r,n){let a=o(),s=i();e.prepare(`
    UPDATE ${t}
    SET daily_issued = CASE WHEN last_reset_day <> ? THEN 0 ELSE daily_issued END,
        hourly_issued = CASE WHEN last_reset_hour <> ? THEN 0 ELSE hourly_issued END,
        last_reset_day = ?,
        last_reset_hour = ?
    WHERE ${r} = ?
  `).run(a,s,a,s,n)}e.s(["checkQuota",0,function(e="",t=""){let r=(0,n.getDbInstance)();if(o(),i(),e){u(r,"provider_key_limits","provider",e);let t=r.prepare("SELECT * FROM provider_key_limits WHERE provider = ?").get(e);if(t){if(null!==t.hourly_issue_limit&&t.hourly_issued>=t.hourly_issue_limit)return{allowed:!1,errorCode:"PROVIDER_QUOTA_EXCEEDED",errorMessage:`Hourly issue limit (${t.hourly_issue_limit}) reached for provider '${e}'`,provider:e};if(null!==t.daily_issue_limit&&t.daily_issued>=t.daily_issue_limit)return{allowed:!1,errorCode:"PROVIDER_QUOTA_EXCEEDED",errorMessage:`Daily issue limit (${t.daily_issue_limit}) reached for provider '${e}'`,provider:e};if(null!==t.max_active_keys){let{activeCount:n}=r.prepare("SELECT COUNT(*) as activeCount FROM registered_keys WHERE provider = ? AND is_active = 1").get(e);if(n>=t.max_active_keys)return{allowed:!1,errorCode:"MAX_ACTIVE_KEYS_EXCEEDED",errorMessage:`Max active keys (${t.max_active_keys}) reached for provider '${e}'`,provider:e,providerActiveKeys:n}}}}if(t){u(r,"account_key_limits","account_id",t);let e=r.prepare("SELECT * FROM account_key_limits WHERE account_id = ?").get(t);if(e){if(null!==e.hourly_issue_limit&&e.hourly_issued>=e.hourly_issue_limit)return{allowed:!1,errorCode:"ACCOUNT_QUOTA_EXCEEDED",errorMessage:`Hourly issue limit (${e.hourly_issue_limit}) reached for account '${t}'`,accountId:t};if(null!==e.daily_issue_limit&&e.daily_issued>=e.daily_issue_limit)return{allowed:!1,errorCode:"ACCOUNT_QUOTA_EXCEEDED",errorMessage:`Daily issue limit (${e.daily_issue_limit}) reached for account '${t}'`,accountId:t};if(null!==e.max_active_keys){let{activeCount:n}=r.prepare("SELECT COUNT(*) as activeCount FROM registered_keys WHERE account_id = ? AND is_active = 1").get(t);if(n>=e.max_active_keys)return{allowed:!1,errorCode:"MAX_ACTIVE_KEYS_EXCEEDED",errorMessage:`Max active keys (${e.max_active_keys}) reached for account '${t}'`,accountId:t,accountActiveKeys:n}}}}return{allowed:!0}},"getAccountKeyLimit",0,function(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM account_key_limits WHERE account_id = ?").get(e);return t?(0,a.rowToCamel)(t):null},"getProviderKeyLimit",0,function(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM provider_key_limits WHERE provider = ?").get(e);return t?(0,a.rowToCamel)(t):null},"getRegisteredKey",0,function(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM registered_keys WHERE id = ?").get(e);return t?(0,a.rowToCamel)(t):null},"incrementRegisteredKeyUsage",0,function(e){(0,n.getDbInstance)().prepare(`
    UPDATE registered_keys
    SET daily_used = daily_used + 1, hourly_used = hourly_used + 1, updated_at = datetime('now')
    WHERE id = ?
  `).run(e)},"issueRegisteredKey",0,function(e){let l=(0,n.getDbInstance)(),{name:c,provider:d="",accountId:p="",idempotencyKey:_,expiresAt:E,dailyBudget:m,hourlyBudget:g}=e;if(_){let e=l.prepare("SELECT * FROM registered_keys WHERE idempotency_key = ?").get(_);if(e)return{idempotencyConflict:!0,existing:(0,a.rowToCamel)(e)}}let y="ork_"+(0,t.randomBytes)(24).toString("base64url"),S=(0,r.v4)(),f=s(y),T=y.slice(0,12);l.prepare(`
    INSERT INTO registered_keys
      (id, key, key_prefix, name, provider, account_id, idempotency_key, expires_at, daily_budget, hourly_budget, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(S,f,T,c,d,p,_??null,E??null,m??null,g??null,o(),i()),d&&(u(l,"provider_key_limits","provider",d),l.prepare(`
      INSERT INTO provider_key_limits (provider, daily_issued, hourly_issued, last_reset_day, last_reset_hour)
      VALUES (?, 1, 1, ?, ?)
      ON CONFLICT(provider) DO UPDATE SET
        daily_issued = daily_issued + 1,
        hourly_issued = hourly_issued + 1,
        updated_at = datetime('now')
    `).run(d,o(),i())),p&&(u(l,"account_key_limits","account_id",p),l.prepare(`
      INSERT INTO account_key_limits (account_id, daily_issued, hourly_issued, last_reset_day, last_reset_hour)
      VALUES (?, 1, 1, ?, ?)
      ON CONFLICT(account_id) DO UPDATE SET
        daily_issued = daily_issued + 1,
        hourly_issued = hourly_issued + 1,
        updated_at = datetime('now')
    `).run(p,o(),i()));let R=l.prepare("SELECT * FROM registered_keys WHERE id = ?").get(S);return{...(0,a.rowToCamel)(R),rawKey:y}},"listRegisteredKeys",0,function(e={}){let t=(0,n.getDbInstance)(),r="SELECT * FROM registered_keys WHERE 1=1",o=[];return e.provider&&(r+=" AND provider = ?",o.push(e.provider)),e.accountId&&(r+=" AND account_id = ?",o.push(e.accountId)),r+=" ORDER BY created_at DESC LIMIT 500",t.prepare(r).all(...o).map(e=>(0,a.rowToCamel)(e))},"revokeRegisteredKey",0,function(e){return(0,n.getDbInstance)().prepare(`
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
  `).run(e,t.maxActiveKeys??null,t.dailyIssueLimit??null,t.hourlyIssueLimit??null,o(),i())},"setProviderKeyLimit",0,function(e,t){(0,n.getDbInstance)().prepare(`
    INSERT INTO provider_key_limits (provider, max_active_keys, daily_issue_limit, hourly_issue_limit, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(provider) DO UPDATE SET
      max_active_keys = excluded.max_active_keys,
      daily_issue_limit = excluded.daily_issue_limit,
      hourly_issue_limit = excluded.hourly_issue_limit,
      updated_at = datetime('now')
  `).run(e,t.maxActiveKeys??null,t.dailyIssueLimit??null,t.hourlyIssueLimit??null,o(),i())},"validateRegisteredKey",0,function(e){let t=(0,n.getDbInstance)(),r=s(e),u=t.prepare(`
    SELECT * FROM registered_keys
    WHERE key = ? AND is_active = 1
      AND (expires_at IS NULL OR expires_at > datetime('now'))
  `).get(r);if(!u)return null;let l=o(),c=i();return((u.last_reset_day!==l||u.last_reset_hour!==c)&&t.prepare(`
      UPDATE registered_keys
      SET daily_used = CASE WHEN last_reset_day <> ? THEN 0 ELSE daily_used END,
          hourly_used = CASE WHEN last_reset_hour <> ? THEN 0 ELSE hourly_used END,
          last_reset_day = ?, last_reset_hour = ?
      WHERE id = ?
    `).run(l,c,l,c,u.id),null!==u.daily_budget&&u.daily_used>=u.daily_budget||null!==u.hourly_budget&&u.hourly_used>=u.hourly_budget)?null:(0,a.rowToCamel)(u)}])},658112,e=>{"use strict";var t=e.i(886588),r=e.i(504208);function n(e){return{id:e.id,pattern:e.pattern,comboId:e.combo_id,comboName:e.combo_name||void 0,priority:e.priority,enabled:1===e.enabled,description:e.description||"",createdAt:e.created_at,updatedAt:e.updated_at}}async function a(){return(0,r.getDbInstance)().prepare(`SELECT m.id, m.pattern, m.combo_id, c.name AS combo_name,
              m.priority, m.enabled, m.description,
              m.created_at, m.updated_at
       FROM model_combo_mappings m
       LEFT JOIN combos c ON c.id = m.combo_id
       ORDER BY m.priority DESC, m.created_at ASC`).all().map(n)}async function o(e){let t=(0,r.getDbInstance)().prepare(`SELECT m.id, m.pattern, m.combo_id, c.name AS combo_name,
              m.priority, m.enabled, m.description,
              m.created_at, m.updated_at
       FROM model_combo_mappings m
       LEFT JOIN combos c ON c.id = m.combo_id
       WHERE m.id = ?`).get(e);return t?n(t):null}async function i(e){let n=(0,r.getDbInstance)(),a=new Date().toISOString(),o=(0,t.v4)();return n.prepare(`INSERT INTO model_combo_mappings
     (id, pattern, combo_id, priority, enabled, description, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(o,e.pattern,e.comboId,e.priority??0,+(!1!==e.enabled),e.description||"",a,a),{id:o,pattern:e.pattern,comboId:e.comboId,priority:e.priority??0,enabled:!1!==e.enabled,description:e.description||"",createdAt:a,updatedAt:a}}async function s(e,t){let n=await o(e);if(!n)return null;let a=(0,r.getDbInstance)(),i=new Date().toISOString(),s={pattern:t.pattern??n.pattern,combo_id:t.comboId??n.comboId,priority:t.priority??n.priority,enabled:void 0!==t.enabled?+!!t.enabled:+!!n.enabled,description:t.description??n.description};return a.prepare(`UPDATE model_combo_mappings
     SET pattern = ?, combo_id = ?, priority = ?, enabled = ?,
         description = ?, updated_at = ?
     WHERE id = ?`).run(s.pattern,s.combo_id,s.priority,s.enabled,s.description,i,e),o(e)}async function u(e){return((0,r.getDbInstance)().prepare("DELETE FROM model_combo_mappings WHERE id = ?").run(e).changes??0)>0}async function l(e){for(let t of(0,r.getDbInstance)().prepare(`SELECT m.pattern, m.combo_id, c.data AS combo_data
       FROM model_combo_mappings m
       JOIN combos c ON c.id = m.combo_id
       WHERE m.enabled = 1
       ORDER BY m.priority DESC, m.created_at ASC`).all())if((function(e){let t=e.replace(/[.+^${}()|[\]\\]/g,"\\$&").replace(/\*/g,".*").replace(/\?/g,".");return RegExp(`^${t}$`,"i")})(t.pattern).test(e))try{let e=JSON.parse(t.combo_data);if(!1===e.isActive)continue;return e}catch{continue}return null}e.s(["createModelComboMapping",0,i,"deleteModelComboMapping",0,u,"getModelComboMappingById",0,o,"getModelComboMappings",0,a,"resolveComboForModel",0,l,"updateModelComboMapping",0,s])},510864,e=>{"use strict";var t=e.i(504208),r=e.i(446202),n=e.i(886588);let a="id, bytes, created_at, filename, purpose, mime_type, api_key_id, expires_at, deleted_at";function o(e){let n=(0,t.getDbInstance)().prepare(`SELECT ${a} FROM files WHERE id = ? AND deleted_at IS NULL`).get(e);return n?(0,r.rowToCamel)(n):null}e.s(["countFiles",0,function(e={}){let r=(0,t.getDbInstance)(),{apiKeyId:n,purpose:a}=e,o="SELECT COUNT(*) as c FROM files WHERE deleted_at IS NULL",i=[];n&&(o+=" AND api_key_id = ?",i.push(n)),a&&(o+=" AND purpose = ?",i.push(a));let s=r.prepare(o).get(...i);return s?Number(s.c):0},"createFile",0,function(e){let r=(0,t.getDbInstance)(),a="file-"+(0,n.v4)().replaceAll("-","").substring(0,24),o=Math.floor(Date.now()/1e3),i=e.expiresAt;void 0===i&&"batch"===e.purpose&&(i=o+2592e3);let s={id:a,bytes:e.bytes,createdAt:o,filename:e.filename,purpose:e.purpose,content:e.content??null,mimeType:e.mimeType??null,apiKeyId:e.apiKeyId??null,expiresAt:i??null,deletedAt:null};return r.prepare(`
    INSERT INTO files (id, bytes, created_at, filename, purpose, content, mime_type, api_key_id, expires_at, deleted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(s.id,s.bytes,s.createdAt,s.filename,s.purpose,s.content,s.mimeType,s.apiKeyId,s.expiresAt,s.deletedAt),s},"deleteFile",0,function(e){return(0,t.getDbInstance)().prepare("UPDATE files SET deleted_at = ?, content = NULL WHERE id = ?").run(Math.floor(Date.now()/1e3),e).changes>0},"formatFileResponse",0,function(e){let t="number"==typeof e.createdAt&&Number.isFinite(e.createdAt)?e.createdAt:0,r="number"==typeof e.expiresAt&&Number.isFinite(e.expiresAt)?e.expiresAt:null;return{id:e.id,bytes:e.bytes,created_at:t,filename:e.filename,object:"file",purpose:e.purpose,expires_at:r}},"getFile",0,o,"getFileContent",0,function(e){let r=(0,t.getDbInstance)().prepare("SELECT content FROM files WHERE id = ? AND deleted_at IS NULL").get(e);return r?.content?Buffer.isBuffer(r.content)?r.content:Buffer.from(r.content):null},"listFiles",0,function(e={}){let n=(0,t.getDbInstance)(),{apiKeyId:i,purpose:s,limit:u=20,after:l,order:c="desc"}=e,d=`SELECT ${a} FROM files WHERE deleted_at IS NULL`,p=[];if(i&&(d+=" AND api_key_id = ?",p.push(i)),s&&(d+=" AND purpose = ?",p.push(s)),l){let e=o(l);e&&("desc"===c?d+=" AND (created_at < ? OR (created_at = ? AND id < ?))":d+=" AND (created_at > ? OR (created_at = ? AND id > ?))",p.push(e.createdAt,e.createdAt,l))}return d+=` ORDER BY created_at ${"asc"===c?"ASC":"DESC"}, id ${"asc"===c?"ASC":"DESC"} LIMIT ?`,p.push(u),n.prepare(d).all(...p).map(e=>(0,r.rowToCamel)(e))}],510864)},33900,e=>{"use strict";var t=e.i(504208),r=e.i(446202),n=e.i(510864),a=e.i(886588);function o(e){let t=(0,r.rowToCamel)(e);if(t.metadata&&"string"==typeof t.metadata)try{t.metadata=JSON.parse(t.metadata)}catch{t.metadata=null}if(t.errors&&"string"==typeof t.errors)try{t.errors=JSON.parse(t.errors)}catch{t.errors=null}if(t.usage&&"string"==typeof t.usage)try{t.usage=JSON.parse(t.usage)}catch{t.usage=null}let n=e=>{if("number"==typeof e&&Number.isFinite(e))return e;if(null==e)return null;let t=Number(e);return Number.isFinite(t)?t:null};return t.createdAt=n(t.createdAt)??0,t.inProgressAt=n(t.inProgressAt),t.expiresAt=n(t.expiresAt),t.finalizingAt=n(t.finalizingAt),t.completedAt=n(t.completedAt),t.failedAt=n(t.failedAt),t.expiredAt=n(t.expiredAt),t.cancellingAt=n(t.cancellingAt),t.cancelledAt=n(t.cancelledAt),t}function i(e){if(null==e)return null;if("string"!=typeof e)return e;try{return JSON.parse(e)}catch{return null}}function s(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM batches WHERE id = ?").get(e);return r?o(r):null}e.s(["countBatchItemCheckpoints",0,function(e){let r=(0,t.getDbInstance)().prepare("SELECT COUNT(*) AS c FROM batch_item_checkpoints WHERE batch_id = ?").get(e);return r?Number(r.c):0},"countBatches",0,function(e){let r=(0,t.getDbInstance)();if(e){let t=r.prepare("SELECT COUNT(*) as c FROM batches WHERE api_key_id = ?").get(e);return t?Number(t.c):0}{let e=r.prepare("SELECT COUNT(*) as c FROM batches").get();return e?Number(e.c):0}},"createBatch",0,function(e){let n=(0,t.getDbInstance)(),o="batch_"+(0,a.v4)().replaceAll("-","").substring(0,24),i=Math.floor(Date.now()/1e3),s={...e,id:o,createdAt:i,status:e.status||"validating",requestCountsTotal:0,requestCountsCompleted:0,requestCountsFailed:0,errors:e.errors||null,model:e.model||null,usage:e.usage||null,outputExpiresAfterSeconds:e.outputExpiresAfterSeconds||null,outputExpiresAfterAnchor:e.outputExpiresAfterAnchor||null},u=(0,r.objToSnake)({...s,metadata:s.metadata?JSON.stringify(s.metadata):null,errors:s.errors?JSON.stringify(s.errors):null,usage:s.usage?JSON.stringify(s.usage):null}),l=Object.keys(u),c=Object.values(u),d=l.map(()=>"?").join(", ");return n.prepare(`INSERT INTO batches (${l.join(", ")}) VALUES (${d})`).run(...c),s},"deleteBatch",0,function(e){let r=(0,t.getDbInstance)(),a=s(e);if(!a)return!1;if(r.prepare("DELETE FROM batch_item_checkpoints WHERE batch_id = ?").run(e),a.inputFileId)try{(0,n.deleteFile)(a.inputFileId)}catch{}if(a.outputFileId)try{(0,n.deleteFile)(a.outputFileId)}catch{}if(a.errorFileId)try{(0,n.deleteFile)(a.errorFileId)}catch{}return r.prepare("DELETE FROM batches WHERE id = ?").run(e).changes>0},"deleteCompletedBatches",0,function(){let e=(0,t.getDbInstance)(),r=e.prepare("SELECT input_file_id, output_file_id, error_file_id FROM batches WHERE status = 'completed'").all(),a=new Set;for(let e of r)e.input_file_id&&a.add(e.input_file_id),e.output_file_id&&a.add(e.output_file_id),e.error_file_id&&a.add(e.error_file_id);let o=0;for(let e of a)try{(0,n.deleteFile)(e)&&o++}catch{}return e.prepare("DELETE FROM batch_item_checkpoints WHERE batch_id IN (SELECT id FROM batches WHERE status = 'completed')").run(),{deletedBatches:e.prepare("DELETE FROM batches WHERE status = 'completed'").run().changes,deletedFiles:o}},"ensureBatchItemCheckpoints",0,function(e,r){if(0===r.length)return;let n=(0,t.getDbInstance)(),a=Math.floor(Date.now()/1e3),o=n.prepare(`
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
  `);n.transaction(()=>{for(let t of r)o.run(e,t.lineNumber,t.customId,a,a)})()},"getBatch",0,s,"getPendingBatches",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM batches WHERE status IN ('validating', 'in_progress', 'finalizing', 'cancelling')").all().map(e=>o(e))},"getTerminalBatches",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM batches WHERE status IN ('completed', 'failed', 'cancelled', 'expired') ORDER BY created_at ASC").all().map(e=>o(e))},"listBatchItemCheckpoints",0,function(e){return(0,t.getDbInstance)().prepare(`
      SELECT batch_id, line_number, custom_id, status, result_json, error_json, created_at, updated_at
      FROM batch_item_checkpoints
      WHERE batch_id = ?
      ORDER BY line_number ASC
    `).all(e).map(e=>({batchId:e.batch_id,lineNumber:Number(e.line_number),customId:e.custom_id??null,status:e.status,result:i(e.result_json),error:i(e.error_json),createdAt:Number(e.created_at),updatedAt:Number(e.updated_at)}))},"listBatches",0,function(e,r=20,n){let a=(0,t.getDbInstance)(),i=n?s(n):null;return(e?i?a.prepare("SELECT * FROM batches WHERE api_key_id = ? AND (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC LIMIT ?").all(e,i.createdAt,i.createdAt,n,r):a.prepare("SELECT * FROM batches WHERE api_key_id = ? ORDER BY created_at DESC, id DESC LIMIT ?").all(e,r):i?a.prepare("SELECT * FROM batches WHERE (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC LIMIT ?").all(i.createdAt,i.createdAt,n,r):a.prepare("SELECT * FROM batches ORDER BY created_at DESC, id DESC LIMIT ?").all(r)).map(e=>o(e))},"markBatchItemError",0,function(e,r,n){let a=(0,t.getDbInstance)(),o=Math.floor(Date.now()/1e3);a.prepare(`
    UPDATE batch_item_checkpoints
    SET custom_id = ?,
        status = 'errored',
        result_json = NULL,
        error_json = ?,
        updated_at = ?
    WHERE batch_id = ? AND line_number = ?
  `).run(r.customId,JSON.stringify(n),o,e,r.lineNumber)},"markBatchItemProcessing",0,function(e,r){let n=(0,t.getDbInstance)(),a=Math.floor(Date.now()/1e3);n.prepare(`
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
  `).run(e,r.lineNumber,r.customId,a,a)},"markBatchItemResult",0,function(e,r,n){let a=(0,t.getDbInstance)(),o=Math.floor(Date.now()/1e3);a.prepare(`
    UPDATE batch_item_checkpoints
    SET custom_id = ?,
        status = 'completed',
        result_json = ?,
        error_json = NULL,
        updated_at = ?
    WHERE batch_id = ? AND line_number = ?
  `).run(r.customId,JSON.stringify(n),o,e,r.lineNumber)},"updateBatch",0,function(e,n){let a=(0,t.getDbInstance)(),o=(0,r.objToSnake)(n);o.metadata&&"string"!=typeof o.metadata&&(o.metadata=JSON.stringify(o.metadata)),o.errors&&"string"!=typeof o.errors&&(o.errors=JSON.stringify(o.errors)),o.usage&&"string"!=typeof o.usage&&(o.usage=JSON.stringify(o.usage));let i=Object.keys(o);if(0===i.length)return!1;let s=i.map(e=>`${e} = ?`).join(", "),u=Object.values(o);return a.prepare(`UPDATE batches SET ${s} WHERE id = ?`).run(...u,e).changes>0}])},825849,e=>{"use strict";var t=e.i(504208),r=e.i(254799);function n(e){return{...e,kind:e.kind||"custom",events:JSON.parse(e.events||'["*"]'),enabled:1===e.enabled}}function a(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM webhooks WHERE id = ?").get(e);return r?n(r):null}e.s(["createWebhook",0,function(e){let n=(0,t.getDbInstance)(),o=r.default.randomUUID(),i=e.secret||`whsec_${r.default.randomBytes(24).toString("hex")}`,s=e.kind||"custom";return n.prepare(`INSERT INTO webhooks (id, url, events, secret, description, kind, metadata_encrypted)
       VALUES (?, ?, ?, ?, ?, ?, ?)`).run(o,e.url,JSON.stringify(e.events||["*"]),i,e.description||"",s,e.metadataEncrypted??null),a(o)},"deleteWebhook",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM webhooks WHERE id = ?").run(e).changes>0},"disableWebhooksWithHighFailures",0,function(e=10){return(0,t.getDbInstance)().prepare("UPDATE webhooks SET enabled = 0 WHERE failure_count >= ? AND enabled = 1").run(e).changes},"getEnabledWebhooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM webhooks WHERE enabled = 1").all().map(n)},"getWebhook",0,a,"getWebhooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM webhooks ORDER BY created_at DESC").all().map(n)},"recordWebhookDelivery",0,function(e,r,n){let a=(0,t.getDbInstance)();n?a.prepare("UPDATE webhooks SET last_triggered_at = datetime('now'), last_status = ?, failure_count = 0 WHERE id = ?").run(r,e):a.prepare("UPDATE webhooks SET last_triggered_at = datetime('now'), last_status = ?, failure_count = failure_count + 1 WHERE id = ?").run(r,e)},"updateWebhook",0,function(e,r){let n=(0,t.getDbInstance)(),o=a(e);if(!o)return null;let i=[],s=[];return(void 0!==r.url&&(i.push("url = ?"),s.push(r.url)),void 0!==r.events&&(i.push("events = ?"),s.push(JSON.stringify(r.events))),void 0!==r.secret&&(i.push("secret = ?"),s.push(r.secret)),void 0!==r.enabled&&(i.push("enabled = ?"),s.push(+!!r.enabled)),void 0!==r.description&&(i.push("description = ?"),s.push(r.description)),void 0!==r.kind&&(i.push("kind = ?"),s.push(r.kind)),void 0!==r.metadataEncrypted&&(i.push("metadata_encrypted = ?"),s.push(r.metadataEncrypted)),0===i.length)?o:(s.push(e),n.prepare(`UPDATE webhooks SET ${i.join(", ")} WHERE id = ?`).run(...s),a(e))}])},788468,e=>{"use strict";var t=e.i(504208),r=e.i(347263);e.s(["getDeliveries",0,function(e,r){return(0,t.getDbInstance)().prepare(`SELECT id, webhook_id, event_type, status, http_status, latency_ms, error, created_at
       FROM webhook_deliveries
       WHERE webhook_id = ?
       ORDER BY created_at DESC, id DESC
       LIMIT ?`).all(e,r)},"insertDelivery",0,function(e){let n=(0,t.getDbInstance)(),a=n.prepare(`INSERT INTO webhook_deliveries
       (webhook_id, event_type, status, http_status, latency_ms, error, payload_snapshot)
     VALUES (?, ?, ?, ?, ?, ?, ?)`),o=n.prepare(`DELETE FROM webhook_deliveries
     WHERE webhook_id = ?
       AND id NOT IN (
         SELECT id FROM webhook_deliveries
         WHERE webhook_id = ?
         ORDER BY created_at DESC, id DESC
         LIMIT ?
       )`),i=null!=e.error&&(0,r.sanitizeErrorMessage)(e.error)||null;n.transaction(()=>{a.run(e.webhookId,e.eventType,e.status,e.httpStatus??null,e.latencyMs??null,i,e.payloadSnapshot??null),o.run(e.webhookId,e.webhookId,100)})()}])},912386,e=>{"use strict";var t=e.i(504208);function r(e){let t;if(e.models)try{let r=JSON.parse(e.models);Array.isArray(r)&&(t=r.map(String))}catch{t=void 0}return{id:e.id,providerId:e.provider_id,method:e.method,endpoint:e.endpoint,authType:e.auth_type??"none",models:t,rateLimit:e.rate_limit,feasibility:e.feasibility??0,riskLevel:e.risk_level??"none",status:e.status,notes:e.notes,discoveredAt:e.discovered_at,verifiedAt:e.verified_at}}function n(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM discovery_results WHERE id = ?").get(e);return n?r(n):null}e.s(["deleteDiscoveryResult",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM discovery_results WHERE id = ?").run(e).changes>0},"getDiscoveryResultById",0,n,"getDiscoveryResults",0,function(e){let n=(0,t.getDbInstance)();return(e?n.prepare("SELECT * FROM discovery_results WHERE provider_id = ? ORDER BY discovered_at DESC, id DESC").all(e):n.prepare("SELECT * FROM discovery_results ORDER BY discovered_at DESC, id DESC").all()).map(r)},"markVerified",0,function(e){return 0===(0,t.getDbInstance)().prepare("UPDATE discovery_results SET status = 'verified', verified_at = datetime('now') WHERE id = ?").run(e).changes?null:n(e)},"upsertDiscoveryResult",0,function(e){let n=(0,t.getDbInstance)(),a=e.models?JSON.stringify(e.models):null;return n.prepare(`INSERT INTO discovery_results
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
       WHERE provider_id = ? AND method = ? AND ifnull(endpoint, '') = ifnull(?, '')`).get(e.providerId,e.method,e.endpoint??null))}])},110002,e=>{"use strict";var t=e.i(504208),r=e.i(446202);let n=0;e.s(["cleanupOldSnapshots",0,function(e=90){let r=Date.now();if(r-n<216e5)return 0;let a=(0,t.getDbInstance)(),o=new Date(Date.now()-24*e*36e5).toISOString();try{let e=a.prepare("DELETE FROM quota_snapshots WHERE created_at < ?").run(o);return n=r,e.changes}catch(e){if(e?.message?.includes("no such table"))return 0;throw e}},"getAggregatedSnapshots",0,function(e){let r=(0,t.getDbInstance)(),n=["created_at >= ?"],a=[e.since];e.provider&&(n.push("provider = ?"),a.push(e.provider)),e.until&&(n.push("created_at <= ?"),a.push(e.until));let o=60*Number(e.bucketMinutes);if(!Number.isFinite(o)||o<=0)throw Error("Invalid bucket size");let i="connection"===e.aggregateBy?"bucket, provider, connection_id, window_key":"bucket, provider, window_key",s="connection"===e.aggregateBy?"provider || ':' || connection_id as provider":"provider";try{let e=`
      SELECT
        datetime((strftime('%s', created_at) / ${o}) * ${o}, 'unixepoch') as bucket,
        ${s},
        AVG(remaining_percentage) as remainingPct,
        MAX(is_exhausted) as isExhausted,
        window_key
      FROM quota_snapshots
      WHERE ${n.join(" AND ")}
      GROUP BY ${i}
      ORDER BY bucket ASC
    `;return r.prepare(e).all(...a).map(e=>({timestamp:e.bucket,provider:e.provider,remainingPct:e.remainingPct??0,isExhausted:1===e.isExhausted,windowKey:e.windowKey}))}catch(e){if(e?.message?.includes("no such table"))return[];throw e}},"getQuotaSnapshots",0,function(e){let n=(0,t.getDbInstance)(),a=["created_at >= ?"],o=[e.since];e.provider&&(a.push("provider = ?"),o.push(e.provider)),e.connectionId&&(a.push("connection_id = ?"),o.push(e.connectionId)),e.until&&(a.push("created_at <= ?"),o.push(e.until));try{let e=`SELECT * FROM quota_snapshots WHERE ${a.join(" AND ")} ORDER BY created_at ASC`;return n.prepare(e).all(...o).map(e=>(0,r.rowToCamel)(e))}catch(e){if(e?.message?.includes("no such table"))return[];throw e}},"saveQuotaSnapshot",0,function(e){let r=(0,t.getDbInstance)(),n=new Date().toISOString();try{r.prepare(`INSERT INTO quota_snapshots
       (provider, connection_id, window_key, remaining_percentage, is_exhausted,
        next_reset_at, window_duration_ms, raw_data, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(e.provider,e.connection_id,e.window_key,e.remaining_percentage,e.is_exhausted,e.next_reset_at,e.window_duration_ms,e.raw_data,n)}catch(e){if(e?.message?.includes("no such table"))return void console.warn("[QuotaSnapshots] Skipping save: quota_snapshots table not found. Awaiting migration.");throw e}}])},188356,e=>{"use strict";var t=e.i(254799),r=e.i(504208);let n="session_account_affinity",a=null;function o(e){return Number.isFinite(e)&&Number(e)>0?Number(e):0}function i(e,r){let n=(0,t.createHash)("sha256").update(`${r}:${e}`).digest("hex");return`${r}:${n}`}function s(e){return new Date(e).toISOString()}function u(e){if("string"!=typeof e)return null;try{let t=JSON.parse(e);if("string"!=typeof t.connectionId||0===t.connectionId.trim().length||"string"!=typeof t.expiresAt||Number.isNaN(Date.parse(t.expiresAt)))return null;return{connectionId:t.connectionId,createdAt:"string"!=typeof t.createdAt||Number.isNaN(Date.parse(t.createdAt))?t.expiresAt:t.createdAt,lastUsedAt:"string"!=typeof t.lastUsedAt||Number.isNaN(Date.parse(t.lastUsedAt))?t.expiresAt:t.lastUsedAt,expiresAt:t.expiresAt}}catch{return null}}function l(e){(0,r.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(n,e)}function c(e,t,a=0,s=Date.now()){if(!e||!t||0>=o(a))return null;let d=i(e,t),p=(0,r.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(n,d),_=u(p?.value);return _?Date.parse(_.expiresAt)<=s?(l(d),null):_:null}function d(e,t,a,u=Date.now(),l=0){let p=o(l);if(!e||!t||!a||p<=0)return;let _=i(e,t),E=c(e,t,p,u),m=s(u),g={connectionId:a,createdAt:E?.createdAt??m,lastUsedAt:m,expiresAt:s(u+p)};(0,r.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(n,_,JSON.stringify(g))}function p(e=18e5,t=Date.now()){let a=(0,r.getDbInstance)(),o=a.prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(n),i=0;return a.transaction(()=>{for(let e of o){if("string"!=typeof e.key)continue;let r=u(e.value);(!r||Date.parse(r.expiresAt)<=t)&&(a.prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(n,e.key),i++)}})(),i}e.s(["cleanupStaleSessionAccountAffinities",0,p,"deleteSessionAccountAffinity",0,function(e,t){e&&t&&l(i(e,t))},"evictSessionAccountAffinityForConnection",0,function(e,t,a){if(!e||!t||!a)return!1;let o=i(e,t),s=(0,r.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(n,o),c=u(s?.value);return!!c&&c.connectionId===a&&(l(o),!0)},"getSessionAccountAffinity",0,c,"startSessionAccountAffinityCleanup",0,function(){if(!a){try{p()}catch(e){console.warn("[SESSION_AFFINITY] Startup cleanup failed:",e)}"object"==typeof(a=setInterval(()=>{try{p()}catch(e){console.warn("[SESSION_AFFINITY] Periodic cleanup failed:",e)}},3e5))&&"unref"in a&&a.unref?.()}},"stopSessionAccountAffinityCleanupForTests",0,function(){a&&(clearInterval(a),a=null)},"touchSessionAccountAffinity",0,function(e,t,r=Date.now(),n=0){let a=o(n);if(a<=0)return;let i=c(e,t,a,r);i&&d(e,t,i.connectionId,r,a)},"upsertSessionAccountAffinity",0,d])},689724,e=>{"use strict";var t=e.i(504208);function r(e){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim()){let t=Number(e);return Number.isFinite(t)?t:null}return null}function n(e){return null!==e&&Number.isFinite(e)?Math.max(0,Math.min(100,e)):null}function a(e){let t=n(e);return null===t?null:Math.max(0,Math.min(100,100-t))}function o(e,t){return null!==e&&(t<=1&&e>t||e-t>=5)}function i(e){if(!e)return null;let t=Date.parse(e);return Number.isFinite(t)?new Date(t).toISOString():null}function s(e){let t=i(e);return t?t.slice(0,10):null}function u(e,r,l=Date.now()){let c=function(e,r,n=Date.now()){if(!e||!r)return null;let a=s(r);if(!a)return null;let o=(0,t.getDbInstance)(),u=new Date(n).toISOString();try{for(let t of o.prepare(`
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
      `).all({connectionId:e,nowIso:u}))if(s(t.windowResetsAt)===a)return i(t.windowStartedAt);return null}catch(e){if(e instanceof Error&&e.message.includes("no such table"))return null;throw e}}(e,r,l),d=function(e,r,u=Date.now()){if(!e||!r)return null;let l=s(r);if(!l)return null;let c=(0,t.getDbInstance)(),d=new Date(u).toISOString();try{let t=c.prepare(`
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
      `).all({connectionId:e,nowIso:d}),r=null,u=null,p=null;for(let e of t){let t=i(e.createdAt);if(!t||s(e.nextResetAt)!==l)continue;r||(r=t);let c=a(n(e.remainingPercentage));null!==c&&(o(p,c)&&(u=t),p=c)}if(u)return{windowStartIso:u,resetDrop:!0};if(r)return{windowStartIso:r,resetDrop:!1};return null}catch(e){if(e instanceof Error&&e.message.includes("no such table"))return null;throw e}}(e,r,l);if(!c&&!d)return null;if(!c&&d)return{windowStartIso:d.windowStartIso,source:"observed_snapshot_reset"};if(c&&!d)return{windowStartIso:c,source:"recorded_reset_event"};let p=Date.parse(c),_=Date.parse(d.windowStartIso);return d.resetDrop&&Number.isFinite(p)&&Number.isFinite(_)&&_>p?{windowStartIso:d.windowStartIso,source:"observed_snapshot_reset"}:{windowStartIso:c,source:"recorded_reset_event"}}e.s(["getProviderQuotaWindowStart",0,u,"getProviderQuotaWindowStartIso",0,function(e,t,r=Date.now()){return u(e,t,r)?.windowStartIso??null},"recordProviderQuotaResetEventIfChanged",0,function(e){let u;if(!e.connectionId||!e.windowKey||!(((u=e.windowKey.toLowerCase().replace(/[^a-z0-9]+/g," ").trim()).includes("weekly")||u.includes("7d"))&&!u.includes("sonnet")))return;let l=i(e.currentResetAt);if(!l)return;let c=e.previousObservation??function(e,n){let a=(0,t.getDbInstance)();try{let t=a.prepare(`
        SELECT
          next_reset_at as nextResetAt,
          remaining_percentage as remainingPercentage
        FROM quota_snapshots
        WHERE connection_id = ?
          AND LOWER(window_key) = LOWER(?)
          AND next_reset_at IS NOT NULL
        ORDER BY created_at DESC, id DESC
        LIMIT 1
      `).get(e,n);if(!t)return null;return{resetAt:t.nextResetAt,remainingPercentage:r(t.remainingPercentage)}}catch(e){if(e instanceof Error&&e.message.includes("no such table"))return null;throw e}}(e.connectionId,e.windowKey),d=i(c?.resetAt??null);if(!d)return;let p=Date.parse(d),_=Date.parse(l);if(!Number.isFinite(p)||!Number.isFinite(_))return;let E=n(r(c?.remainingPercentage)),m=n(r(e.currentRemainingPercentage)),g=i(e.observedAt??null)??new Date().toISOString(),y=a(E),S=a(m),f=_>p&&s(d)!==s(l),T=s(d)===s(l)&&null!==S&&o(y,S);if(!f&&!T)return;let R=f?d:g;try{(0,t.getDbInstance)().prepare(`
      INSERT OR IGNORE INTO provider_quota_reset_events
        (provider, connection_id, window_key, window_started_at, window_resets_at,
         observed_at, previous_remaining_percentage, new_remaining_percentage,
         previous_used_percentage, new_used_percentage, raw_data)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(e.provider,e.connectionId,e.windowKey,R,l,g,E,m,y,S,null)}catch(e){if(e instanceof Error&&e.message.includes("no such table"))return;throw e}}])},620561,e=>{"use strict";var t=e.i(504208);function r(e){if(null===e)return null;try{return JSON.stringify(e)}catch{return null}}function n(e){let t=e&&"object"==typeof e?e:{};return{id:"number"==typeof t.id?t.id:0,tool:"string"==typeof t.tool?t.tool:"",currentVersion:null===t.current_version?null:"string"==typeof t.current_version?t.current_version:null,installedVersion:null===t.installed_version?null:"string"==typeof t.installed_version?t.installed_version:null,pinnedVersion:null===t.pinned_version?null:"string"==typeof t.pinned_version?t.pinned_version:null,binaryPath:null===t.binary_path?null:"string"==typeof t.binary_path?t.binary_path:null,status:"string"==typeof t.status?t.status:"not_installed",pid:null===t.pid?null:"number"==typeof t.pid?t.pid:null,port:"number"==typeof t.port?t.port:8317,apiKey:null===t.api_key?null:"string"==typeof t.api_key?t.api_key:null,managementKey:null===t.management_key?null:"string"==typeof t.management_key?t.management_key:null,autoUpdate:1===t.auto_update||!0===t.auto_update||"1"===t.auto_update,autoStart:1===t.auto_start||!0===t.auto_start||"1"===t.auto_start,lastHealthCheck:null===t.last_health_check?null:"string"==typeof t.last_health_check?t.last_health_check:null,lastUpdateCheck:null===t.last_update_check?null:"string"==typeof t.last_update_check?t.last_update_check:null,healthStatus:"string"==typeof t.health_status?t.health_status:"unknown",configOverrides:function(e){if(!e||"string"!=typeof e||""===e.trim())return null;try{let t=JSON.parse(e);return"object"==typeof t&&null!==t?t:null}catch{return null}}(t.config_overrides),errorMessage:null===t.error_message?null:"string"==typeof t.error_message?t.error_message:null,createdAt:"string"==typeof t.created_at?t.created_at:"",updatedAt:"string"==typeof t.updated_at?t.updated_at:"",logsBufferPath:null===t.logs_buffer_path?null:"string"==typeof t.logs_buffer_path?t.logs_buffer_path:null,providerExpose:1===t.provider_expose||!0===t.provider_expose||"1"===t.provider_expose,lastSyncAt:null===t.last_sync_at?null:"string"==typeof t.last_sync_at?t.last_sync_at:null}}async function a(){return(0,t.getDbInstance)().prepare("SELECT * FROM version_manager").all().map(n)}async function o(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM version_manager WHERE tool = ?").get(e);return r?n(r):null}async function i(e){(0,t.getDbInstance)().prepare(`
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
  `).run(e.tool,e.currentVersion??null,e.installedVersion??null,e.pinnedVersion??null,e.binaryPath??null,e.status??"not_installed",e.pid??null,e.port??8317,e.apiKey??null,e.managementKey??null,void 0!==e.autoUpdate?+!!e.autoUpdate:1,void 0!==e.autoStart?+!!e.autoStart:0,e.healthStatus??"unknown",r(e.configOverrides??null),e.errorMessage??null);let n=await o(e.tool);if(!n)throw Error("Failed to retrieve inserted version manager tool");return n}async function s(e,n){let a=(0,t.getDbInstance)();if(!await o(e))return null;let i=new Set(["currentVersion","installedVersion","pinnedVersion","binaryPath","status","pid","port","apiKey","managementKey","autoUpdate","autoStart","healthStatus","configOverrides","errorMessage","logsBufferPath","providerExpose","lastSyncAt"]),s=["updated_at = datetime('now')"],u={tool:e};for(let[e,t]of Object.entries(n)){if(!i.has(e))continue;let n=e.replace(/([A-Z])/g,"_$1").toLowerCase();"configOverrides"===e?(s.push("config_overrides = @configOverrides"),u.configOverrides=r(t)):"autoUpdate"===e||"autoStart"===e||"providerExpose"===e?(s.push(`${n} = @${e}`),u[e]=+(!0===t)):null===t?s.push(`${n} = null`):(s.push(`${n} = @${e}`),u[e]=t)}return a.prepare(`UPDATE version_manager SET ${s.join(", ")} WHERE tool = @tool`).run(u),o(e)}async function u(e){return(0,t.getDbInstance)().prepare("DELETE FROM version_manager WHERE tool = ?").run(e).changes>0}async function l(e,r){return(0,t.getDbInstance)().prepare("UPDATE version_manager SET health_status = ?, last_health_check = datetime('now') WHERE tool = ?").run(r,e).changes>0}async function c(e,r,n){return(0,t.getDbInstance)().prepare(`UPDATE version_manager SET ${r} = ?, updated_at = datetime('now') WHERE tool = ?`).run(n,e).changes>0}async function d(e,r,n,a){return(0,t.getDbInstance)().prepare(void 0!==n?"UPDATE version_manager SET status = ?, pid = ?, error_message = ?, updated_at = datetime('now') WHERE tool = ?":"UPDATE version_manager SET status = ?, error_message = ?, updated_at = datetime('now') WHERE tool = ?").run(...void 0!==n?[r,n,a??null,e]:[r,a??null,e]).changes>0}async function p(e){return o(e)}let _=new Set(["logsBufferPath","providerExpose","lastSyncAt","status","pid","port","apiKey","autoStart","autoUpdate","healthStatus","errorMessage","currentVersion","installedVersion","binaryPath"]);async function E(e,t,r){if(!_.has(t))throw Error(`updateServiceField: field "${t}" is not in the allowed list`);return s(e,{[t]:r})}e.s(["deleteVersionManagerTool",0,u,"getServiceRow",0,p,"getVersionManagerStatus",0,a,"getVersionManagerTool",0,o,"setToolStatus",0,d,"updateServiceField",0,E,"updateToolHealth",0,l,"updateToolVersion",0,c,"updateVersionManagerTool",0,s,"upsertVersionManagerTool",0,i])},104472,e=>{"use strict";var t=e.i(886588),r=e.i(504208),n=e.i(446202),a=e.i(223194);function o(e){var t;let r=(t=(0,n.rowToCamel)(e))&&"object"==typeof t&&!Array.isArray(t)?t:{};return"string"!=typeof r.id||"string"!=typeof r.name?null:{id:r.id,name:r.name,tokenHash:"string"==typeof r.tokenHash?r.tokenHash:"",syncApiKeyId:"string"==typeof r.syncApiKeyId?r.syncApiKeyId:null,revokedAt:"string"==typeof r.revokedAt?r.revokedAt:null,lastUsedAt:"string"==typeof r.lastUsedAt?r.lastUsedAt:null,createdAt:"string"==typeof r.createdAt?r.createdAt:new Date().toISOString(),updatedAt:"string"==typeof r.updatedAt?r.updatedAt:new Date().toISOString()}}function i(e){e.exec(`
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
  `)}async function s(){let e=(0,r.getDbInstance)();return i(e),e.prepare("SELECT * FROM sync_tokens ORDER BY datetime(created_at) DESC, name COLLATE NOCASE ASC").all().map(e=>o(e)).filter(e=>null!==e)}async function u(e){let t=(0,r.getDbInstance)();return i(t),o(t.prepare("SELECT * FROM sync_tokens WHERE id = ?").get(e))}async function l(e){let t=(0,r.getDbInstance)();return i(t),o(t.prepare("SELECT * FROM sync_tokens WHERE token_hash = ?").get(e))}async function c(e){let n=(0,r.getDbInstance)();i(n);let o=new Date().toISOString(),s={id:(0,t.v4)(),name:e.name,tokenHash:e.tokenHash,syncApiKeyId:e.syncApiKeyId||null,revokedAt:null,lastUsedAt:null,createdAt:o,updatedAt:o};return n.prepare(`INSERT INTO sync_tokens (
      id, name, token_hash, sync_api_key_id, revoked_at, last_used_at, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(s.id,s.name,s.tokenHash,s.syncApiKeyId,s.revokedAt,s.lastUsedAt,s.createdAt,s.updatedAt),(0,a.backupDbFile)("pre-write"),s}async function d(e){let t=(0,r.getDbInstance)();i(t);let n=await u(e);if(!n)return null;if(n.revokedAt)return n;let o=new Date().toISOString();return t.prepare("UPDATE sync_tokens SET revoked_at = ?, updated_at = ? WHERE id = ?").run(o,o,e),(0,a.backupDbFile)("pre-write"),await u(e)}async function p(e,t=new Date().toISOString()){let n=(0,r.getDbInstance)();return i(n),Number(n.prepare("UPDATE sync_tokens SET last_used_at = ?, updated_at = ? WHERE id = ?").run(t,t,e).changes||0)>0}e.s(["createSyncTokenRecord",0,c,"getSyncTokenByHash",0,l,"getSyncTokenById",0,u,"listSyncTokens",0,s,"revokeSyncToken",0,d,"touchSyncTokenLastUsed",0,p])},653900,e=>{"use strict";var t=e.i(504208);function r(e){return e&&"object"==typeof e?e:{}}let n=["metadata.google.internal","169.254.169.254","metadata.aws.internal"];function a(e){let t=null;if(e.cliproxyapi_model_mapping&&"string"==typeof e.cliproxyapi_model_mapping)try{t=JSON.parse(e.cliproxyapi_model_mapping)}catch{t=null}return{id:e.id,providerId:e.provider_id,mode:e.mode,cliproxyapiModelMapping:t,nativePriority:e.native_priority,cliproxyapiPriority:e.cliproxyapi_priority,enabled:1===e.enabled||!0===e.enabled,family:"string"==typeof e.family?e.family:"auto",createdAt:e.created_at,updatedAt:e.updated_at}}async function o(){return(0,t.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config ORDER BY provider_id").all().map(e=>a(r(e)))}async function i(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config WHERE provider_id = ?").get(e);return n?a(r(n)):null}async function s(e){let r=(0,t.getDbInstance)(),n=e.mode??"native",a=void 0!==e.cliproxyapiModelMapping?JSON.stringify(e.cliproxyapiModelMapping):null,o=e.nativePriority??1,s=e.cliproxyapiPriority??2,u=+(!1!==e.enabled),l=e.family??"auto";return r.prepare(`INSERT INTO upstream_proxy_config
     (provider_id, mode, cliproxyapi_model_mapping, native_priority, cliproxyapi_priority, enabled, family, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
     ON CONFLICT(provider_id) DO UPDATE SET
       mode = excluded.mode,
       cliproxyapi_model_mapping = excluded.cliproxyapi_model_mapping,
       native_priority = excluded.native_priority,
       cliproxyapi_priority = excluded.cliproxyapi_priority,
       enabled = excluded.enabled,
       family = excluded.family,
       updated_at = datetime('now')`).run(e.providerId,n,a,o,s,u,l),i(e.providerId)}async function u(e,r){let n=(0,t.getDbInstance)();if(!await i(e))throw Error(`Provider ${e} not found`);let a=["updated_at = datetime('now')"],o=[];return void 0!==r.mode&&(a.push("mode = ?"),o.push(r.mode)),void 0!==r.cliproxyapiModelMapping&&(a.push("cliproxyapi_model_mapping = ?"),o.push(null===r.cliproxyapiModelMapping?null:JSON.stringify(r.cliproxyapiModelMapping))),void 0!==r.nativePriority&&(a.push("native_priority = ?"),o.push(r.nativePriority)),void 0!==r.cliproxyapiPriority&&(a.push("cliproxyapi_priority = ?"),o.push(r.cliproxyapiPriority)),void 0!==r.enabled&&(a.push("enabled = ?"),o.push(+(!0===r.enabled))),void 0!==r.family&&(a.push("family = ?"),o.push(r.family)),o.push(e),n.prepare(`UPDATE upstream_proxy_config SET ${a.join(", ")} WHERE provider_id = ?`).run(...o),i(e)}async function l(e){return(0,t.getDbInstance)().prepare("DELETE FROM upstream_proxy_config WHERE provider_id = ?").run(e).changes>0}async function c(e){return(0,t.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config WHERE mode = ? AND enabled = 1 ORDER BY provider_id").all(e).map(e=>a(r(e)))}async function d(e){let t=await i(e);if(!t)return[];let r=[];return t.enabled&&(r.push({executor:"native",priority:t.nativePriority}),("cliproxyapi"===t.mode||"fallback"===t.mode)&&r.push({executor:"cliproxyapi",priority:t.cliproxyapiPriority})),r.sort((e,t)=>e.priority-t.priority),r}e.s(["deleteUpstreamProxyConfig",0,l,"getFallbackChainForProvider",0,d,"getProvidersByMode",0,c,"getUpstreamProxyConfig",0,i,"getUpstreamProxyConfigs",0,o,"updateUpstreamProxyConfig",0,u,"upsertUpstreamProxyConfig",0,s,"validateProxyUrl",0,function(e){try{var t;let r=new URL(e);if(!["http:","https:"].includes(r.protocol))return{valid:!1,error:`Unsupported protocol "${r.protocol}" — use http or https`};if(t=r.hostname,"localhost"!==t&&"127.0.0.1"!==t&&"::1"!==t&&(n.includes(t)||/^10\./.test(t)||/^172\.(1[6-9]|2\d|3[01])\./.test(t)||/^192\.168\./.test(t)||/^0\./.test(t)||/^127\./.test(t)||/^224\./.test(t)||/^169\.254\./.test(t)||0))return{valid:!1,error:`Proxy URL cannot point to private/internal address "${r.hostname}"`};return{valid:!0,url:e}}catch{return{valid:!1,error:`Invalid URL: "${e}"`}}}])},91973,e=>{"use strict";var t=e.i(504208);let r="providerLimitsCache";function n(e){try{return JSON.parse(e)}catch{return null}}function a(e){return e&&"object"==typeof e&&!Array.isArray(e)?e:null}function o(e){let t=a(e);if(!t)return null;let r="string"==typeof t.fetchedAt&&t.fetchedAt.trim()?t.fetchedAt:null;if(!r)return null;let n=Number(t.bankedResetCredits);return{quotas:a(t.quotas),plan:t.plan??null,message:"string"==typeof t.message?t.message:null,fetchedAt:r,source:"string"==typeof t.source?t.source:null,...Number.isFinite(n)?{bankedResetCredits:n}:{}}}e.s(["deleteProviderLimitsCache",0,function(e){t.isBuildPhase||t.isCloud||(0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(r,e)},"getAllProviderLimitsCache",0,function(){if(t.isBuildPhase||t.isCloud)return{};let e=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(r),a={};for(let t of e){let e=o(n(t.value));e&&(a[t.key]=e)}return a},"getProviderLimitsCache",0,function(e){if(t.isBuildPhase||t.isCloud)return null;let a=(0,t.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(r,e);return a?.value?o(n(a.value)):null},"setProviderLimitsCache",0,function(e,n){return t.isBuildPhase||t.isCloud||(0,t.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(r,e,JSON.stringify(n)),n},"setProviderLimitsCacheBatch",0,function(e){if(t.isBuildPhase||t.isCloud||0===e.length)return 0;let n=(0,t.getDbInstance)(),a=n.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)");return n.transaction(e=>{for(let t of e)a.run(r,t.connectionId,JSON.stringify(t.entry))})(e),e.length}])},490484,e=>{"use strict";var t=e.i(504208);let r="antigravityCreditBalance";function n(e){try{return JSON.parse(e)}catch{return null}}e.s(["getAllPersistedCreditBalances",0,function(){let e=new Map;if(t.isBuildPhase||t.isCloud)return e;for(let a of(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(r)){let t=n(a.value);t&&"number"==typeof t.balance&&e.set(a.key,t.balance)}return e},"getPersistedCreditBalance",0,function(e){if(t.isBuildPhase||t.isCloud)return null;let a=(0,t.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(r,e);if(!a?.value)return null;let o=n(a.value);return o&&"number"==typeof o.balance?o.balance:null},"persistCreditBalance",0,function(e,n){if(t.isBuildPhase||t.isCloud)return;let a=(0,t.getDbInstance)(),o={balance:n,updatedAt:new Date().toISOString()};a.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(r,e,JSON.stringify(o))}])},389769,e=>{"use strict";var t=e.i(504208);let r=null,n=[["actual_prompt_tokens","INTEGER"],["actual_completion_tokens","INTEGER"],["actual_total_tokens","INTEGER"],["actual_cache_read_tokens","INTEGER"],["actual_cache_write_tokens","INTEGER"],["estimated_usd_saved","REAL"],["mcp_description_tokens_saved","INTEGER DEFAULT 0"],["multimodal_skip_count","INTEGER DEFAULT 0"],["receipt_source","TEXT"],["validation_fallback","INTEGER DEFAULT 0"],["output_mode","TEXT"],["compression_combo_id","TEXT"],["engine","TEXT"],["rtk_raw_output_pointer","TEXT"],["rtk_raw_output_bytes","INTEGER"],["rtk_raw_output_pointers","TEXT"],["rtk_raw_output_total_bytes","INTEGER"],["skip_reason","TEXT"]];function a(){let e=(0,t.getDbInstance)();if(r===e)return;let a=new Set(e.prepare("PRAGMA table_info(compression_analytics)").all().map(e=>e.name));for(let[t,r]of n)a.has(t)||e.exec(`ALTER TABLE compression_analytics ADD COLUMN ${t} ${r}`);r=e}function o(e,t){return e?`${e} AND ${t}`:`WHERE ${t}`}e.s(["getCompressionAnalyticsSummary",0,function(e){let r=(0,t.getDbInstance)();a();let n=null;"24h"===e?n=new Date(Date.now()-864e5).toISOString():"7d"===e?n=new Date(Date.now()-6048e5).toISOString():"30d"===e&&(n=new Date(Date.now()-2592e6).toISOString());let i=n?"WHERE timestamp >= ?":"",s=n?[n]:[],u=o(i,"skip_reason IS NULL"),l=r.prepare(`
    SELECT
      COUNT(*) as total,
      COALESCE(SUM(tokens_saved), 0) as totalSaved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct,
      COALESCE(AVG(duration_ms), 0) as avgDur
    FROM compression_analytics ${u}
  `).get(...s),c=r.prepare(`
    SELECT mode, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct
    FROM compression_analytics ${u}
    GROUP BY mode
  `).all(...s),d=r.prepare(`
    SELECT mode, COUNT(*) as cnt
    FROM compression_analytics ${o(i,"skip_reason IS NOT NULL")}
    GROUP BY mode
  `).all(...s),p={};for(let e of c)p[e.mode]={count:e.cnt,tokensSaved:e.saved,avgSavingsPct:Math.round(e.avgPct),skipped:0};for(let e of d)p[e.mode]?p[e.mode].skipped=e.cnt:p[e.mode]={count:0,tokensSaved:0,avgSavingsPct:0,skipped:e.cnt};let _=r.prepare(`
    SELECT COALESCE(engine, mode) as engine, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct
    FROM compression_analytics ${u}
    GROUP BY COALESCE(engine, mode)
  `).all(...s),E={};for(let e of _)E[e.engine]={count:e.cnt,tokensSaved:e.saved,avgSavingsPct:Math.round(e.avgPct)};let m=r.prepare(`
    SELECT compression_combo_id as compressionComboId, COUNT(*) as cnt,
      COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics ${o(u,"compression_combo_id IS NOT NULL")}
    GROUP BY compression_combo_id ORDER BY cnt DESC
  `).all(...s),g={};for(let e of m)g[e.compressionComboId??"unknown"]={count:e.cnt,tokensSaved:e.saved};let y=r.prepare(`
    SELECT provider, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics ${u}
    GROUP BY provider ORDER BY cnt DESC
  `).all(...s),S={};for(let e of y)S[e.provider??"unknown"]={count:e.cnt,tokensSaved:e.saved};let f=new Map,T=new Date;for(let e=23;e>=0;e--){let t=new Date(T.getTime()-60*e*6e4).toISOString().substring(0,14)+"00:00Z";f.set(t,{hour:t,count:0,tokensSaved:0})}for(let e of r.prepare(`
    SELECT strftime('%Y-%m-%dT%H:00:00Z', timestamp) as hour,
      COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics
    WHERE timestamp >= ? AND skip_reason IS NULL
    GROUP BY hour ORDER BY hour ASC
  `).all(new Date(T.getTime()-864e5).toISOString()))f.has(e.hour)&&f.set(e.hour,{hour:e.hour,count:e.cnt,tokensSaved:e.saved});let R=Array.from(f.values()),O=r.prepare(`
    SELECT receipt_source as source, COUNT(*) as cnt,
      COALESCE(SUM(actual_prompt_tokens), 0) as prompt,
      COALESCE(SUM(actual_completion_tokens), 0) as completion,
      COALESCE(SUM(actual_total_tokens), 0) as total,
      COALESCE(SUM(actual_cache_read_tokens), 0) as cacheRead,
      COALESCE(SUM(actual_cache_write_tokens), 0) as cacheWrite,
      COALESCE(SUM(estimated_usd_saved), 0) as usdSaved
    FROM compression_analytics ${o(u,"receipt_source IS NOT NULL")}
    GROUP BY receipt_source
  `).all(...s),D={requestsWithReceipts:0,promptTokens:0,completionTokens:0,totalTokens:0,cacheReadTokens:0,cacheWriteTokens:0,estimatedUsdSaved:0,bySource:{}};for(let e of O){let t=e.source??"unknown";D.requestsWithReceipts+=e.cnt,D.promptTokens+=e.prompt,D.completionTokens+=e.completion,D.totalTokens+=e.total,D.cacheReadTokens+=e.cacheRead,D.cacheWriteTokens+=e.cacheWrite,D.estimatedUsdSaved+=e.usdSaved,D.bySource[t]=e.cnt}let A=r.prepare(`
    SELECT COUNT(*) as cnt
    FROM compression_analytics ${o(u,"validation_fallback = 1")}
  `).get(...s),b=r.prepare(`
    SELECT COUNT(*) as cnt, COALESCE(SUM(mcp_description_tokens_saved), 0) as saved
    FROM compression_analytics ${o(u,"mcp_description_tokens_saved > 0")}
  `).get(...s),I=r.prepare(`
    SELECT skip_reason as reason, COUNT(*) as cnt
    FROM compression_analytics ${o(i,"skip_reason IS NOT NULL")}
    GROUP BY skip_reason
  `).all(...s),L={},N=0;for(let e of I)L[e.reason??"unknown"]=e.cnt,N+=e.cnt;return{totalRequests:l?.total??0,totalTokensSaved:l?.totalSaved??0,avgSavingsPct:Math.round(l?.avgPct??0),avgDurationMs:Math.round(l?.avgDur??0),byMode:p,byEngine:E,byCompressionCombo:g,byProvider:S,last24h:R,totalSkipped:N,bySkipReason:L,validationFallbacks:A?.cnt??0,realUsage:D,mcpDescriptionCompression:{snapshots:b?.cnt??0,estimatedTokensSaved:b?.saved??0}}},"insertCompressionAnalyticsRow",0,function(e){let r=(0,t.getDbInstance)();a(),r.prepare(`
    INSERT INTO compression_analytics (
      timestamp, combo_id, compression_combo_id, engine, provider, mode, original_tokens, compressed_tokens, tokens_saved,
      duration_ms, request_id, actual_prompt_tokens, actual_completion_tokens,
      actual_total_tokens, actual_cache_read_tokens, actual_cache_write_tokens,
      estimated_usd_saved, mcp_description_tokens_saved, multimodal_skip_count,
      receipt_source, validation_fallback, output_mode, rtk_raw_output_pointer, rtk_raw_output_bytes,
      rtk_raw_output_pointers, rtk_raw_output_total_bytes, skip_reason
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(e.timestamp,e.combo_id??null,e.compression_combo_id??null,e.engine??e.mode,e.provider??null,e.mode,e.original_tokens,e.compressed_tokens,e.tokens_saved,e.duration_ms??null,e.request_id??null,e.actual_prompt_tokens??null,e.actual_completion_tokens??null,e.actual_total_tokens??null,e.actual_cache_read_tokens??null,e.actual_cache_write_tokens??null,e.estimated_usd_saved??null,e.mcp_description_tokens_saved??0,e.multimodal_skip_count??0,e.receipt_source??null,+!!e.validation_fallback,e.output_mode??null,e.rtk_raw_output_pointer??null,e.rtk_raw_output_bytes??null,e.rtk_raw_output_pointers??null,e.rtk_raw_output_total_bytes??null,e.skip_reason??null)}])},63477,e=>{"use strict";var t=e.i(254799),r=e.i(504208),n=e.i(223194);function a(e){return e&&"object"==typeof e?e:{}}function o(e){let t=a(e);return{id:"string"==typeof t.id?t.id:"",name:"string"==typeof t.name?t.name:"",type:"string"==typeof t.type?t.type:"http",host:"string"==typeof t.host?t.host:"",port:Number(t.port)||0,region:"string"==typeof t.region?t.region:null,notes:"string"==typeof t.notes?t.notes:null,status:"string"==typeof t.status?t.status:"active",source:"string"==typeof t.source?t.source:"oneproxy",qualityScore:"number"==typeof t.quality_score?t.quality_score:null,latencyMs:"number"==typeof t.latency_ms?t.latency_ms:null,anonymity:"string"==typeof t.anonymity?t.anonymity:null,googleAccess:1===t.google_access||!0===t.google_access,lastValidated:"string"==typeof t.last_validated?t.last_validated:null,countryCode:"string"==typeof t.country_code?t.country_code:null,createdAt:"string"==typeof t.created_at?t.created_at:"",updatedAt:"string"==typeof t.updated_at?t.updated_at:""}}async function i(e){let t=(0,r.getDbInstance)(),n="SELECT * FROM proxy_registry WHERE source = 'oneproxy' AND status = 'active'",a=[];return e?.protocol&&(n+=" AND type = ?",a.push(e.protocol)),e?.countryCode&&(n+=" AND country_code = ?",a.push(e.countryCode)),e?.minQuality!=null&&(n+=" AND quality_score >= ?",a.push(e.minQuality)),n+=" ORDER BY quality_score DESC, last_validated DESC",e?.limit&&(n+=" LIMIT ?",a.push(e.limit)),t.prepare(n).all(...a).map(o)}async function s(){let e,t=(0,r.getDbInstance)(),n={total:Number((e=a(t.prepare(`SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
        AVG(quality_score) as avg_quality,
        MAX(last_validated) as last_validated
       FROM proxy_registry WHERE source = 'oneproxy'`).get())).total)||0,active:Number(e.active)||0,avgQuality:null!==e.avg_quality&&void 0!==e.avg_quality?Math.round(100*Number(e.avg_quality))/100:null,lastValidated:"string"==typeof e.last_validated?e.last_validated:null},o=t.prepare("SELECT type as protocol, COUNT(*) as count FROM proxy_registry WHERE source = 'oneproxy' GROUP BY type ORDER BY count DESC").all(),i=t.prepare("SELECT country_code as countryCode, COUNT(*) as count FROM proxy_registry WHERE source = 'oneproxy' AND country_code IS NOT NULL GROUP BY country_code ORDER BY count DESC LIMIT 20").all();return{...n,byProtocol:o.map(e=>({protocol:String(e.protocol||"unknown"),count:Number(e.count)||0})),byCountry:i.map(e=>({countryCode:String(e.countryCode||"unknown"),count:Number(e.count)||0}))}}async function u(e){let a=(0,r.getDbInstance)(),o=new Date().toISOString(),i=`${e.protocol?.toUpperCase()||"HTTP"} - ${e.countryCode||"Unknown"} - ${e.ip}`,s=a.prepare("SELECT id FROM proxy_registry WHERE host = ? AND port = ? AND source = 'oneproxy'").get(e.ip,e.port);if(s?.id)return a.prepare(`UPDATE proxy_registry
       SET status = ?, quality_score = ?, latency_ms = ?, anonymity = ?,
           google_access = ?, last_validated = ?, country_code = ?, updated_at = ?
       WHERE id = ?`).run("active",e.qualityScore??null,e.latencyMs??null,e.anonymity??null,+!!e.googleAccess,e.lastValidated??o,e.countryCode??null,o,s.id),(0,n.backupDbFile)("pre-write"),{proxy:await l(s.id),action:"updated"};let u=(0,t.randomUUID)();return a.prepare(`INSERT INTO proxy_registry
     (id, name, type, host, port, region, notes, status, source,
      quality_score, latency_ms, anonymity, google_access, last_validated, country_code,
      created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(u,i,e.protocol||"http",e.ip,e.port,e.countryCode??null,null,"active","oneproxy",e.qualityScore??null,e.latencyMs??null,e.anonymity??null,+!!e.googleAccess,e.lastValidated??o,e.countryCode??null,o,o),(0,n.backupDbFile)("pre-write"),{proxy:await l(u),action:"created"}}async function l(e){let t=(0,r.getDbInstance)().prepare("SELECT * FROM proxy_registry WHERE id = ? AND source = 'oneproxy'").get(e);return t?o(t):null}async function c(e){let t=(0,r.getDbInstance)().prepare("DELETE FROM proxy_registry WHERE id = ? AND source = 'oneproxy'").run(e);return(0,n.backupDbFile)("pre-write"),t.changes>0}async function d(){let e=(0,r.getDbInstance)().prepare("DELETE FROM proxy_registry WHERE source = 'oneproxy'").run();return(0,n.backupDbFile)("pre-write"),e.changes}async function p(e){let t=(0,r.getDbInstance)(),n=e?.strategy||"quality",a="SELECT * FROM proxy_registry WHERE source = 'oneproxy' AND status = 'active'";switch(n){case"quality":a+=" ORDER BY quality_score DESC, latency_ms ASC LIMIT 1";break;case"random":a+=" ORDER BY RANDOM() LIMIT 1";break;case"sequential":a+=" ORDER BY last_validated ASC LIMIT 1"}let i=t.prepare(a).get();return i?o(i):null}async function _(e,t){let a=(0,r.getDbInstance)().prepare(`UPDATE proxy_registry
       SET quality_score = MAX(0, COALESCE(quality_score, 50) - 10),
           status = CASE WHEN COALESCE(quality_score, 50) <= 10 THEN 'inactive' ELSE status END,
           updated_at = datetime('now')
       WHERE host = ? AND port = ? AND source = 'oneproxy'`).run(e,t);return(0,n.backupDbFile)("pre-write"),a.changes>0}e.s(["clearAllOneproxyProxies",0,d,"deleteOneproxyProxy",0,c,"getOneproxyProxyById",0,l,"getOneproxyProxyForRotation",0,p,"getOneproxyStats",0,s,"listOneproxyProxies",0,i,"markOneproxyProxyFailed",0,_,"upsertOneproxyProxy",0,u])},423421,e=>{"use strict";var t=e.i(504208);function r(){return(0,t.getDbInstance)()}function n(e){let t=r().prepare("SELECT COALESCE(SUM(amount), 0) AS total FROM token_ledger WHERE to_api_key_id = ?").get(e),n=r().prepare("SELECT COALESCE(SUM(amount), 0) AS total FROM token_ledger WHERE from_api_key_id = ?").get(e);return t.total-n.total}e.s(["addXp",0,function(e,t,n,a){r().prepare(`INSERT INTO xp_audit_log (api_key_id, action, xp_earned, metadata)
     VALUES (?, ?, ?, ?)`).run(e,t,n,a??null),r().prepare(`INSERT INTO user_levels (api_key_id, total_xp, current_level, updated_at)
     VALUES (?, ?, ?, datetime('now'))
     ON CONFLICT(api_key_id)
     DO UPDATE SET total_xp = total_xp + excluded.total_xp, updated_at = datetime('now')`).run(e,n,n<=0?1:Math.max(1,Math.floor(Math.pow(2.5*n/100,.4))))},"connectServer",0,function(e,t,n,a){r().prepare(`INSERT OR REPLACE INTO community_servers (id, name, url, api_key_hash)
     VALUES (?, ?, ?, ?)`).run(e,t,n,a)},"createInviteToken",0,function(e,t,n,a,o,i){r().prepare(`INSERT INTO invite_tokens (id, code, token_hash, created_by, server_url, max_uses)
     VALUES (?, ?, ?, ?, ?, ?)`).run(e,t,n,a,o??null,i??1)},"disconnectServer",0,function(e){r().prepare("UPDATE community_servers SET status = 'disconnected' WHERE id = ?").run(e)},"getBadgeDefinitions",0,function(e){let t=e?"SELECT * FROM badge_definitions WHERE category = ?":"SELECT * FROM badge_definitions";return(e?r().prepare(t).all(e):r().prepare(t).all()).map(e=>({id:e.id,name:e.name,description:e.description,icon:e.icon,category:e.category,rarity:e.rarity,criteria:e.criteria,hidden:e.hidden,createdAt:e.created_at}))},"getBadges",0,function(e){return r().prepare(`SELECT ub.api_key_id, ub.badge_id, ub.unlocked_at,
            bd.name, bd.description, bd.icon, bd.category, bd.rarity
     FROM user_badges ub
     JOIN badge_definitions bd ON bd.id = ub.badge_id
     WHERE ub.api_key_id = ?`).all(e).map(e=>({apiKeyId:e.api_key_id,badgeId:e.badge_id,unlockedAt:e.unlocked_at,badgeName:e.name,badgeDescription:e.description,badgeIcon:e.icon,badgeCategory:e.category,badgeRarity:e.rarity}))},"getBalance",0,n,"getConnectedServerByKeyHash",0,function(e){return r().prepare("SELECT id FROM community_servers WHERE api_key_hash = ? AND status = 'connected'").get(e)},"getHistory",0,function(e,t){return r().prepare(`SELECT * FROM token_ledger
     WHERE from_api_key_id = ? OR to_api_key_id = ?
     ORDER BY created_at DESC LIMIT ?`).all(e,e,t).map(e=>({id:e.id,fromApiKeyId:e.from_api_key_id,toApiKeyId:e.to_api_key_id,amount:e.amount,reason:e.reason,idempotencyKey:e.idempotency_key,createdAt:e.created_at}))},"getInviteByCode",0,function(e){let t=r().prepare("SELECT * FROM invite_tokens WHERE code = ?").get(e);return t?{id:t.id,code:t.code,tokenHash:t.token_hash,createdBy:t.created_by,usedBy:t.used_by,serverUrl:t.server_url,maxUses:t.max_uses,useCount:t.use_count,expiresAt:t.expires_at,revokedAt:t.revoked_at,createdAt:t.created_at}:null},"getRank",0,function(e,t){let n=r().prepare("SELECT score FROM leaderboard WHERE api_key_id = ? AND scope = ?").get(e,t);return n?r().prepare("SELECT COUNT(*) + 1 AS rank FROM leaderboard WHERE scope = ? AND score > ?").get(t,n.score).rank:0},"getTopN",0,function(e,t,n=0){return r().prepare(`SELECT api_key_id, scope, score, updated_at FROM leaderboard
     WHERE scope = ? ORDER BY score DESC LIMIT ? OFFSET ?`).all(e,t,n).map(e=>({apiKeyId:e.api_key_id,scope:e.scope,score:e.score,updatedAt:e.updated_at}))},"getXp",0,function(e){let t=r().prepare("SELECT api_key_id, total_xp, current_level, updated_at FROM user_levels WHERE api_key_id = ?").get(e);return t?{apiKeyId:t.api_key_id,totalXp:t.total_xp,currentLevel:t.current_level,updatedAt:t.updated_at}:null},"hasBadge",0,function(e,t){return!!r().prepare("SELECT 1 FROM user_badges WHERE api_key_id = ? AND badge_id = ? LIMIT 1").get(e,t)},"listServers",0,function(){return r().prepare("SELECT id, name, url, connected_at, last_sync_at, status, error_message FROM community_servers").all().map(e=>({id:e.id,name:e.name,url:e.url,connectedAt:e.connected_at,lastSyncAt:e.last_sync_at,status:e.status,errorMessage:e.error_message}))},"redeemInvite",0,function(e,t){return r().prepare(`UPDATE invite_tokens
     SET use_count = use_count + 1, used_by = ?
     WHERE code = ? AND revoked_at IS NULL
       AND use_count < max_uses
       AND (expires_at IS NULL OR expires_at > datetime('now'))`).run(t,e).changes>0},"revokeInvite",0,function(e){r().prepare("UPDATE invite_tokens SET revoked_at = datetime('now') WHERE id = ?").run(e)},"transferTokens",0,function(e,r,a,o,i){let s=(0,t.getDbInstance)();return s.transaction(()=>s.prepare("SELECT id FROM token_ledger WHERE idempotency_key = ?").get(i)?{success:!0}:n(e)<a?{success:!1,error:"insufficient_balance"}:(s.prepare(`INSERT INTO token_ledger (from_api_key_id, to_api_key_id, amount, reason, idempotency_key)
         VALUES (?, ?, ?, ?, ?)`).run(e,r,a,o,i),{success:!0}))()},"unlockBadge",0,function(e,t){r().prepare("INSERT OR IGNORE INTO user_badges (api_key_id, badge_id) VALUES (?, ?)").run(e,t)},"updateLevel",0,function(e,t){r().prepare(`INSERT INTO user_levels (api_key_id, total_xp, current_level, updated_at)
     VALUES (?, 0, ?, datetime('now'))
     ON CONFLICT(api_key_id)
     DO UPDATE SET current_level = ?, updated_at = datetime('now')`).run(e,t,t)},"updateScore",0,function(e,t,n){r().prepare(`INSERT INTO leaderboard (api_key_id, scope, score, updated_at)
     VALUES (?, ?, ?, datetime('now'))
     ON CONFLICT(api_key_id, scope)
     DO UPDATE SET score = score + excluded.score, updated_at = datetime('now')`).run(e,t,n)}],423421)},53906,e=>{"use strict";var t=e.i(504208);function r(e){return{name:e.name,description:e.description,priority:e.priority,scope:"combo"===e.scope_type&&e.combo_id?{type:"combo",comboId:e.combo_id}:{type:"global"},enabled:1===e.enabled,code:e.code,createdAt:e.created_at,updatedAt:e.updated_at,runCount:e.run_count,lastError:e.last_error||void 0}}function n(e){return{name:e.name,description:e.description,priority:e.priority,scope_type:e.scope.type,combo_id:"combo"===e.scope.type?e.scope.comboId:null,enabled:+!!e.enabled,code:e.code,created_at:e.createdAt||new Date().toISOString(),updated_at:new Date().toISOString(),run_count:e.runCount||0,last_error:e.lastError}}function a(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE name = ?").get(e);return n?r(n):void 0}e.s(["cleanupHookLogs",0,function(e=1e4){return(0,t.getDbInstance)().prepare(`
    DELETE FROM middleware_logs WHERE id NOT IN (
      SELECT id FROM middleware_logs ORDER BY timestamp DESC LIMIT ?
    )
  `).run(e).changes},"createMiddlewareHook",0,function(e){let r=(0,t.getDbInstance)(),o=n(e);return o.created_at=new Date().toISOString(),o.updated_at=o.created_at,r.prepare(`
    INSERT INTO middleware_hooks (name, description, priority, scope_type, combo_id, enabled, code, created_at, updated_at, run_count, last_error)
    VALUES (@name, @description, @priority, @scope_type, @combo_id, @enabled, @code, @created_at, @updated_at, @run_count, @last_error)
  `).run(o),a(e.name)},"deleteMiddlewareHook",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM middleware_hooks WHERE name = ?").run(e).changes>0},"getAllMiddlewareHooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks ORDER BY priority ASC, name ASC").all().map(r)},"getComboMiddlewareHooks",0,function(e){return(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE enabled = 1 AND (scope_type = 'global' OR (scope_type = 'combo' AND combo_id = ?)) ORDER BY priority ASC").all(e).map(r)},"getEnabledMiddlewareHooks",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE enabled = 1 ORDER BY priority ASC").all().map(r)},"getHookLogs",0,function(e,r=50){let n=(0,t.getDbInstance)();return(e?n.prepare("SELECT * FROM middleware_logs WHERE hook_name = ? ORDER BY timestamp DESC LIMIT ?").all(e,r):n.prepare("SELECT * FROM middleware_logs ORDER BY timestamp DESC LIMIT ?").all(r)).map(e=>({id:e.id,hookName:e.hook_name,requestId:e.request_id,durationMs:e.duration_ms,mutated:1===e.mutated,skipped:1===e.skipped,error:e.error,timestamp:e.timestamp}))},"getMiddlewareHook",0,a,"insertHookLog",0,function(e){(0,t.getDbInstance)().prepare(`
    INSERT INTO middleware_logs (id, hook_name, request_id, duration_ms, mutated, skipped, error, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(e.id,e.hookName,e.requestId,e.durationMs,+!!e.mutated,+!!e.skipped,e.error||null,e.timestamp)},"recordHookExecution",0,function(e,r){let n=(0,t.getDbInstance)();r?n.prepare("UPDATE middleware_hooks SET run_count = run_count + 1, last_error = ?, updated_at = datetime('now') WHERE name = ?").run(r,e):n.prepare("UPDATE middleware_hooks SET run_count = run_count + 1, last_error = NULL, updated_at = datetime('now') WHERE name = ?").run(e)},"updateMiddlewareHook",0,function(e,r){let o=a(e);if(!o)return;let i=n({...o,...r,updatedAt:new Date().toISOString()});return(0,t.getDbInstance)().prepare(`
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
  `).run(i),a(e)}])},47894,e=>{"use strict";var t=e.i(666680),r=e.i(504208),n=e.i(446202);function a(e){let t=(0,r.getDbInstance)().prepare("SELECT * FROM relay_tokens WHERE id = ?").get(e);return t?{...(0,n.rowToCamel)(t),enabled:1===t.enabled}:null}e.s(["checkRateLimit",0,function(e,t){let a=(0,r.getDbInstance)(),o=t;if(!o){let t=a.prepare("SELECT * FROM relay_tokens WHERE id = ?").get(e);if(!t)return{allowed:!1,remaining:0,resetIn:0};o=(0,n.rowToCamel)(t)}let i=Math.floor(Date.now()/1e3),s=60*Math.floor(i/60),u=86400*Math.floor(i/86400),l=a.prepare("SELECT request_count, cost FROM relay_rate_limits WHERE token_id = ? AND window_start = ?").get(e,s),c=l?.request_count||0;if(c>=o.maxRequestsPerMinute)return{allowed:!1,remaining:0,resetIn:60-i%60};let d=a.prepare("SELECT SUM(request_count) as total FROM relay_rate_limits WHERE token_id = ? AND window_start >= ?").get(e,u),p=d?.total||0;return p>=o.maxRequestsPerDay?{allowed:!1,remaining:0,resetIn:86400-i%86400}:{allowed:!0,remaining:Math.min(o.maxRequestsPerMinute-c,o.maxRequestsPerDay-p),resetIn:60-i%60}},"createRelayToken",0,function(a){let o=(0,r.getDbInstance)(),i="rl_"+(0,t.randomBytes)(16).toString("hex"),s="relay_"+(0,t.randomBytes)(24).toString("hex"),u=function(t){let{createHash:r}=e.r(666680);return r("sha256").update(t).digest("hex")}(s),l=Math.floor(Date.now()/1e3),c="rl_"+s.slice(6,14);o.prepare(`
    INSERT INTO relay_tokens (id, name, token_hash, token_prefix, description, combo_id, allowed_models,
      max_tokens_per_request, max_requests_per_minute, max_requests_per_day, max_cost_per_day,
      enabled, created_at, updated_at, expires_at, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
  `).run(i,a.name,u,c,a.description||"",a.comboId||null,JSON.stringify(a.allowedModels||["*"]),a.maxTokensPerRequest||128e3,a.maxRequestsPerMinute||60,a.maxRequestsPerDay||1e4,a.maxCostPerDay||0,l,l,a.expiresAt||null,JSON.stringify(a.metadata||{}));let d=o.prepare("SELECT * FROM relay_tokens WHERE id = ?").get(i);return{...(0,n.rowToCamel)(d),rawToken:s}},"deleteRelayToken",0,function(e){(0,r.getDbInstance)().prepare("DELETE FROM relay_tokens WHERE id = ?").run(e)},"getRelayLogs",0,function(e,t=50){let n=(0,r.getDbInstance)();return e?n.prepare("SELECT * FROM relay_logs WHERE token_id = ? ORDER BY created_at DESC LIMIT ?").all(e,t):n.prepare("SELECT * FROM relay_logs ORDER BY created_at DESC LIMIT ?").all(t)},"getRelayToken",0,a,"getRelayTokenByHash",0,function(e){let t=(0,r.getDbInstance)().prepare("SELECT * FROM relay_tokens WHERE token_hash = ? AND enabled = 1").get(e);return t?{...(0,n.rowToCamel)(t),enabled:1===t.enabled}:null},"getRelayTokens",0,function(){return(0,r.getDbInstance)().prepare("SELECT * FROM relay_tokens ORDER BY created_at DESC").all().map(e=>({...(0,n.rowToCamel)(e),enabled:1===e.enabled}))},"getRelayUsage",0,function(e,t){let n=(0,r.getDbInstance)().prepare("SELECT COUNT(*) as request_count, COALESCE(SUM(cost), 0) as total_cost FROM relay_logs WHERE token_id = ? AND created_at >= ?").get(e,t);return{requestCount:n.request_count,totalCost:n.total_cost}},"recordRelayUsage",0,function(e,t){let n=(0,r.getDbInstance)(),a=Math.floor(Date.now()/1e3),o=60*Math.floor(a/60);n.prepare(`
    INSERT INTO relay_rate_limits (token_id, window_start, request_count, cost)
    VALUES (?, ?, 1, ?)
    ON CONFLICT(token_id, window_start) DO UPDATE SET
      request_count = request_count + 1,
      cost = cost + ?
  `).run(e,o,t.cost||0,t.cost||0),n.prepare("UPDATE relay_tokens SET last_used_at = ? WHERE id = ?").run(a,e),n.prepare(`
    INSERT INTO relay_logs (token_id, request_id, model, prompt_tokens, completion_tokens, cost,
      status, status_code, latency_ms, client_ip, user_agent, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(e,t.requestId||null,t.model||null,t.promptTokens||0,t.completionTokens||0,t.cost||0,t.status||"success",t.statusCode||200,t.latencyMs||0,t.clientIp||null,t.userAgent||null,a)},"toggleRelayToken",0,function(e,t){let n=(0,r.getDbInstance)(),o=Math.floor(Date.now()/1e3);return n.prepare("UPDATE relay_tokens SET enabled = ?, updated_at = ? WHERE id = ?").run(+!!t,o,e),a(e)},"updateRelayToken",0,function(e,t){let n=(0,r.getDbInstance)(),o=Math.floor(Date.now()/1e3),i=["updated_at = ?"],s=[o];return void 0!==t.name&&(i.push("name = ?"),s.push(t.name)),void 0!==t.description&&(i.push("description = ?"),s.push(t.description)),void 0!==t.comboId&&(i.push("combo_id = ?"),s.push(t.comboId)),void 0!==t.allowedModels&&(i.push("allowed_models = ?"),s.push(JSON.stringify(t.allowedModels))),void 0!==t.maxTokensPerRequest&&(i.push("max_tokens_per_request = ?"),s.push(t.maxTokensPerRequest)),void 0!==t.maxRequestsPerMinute&&(i.push("max_requests_per_minute = ?"),s.push(t.maxRequestsPerMinute)),void 0!==t.maxRequestsPerDay&&(i.push("max_requests_per_day = ?"),s.push(t.maxRequestsPerDay)),void 0!==t.maxCostPerDay&&(i.push("max_cost_per_day = ?"),s.push(t.maxCostPerDay)),s.push(e),n.prepare(`UPDATE relay_tokens SET ${i.join(", ")} WHERE id = ?`).run(...s),a(e)}])},330837,e=>{"use strict";var t=e.i(254799),r=e.i(504208),n=e.i(223194);function a(e){return{id:String(e.id??""),source:String(e.source??"1proxy"),host:String(e.host??""),port:Number(e.port)||0,type:String(e.type??"http"),countryCode:null!=e.country_code?String(e.country_code):null,qualityScore:null!=e.quality_score?Number(e.quality_score):null,latencyMs:null!=e.latency_ms?Number(e.latency_ms):null,anonymity:null!=e.anonymity?String(e.anonymity):null,lastValidated:null!=e.last_validated?String(e.last_validated):null,inPool:1===e.in_pool||!0===e.in_pool,poolProxyId:null!=e.pool_proxy_id?String(e.pool_proxy_id):null,createdAt:String(e.created_at??""),updatedAt:String(e.updated_at??"")}}async function o(e){let n=(0,r.getDbInstance)(),a=new Date().toISOString(),o=n.prepare("SELECT id FROM free_proxies WHERE source = ? AND host = ? AND port = ?").get(e.source,e.host,e.port);if(o?.id)return n.prepare(`UPDATE free_proxies
       SET type = ?, country_code = ?, quality_score = ?, latency_ms = ?,
           anonymity = ?, last_validated = ?, updated_at = ?
       WHERE id = ?`).run(e.type,e.countryCode??null,e.qualityScore??null,e.latencyMs??null,e.anonymity??null,e.lastValidated??a,a,o.id),{id:o.id,action:"updated"};let i=(0,t.randomUUID)();return n.prepare(`INSERT INTO free_proxies
     (id, source, host, port, type, country_code, quality_score, latency_ms,
      anonymity, last_validated, in_pool, pool_proxy_id, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)`).run(i,e.source,e.host,e.port,e.type,e.countryCode??null,e.qualityScore??null,e.latencyMs??null,e.anonymity??null,e.lastValidated??a,a,a),{id:i,action:"created"}}async function i(e){let t=(0,r.getDbInstance)(),n=[],o="SELECT * FROM free_proxies WHERE 1=1";e?.sources?.length&&(o+=` AND source IN (${e.sources.map(()=>"?").join(",")})`,n.push(...e.sources)),e?.protocol&&(o+=" AND type = ?",n.push(e.protocol)),e?.country&&(o+=" AND country_code = ?",n.push(e.country.toUpperCase())),e?.minQuality!=null&&(o+=" AND quality_score >= ?",n.push(e.minQuality)),e?.onlyInPool&&(o+=" AND in_pool = 1"),e?.onlyNotInPool&&(o+=" AND in_pool = 0"),e?.search&&(o+=" AND host LIKE ?",n.push(`%${e.search}%`));let i=e?.sortBy==="latency"?"ORDER BY latency_ms IS NULL, latency_ms ASC":e?.sortBy==="recent"?"ORDER BY last_validated DESC":"ORDER BY quality_score DESC, last_validated DESC";return o+=` ${i}`,e?.limit&&(o+=" LIMIT ?",n.push(e.limit),e?.offset&&(o+=" OFFSET ?",n.push(e.offset))),t.prepare(o).all(...n).map(a)}async function s(e){let t=(0,r.getDbInstance)(),n=[],a="SELECT COUNT(*) AS count FROM free_proxies WHERE 1=1";e?.sources?.length&&(a+=` AND source IN (${e.sources.map(()=>"?").join(",")})`,n.push(...e.sources)),e?.protocol&&(a+=" AND type = ?",n.push(e.protocol)),e?.country&&(a+=" AND country_code = ?",n.push(e.country.toUpperCase())),e?.minQuality!=null&&(a+=" AND quality_score >= ?",n.push(e.minQuality)),e?.onlyInPool&&(a+=" AND in_pool = 1"),e?.onlyNotInPool&&(a+=" AND in_pool = 0"),e?.search&&(a+=" AND host LIKE ?",n.push(`%${e.search}%`));let o=t.prepare(a).get(...n),i=o?.count;return"number"==typeof i?i:Number(i??0)}async function u(e,t){return(await i({sources:[e],protocol:t.protocol,country:t.country,minQuality:t.minQuality,limit:t.limit})).map(e=>({source:e.source,host:e.host,port:e.port,type:e.type,countryCode:e.countryCode,qualityScore:e.qualityScore,latencyMs:e.latencyMs,anonymity:e.anonymity,lastValidated:e.lastValidated}))}async function l(e){let t=(0,r.getDbInstance)().prepare("SELECT * FROM free_proxies WHERE id = ?").get(e);return t?a(t):null}async function c(e,t){let a=(0,r.getDbInstance)(),o=new Date().toISOString();a.prepare("UPDATE free_proxies SET in_pool = 1, pool_proxy_id = ?, updated_at = ? WHERE id = ?").run(t,o,e),(0,n.backupDbFile)("pre-write")}async function d(e,a){let o=(0,r.getDbInstance)(),i=new Date().toISOString(),s=(0,t.randomUUID)(),u=o.transaction(()=>{let t=o.prepare("SELECT id, in_pool FROM free_proxies WHERE id = ? LIMIT 1").get(e);return t?.id?(o.prepare(`INSERT INTO proxy_registry
        (id, name, type, host, port, username, password, region, notes, status, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, '', '', NULL, NULL, 'active', ?, ?, ?)`).run(s,a.name,a.type,a.host,Number(a.port),a.source,i,i),o.prepare("UPDATE free_proxies SET in_pool = 1, pool_proxy_id = ?, updated_at = ? WHERE id = ?").run(s,i,e),s):null})();return u&&(0,n.backupDbFile)("pre-write"),u}async function p(e){let t=(0,r.getDbInstance)().prepare("DELETE FROM free_proxies WHERE id = ?").run(e);return(0,n.backupDbFile)("pre-write"),t.changes>0}async function _(e){let t=(0,r.getDbInstance)().prepare("DELETE FROM free_proxies WHERE source = ? AND in_pool = 0").run(e);return(0,n.backupDbFile)("pre-write"),t.changes}async function E(e,t){let a=(0,r.getDbInstance)(),o=a.prepare("SELECT id, host, port FROM free_proxies WHERE source = ? AND in_pool = 0").all(e).filter(e=>!t.has(`${e.host}:${e.port}`)).map(e=>e.id);if(0===o.length)return 0;let i=o.map(()=>"?").join(","),s=a.prepare(`DELETE FROM free_proxies WHERE id IN (${i})`).run(...o);return(0,n.backupDbFile)("pre-write"),s.changes}let m="free_proxies",g="last_sync_at";async function y(e){let t=(0,r.getDbInstance)(),a=e??new Date().toISOString();return t.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(m,g,a),(0,n.backupDbFile)("pre-write"),a}async function S(){let e,t=(0,r.getDbInstance)(),n=t.prepare(`SELECT COUNT(*) as total,
              SUM(CASE WHEN in_pool = 1 THEN 1 ELSE 0 END) as in_pool_count,
              AVG(quality_score) as avg_quality,
              MAX(last_validated) as last_sync_at
       FROM free_proxies`).get(),a=t.prepare("SELECT source, COUNT(*) as count FROM free_proxies GROUP BY source ORDER BY count DESC").all(),o=(e=t.prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(m,g),e?.value!=null?String(e.value):null),i=null!=n.last_sync_at?String(n.last_sync_at):null;return{total:Number(n.total)||0,inPool:Number(n.in_pool_count)||0,avgQuality:null!=n.avg_quality?Math.round(Number(n.avg_quality)):null,bySource:a.map(e=>({source:String(e.source),count:Number(e.count)})),lastSyncAt:o??i}}async function f(e,t){let a=(0,r.getDbInstance)(),o=new Date().toISOString();a.prepare("INSERT OR REPLACE INTO free_proxy_sync_errors (source, errors, updated_at) VALUES (?, ?, ?)").run(e,JSON.stringify(t),o),(0,n.backupDbFile)("pre-write")}async function T(e){(0,r.getDbInstance)().prepare("DELETE FROM free_proxy_sync_errors WHERE source = ?").run(e),(0,n.backupDbFile)("pre-write")}async function R(){let e=(0,r.getDbInstance)().prepare("SELECT source, errors FROM free_proxy_sync_errors").all(),t={};for(let r of e)if(r.source)try{let e=JSON.parse(r.errors);t[r.source]=Array.isArray(e)?e.map(String):[String(r.errors)]}catch{t[r.source]=[String(r.errors)]}return t}e.s(["clearFreeProxiesBySource",0,_,"clearFreeProxySyncErrors",0,T,"countFreeProxies",0,s,"deleteFreeProxy",0,p,"getFreeProxyById",0,l,"getFreeProxyStats",0,S,"getFreeProxySyncErrors",0,R,"listFreeProxies",0,i,"listFreeProxiesBySource",0,u,"markFreeProxyInPool",0,c,"promoteFreeProxyToPool",0,d,"pruneStaleFreeProxies",0,E,"recordFreeProxySync",0,y,"recordFreeProxySyncErrors",0,f,"upsertFreeProxy",0,o])},162186,e=>{"use strict";var t=e.i(504208),r=e.i(666680);function n(e){let t={};try{let r=JSON.parse(e.params_json);null===r||"object"!=typeof r||Array.isArray(r)||(t=r)}catch{t={}}return{id:e.id,name:e.name,endpoint:e.endpoint,model:e.model,system:e.system,params:t,created_at:e.created_at}}function a(e){let r=(0,t.getDbInstance)().prepare("SELECT * FROM playground_presets WHERE id = ? LIMIT 1").get(e);return r?n(r):null}e.s(["createPlaygroundPreset",0,function(e){let n=(0,t.getDbInstance)(),o=(0,r.randomUUID)(),i=JSON.stringify(e.params??{}),s=e.system??null;return n.prepare("INSERT INTO playground_presets (id, name, endpoint, model, system, params_json) VALUES (?, ?, ?, ?, ?, ?)").run(o,e.name,e.endpoint,e.model,s,i),a(o)},"deletePlaygroundPreset",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM playground_presets WHERE id = ?").run(e).changes>0},"getPlaygroundPreset",0,a,"listPlaygroundPresets",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM playground_presets ORDER BY created_at DESC").all().map(n)},"updatePlaygroundPreset",0,function(e,r){let n=(0,t.getDbInstance)(),o=a(e);if(!o)return null;let i=[],s=[];return(void 0!==r.name&&(i.push("name = ?"),s.push(r.name)),void 0!==r.endpoint&&(i.push("endpoint = ?"),s.push(r.endpoint)),void 0!==r.model&&(i.push("model = ?"),s.push(r.model)),"system"in r&&(i.push("system = ?"),s.push(r.system??null)),void 0!==r.params&&(i.push("params_json = ?"),s.push(JSON.stringify(r.params))),0===i.length)?o:(s.push(e),n.prepare(`UPDATE playground_presets SET ${i.join(", ")} WHERE id = ?`).run(...s),a(e))}])},897325,e=>{"use strict";var t=e.i(504208);function r(){let e=(0,t.getDbInstance)().prepare("SELECT active_dim, embedding_signature, last_reset_at, vec_loaded FROM memory_vec_meta WHERE id = 1").get();return e?{activeDim:e.active_dim,embeddingSignature:e.embedding_signature,lastResetAt:e.last_reset_at,vecLoaded:1===e.vec_loaded}:{activeDim:null,embeddingSignature:null,lastResetAt:null,vecLoaded:!1}}e.s(["countMemoryReindexPending",0,function(){return(0,t.getDbInstance)().prepare("SELECT COUNT(*) AS cnt FROM memories WHERE needs_reindex = 1").get().cnt},"getMemoryReindexQueue",0,function(e){return(0,t.getDbInstance)().prepare(`SELECT id, content, COALESCE(key, '') AS key
       FROM memories
       WHERE needs_reindex = 1
       ORDER BY created_at ASC
       LIMIT ?`).all(e)},"getMemoryVecMeta",0,r,"markAllMemoriesNeedReindex",0,function(){return(0,t.getDbInstance)().prepare("UPDATE memories SET needs_reindex = 1").run().changes},"markMemoryNeedsReindex",0,function(e,r){(0,t.getDbInstance)().prepare("UPDATE memories SET needs_reindex = ? WHERE id = ?").run(+!!r,e)},"setMemoryVecMeta",0,function(e){let n=(0,t.getDbInstance)(),a=r(),o="activeDim"in e?e.activeDim??null:a.activeDim,i="embeddingSignature"in e?e.embeddingSignature??null:a.embeddingSignature,s="lastResetAt"in e?e.lastResetAt??null:a.lastResetAt,u="vecLoaded"in e?+!!e.vecLoaded:+!!a.vecLoaded;n.prepare(`INSERT OR REPLACE INTO memory_vec_meta
       (id, active_dim, embedding_signature, last_reset_at, vec_loaded)
     VALUES (1, ?, ?, ?, ?)`).run(o,i,s,u)}])},797640,e=>{"use strict";var t=e.i(504208);function r(e){return{agent_id:e.agent_id,dns_enabled:1===e.dns_enabled,cert_trusted:1===e.cert_trusted,setup_completed:1===e.setup_completed,last_started_at:e.last_started_at,last_error:e.last_error}}function n(e){let n=(0,t.getDbInstance)().prepare("SELECT * FROM agent_bridge_state WHERE agent_id = ?").get(e);return n?r(n):null}e.s(["getAgentBridgeState",0,n,"getAllAgentBridgeStates",0,function(){return(0,t.getDbInstance)().prepare("SELECT * FROM agent_bridge_state ORDER BY agent_id ASC").all().map(r)},"setLastError",0,function(e,r){(0,t.getDbInstance)().prepare(`INSERT INTO agent_bridge_state (agent_id, last_error)
     VALUES (?, ?)
     ON CONFLICT(agent_id) DO UPDATE SET last_error = excluded.last_error`).run(e,r)},"setLastStarted",0,function(e,r){(0,t.getDbInstance)().prepare(`INSERT INTO agent_bridge_state (agent_id, last_started_at)
     VALUES (?, ?)
     ON CONFLICT(agent_id) DO UPDATE SET last_started_at = excluded.last_started_at`).run(e,r)},"upsertAgentBridgeState",0,function(e){let r=(0,t.getDbInstance)();if(n(e.agent_id)){let t=[],n=[];if(void 0!==e.dns_enabled&&(t.push("dns_enabled = ?"),n.push(+!!e.dns_enabled)),void 0!==e.cert_trusted&&(t.push("cert_trusted = ?"),n.push(+!!e.cert_trusted)),void 0!==e.setup_completed&&(t.push("setup_completed = ?"),n.push(+!!e.setup_completed)),void 0!==e.last_started_at&&(t.push("last_started_at = ?"),n.push(e.last_started_at)),void 0!==e.last_error&&(t.push("last_error = ?"),n.push(e.last_error)),0===t.length)return;n.push(e.agent_id),r.prepare(`UPDATE agent_bridge_state SET ${t.join(", ")} WHERE agent_id = ?`).run(...n)}else r.prepare(`INSERT INTO agent_bridge_state
         (agent_id, dns_enabled, cert_trusted, setup_completed, last_started_at, last_error)
       VALUES (?, ?, ?, ?, ?, ?)`).run(e.agent_id,void 0!==e.dns_enabled?+!!e.dns_enabled:0,void 0!==e.cert_trusted?+!!e.cert_trusted:0,void 0!==e.setup_completed?+!!e.setup_completed:0,e.last_started_at??null,e.last_error??null)}])},829778,e=>{"use strict";var t=e.i(504208);e.s(["deleteMapping",0,function(e,r){(0,t.getDbInstance)().prepare("DELETE FROM agent_bridge_mappings WHERE agent_id = ? AND source_model = ?").run(e,r)},"getMappingsForAgent",0,function(e){return(0,t.getDbInstance)().prepare("SELECT agent_id, source_model, target_model, updated_at FROM agent_bridge_mappings WHERE agent_id = ? ORDER BY source_model ASC").all(e)},"setMappings",0,function(e,r){let n=(0,t.getDbInstance)(),a=new Date().toISOString(),o=n.prepare("DELETE FROM agent_bridge_mappings WHERE agent_id = ?"),i=n.prepare(`INSERT INTO agent_bridge_mappings (agent_id, source_model, target_model, updated_at)
     VALUES (?, ?, ?, ?)`);n.transaction(()=>{for(let t of(o.run(e),r))i.run(e,t.source,t.target,a)})()}])},316020,e=>{"use strict";var t=e.i(504208);function r(e){return{pattern:e.pattern,source:e.source,created_at:e.created_at}}e.s(["getAllBypassPatterns",0,function(){return(0,t.getDbInstance)().prepare("SELECT pattern, source, created_at FROM agent_bridge_bypass ORDER BY source ASC, pattern ASC").all().map(r)},"getUserBypassPatterns",0,function(){return(0,t.getDbInstance)().prepare("SELECT pattern FROM agent_bridge_bypass WHERE source = 'user' ORDER BY pattern ASC").all().map(e=>e.pattern)},"replaceUserBypassPatterns",0,function(e){let r=(0,t.getDbInstance)(),n=new Date().toISOString(),a=r.prepare("DELETE FROM agent_bridge_bypass WHERE source = 'user'"),o=r.prepare("INSERT INTO agent_bridge_bypass (pattern, source, created_at) VALUES (?, 'user', ?)");r.transaction(()=>{for(let t of(a.run(),e))o.run(t,n)})()},"seedDefaultBypassPatterns",0,function(e){let r=(0,t.getDbInstance)(),n=new Date().toISOString(),a=r.prepare("INSERT OR IGNORE INTO agent_bridge_bypass (pattern, source, created_at) VALUES (?, 'default', ?)");r.transaction(()=>{for(let t of e)a.run(t,n)})()}])},115205,e=>{"use strict";var t=e.i(504208);function r(e){return{host:e.host,enabled:1===e.enabled,label:e.label,kind:e.kind,added_at:e.added_at,last_seen_at:e.last_seen_at}}e.s(["addCustomHost",0,function(e,r="custom",n){let a=(0,t.getDbInstance)(),o=new Date().toISOString();a.prepare(`INSERT OR IGNORE INTO inspector_custom_hosts (host, enabled, label, kind, added_at)
     VALUES (?, 1, ?, ?, ?)`).run(e,n??null,r,o)},"isCustomHost",0,function(e){return void 0!==(0,t.getDbInstance)().prepare("SELECT 1 AS found FROM inspector_custom_hosts WHERE host = ? AND enabled = 1").get(e)},"listCustomHosts",0,function(e){let n=(0,t.getDbInstance)();return(e?.enabledOnly===!0?n.prepare("SELECT * FROM inspector_custom_hosts WHERE enabled = 1 ORDER BY host ASC").all():n.prepare("SELECT * FROM inspector_custom_hosts ORDER BY host ASC").all()).map(r)},"removeCustomHost",0,function(e){(0,t.getDbInstance)().prepare("DELETE FROM inspector_custom_hosts WHERE host = ?").run(e)},"toggleCustomHost",0,function(e,r){(0,t.getDbInstance)().prepare("UPDATE inspector_custom_hosts SET enabled = ? WHERE host = ?").run(+!!r,e)},"touchLastSeen",0,function(e){let r=(0,t.getDbInstance)(),n=new Date().toISOString();r.prepare("UPDATE inspector_custom_hosts SET last_seen_at = ? WHERE host = ?").run(n,e)}])},194950,e=>e.a(async(t,r)=>{try{var n=e.i(677850),a=t([n]);[n]=a.then?(await a)():a;let o=n.z.object({id:n.z.string().uuid(),source:n.z.enum(["agent-bridge","custom-host","http-proxy","system-proxy","tproxy"]),agent:n.z.string().optional(),timestamp:n.z.string().datetime(),method:n.z.string(),host:n.z.string(),path:n.z.string(),requestHeaders:n.z.record(n.z.string(),n.z.string()),requestBody:n.z.string().nullable(),requestSize:n.z.number().int().nonnegative(),responseHeaders:n.z.record(n.z.string(),n.z.string()),responseBody:n.z.string().nullable(),responseSize:n.z.number().int().nonnegative(),status:n.z.union([n.z.number().int(),n.z.literal("in-flight"),n.z.literal("error")]),proxyLatencyMs:n.z.number().nonnegative().optional(),upstreamLatencyMs:n.z.number().nonnegative().optional(),totalLatencyMs:n.z.number().nonnegative().optional(),error:n.z.string().optional(),sourceModel:n.z.string().nullable().optional(),mappedModel:n.z.string().nullable().optional(),detectedKind:n.z.enum(["llm","app","unknown"]).optional(),contextKey:n.z.string().optional(),annotation:n.z.string().optional(),sessionId:n.z.string().uuid().optional(),note:n.z.string().optional(),pid:n.z.number().int().nonnegative().optional(),processName:n.z.string().optional()});e.s(["InterceptedRequestSchema",0,o]),r()}catch(e){r(e)}},!1),90896,e=>e.a(async(t,r)=>{try{var n=e.i(254799),a=e.i(504208),o=e.i(194950),i=t([o]);function s(e){return{id:e.id,name:e.name,started_at:e.started_at,ended_at:e.ended_at,request_count:e.request_count,profile:e.profile}}function u(e){let t=(0,a.getDbInstance)().prepare("SELECT * FROM inspector_sessions WHERE id = ?").get(e);return t?s(t):null}function l(e){return(0,a.getDbInstance)().prepare("SELECT seq, payload FROM inspector_session_requests WHERE session_id = ? ORDER BY seq ASC").all(e).map(e=>({seq:e.seq,payload:e.payload}))}[o]=i.then?(await i)():i,e.s(["appendSessionRequest",0,function(e,t){let r=(0,a.getDbInstance)(),n=0;return r.transaction(()=>{let a=r.prepare("SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM inspector_session_requests WHERE session_id = ?").get(e).next_seq;r.prepare("INSERT INTO inspector_session_requests (session_id, seq, payload) VALUES (?, ?, ?)").run(e,a,t),r.prepare("UPDATE inspector_sessions SET request_count = request_count + 1 WHERE id = ?").run(e),n=a})(),n},"createSession",0,function(e){let t=(0,a.getDbInstance)(),r=(0,n.randomUUID)(),o=new Date().toISOString();return t.prepare("INSERT INTO inspector_sessions (id, name, started_at, profile) VALUES (?, ?, ?, ?)").run(r,e?.name??null,o,e?.profile??null),{id:r,started_at:o}},"deleteSession",0,function(e){(0,a.getDbInstance)().prepare("DELETE FROM inspector_sessions WHERE id = ?").run(e)},"getSession",0,u,"getSessionRequests",0,l,"listSessions",0,function(){return(0,a.getDbInstance)().prepare("SELECT * FROM inspector_sessions ORDER BY started_at DESC").all().map(s)},"renameSession",0,function(e,t){(0,a.getDbInstance)().prepare("UPDATE inspector_sessions SET name = ? WHERE id = ?").run(t,e)},"snapshotSession",0,function(e){let t=u(e);if(null===t)return null;let r=l(e),n=[];for(let e of r){let t;try{t=JSON.parse(e.payload)}catch{continue}let r=o.InterceptedRequestSchema.safeParse(t);r.success&&n.push(r.data)}return n},"stopSession",0,function(e){let t=(0,a.getDbInstance)(),r=new Date().toISOString();t.prepare("UPDATE inspector_sessions SET ended_at = ? WHERE id = ?").run(r,e)}]),r()}catch(e){r(e)}},!1),52530,e=>{"use strict";var t=e.i(446786),r=e.i(814747),n=e.i(785148);let a=()=>r.default.join(r.default.join(t.default.homedir(),".omp","agent"),"agent.db");e.s(["deleteOmpCredentials",0,function(e){let t=a(),r=new n.default(t);r.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(e),r.close()},"getOmpCredentials",0,function(e){let t=a();try{let r=new n.default(t,{readonly:!0}),a=r.prepare("SELECT data FROM auth_credentials WHERE provider = ? AND credential_type = 'api_key'").get(e);if(r.close(),a?.data){let e=JSON.parse(a.data);return{hasOmniRoute:!0,baseUrl:e.baseUrl||null,apiKey:e.apiKey||null}}return{hasOmniRoute:!1,baseUrl:null,apiKey:null}}catch{return{hasOmniRoute:!1,baseUrl:null,apiKey:null}}},"saveOmpCredentials",0,function(e,t,r){let o=a(),i=new n.default(o);i.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(e),i.prepare("INSERT INTO auth_credentials (provider, credential_type, data, disabled_cause, identity_key, created_at, updated_at) VALUES (?, ?, ?, NULL, NULL, ?, ?)").run(e,"api_key",JSON.stringify({apiKey:t,baseUrl:r}),Math.floor(Date.now()/1e3),Math.floor(Date.now()/1e3)),i.close()}])},269032,e=>{"use strict";var t=e.i(504208);function r(e){return{poolId:e.pool_id,apiKeyId:e.api_key_id,model:e.model,capValue:e.cap_value,capUnit:e.cap_unit}}function n(){return(0,t.getDbInstance)()}e.s(["deleteModelCap",0,function(e,t,r){n().prepare(`DELETE FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ? AND model = ?`).run(e,t,r)},"getModelCap",0,function(e,t,a){let o=n().prepare(`SELECT pool_id, api_key_id, model, cap_value, cap_unit
       FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ? AND model = ?`).get(e,t,a);return o?r(o):null},"listModelCaps",0,function(e,t){return n().prepare(`SELECT pool_id, api_key_id, model, cap_value, cap_unit
       FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ?`).all(e,t).map(r)},"setModelCap",0,function(e){n().prepare(`INSERT INTO quota_allocation_model_caps
         (pool_id, api_key_id, model, cap_value, cap_unit)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(pool_id, api_key_id, model) DO UPDATE SET
         cap_value = excluded.cap_value,
         cap_unit  = excluded.cap_unit`).run(e.poolId,e.apiKeyId,e.model,e.capValue,e.capUnit)}])},675367,e=>{"use strict";var t=e.i(504208);function r(){return(0,t.getDbInstance)()}e.s(["gcOlderThan",0,function(e){return r().prepare("DELETE FROM quota_consumption WHERE updated_at < ?").run(e).changes},"getBucket",0,function(e,t,n){let a=r().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(e,t,n);return a?.consumed??0},"getPair",0,function(e,t,n){let a=r().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(e,t,n),o=r().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(e,t,n-1);return{curr:a?.consumed??0,prev:o?.consumed??0}},"incrementBucket",0,function(e,t,n,a,o){r().prepare(`INSERT INTO quota_consumption (api_key_id, dimension_key, bucket_index, consumed, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(api_key_id, dimension_key, bucket_index)
       DO UPDATE SET
         consumed = consumed + excluded.consumed,
         updated_at = excluded.updated_at`).run(e,t,n,a,o)},"sumPoolDimension",0,function(e,t){let n=r().prepare(`SELECT COALESCE(SUM(consumed), 0) AS total
       FROM quota_consumption
       WHERE dimension_key = ? AND bucket_index = ?`).get(e,t),a=r().prepare(`SELECT COALESCE(SUM(consumed), 0) AS total
       FROM quota_consumption
       WHERE dimension_key = ? AND bucket_index = ?`).get(e,t-1);return{currTotal:n?.total??0,prevTotal:a?.total??0}}])},255329,e=>{"use strict";var t=e.i(504208);function r(){return(0,t.getDbInstance)()}function n(e){let t=[];try{t=JSON.parse(e.dimensions_json)}catch{t=[]}return{connectionId:e.connection_id,provider:e.provider,dimensions:t,source:e.source}}e.s(["deletePlan",0,function(e){return r().prepare("DELETE FROM provider_plans WHERE connection_id = ?").run(e).changes>0},"getPlan",0,function(e){let t=r().prepare(`SELECT connection_id, provider, dimensions_json, source, updated_at
       FROM provider_plans WHERE connection_id = ?`).get(e);return t?n(t):null},"listPlans",0,function(){return r().prepare(`SELECT connection_id, provider, dimensions_json, source, updated_at
       FROM provider_plans ORDER BY provider ASC`).all().map(n)},"upsertPlan",0,function(e,t,n,a){let o=new Date().toISOString(),i=JSON.stringify(n);r().prepare(`INSERT INTO provider_plans (connection_id, provider, dimensions_json, source, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(connection_id)
       DO UPDATE SET
         provider = excluded.provider,
         dimensions_json = excluded.dimensions_json,
         source = excluded.source,
         updated_at = excluded.updated_at`).run(e,t,i,a,o)}])},472139,e=>{"use strict";var t=e.i(254799),r=e.i(504208);e.i(665412),e.i(664481);let n=/^(\d{2}):(\d{2})$/;function a(e,t,r,n,a){return Date.UTC(e,t,r,n,a,0,0)}let o=!1;function i(e){return e&&"object"==typeof e&&!Array.isArray(e)?e:{}}function s(e,t=0){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let r=Number(e);return Number.isFinite(r)?r:t}return t}function u(e){return"model"===e||"provider"===e||"global"===e?e:"global"}function l(e){return"daily"===e||"weekly"===e||"monthly"===e?e:"monthly"}function c(){o||((0,r.getDbInstance)().exec(`
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
  `),o=!0)}function d(e){let t=i(e);return{id:"string"==typeof t.id?t.id:"",apiKeyId:"string"==typeof t.api_key_id?t.api_key_id:"",scopeType:u(t.scope_type),scopeValue:"string"==typeof t.scope_value?t.scope_value:"",tokenLimit:s(t.token_limit),resetInterval:l(t.reset_interval),resetTime:"string"==typeof t.reset_time&&t.reset_time?t.reset_time:"00:00",enabled:0!==s(t.enabled,1),createdAt:"string"==typeof t.created_at?t.created_at:"",updatedAt:"string"==typeof t.updated_at?t.updated_at:""}}function p(e,t=Date.now()){let r=function(e,t="00:00",r=Date.now()){let o,i=new Date(r),[s,u]=(o=(function(e){if("string"==typeof e){let t=e.trim().match(n);if(t){let e=Math.min(Math.max(parseInt(t[1],10),0),23),r=Math.min(Math.max(parseInt(t[2],10),0),59);return`${String(e).padStart(2,"0")}:${String(r).padStart(2,"0")}`}}return"00:00"})(t).match(n))?[parseInt(o[1],10),parseInt(o[2],10)]:[0,0],l=i.getUTCFullYear(),c=i.getUTCMonth(),d=i.getUTCDate();if("weekly"===e){let e=(i.getUTCDay()+6)%7,t=a(l,c,d-e,s,u);return r>=t?{periodStartAt:t,nextResetAt:a(l,c,d-e+7,s,u)}:{periodStartAt:a(l,c,d-e-7,s,u),nextResetAt:t}}if("monthly"===e){let e=a(l,c,1,s,u);return r>=e?{periodStartAt:e,nextResetAt:a(l,c+1,1,s,u)}:{periodStartAt:a(l,c-1,1,s,u),nextResetAt:e}}let p=a(l,c,d,s,u);return r>=p?{periodStartAt:p,nextResetAt:a(l,c,d+1,s,u)}:{periodStartAt:a(l,c,d-1,s,u),nextResetAt:p}}(e.resetInterval,e.resetTime,t);return{windowStart:String(r.periodStartAt),didReset:!1,periodStartAt:r.periodStartAt,nextResetAt:r.nextResetAt}}e.s(["deleteTokenLimit",0,function(e){c();let t=(0,r.getDbInstance)();return t.prepare("DELETE FROM api_key_token_counters WHERE limit_id = ?").run(e),t.prepare("DELETE FROM api_key_token_limit_reset_logs WHERE limit_id = ?").run(e),t.prepare("DELETE FROM api_key_token_limits WHERE id = ?").run(e).changes>0},"getTokenLimitsForRequest",0,function(e,t,n){return c(),(0,r.getDbInstance)().prepare(`SELECT * FROM api_key_token_limits
       WHERE api_key_id = @apiKeyId
         AND enabled = 1
         AND (
           (scope_type = 'global')
           OR (scope_type = 'model' AND scope_value = @model)
           OR (scope_type = 'provider' AND scope_value = @provider)
         )`).all({apiKeyId:e,model:n||"",provider:t||""}).map(d)},"getWindowUsage",0,function(e,t=Date.now()){c();let n=(0,r.getDbInstance)(),{windowStart:a}=p(e,t);return s(i(n.prepare("SELECT tokens_used FROM api_key_token_counters WHERE limit_id = ? AND window_start = ?").get(e.id,a)).tokens_used)},"incrementWindowTokens",0,function(e,t,n){c();let a=(0,r.getDbInstance)(),o=Math.max(0,Math.floor(s(n)));return s(i(a.prepare(`INSERT INTO api_key_token_counters (limit_id, window_start, tokens_used, updated_at)
       VALUES (@limitId, @windowStart, @tokens, datetime('now'))
       ON CONFLICT(limit_id, window_start)
       DO UPDATE SET tokens_used = tokens_used + excluded.tokens_used,
                     updated_at  = datetime('now')
       RETURNING tokens_used`).get({limitId:e,windowStart:t,tokens:o})).tokens_used)},"listTokenLimits",0,function(e){return c(),(0,r.getDbInstance)().prepare(`SELECT * FROM api_key_token_limits
       WHERE api_key_id = ?
       ORDER BY CASE scope_type WHEN 'model' THEN 0 WHEN 'provider' THEN 1 ELSE 2 END, scope_value`).all(e).map(d)},"logTokenLimitReset",0,function(e,t,n){c(),(0,r.getDbInstance)().prepare(`INSERT INTO api_key_token_limit_reset_logs (limit_id, reset_at, prev_tokens, window_start)
     VALUES (?, datetime('now'), ?, ?)`).run(e,Math.max(0,Math.floor(s(t))),n)},"resetWindowIfElapsed",0,p,"upsertTokenLimit",0,function(e){c();let n=(0,r.getDbInstance)(),a=u(e.scopeType),o="global"===a?"":(e.scopeValue??"").trim(),i=l(e.resetInterval),p="string"==typeof e.resetTime&&e.resetTime?e.resetTime:"00:00",_=+(!1!==e.enabled),E=Math.floor(s(e.tokenLimit)),m=e.id&&e.id.trim()?e.id.trim():(0,t.randomUUID)();return n.prepare(`INSERT INTO api_key_token_limits
       (id, api_key_id, scope_type, scope_value, token_limit, reset_interval, reset_time, enabled, created_at, updated_at)
     VALUES (@id, @apiKeyId, @scopeType, @scopeValue, @tokenLimit, @resetInterval, @resetTime, @enabled, datetime('now'), datetime('now'))
     ON CONFLICT(api_key_id, scope_type, scope_value)
     DO UPDATE SET token_limit    = excluded.token_limit,
                   reset_interval = excluded.reset_interval,
                   reset_time     = excluded.reset_time,
                   enabled        = excluded.enabled,
                   updated_at     = datetime('now')`).run({id:m,apiKeyId:e.apiKeyId,scopeType:a,scopeValue:o,tokenLimit:E,resetInterval:i,resetTime:p,enabled:_}),d(n.prepare("SELECT * FROM api_key_token_limits WHERE api_key_id = ? AND scope_type = ? AND scope_value = ?").get(e.apiKeyId,a,o))}],472139)},581904,e=>{"use strict";let t;var r,n=e.i(504208),a=e.i(118770);let o={debug:0,info:1,warn:2,error:3},i=(0,a.getAppLogLevel)("info").toLowerCase(),s=Object.prototype.hasOwnProperty.call(o,i)?o[i]:o.info,u="json"===(0,a.getAppLogFormat)("text");function l(e){switch(e){case"debug":return console.debug;case"warn":return console.warn;case"error":return console.error;default:return console.log}}function c(e){if(!e||"object"!=typeof e)return"";let t={};for(let[r,n]of Object.entries(e))null!=n&&(t[r]=n);return Object.keys(t).length>0?` ${JSON.stringify(t)}`:""}!function(e=null){}();let d=(r="DB_PLUGINS",t=(e,t,n)=>{if(o[e]<s)return;let a=l(e);if(u){let o={ts:new Date().toISOString(),level:e,tag:r,msg:t};n&&"object"==typeof n&&Object.keys(n).length>0&&(o.data=n),a(JSON.stringify(o))}else a(`[${e.toUpperCase()}] [${r}] ${t}${c(n)}`)},{debug:(e,r)=>t("debug",e,r),info:(e,r)=>t("info",e,r),warn:(e,r)=>t("warn",e,r),error:(e,r)=>t("error",e,r)});function p(e){return{id:e.id,name:e.name,version:e.version,description:e.description,author:e.author,license:e.license,main:e.main,source:e.source,tags:e.tags,status:e.status,enabled:e.enabled,manifest:e.manifest,config:e.config,configSchema:e.config_schema,hooks:e.hooks,permissions:e.permissions,pluginDir:e.plugin_dir,errorMessage:e.error_message,installedAt:e.installed_at,updatedAt:e.updated_at,activatedAt:e.activated_at}}function _(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM plugins WHERE name = ?").get(e);return t?p(t):null}e.s(["deletePlugin",0,function(e){let t=(0,n.getDbInstance)().prepare("DELETE FROM plugins WHERE name = ?").run(e);return t.changes>0&&d.info("plugin.deleted",{name:e}),t.changes>0},"getPluginById",0,function(e){let t=(0,n.getDbInstance)().prepare("SELECT * FROM plugins WHERE id = ?").get(e);return t?p(t):null},"getPluginByName",0,_,"insertPlugin",0,function(e){let t=(0,n.getDbInstance)(),r=new Date().toISOString();t.prepare(`INSERT INTO plugins (
      id, name, version, description, author, license, main, source, tags,
      status, enabled, manifest, config, config_schema, hooks, permissions,
      plugin_dir, installed_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(e.id,e.name,e.version,e.description??null,e.author??null,e.license??"MIT",e.main,e.source??"local",JSON.stringify(e.tags??[]),e.status??"installed",+!!e.enabled,JSON.stringify(e.manifest),JSON.stringify(e.config??{}),JSON.stringify(e.configSchema??{}),JSON.stringify(e.hooks??[]),JSON.stringify(e.permissions??[]),e.pluginDir,r,r),d.info("plugin.inserted",{id:e.id,name:e.name});let a=_(e.name);if(!a)throw Error(`Failed to retrieve plugin '${e.name}' after insertion`);return a},"listPlugins",0,function(e){let t=(0,n.getDbInstance)();return(e?t.prepare("SELECT * FROM plugins WHERE status = ? ORDER BY name").all(e):t.prepare("SELECT * FROM plugins ORDER BY name").all()).map(p)},"pluginExists",0,function(e){return!!(0,n.getDbInstance)().prepare("SELECT 1 FROM plugins WHERE name = ?").get(e)},"updatePluginConfig",0,function(e,t){let r=(0,n.getDbInstance)(),a=new Date().toISOString();return r.prepare("UPDATE plugins SET config = ?, updated_at = ? WHERE name = ?").run(JSON.stringify(t),a,e).changes>0},"updatePluginStatus",0,function(e,t,r){let a=(0,n.getDbInstance)(),o=new Date().toISOString(),i="active"===t?o:null,s=a.prepare(`UPDATE plugins SET status = ?, enabled = ?, error_message = ?,
       updated_at = ?, activated_at = COALESCE(?, activated_at)
       WHERE name = ?`).run(t,+("active"===t),r??null,o,i,e);return s.changes>0&&d.info("plugin.status_updated",{name:e,status:t}),s.changes>0}],581904)},976974,e=>{"use strict";var t=e.i(504208);function r(e){return{apiKeyId:e.api_key_id,sourceType:e.source_type,token:e.token,baseUrl:e.base_url,vaultPath:e.vault_path,enabled:1===e.enabled}}e.s(["deleteApiKeyContextSource",0,function(e,r){(0,t.getDbInstance)().prepare("DELETE FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ?").run(e,r)},"getApiKeyContextSource",0,function(e,n){if(!e)return null;let a=(0,t.getDbInstance)().prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ? AND enabled = 1").get(e,n);return a?r(a):null},"listApiKeyContextSources",0,function(e){return(0,t.getDbInstance)().prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ?").all(e).map(r)},"setApiKeyContextSource",0,function(e,r,n){let a=(0,t.getDbInstance)(),o=a.prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ?").get(e,r),i=new Date().toISOString();o?a.prepare(`UPDATE api_key_context_sources SET
        token = COALESCE(?, token),
        base_url = COALESCE(?, base_url),
        vault_path = COALESCE(?, vault_path),
        enabled = COALESCE(?, enabled),
        updated_at = ?
      WHERE api_key_id = ? AND source_type = ?`).run(n.token??null,n.baseUrl??null,n.vaultPath??null,void 0!==n.enabled?+!!n.enabled:null,i,e,r):a.prepare(`INSERT INTO api_key_context_sources
        (api_key_id, source_type, token, base_url, vault_path, enabled, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(e,r,n.token??null,n.baseUrl??null,n.vaultPath??null,void 0!==n.enabled?+!!n.enabled:1,i,i)}])},979158,e=>{"use strict";var t=e.i(504208);e.s(["sumUsageTokensThisMonth",0,function(e=(0,t.getDbInstance)()){try{let t=e.prepare(`SELECT COALESCE(SUM(total_input_tokens + total_output_tokens), 0) AS used
         FROM daily_usage_summary
         WHERE date >= strftime('%Y-%m-01','now')`).get();return t?.used??0}catch{return 0}}])},846702,e=>{"use strict";var t=e.i(504208),r=e.i(446202);function n(e){let t=(0,r.rowToCamel)(e)??{};return{model:String(t.model??""),source:String(t.source??""),category:String(t.category??""),score:"number"==typeof t.score?t.score:0,eloRaw:"number"==typeof t.eloRaw?t.eloRaw:null,confidence:"string"==typeof t.confidence?t.confidence:null,syncedAt:String(t.syncedAt??""),expiresAt:"string"==typeof t.expiresAt?t.expiresAt:null}}function a(e,r){let a=(0,t.getDbInstance)().prepare(`SELECT * FROM model_intelligence
       WHERE model = ? AND category = ?
         AND source IN ('user_override', 'arena_elo', 'models_dev_tier')
         AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))
       ORDER BY CASE source
         WHEN 'user_override' THEN 1
         WHEN 'arena_elo' THEN 2
         WHEN 'models_dev_tier' THEN 3
       END
       LIMIT 1`).get(e,r);return a?n(a):null}function o(e){(0,t.getDbInstance)().prepare(`INSERT OR REPLACE INTO model_intelligence
       (model, source, category, score, elo_raw, confidence, synced_at, expires_at)
     VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)`).run(e.model,e.source,e.category,e.score,e.eloRaw??null,e.confidence??null,e.expiresAt??null)}function i(e,r,n){return((0,t.getDbInstance)().prepare(`DELETE FROM model_intelligence
       WHERE model = ? AND source = ? AND category = ?`).run(e,r,n).changes??0)>0}e.s(["bulkUpsertModelIntelligence",0,function(e){if(0===e.length)return 0;let r=(0,t.getDbInstance)(),n=r.prepare(`INSERT OR REPLACE INTO model_intelligence
       (model, source, category, score, elo_raw, confidence, synced_at, expires_at)
     VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)`);return r.transaction(()=>{let t=0;for(let r of e)n.run(r.model,r.source,r.category,r.score,r.eloRaw??null,r.confidence??null,r.expiresAt??null),t++;return t})()},"deleteExpiredIntelligence",0,function(e){let r=(0,t.getDbInstance)(),n=["expires_at IS NOT NULL","datetime(expires_at) < datetime('now')"],a=[];e&&(n.push("source = ?"),a.push(e));let o=n.join(" AND ");return r.prepare(`DELETE FROM model_intelligence WHERE ${o}`).run(...a).changes??0},"deleteModelIntelligence",0,i,"deleteModelIntelligenceBySource",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM model_intelligence WHERE source = ?").run(e).changes??0},"deleteUserFitnessOverrideEntry",0,function(e,t){return i(e.toLowerCase(),"user_override",t.toLowerCase())},"getModelIntelligence",0,a,"getModelIntelligenceBySource",0,function(e,r,a){let o=(0,t.getDbInstance)().prepare(`SELECT * FROM model_intelligence
       WHERE model = ? AND source = ? AND category = ?
         AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))`).get(e,r,a);return o?n(o):null},"getResolvedTaskFitness",0,function(e,t){let r=a(e,t);return r?r.score:null},"listModelIntelligence",0,function(e){let r=(0,t.getDbInstance)(),a=[],o=[];e?.source&&(a.push("source = ?"),o.push(e.source)),e?.category&&(a.push("category = ?"),o.push(e.category));let i=a.length>0?`WHERE ${a.join(" AND ")}`:"",s=`SELECT * FROM model_intelligence ${i} ORDER BY model ASC, source ASC, category ASC`;return r.prepare(s).all(...o).map(n)},"setUserFitnessOverrideEntry",0,function(e,t,r){o({model:e.toLowerCase(),source:"user_override",category:t.toLowerCase(),score:Math.max(0,Math.min(1,r)),eloRaw:null,confidence:null,expiresAt:null})},"upsertModelIntelligence",0,o])},513586,e=>{"use strict";var t=e.i(504208);e.s(["getFallbackStats",0,function(e,r){return(0,t.getDbInstance)().prepare(`
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
      `).all()}])},633274,e=>{"use strict";var t=e.i(504208);e.s(["getAccountCostRows",0,function(e,r){return(0,t.getDbInstance)().prepare(`
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
    `).all(r)}])},657986,e=>{"use strict";var t=e.i(504208);e.s(["getAutoRoutingTopProviders",0,function(){return(0,t.getDbInstance)().prepare(`
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
    `).all()}])},997721,e=>{"use strict";var t=e.i(504208);let r=["created_at","expires_at","hit_count","tokens_saved","model"];e.s(["deleteSemanticCacheByModel",0,function(e){return{deleted:(0,t.getDbInstance)().prepare("DELETE FROM semantic_cache WHERE model = ?").run(e).changes}},"deleteSemanticCacheBySignature",0,function(e){return(0,t.getDbInstance)().prepare("DELETE FROM semantic_cache WHERE signature = ?").run(e),{deleted:1}},"listSemanticCacheEntries",0,function(e){let n=(0,t.getDbInstance)(),{page:a,limit:o,search:i,model:s,sortBy:u,sortOrder:l}=e,c=[],d=[];i&&(c.push("(signature LIKE ? OR model LIKE ?)"),d.push(`%${i}%`,`%${i}%`)),s&&(c.push("model = ?"),d.push(s));let p=c.length>0?`WHERE ${c.join(" AND ")}`:"",_=r.includes(u)?u:"created_at",E=n.prepare(`SELECT COUNT(*) as total FROM semantic_cache ${p}`).get(...d);return{entries:n.prepare(`SELECT id, signature, model, hit_count, tokens_saved, created_at, expires_at
       FROM semantic_cache ${p}
       ORDER BY ${_} ${"asc"===l?"ASC":"DESC"}
       LIMIT ? OFFSET ?`).all(...d,o,(a-1)*o),total:E?.total||0}}])},605555,e=>{"use strict";var t=e.i(504208);e.s(["exportProxyLogsSince",0,function(e){return(0,t.getDbInstance)().prepare("SELECT * FROM proxy_logs WHERE timestamp >= @since ORDER BY timestamp DESC").all({since:e})}])},164456,e=>{"use strict";var t=e.i(504208);let r="provider_param_filters",n=null,a=0;function o(){a++,n=null}function i(e){return null!==e&&"object"==typeof e&&!Array.isArray(e)}function s(e){return"string"==typeof e&&e.length>0?e:null}function u(e){return Array.isArray(e)?e.filter(e=>"string"==typeof e):[]}function l(){return null===n&&(n=function(){let e=function(e){let r=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(e),n={};for(let e of r)n[e.key]=function(e){if("string"!=typeof e)return e;try{return JSON.parse(e)}catch{return e}}(e.value);return n}(r),n=new Map;for(let[t,r]of Object.entries(e)){let e=function(e){if(!i(e))return null;let t=u(e.block),r=u(e.allow),n=function(e){let t={};if(!i(e))return t;for(let[r,n]of Object.entries(e)){if(!i(n))continue;let e=function(e){let t=u(e.block),r=u(e.allow);if(0===t.length&&0===r.length)return null;let n={};return t.length>0&&(n.block=t),r.length>0&&(n.allow=r),n}(n);e&&(t[r]=e)}return t}(e.models),a="boolean"==typeof e.autoLearn&&e.autoLearn;return{block:t,allow:r,models:Object.keys(n).length>0?n:void 0,autoLearn:a}}(r);e&&n.set(t,e)}return n}()),n}function c(e){return s(e)?l().get(e)??null:null}function d(e,n){if(!s(e))return;let a=(0,t.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)"),i={block:n.block??[],allow:n.allow??[],autoLearn:n.autoLearn??!1,models:n.models&&Object.keys(n.models).length>0?n.models:void 0};a.run(r,e,JSON.stringify(i)),o()}let p="__global__";e.s(["addParamToBlocklist",0,function(e,t,r){if(!s(e)||!s(t))return;let n=c(e)??{block:[],allow:[],autoLearn:!1};if(r){let e=n.models??{},a=e[r]??{};if(Array.isArray(a.block)&&a.block.includes(t))return;let o=[...a.block??[],t];e[r]={...a,block:o},n.models=e}else{if(n.block.includes(t))return;n.block=[...n.block,t]}d(e,n)},"deleteParamFilterConfig",0,function(e){s(e)&&((0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(r,e),o())},"getParamFilterConfig",0,c,"isAutoLearnGloballyEnabled",0,function(){let e=c(p);return e?.autoLearn===!0},"loadParamFilterConfigs",0,l,"setGlobalAutoLearnEnabled",0,function(e){let t=c(p);d(p,{block:t?.block??[],allow:t?.allow??[],autoLearn:e})},"setParamFilterConfig",0,d])},976119,e=>{"use strict";var t=e.i(504208);let r="interception_rules",n=null;function a(e){return null!==e&&"object"==typeof e&&!Array.isArray(e)}function o(e){return"string"==typeof e&&e.trim().length>0?e.trim():null}function i(e){return"boolean"==typeof e?e:void 0}function s(e){return"firecrawl"===e||"jina"===e||"tavily"===e?e:void 0}function u(e){return o(e)?(null===n&&(n=function(){let e=function(e){let r=(0,t.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(e),n={};for(let e of r)n[e.key]=function(e){if("string"!=typeof e)return e;try{return JSON.parse(e)}catch{return e}}(e.value);return n}(r),n=new Map;for(let[t,r]of Object.entries(e)){let e=function(e){if(!a(e))return null;let t=function(e){let t={};if(!a(e))return t;for(let[r,n]of Object.entries(e)){let e=function(e){if(!a(e))return null;let t={interceptSearch:i(e.interceptSearch),interceptFetch:i(e.interceptFetch),fetchBackend:s(e.fetchBackend),fetchProxyUrl:o(e.fetchProxyUrl)??void 0};return Object.values(t).some(e=>void 0!==e)?t:null}(n);e&&(t[r]=e)}return t}(e.models);return{interceptSearch:i(e.interceptSearch),interceptFetch:i(e.interceptFetch),fetchBackend:s(e.fetchBackend),fetchProxyUrl:o(e.fetchProxyUrl)??void 0,models:Object.keys(t).length>0?t:void 0}}(r);e&&n.set(t,e)}return n}()),n).get(e)??null:null}e.s(["deleteInterceptionRules",0,function(e){let a=o(e);a&&((0,t.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(r,a),n=null)},"getInterceptionRules",0,u,"resolveInterceptSearch",0,function(e,t){let r=o(e);if(!r)return;let n=u(r);if(!n)return;let a=o(t);return a&&n.models?.[a]?.interceptSearch!==void 0?n.models[a].interceptSearch:n.interceptSearch},"setInterceptionRules",0,function(e,a){let i=o(e);if(!i)return;let s=(0,t.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)"),u={interceptSearch:a.interceptSearch,interceptFetch:a.interceptFetch,fetchBackend:a.fetchBackend,fetchProxyUrl:a.fetchProxyUrl,models:a.models&&Object.keys(a.models).length>0?a.models:void 0};s.run(r,i,JSON.stringify(u)),n=null}])},265935,e=>e.a(async(t,r)=>{try{var n=e.i(261574);e.i(342507),e.i(359624),e.i(839193),e.i(660623),e.i(53671),e.i(203119),e.i(542876),e.i(376369);var a=e.i(298422);e.i(410701),e.i(267365),e.i(825538),e.i(223194),e.i(109536),e.i(655734),e.i(130521),e.i(658112),e.i(510864),e.i(33900),e.i(825849),e.i(788468),e.i(912386),e.i(110002),e.i(188356),e.i(689724),e.i(620561),e.i(104472),e.i(653900),e.i(91973),e.i(490484),e.i(389769),e.i(504525),e.i(63477),e.i(423421),e.i(163971),e.i(584993),e.i(53906),e.i(525503),e.i(47894),e.i(330837),e.i(162186),e.i(897325),e.i(797640),e.i(829778),e.i(316020),e.i(115205);var o=e.i(90896);e.i(52530),e.i(807741),e.i(269032),e.i(218550),e.i(675367),e.i(255329),e.i(472139),e.i(581904),e.i(976974),e.i(979158),e.i(846702),e.i(513586),e.i(633274),e.i(657986),e.i(997721),e.i(605555),e.i(164456),e.i(976119);var i=t([n,a,o]);[n,a,o]=i.then?(await i)():i,e.s([]),r()}catch(e){r(e)}},!1)];

//# sourceMappingURL=src_1ytplee._.js.map