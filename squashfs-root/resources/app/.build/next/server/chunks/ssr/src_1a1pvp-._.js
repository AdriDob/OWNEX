module.exports=[364299,a=>{"use strict";var b=a.i(738037);a.s(["getCacheStatsSummary",0,function(a){let c=(0,b.getDbInstance)();a&&a.toISOString();let d=a?c.prepare("SELECT COUNT(*) as totalRequests, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats WHERE created_at >= ?").get(a.toISOString()):c.prepare("SELECT COUNT(*) as totalRequests, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats").get();if(!d||0===d.totalRequests)return{totalRequests:0,avgNetSavings:0,cacheHitRate:0,byProvider:{}};let e=a?c.prepare("SELECT provider, COUNT(*) as count, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats WHERE created_at >= ? GROUP BY provider").all(a.toISOString()):c.prepare("SELECT provider, COUNT(*) as count, AVG(net_savings) as avgNetSavings, SUM(estimated_cache_hit) * 1.0 / COUNT(*) as cacheHitRate FROM compression_cache_stats GROUP BY provider").all(),f={};for(let a of e)f[a.provider]={count:a.count,avgNetSavings:a.avgNetSavings,cacheHitRate:a.cacheHitRate};return{totalRequests:d.totalRequests,avgNetSavings:d.avgNetSavings??0,cacheHitRate:d.cacheHitRate??0,byProvider:f}},"recordCacheStats",0,function(a){let c=(0,b.getDbInstance)(),d=`INSERT INTO compression_cache_stats (
    provider, 
    model, 
    compression_mode, 
    cache_control_present, 
    estimated_cache_hit, 
    tokens_saved_compression, 
    tokens_saved_caching, 
    net_savings
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;c.prepare(d).run(a.provider,a.model??"",a.compressionMode,+!!a.cacheControlPresent,+!!a.estimatedCacheHit,a.tokensSavedCompression,a.tokensSavedCaching,a.netSavings)}])},585868,a=>{"use strict";var b=a.i(772522),c=a.i(606373),d=a.i(738037),e=a.i(144544);let f="default-caveman",g="Standard Savings",h="Default RTK + Caveman compression pipeline";function i(){return[{engine:"rtk",intensity:"standard"},{engine:"caveman",intensity:"full"}]}function j(a,b){if(Array.isArray(a))return a;if("string"!=typeof a)return b;try{let c=JSON.parse(a);return Array.isArray(c)?c:b}catch{return b}}let k=["lite","caveman","aggressive","ultra","rtk","headroom","session-dedup","ccr","llmlingua","relevance"];function l(a){return j(a,[]).filter(a=>a&&"object"==typeof a&&k.includes(String(a.engine)))}function m(){let a=(0,d.getDbInstance)();a.exec(`
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
  `),a.prepare(`
    INSERT OR IGNORE INTO compression_combos (
      id, name, description, pipeline, language_packs, output_mode, output_mode_intensity, is_default
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(f,g,h,JSON.stringify(i()),JSON.stringify(["en"]),0,"full",1),function(){let a=(0,d.getDbInstance)(),b=a.prepare("SELECT name, description, pipeline FROM compression_combos WHERE id = ?").get(f);if(!b)return;let c=String(b.description??"");String(b.name??"")===g&&("Default Caveman compression pipeline"===c||c===h)&&function(a){if(1!==a.length)return!1;let[b]=a;return"caveman"===b.engine&&(void 0===b.intensity||"full"===b.intensity)}(l(b.pipeline))&&a.prepare(`
    UPDATE compression_combos
    SET description = ?, pipeline = ?, updated_at = ?
    WHERE id = ?
  `).run(h,JSON.stringify(i()),new Date().toISOString(),f)}()}function n(a){let b;if(!a)return null;let c=(0,e.rowToCamel)(a);return{id:String(c.id),name:String(c.name??""),description:String(c.description??""),pipeline:l(c.pipeline),languagePacks:[...new Set((b=j(c.languagePacks,["en"]).filter(a=>"string"==typeof a&&a.trim().length>0)).length>0?b.map(a=>a.trim()):["en"])],outputMode:!!c.outputMode,outputModeIntensity:String(c.outputModeIntensity??"full"),isDefault:!!c.isDefault,createdAt:String(c.createdAt??""),updatedAt:String(c.updatedAt??"")}}function o(a){if(!a)return null;let b=(0,e.rowToCamel)(a);return{id:String(b.id),compressionComboId:String(b.compressionComboId),routingComboId:String(b.routingComboId),createdAt:String(b.createdAt??"")}}function p(a,c){let d=new Date().toISOString();return{id:c?.id??a.id??(0,b.v4)(),name:a.name?.trim()||c?.name||"Compression Combo",description:a.description??c?.description??"",pipeline:a.pipeline&&a.pipeline.length>0?a.pipeline:c?.pipeline&&c.pipeline.length>0?c.pipeline:i(),languagePacks:a.languagePacks&&a.languagePacks.length>0?a.languagePacks:c?.languagePacks&&c.languagePacks.length>0?c.languagePacks:["en"],outputMode:a.outputMode??c?.outputMode??!1,outputModeIntensity:a.outputModeIntensity??c?.outputModeIntensity??"full",isDefault:a.isDefault??c?.isDefault??!1,createdAt:c?.createdAt??d,updatedAt:d}}function q(a){return m(),n((0,d.getDbInstance)().prepare("SELECT * FROM compression_combos WHERE id = ?").get(a))}function r(){return m(),n((0,d.getDbInstance)().prepare("SELECT * FROM compression_combos WHERE is_default = 1 ORDER BY updated_at DESC LIMIT 1").get())}let s={"session-dedup":3,ccr:4,lite:5,rtk:10,headroom:15,caveman:20,aggressive:30,llmlingua:35,ultra:40};a.s(["assignRoutingCombo",0,function(a,e){return m(),!!q(a)&&!!e.trim()&&((0,d.getDbInstance)().prepare(`
      INSERT OR REPLACE INTO compression_combo_assignments (
        id, compression_combo_id, routing_combo_id, created_at
      )
      VALUES (?, ?, ?, ?)
    `).run((0,b.v4)(),a,e.trim(),new Date().toISOString()),(0,c.backupDbFile)("pre-write"),!0)},"createCompressionCombo",0,function(a){m();let b=(0,d.getDbInstance)(),e=p(a);return b.transaction(()=>{e.isDefault&&b.prepare("UPDATE compression_combos SET is_default = 0").run(),b.prepare(`
      INSERT INTO compression_combos (
        id, name, description, pipeline, language_packs, output_mode, output_mode_intensity,
        is_default, created_at, updated_at
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(e.id,e.name,e.description,JSON.stringify(e.pipeline),JSON.stringify(e.languagePacks),+!!e.outputMode,e.outputModeIntensity,+!!e.isDefault,e.createdAt,e.updatedAt)})(),(0,c.backupDbFile)("pre-write"),q(e.id)},"deleteCompressionCombo",0,function(a){m();let b=q(a);if(!b||b.isDefault)return!1;let e=(0,d.getDbInstance)().prepare("DELETE FROM compression_combos WHERE id = ?").run(a);return e.changes>0&&(0,c.backupDbFile)("pre-write"),e.changes>0},"getAssignmentsForCompressionCombo",0,function(a){return m(),(0,d.getDbInstance)().prepare("SELECT * FROM compression_combo_assignments WHERE compression_combo_id = ? ORDER BY routing_combo_id").all(a).map(o).filter(a=>null!==a)},"getCompressionCombo",0,q,"getCompressionComboForRoutingCombo",0,function(a){return m(),n((0,d.getDbInstance)().prepare(`
      SELECT c.*
      FROM compression_combos c
      JOIN compression_combo_assignments a ON a.compression_combo_id = c.id
      WHERE a.routing_combo_id = ?
      LIMIT 1
    `).get(a))},"getDefaultCompressionCombo",0,r,"listCompressionCombos",0,function(){return m(),(0,d.getDbInstance)().prepare("SELECT * FROM compression_combos ORDER BY is_default DESC, name COLLATE NOCASE ASC").all().map(n).filter(a=>null!==a)},"setDefaultCompressionCombo",0,function(a){if(m(),!q(a))return!1;let b=(0,d.getDbInstance)(),e=new Date().toISOString();return b.transaction(()=>{b.prepare("UPDATE compression_combos SET is_default = 0").run(),b.prepare("UPDATE compression_combos SET is_default = 1, updated_at = ? WHERE id = ?").run(e,a)})(),(0,c.backupDbFile)("pre-write"),!0},"setEngineInDefaultCombo",0,function(a,b,e){if(!k.includes(a))return null;m();let f=r();if(!f)return null;let g=[...f.pipeline];if(b){let b=g.findIndex(b=>b.engine===a);b>=0?void 0!==e&&(g[b]={...g[b],config:e}):g.push({engine:a,...e?{config:e}:{}}),g.sort((a,b)=>(s[a.engine]??50)-(s[b.engine]??50))}else g=g.filter(b=>b.engine!==a);let h=(0,d.getDbInstance)(),i=new Date().toISOString();return h.prepare("UPDATE compression_combos SET pipeline = ?, updated_at = ? WHERE id = ?").run(JSON.stringify(g),i,f.id),(0,c.backupDbFile)("pre-write"),q(f.id)},"unassignRoutingCombo",0,function(a,b){m();let e=(0,d.getDbInstance)().prepare("DELETE FROM compression_combo_assignments WHERE compression_combo_id = ? AND routing_combo_id = ?").run(a,b);return e.changes>0&&(0,c.backupDbFile)("pre-write"),e.changes>0},"updateAssignments",0,function(a,e){if(m(),!q(a))return!1;let f=[...new Set(e.map(a=>a.trim()).filter(Boolean))],g=(0,d.getDbInstance)();return g.transaction(()=>{if(g.prepare("DELETE FROM compression_combo_assignments WHERE compression_combo_id = ?").run(a),f.length>0){let c=g.prepare("DELETE FROM compression_combo_assignments WHERE routing_combo_id = ?"),d=g.prepare(`
        INSERT INTO compression_combo_assignments (
          id, compression_combo_id, routing_combo_id, created_at
        )
        VALUES (?, ?, ?, ?)
      `);for(let e of f)c.run(e),d.run((0,b.v4)(),a,e,new Date().toISOString())}})(),(0,c.backupDbFile)("pre-write"),!0},"updateCompressionCombo",0,function(a,b){m();let e=q(a);if(!e)return null;let f=p(b,e),g=(0,d.getDbInstance)();return g.transaction(()=>{f.isDefault&&g.prepare("UPDATE compression_combos SET is_default = 0").run(),g.prepare(`
      UPDATE compression_combos
      SET name = ?, description = ?, pipeline = ?, language_packs = ?, output_mode = ?,
          output_mode_intensity = ?, is_default = ?, updated_at = ?
      WHERE id = ?
    `).run(f.name,f.description,JSON.stringify(f.pipeline),JSON.stringify(f.languagePacks),+!!f.outputMode,f.outputModeIntensity,+!!f.isDefault,f.updatedAt,a)})(),(0,c.backupDbFile)("pre-write"),q(a)}])},446801,a=>{"use strict";var b=a.i(738037);function c(){(0,b.getDbInstance)().exec(`
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
  `)}a.s(["getCompressionRunTelemetrySummary",0,function(){let a=(0,b.getDbInstance)();c();let d=a.prepare(`SELECT tokens_before, tokens_after, output_styles, output_style_bypass, output_tokens
       FROM compression_run_telemetry`).all(),e={totalRuns:d.length,totalTokensSaved:0,runsWithStyles:0,bypassCount:0,totalOutputTokens:0,appliedStyleCounts:{}};for(let a of d)if(e.totalTokensSaved+=Math.max(0,a.tokens_before-a.tokens_after),e.totalOutputTokens+=a.output_tokens??0,a.output_style_bypass&&(e.bypassCount+=1),a.output_styles){e.runsWithStyles+=1;try{for(let b of JSON.parse(a.output_styles))e.appliedStyleCounts[b.id]=(e.appliedStyleCounts[b.id]??0)+1}catch{}}return e},"insertCompressionRunTelemetryRow",0,function(a){try{let d=(0,b.getDbInstance)();c(),d.prepare(`INSERT INTO compression_run_telemetry (
        timestamp, request_id, model, provider, source,
        tokens_before, tokens_after, ratio, cost_delta,
        output_styles, output_style_bypass, output_tokens
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(Date.now(),a.requestId??null,a.model??null,a.provider??null,a.source??null,a.tokensBefore,a.tokensAfter,a.ratio,a.costDelta??null,a.outputStyles&&a.outputStyles.length>0?JSON.stringify(a.outputStyles):null,a.outputStyleBypass??null,a.outputTokens??null)}catch{}}])},426720,a=>{"use strict";var b=a.i(666680),c=a.i(738037),d=a.i(144544);function e(a,b,c){return a.prepare(`PRAGMA table_info(${b})`).all().some(a=>a&&"string"==typeof a.name&&a.name===c)}function f(a){a.prepare(`CREATE TABLE IF NOT EXISTS eval_suites (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )`).run(),e(a,"eval_suites","description")||a.prepare("ALTER TABLE eval_suites ADD COLUMN description TEXT").run(),e(a,"eval_suites","created_at")||a.prepare("ALTER TABLE eval_suites ADD COLUMN created_at TEXT NOT NULL DEFAULT ''").run(),e(a,"eval_suites","updated_at")||a.prepare("ALTER TABLE eval_suites ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''").run(),a.prepare(`CREATE TABLE IF NOT EXISTS eval_cases (
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
    )`).run(),e(a,"eval_cases","sort_order")||a.prepare("ALTER TABLE eval_cases ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0").run(),e(a,"eval_cases","model")||a.prepare("ALTER TABLE eval_cases ADD COLUMN model TEXT").run(),e(a,"eval_cases","input_json")||a.prepare("ALTER TABLE eval_cases ADD COLUMN input_json TEXT NOT NULL DEFAULT '{}'").run(),e(a,"eval_cases","expected_strategy")||a.prepare("ALTER TABLE eval_cases ADD COLUMN expected_strategy TEXT NOT NULL DEFAULT 'contains'").run(),e(a,"eval_cases","expected_value")||a.prepare("ALTER TABLE eval_cases ADD COLUMN expected_value TEXT").run(),e(a,"eval_cases","tags_json")||a.prepare("ALTER TABLE eval_cases ADD COLUMN tags_json TEXT").run(),e(a,"eval_cases","created_at")||a.prepare("ALTER TABLE eval_cases ADD COLUMN created_at TEXT NOT NULL DEFAULT ''").run(),e(a,"eval_cases","updated_at")||a.prepare("ALTER TABLE eval_cases ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''").run(),a.prepare("CREATE INDEX IF NOT EXISTS idx_eval_suites_updated_at ON eval_suites(updated_at DESC)").run(),a.prepare("CREATE INDEX IF NOT EXISTS idx_eval_cases_suite_order ON eval_cases(suite_id, sort_order ASC, created_at ASC)").run()}function g(a){if(a&&"object"==typeof a&&!Array.isArray(a))return a;if("string"!=typeof a||0===a.trim().length)return{};try{let b=JSON.parse(a);return b&&"object"==typeof b&&!Array.isArray(b)?b:{}}catch{return{}}}function h(a){let b=Number(a);return Number.isFinite(b)?b:0}function i(a){var b;let c=a&&"object"==typeof a&&!Array.isArray(a)?a:{},d=h(c.max_tokens),e={messages:Array.isArray(b=c.messages)?b.map(a=>{if(!a||"object"!=typeof a||Array.isArray(a))return null;let b="string"==typeof a.role?a.role.trim():"",c="string"==typeof a.content?a.content:"";return b&&c.trim()?{role:b,content:c}:null}).filter(a=>null!==a):[]};return d>0&&(e.max_tokens=Math.floor(d)),e}function j(a){let b=a&&"object"==typeof a&&!Array.isArray(a)?a:{},c="string"==typeof b.strategy?b.strategy.trim():"",d="string"==typeof b.value&&b.value.trim().length>0?b.value:void 0;return{strategy:"exact"===c||"regex"===c||"custom"===c?c:"contains",...d?{value:d}:{}}}function k(a,b){return`${a}:${"string"==typeof b&&b.trim().length>0?b.trim():"__default__"}`}function l(a={}){let b=(0,c.getDbInstance)(),e=[],f=[];a.suiteId&&(e.push("suite_id = ?"),f.push(a.suiteId)),a.runGroupId&&(e.push("run_group_id = ?"),f.push(a.runGroupId));let i=Number.isFinite(Number(a.limit))?Math.min(200,Math.max(1,Math.floor(Number(a.limit)))):20;f.push(i);let j=`SELECT *
    FROM eval_runs
    ${e.length>0?`WHERE ${e.join(" AND ")}`:""}
    ORDER BY created_at DESC
    LIMIT ?`;return b.prepare(j).all(...f).map(a=>(function(a){let b,c,e,f,i=(0,d.rowToCamel)(a);if(!i)return null;let j=g(i.summary??i.summaryJson),l=Object.fromEntries(Object.entries(g(i.outputs??i.outputsJson)).filter(a=>"string"==typeof a[0]).map(([a,b])=>[a,"string"==typeof b?b:String(b??"")]));return{id:"string"==typeof i.id?i.id:"",runGroupId:"string"==typeof i.runGroupId&&i.runGroupId.trim().length>0?i.runGroupId:null,suiteId:"string"==typeof i.suiteId?i.suiteId:"",suiteName:"string"==typeof i.suiteName?i.suiteName:"",target:(b=i.targetType,e="string"==typeof(c=i.targetId)&&c.trim().length>0?c.trim():null,{type:f="combo"===b||"model"===b||"suite-default"===b?b:"suite-default",id:e,key:k(f,e),label:"string"==typeof i.targetLabel&&i.targetLabel.trim().length>0?i.targetLabel.trim():"combo"===f?`Combo: ${e||"Unknown"}`:"model"===f?`Model: ${e||"Unknown"}`:"Suite defaults"}),apiKeyId:"string"==typeof i.apiKeyId&&i.apiKeyId.trim().length>0?i.apiKeyId:null,avgLatencyMs:h(i.avgLatencyMs),summary:{total:h(j.total??i.total),passed:h(j.passed??i.passed),failed:h(j.failed??i.failed),passRate:h(j.passRate??i.passRate)},results:function(a){if(Array.isArray(a))return a.filter(a=>!!a&&"object"==typeof a&&!Array.isArray(a));if("string"!=typeof a||0===a.trim().length)return[];try{let b=JSON.parse(a);return Array.isArray(b)?b.filter(a=>!!a&&"object"==typeof a&&!Array.isArray(a)):[]}catch{return[]}}(i.results??i.resultsJson),outputs:l,createdAt:"string"==typeof i.createdAt?i.createdAt:""}})(a)).filter(a=>null!==a)}function m(){let a=(0,c.getDbInstance)();f(a);let b=a.prepare("SELECT * FROM eval_suites ORDER BY updated_at DESC, created_at DESC").all(),e=a.prepare("SELECT * FROM eval_cases ORDER BY suite_id ASC, sort_order ASC, created_at ASC, id ASC").all(),k=new Map;for(let a of e){let b=function(a){let b=(0,d.rowToCamel)(a);if(!b)return null;let c=i(g(b.input??b.inputJson)),e=j({strategy:b.expectedStrategy,value:b.expectedValue});return{id:"string"==typeof b.id?b.id:"",suiteId:"string"==typeof b.suiteId?b.suiteId:"",name:"string"==typeof b.name?b.name:"",..."string"==typeof b.model&&b.model.trim().length>0?{model:b.model.trim()}:{},input:c,expected:e,tags:function(a){if(Array.isArray(a))return a.filter(a=>"string"==typeof a).map(a=>a.trim()).filter(a=>a.length>0);if("string"!=typeof a||0===a.trim().length)return[];try{let b=JSON.parse(a);return Array.isArray(b)?b.filter(a=>"string"==typeof a).map(a=>a.trim()).filter(a=>a.length>0):[]}catch{return[]}}(b.tags??b.tagsJson),sortOrder:h(b.sortOrder),createdAt:"string"==typeof b.createdAt?b.createdAt:"",updatedAt:"string"==typeof b.updatedAt?b.updatedAt:""}}(a);if(!b||!b.suiteId)continue;let c=k.get(b.suiteId)||[];c.push(b),k.set(b.suiteId,c)}return b.map(a=>{var b;let c,e=(0,d.rowToCamel)(a),f=e&&"string"==typeof e.id?e.id:"";return b=k.get(f)||[],(c=(0,d.rowToCamel)(a))?{id:"string"==typeof c.id?c.id:"",name:"string"==typeof c.name?c.name:"",..."string"==typeof c.description&&c.description.trim().length>0?{description:c.description}:{},source:"custom",caseCount:b.length,cases:b,createdAt:"string"==typeof c.createdAt?c.createdAt:"",updatedAt:"string"==typeof c.updatedAt?c.updatedAt:""}:null}).filter(a=>null!==a)}function n(a){let b=a.trim();return b&&m().find(a=>a.id===b)||null}a.s(["deleteCustomEvalSuite",0,function(a){let b=(0,c.getDbInstance)();f(b);let d=a.trim();if(!d)return!1;b.prepare("BEGIN").run();try{b.prepare("DELETE FROM eval_cases WHERE suite_id = ?").run(d);let a=b.prepare("DELETE FROM eval_suites WHERE id = ?").run(d);return b.prepare("COMMIT").run(),a.changes>0}catch(a){throw b.prepare("ROLLBACK").run(),a}},"getCustomEvalSuite",0,n,"getEvalScorecard",0,function(a={}){var b;let c,d,e=l({suiteId:a.suiteId,limit:a.limit||50});if(0===e.length)return null;let f=new Map;for(let a of e){let b=`${a.suiteId}:${a.target.key}`;f.has(b)||f.set(b,a)}return c=(b=Array.from(f.values()).map(a=>({suiteId:`${a.suiteId}:${a.target.key}`,suiteName:`${a.suiteName} \xb7 ${a.target.label}`,results:a.results,summary:a.summary}))).reduce((a,b)=>a+b.summary.total,0),d=b.reduce((a,b)=>a+b.summary.passed,0),{suites:b.length,totalCases:c,totalPassed:d,overallPassRate:c>0?Math.round(d/c*100):0,perSuite:b.map(a=>({id:a.suiteId,name:a.suiteName,passRate:a.summary.passRate}))}},"listCustomEvalSuites",0,m,"listEvalRuns",0,l,"saveCustomEvalSuite",0,function(a){let d=(0,c.getDbInstance)();f(d);let e=new Date().toISOString(),g="string"==typeof a.id&&a.id.trim().length>0?a.id.trim():(0,b.randomUUID)(),h=a.name.trim(),k="string"==typeof a.description&&a.description.trim().length>0?a.description.trim():null;if(!h)throw Error("Suite name is required");if(!Array.isArray(a.cases)||0===a.cases.length)throw Error("At least one eval case is required");d.prepare("BEGIN").run();try{d.prepare("SELECT id FROM eval_suites WHERE id = ?").get(g)?d.prepare(`UPDATE eval_suites
         SET name = ?, description = ?, updated_at = ?
         WHERE id = ?`).run(h,k,e,g):d.prepare(`INSERT INTO eval_suites (id, name, description, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?)`).run(g,h,k,e,e),d.prepare("DELETE FROM eval_cases WHERE suite_id = ?").run(g),a.cases.forEach((a,c)=>{let f="string"==typeof a.id&&a.id.trim().length>0?a.id.trim():(0,b.randomUUID)(),h=a.name.trim(),k="string"==typeof a.model&&a.model.trim().length>0?a.model.trim():null,l=i(a.input),m=j(a.expected),n=Array.isArray(a.tags)?a.tags.map(a=>a.trim()).filter(a=>a.length>0):[];if(!h)throw Error(`Case ${c+1} is missing a name`);if(0===l.messages.length)throw Error(`Case ${c+1} must include at least one message`);if(("contains"===m.strategy||"exact"===m.strategy||"regex"===m.strategy)&&!m.value)throw Error(`Case ${c+1} must include an expected value`);d.prepare(`INSERT INTO eval_cases
          (id, suite_id, sort_order, name, model, input_json, expected_strategy, expected_value,
           tags_json, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(f,g,c,h,k,JSON.stringify(l),m.strategy,m.value||null,JSON.stringify(n),e,e)}),d.prepare("COMMIT").run()}catch(a){throw d.prepare("ROLLBACK").run(),a}let l=n(g);if(!l)throw Error("Failed to persist eval suite");return l},"saveEvalRun",0,function(a){let d=(0,c.getDbInstance)(),e=a.createdAt||new Date().toISOString(),f=(0,b.randomUUID)(),g="string"==typeof a.target.id&&a.target.id.trim().length>0?a.target.id.trim():null,h=Number.isFinite(Number(a.avgLatencyMs))?Math.max(0,Math.round(Number(a.avgLatencyMs))):0;return d.prepare(`INSERT INTO eval_runs
      (id, run_group_id, suite_id, suite_name, target_type, target_id, target_label, api_key_id,
       pass_rate, total, passed, failed, avg_latency_ms, summary_json, results_json, outputs_json, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(f,a.runGroupId||null,a.suiteId,a.suiteName,a.target.type,g,a.target.label,a.apiKeyId||null,a.summary.passRate,a.summary.total,a.summary.passed,a.summary.failed,h,JSON.stringify(a.summary),JSON.stringify(a.results||[]),JSON.stringify(a.outputs||{}),e),{id:f,runGroupId:a.runGroupId||null,suiteId:a.suiteId,suiteName:a.suiteName,target:{type:a.target.type,id:g,key:k(a.target.type,g),label:a.target.label},apiKeyId:a.apiKeyId||null,avgLatencyMs:h,summary:a.summary,results:a.results||[],outputs:a.outputs||{},createdAt:e}},"serializeEvalTargetKey",0,k])},273294,a=>{"use strict";var b=a.i(738037),c=a.i(112496),d=a.i(606373);let e=["litellm"],f=parseInt(process.env.PRICING_SYNC_INTERVAL||"86400",10),g=Number.isFinite(f)&&f>0?1e3*f:864e5,h=(process.env.PRICING_SYNC_SOURCES||"litellm").split(",").map(a=>a.trim()).filter(a=>e.includes(a)),i={openai:["openai","cx"],anthropic:["anthropic","cc"],vertex_ai:["gemini"],"vertex_ai-anthropic_models":["anthropic"],google:["gemini"],deepseek:["if"],groq:["groq"],together_ai:["openrouter"],bedrock:["kiro"],fireworks_ai:["fireworks"],cerebras:["cerebras"],nvidia_nim:["nvidia"],siliconflow:["siliconflow"],"vertex_ai-language_models":["gemini"],"vertex_ai-mistral_models":["mistral"],gemini:["gemini"],bedrock_converse:["kiro"],cloudflare:["cloudflare-ai"],stability:["stability-ai"]},j=null,k=null,l=0,m=g;async function n(){let a=await fetch("https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",{signal:AbortSignal.timeout(3e4)});if(!a.ok)throw Error(`LiteLLM fetch failed [${a.status}]: ${a.statusText}`);let b=await a.text();try{return JSON.parse(b)}catch{throw Error(`LiteLLM returned invalid JSON (${b.slice(0,100)}...)`)}}function o(a){return a&&"object"==typeof a?a:{}}function p(a){let e=(0,b.getDbInstance)(),f=e.prepare("DELETE FROM key_value WHERE namespace = 'pricing_synced'"),g=e.prepare("INSERT INTO key_value (namespace, key, value) VALUES ('pricing_synced', ?, ?)");e.transaction(()=>{for(let[b,c]of(f.run(),Object.entries(a)))g.run(b,JSON.stringify(c))})(),(0,d.backupDbFile)("pre-write"),(0,c.invalidateDbCache)("pricing")}let q="pricing_sync_status",r="last_sync";async function s(a){let c=a?.sources||h,d=a?.dryRun??!1,f=c.filter(a=>e.includes(a)),g=c.filter(a=>!e.includes(a));if(0===f.length){let a=e.join(", ");return{success:!1,modelCount:0,providerCount:0,source:c.join(","),dryRun:d,error:`No valid sources provided. Supported: ${a}. Invalid: ${g.join(", ")}`}}try{let a={};for(let b of f)if("litellm"===b){let b=await n(),c=function(a){let b={};for(let[c,d]of Object.entries(a)){let a=["input_cost_per_second","output_cost_per_second","input_cost_per_image","output_cost_per_image","input_cost_per_pixel","output_cost_per_pixel","input_cost_per_character","output_cost_per_character","input_cost_per_video_per_second","output_cost_per_video_per_second","search_unit_cost","ocr_cost_per_page"],e=null!=d.input_cost_per_token||null!=d.output_cost_per_token,f=a.some(a=>null!=d[a]);if(!e&&!f)continue;let g=1e6*(d.input_cost_per_token||0),h={input:Math.round(1e3*g)/1e3,output:Math.round(1e3*(1e6*(d.output_cost_per_token||0)))/1e3};for(let b of(d.mode&&(h.mode=d.mode),null!=d.cache_read_input_token_cost&&(h.cached=Math.round(1e6*d.cache_read_input_token_cost*1e3)/1e3),null!=d.cache_creation_input_token_cost&&(h.cache_creation=Math.round(1e6*d.cache_creation_input_token_cost*1e3)/1e3),a)){let a=d[b];"number"==typeof a&&Number.isFinite(a)&&(h[b]=a)}let j=c.indexOf("/"),k=j>=0?c.slice(j+1):c,l=d.litellm_provider||"",m=i[l];if(m)for(let a of m)b[a]||(b[a]={}),b[a][k]=h;else l&&(b[l]||(b[l]={}),b[l][k]=h)}return b}(b);for(let[b,d]of Object.entries(c))a[b]||(a[b]={}),Object.assign(a[b],d)}let c=Object.values(a).reduce((a,b)=>a+Object.keys(b).length,0),e=Object.keys(a).length;if(!d){var j;p(a),k=new Date().toISOString(),l=c,j=k,(0,b.getDbInstance)().prepare("INSERT INTO key_value (namespace, key, value) VALUES (?, ?, ?) ON CONFLICT(namespace, key) DO UPDATE SET value = excluded.value").run(q,r,JSON.stringify({lastSyncTime:j,lastSyncModelCount:c}))}return{success:!0,modelCount:c,providerCount:e,source:f.join(","),dryRun:d,...g.length>0?{warnings:[`Unknown sources ignored: ${g.join(", ")}`]}:{},...d?{data:a}:{}}}catch(b){let a=b instanceof Error?b.message:String(b);return console.warn("[PRICING_SYNC] Sync failed:",a),{success:!1,modelCount:0,providerCount:0,source:c.join(","),dryRun:d,error:a}}}function t(a){if(j)return;let b=a??g;m=b,console.log(`[PRICING_SYNC] Starting periodic sync every ${b/1e3}s`),s().then(a=>{a.success&&console.log(`[PRICING_SYNC] Initial sync complete: ${a.modelCount} models from ${a.providerCount} providers`)}).catch(a=>{console.warn("[PRICING_SYNC] Initial sync error:",a instanceof Error?a.message:a)}),(j=setInterval(()=>{s().then(a=>{a.success&&console.log(`[PRICING_SYNC] Periodic sync complete: ${a.modelCount} models`)}).catch(a=>{console.warn("[PRICING_SYNC] Periodic sync error:",a instanceof Error?a.message:a)})},b))&&"object"==typeof j&&"unref"in j&&j.unref?.()}async function u(){"true"!==process.env.PRICING_SYNC_ENABLED?console.log("[PRICING_SYNC] Disabled (set PRICING_SYNC_ENABLED=true to enable)"):t()}a.s(["clearSyncedPricing",0,function(){(0,b.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = 'pricing_synced'").run(),(0,d.backupDbFile)("pre-write"),(0,c.invalidateDbCache)("pricing")},"getSyncStatus",0,function(){let a="true"===process.env.PRICING_SYNC_ENABLED,c=null===k?function(){let a=o((0,b.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(q,r)),c="string"==typeof a.value?a.value:null;if(!c)return null;try{let a=JSON.parse(c);if("string"!=typeof a.lastSyncTime)return null;return{lastSyncTime:a.lastSyncTime,lastSyncModelCount:"number"==typeof a.lastSyncModelCount?a.lastSyncModelCount:0}}catch{return null}}():null,d=k??c?.lastSyncTime??null;return{enabled:a,lastSync:d,lastSyncModelCount:null!==k?l:c?.lastSyncModelCount??0,nextSync:d?new Date(new Date(d).getTime()+m).toISOString():null,intervalMs:m,sources:h}},"getSyncedPricing",0,function(){let a=(0,b.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = 'pricing_synced'").all(),c={};for(let b of a){let a=o(b),d="string"==typeof a.key?a.key:null,e="string"==typeof a.value?a.value:null;if(d&&null!==e)try{c[d]=JSON.parse(e)}catch{console.warn(`[PRICING_SYNC] Corrupted data for provider "${d}", skipping`)}}return c},"initPricingSync",0,u,"saveSyncedPricing",0,p,"startPeriodicSync",0,t,"stopPeriodicSync",0,function(){j&&(clearInterval(j),j=null,console.log("[PRICING_SYNC] Periodic sync stopped"))},"syncPricingFromSources",0,s])},913555,a=>{"use strict";var b=a.i(738037);let c=new Set(["enabled","mode","updated_at"]);a.s(["updateSkill",0,function(a,d){let e=(0,b.getDbInstance)(),f=[],g=[];for(let[a,b]of Object.entries(d))c.has(a)&&(f.push(`${a} = ?`),g.push(b));return 0===f.length?0:(f.push("updated_at = datetime('now')"),g.push(a),e.prepare(`UPDATE skills SET ${f.join(", ")} WHERE id = ?`).run(...g).changes)}])},651316,a=>{"use strict";var b=a.i(254799),c=a.i(772522),d=a.i(738037),e=a.i(144544);function f(){return new Date().toISOString().slice(0,10)}function g(){return new Date().toISOString().slice(0,13)}function h(a){return a&&"string"==typeof a?(0,b.createHash)("sha256").update(a).digest("hex"):""}function i(a,b,c,d){let e=f(),h=g();a.prepare(`
    UPDATE ${b}
    SET daily_issued = CASE WHEN last_reset_day <> ? THEN 0 ELSE daily_issued END,
        hourly_issued = CASE WHEN last_reset_hour <> ? THEN 0 ELSE hourly_issued END,
        last_reset_day = ?,
        last_reset_hour = ?
    WHERE ${c} = ?
  `).run(e,h,e,h,d)}a.s(["checkQuota",0,function(a="",b=""){let c=(0,d.getDbInstance)();if(f(),g(),a){i(c,"provider_key_limits","provider",a);let b=c.prepare("SELECT * FROM provider_key_limits WHERE provider = ?").get(a);if(b){if(null!==b.hourly_issue_limit&&b.hourly_issued>=b.hourly_issue_limit)return{allowed:!1,errorCode:"PROVIDER_QUOTA_EXCEEDED",errorMessage:`Hourly issue limit (${b.hourly_issue_limit}) reached for provider '${a}'`,provider:a};if(null!==b.daily_issue_limit&&b.daily_issued>=b.daily_issue_limit)return{allowed:!1,errorCode:"PROVIDER_QUOTA_EXCEEDED",errorMessage:`Daily issue limit (${b.daily_issue_limit}) reached for provider '${a}'`,provider:a};if(null!==b.max_active_keys){let{activeCount:d}=c.prepare("SELECT COUNT(*) as activeCount FROM registered_keys WHERE provider = ? AND is_active = 1").get(a);if(d>=b.max_active_keys)return{allowed:!1,errorCode:"MAX_ACTIVE_KEYS_EXCEEDED",errorMessage:`Max active keys (${b.max_active_keys}) reached for provider '${a}'`,provider:a,providerActiveKeys:d}}}}if(b){i(c,"account_key_limits","account_id",b);let a=c.prepare("SELECT * FROM account_key_limits WHERE account_id = ?").get(b);if(a){if(null!==a.hourly_issue_limit&&a.hourly_issued>=a.hourly_issue_limit)return{allowed:!1,errorCode:"ACCOUNT_QUOTA_EXCEEDED",errorMessage:`Hourly issue limit (${a.hourly_issue_limit}) reached for account '${b}'`,accountId:b};if(null!==a.daily_issue_limit&&a.daily_issued>=a.daily_issue_limit)return{allowed:!1,errorCode:"ACCOUNT_QUOTA_EXCEEDED",errorMessage:`Daily issue limit (${a.daily_issue_limit}) reached for account '${b}'`,accountId:b};if(null!==a.max_active_keys){let{activeCount:d}=c.prepare("SELECT COUNT(*) as activeCount FROM registered_keys WHERE account_id = ? AND is_active = 1").get(b);if(d>=a.max_active_keys)return{allowed:!1,errorCode:"MAX_ACTIVE_KEYS_EXCEEDED",errorMessage:`Max active keys (${a.max_active_keys}) reached for account '${b}'`,accountId:b,accountActiveKeys:d}}}}return{allowed:!0}},"getAccountKeyLimit",0,function(a){let b=(0,d.getDbInstance)().prepare("SELECT * FROM account_key_limits WHERE account_id = ?").get(a);return b?(0,e.rowToCamel)(b):null},"getProviderKeyLimit",0,function(a){let b=(0,d.getDbInstance)().prepare("SELECT * FROM provider_key_limits WHERE provider = ?").get(a);return b?(0,e.rowToCamel)(b):null},"getRegisteredKey",0,function(a){let b=(0,d.getDbInstance)().prepare("SELECT * FROM registered_keys WHERE id = ?").get(a);return b?(0,e.rowToCamel)(b):null},"incrementRegisteredKeyUsage",0,function(a){(0,d.getDbInstance)().prepare(`
    UPDATE registered_keys
    SET daily_used = daily_used + 1, hourly_used = hourly_used + 1, updated_at = datetime('now')
    WHERE id = ?
  `).run(a)},"issueRegisteredKey",0,function(a){let j=(0,d.getDbInstance)(),{name:k,provider:l="",accountId:m="",idempotencyKey:n,expiresAt:o,dailyBudget:p,hourlyBudget:q}=a;if(n){let a=j.prepare("SELECT * FROM registered_keys WHERE idempotency_key = ?").get(n);if(a)return{idempotencyConflict:!0,existing:(0,e.rowToCamel)(a)}}let r="ork_"+(0,b.randomBytes)(24).toString("base64url"),s=(0,c.v4)(),t=h(r),u=r.slice(0,12);j.prepare(`
    INSERT INTO registered_keys
      (id, key, key_prefix, name, provider, account_id, idempotency_key, expires_at, daily_budget, hourly_budget, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(s,t,u,k,l,m,n??null,o??null,p??null,q??null,f(),g()),l&&(i(j,"provider_key_limits","provider",l),j.prepare(`
      INSERT INTO provider_key_limits (provider, daily_issued, hourly_issued, last_reset_day, last_reset_hour)
      VALUES (?, 1, 1, ?, ?)
      ON CONFLICT(provider) DO UPDATE SET
        daily_issued = daily_issued + 1,
        hourly_issued = hourly_issued + 1,
        updated_at = datetime('now')
    `).run(l,f(),g())),m&&(i(j,"account_key_limits","account_id",m),j.prepare(`
      INSERT INTO account_key_limits (account_id, daily_issued, hourly_issued, last_reset_day, last_reset_hour)
      VALUES (?, 1, 1, ?, ?)
      ON CONFLICT(account_id) DO UPDATE SET
        daily_issued = daily_issued + 1,
        hourly_issued = hourly_issued + 1,
        updated_at = datetime('now')
    `).run(m,f(),g()));let v=j.prepare("SELECT * FROM registered_keys WHERE id = ?").get(s);return{...(0,e.rowToCamel)(v),rawKey:r}},"listRegisteredKeys",0,function(a={}){let b=(0,d.getDbInstance)(),c="SELECT * FROM registered_keys WHERE 1=1",f=[];return a.provider&&(c+=" AND provider = ?",f.push(a.provider)),a.accountId&&(c+=" AND account_id = ?",f.push(a.accountId)),c+=" ORDER BY created_at DESC LIMIT 500",b.prepare(c).all(...f).map(a=>(0,e.rowToCamel)(a))},"revokeRegisteredKey",0,function(a){return(0,d.getDbInstance)().prepare(`
    UPDATE registered_keys
    SET is_active = 0, revoked_at = datetime('now'), updated_at = datetime('now')
    WHERE id = ? AND is_active = 1
  `).run(a).changes>0},"setAccountKeyLimit",0,function(a,b){(0,d.getDbInstance)().prepare(`
    INSERT INTO account_key_limits (account_id, max_active_keys, daily_issue_limit, hourly_issue_limit, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(account_id) DO UPDATE SET
      max_active_keys = excluded.max_active_keys,
      daily_issue_limit = excluded.daily_issue_limit,
      hourly_issue_limit = excluded.hourly_issue_limit,
      updated_at = datetime('now')
  `).run(a,b.maxActiveKeys??null,b.dailyIssueLimit??null,b.hourlyIssueLimit??null,f(),g())},"setProviderKeyLimit",0,function(a,b){(0,d.getDbInstance)().prepare(`
    INSERT INTO provider_key_limits (provider, max_active_keys, daily_issue_limit, hourly_issue_limit, last_reset_day, last_reset_hour)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(provider) DO UPDATE SET
      max_active_keys = excluded.max_active_keys,
      daily_issue_limit = excluded.daily_issue_limit,
      hourly_issue_limit = excluded.hourly_issue_limit,
      updated_at = datetime('now')
  `).run(a,b.maxActiveKeys??null,b.dailyIssueLimit??null,b.hourlyIssueLimit??null,f(),g())},"validateRegisteredKey",0,function(a){let b=(0,d.getDbInstance)(),c=h(a),i=b.prepare(`
    SELECT * FROM registered_keys
    WHERE key = ? AND is_active = 1
      AND (expires_at IS NULL OR expires_at > datetime('now'))
  `).get(c);if(!i)return null;let j=f(),k=g();return((i.last_reset_day!==j||i.last_reset_hour!==k)&&b.prepare(`
      UPDATE registered_keys
      SET daily_used = CASE WHEN last_reset_day <> ? THEN 0 ELSE daily_used END,
          hourly_used = CASE WHEN last_reset_hour <> ? THEN 0 ELSE hourly_used END,
          last_reset_day = ?, last_reset_hour = ?
      WHERE id = ?
    `).run(j,k,j,k,i.id),null!==i.daily_budget&&i.daily_used>=i.daily_budget||null!==i.hourly_budget&&i.hourly_used>=i.hourly_budget)?null:(0,e.rowToCamel)(i)}])},724738,a=>{"use strict";var b=a.i(772522),c=a.i(738037);function d(a){return{id:a.id,pattern:a.pattern,comboId:a.combo_id,comboName:a.combo_name||void 0,priority:a.priority,enabled:1===a.enabled,description:a.description||"",createdAt:a.created_at,updatedAt:a.updated_at}}async function e(){return(0,c.getDbInstance)().prepare(`SELECT m.id, m.pattern, m.combo_id, c.name AS combo_name,
              m.priority, m.enabled, m.description,
              m.created_at, m.updated_at
       FROM model_combo_mappings m
       LEFT JOIN combos c ON c.id = m.combo_id
       ORDER BY m.priority DESC, m.created_at ASC`).all().map(d)}async function f(a){let b=(0,c.getDbInstance)().prepare(`SELECT m.id, m.pattern, m.combo_id, c.name AS combo_name,
              m.priority, m.enabled, m.description,
              m.created_at, m.updated_at
       FROM model_combo_mappings m
       LEFT JOIN combos c ON c.id = m.combo_id
       WHERE m.id = ?`).get(a);return b?d(b):null}async function g(a){let d=(0,c.getDbInstance)(),e=new Date().toISOString(),f=(0,b.v4)();return d.prepare(`INSERT INTO model_combo_mappings
     (id, pattern, combo_id, priority, enabled, description, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(f,a.pattern,a.comboId,a.priority??0,+(!1!==a.enabled),a.description||"",e,e),{id:f,pattern:a.pattern,comboId:a.comboId,priority:a.priority??0,enabled:!1!==a.enabled,description:a.description||"",createdAt:e,updatedAt:e}}async function h(a,b){let d=await f(a);if(!d)return null;let e=(0,c.getDbInstance)(),g=new Date().toISOString(),h={pattern:b.pattern??d.pattern,combo_id:b.comboId??d.comboId,priority:b.priority??d.priority,enabled:void 0!==b.enabled?+!!b.enabled:+!!d.enabled,description:b.description??d.description};return e.prepare(`UPDATE model_combo_mappings
     SET pattern = ?, combo_id = ?, priority = ?, enabled = ?,
         description = ?, updated_at = ?
     WHERE id = ?`).run(h.pattern,h.combo_id,h.priority,h.enabled,h.description,g,a),f(a)}async function i(a){return((0,c.getDbInstance)().prepare("DELETE FROM model_combo_mappings WHERE id = ?").run(a).changes??0)>0}async function j(a){for(let b of(0,c.getDbInstance)().prepare(`SELECT m.pattern, m.combo_id, c.data AS combo_data
       FROM model_combo_mappings m
       JOIN combos c ON c.id = m.combo_id
       WHERE m.enabled = 1
       ORDER BY m.priority DESC, m.created_at ASC`).all())if((function(a){let b=a.replace(/[.+^${}()|[\]\\]/g,"\\$&").replace(/\*/g,".*").replace(/\?/g,".");return RegExp(`^${b}$`,"i")})(b.pattern).test(a))try{let a=JSON.parse(b.combo_data);if(!1===a.isActive)continue;return a}catch{continue}return null}a.s(["createModelComboMapping",0,g,"deleteModelComboMapping",0,i,"getModelComboMappingById",0,f,"getModelComboMappings",0,e,"resolveComboForModel",0,j,"updateModelComboMapping",0,h])},441114,a=>{"use strict";var b=a.i(738037),c=a.i(144544),d=a.i(772522);let e="id, bytes, created_at, filename, purpose, mime_type, api_key_id, expires_at, deleted_at";function f(a){let d=(0,b.getDbInstance)().prepare(`SELECT ${e} FROM files WHERE id = ? AND deleted_at IS NULL`).get(a);return d?(0,c.rowToCamel)(d):null}a.s(["countFiles",0,function(a={}){let c=(0,b.getDbInstance)(),{apiKeyId:d,purpose:e}=a,f="SELECT COUNT(*) as c FROM files WHERE deleted_at IS NULL",g=[];d&&(f+=" AND api_key_id = ?",g.push(d)),e&&(f+=" AND purpose = ?",g.push(e));let h=c.prepare(f).get(...g);return h?Number(h.c):0},"createFile",0,function(a){let c=(0,b.getDbInstance)(),e="file-"+(0,d.v4)().replaceAll("-","").substring(0,24),f=Math.floor(Date.now()/1e3),g=a.expiresAt;void 0===g&&"batch"===a.purpose&&(g=f+2592e3);let h={id:e,bytes:a.bytes,createdAt:f,filename:a.filename,purpose:a.purpose,content:a.content??null,mimeType:a.mimeType??null,apiKeyId:a.apiKeyId??null,expiresAt:g??null,deletedAt:null};return c.prepare(`
    INSERT INTO files (id, bytes, created_at, filename, purpose, content, mime_type, api_key_id, expires_at, deleted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(h.id,h.bytes,h.createdAt,h.filename,h.purpose,h.content,h.mimeType,h.apiKeyId,h.expiresAt,h.deletedAt),h},"deleteFile",0,function(a){return(0,b.getDbInstance)().prepare("UPDATE files SET deleted_at = ?, content = NULL WHERE id = ?").run(Math.floor(Date.now()/1e3),a).changes>0},"formatFileResponse",0,function(a){let b="number"==typeof a.createdAt&&Number.isFinite(a.createdAt)?a.createdAt:0,c="number"==typeof a.expiresAt&&Number.isFinite(a.expiresAt)?a.expiresAt:null;return{id:a.id,bytes:a.bytes,created_at:b,filename:a.filename,object:"file",purpose:a.purpose,expires_at:c}},"getFile",0,f,"getFileContent",0,function(a){let c=(0,b.getDbInstance)().prepare("SELECT content FROM files WHERE id = ? AND deleted_at IS NULL").get(a);return c?.content?Buffer.isBuffer(c.content)?c.content:Buffer.from(c.content):null},"listFiles",0,function(a={}){let d=(0,b.getDbInstance)(),{apiKeyId:g,purpose:h,limit:i=20,after:j,order:k="desc"}=a,l=`SELECT ${e} FROM files WHERE deleted_at IS NULL`,m=[];if(g&&(l+=" AND api_key_id = ?",m.push(g)),h&&(l+=" AND purpose = ?",m.push(h)),j){let a=f(j);a&&("desc"===k?l+=" AND (created_at < ? OR (created_at = ? AND id < ?))":l+=" AND (created_at > ? OR (created_at = ? AND id > ?))",m.push(a.createdAt,a.createdAt,j))}return l+=` ORDER BY created_at ${"asc"===k?"ASC":"DESC"}, id ${"asc"===k?"ASC":"DESC"} LIMIT ?`,m.push(i),d.prepare(l).all(...m).map(a=>(0,c.rowToCamel)(a))}],441114)},132758,a=>{"use strict";var b=a.i(738037),c=a.i(144544),d=a.i(441114),e=a.i(772522);function f(a){let b=(0,c.rowToCamel)(a);if(b.metadata&&"string"==typeof b.metadata)try{b.metadata=JSON.parse(b.metadata)}catch{b.metadata=null}if(b.errors&&"string"==typeof b.errors)try{b.errors=JSON.parse(b.errors)}catch{b.errors=null}if(b.usage&&"string"==typeof b.usage)try{b.usage=JSON.parse(b.usage)}catch{b.usage=null}let d=a=>{if("number"==typeof a&&Number.isFinite(a))return a;if(null==a)return null;let b=Number(a);return Number.isFinite(b)?b:null};return b.createdAt=d(b.createdAt)??0,b.inProgressAt=d(b.inProgressAt),b.expiresAt=d(b.expiresAt),b.finalizingAt=d(b.finalizingAt),b.completedAt=d(b.completedAt),b.failedAt=d(b.failedAt),b.expiredAt=d(b.expiredAt),b.cancellingAt=d(b.cancellingAt),b.cancelledAt=d(b.cancelledAt),b}function g(a){if(null==a)return null;if("string"!=typeof a)return a;try{return JSON.parse(a)}catch{return null}}function h(a){let c=(0,b.getDbInstance)().prepare("SELECT * FROM batches WHERE id = ?").get(a);return c?f(c):null}a.s(["countBatchItemCheckpoints",0,function(a){let c=(0,b.getDbInstance)().prepare("SELECT COUNT(*) AS c FROM batch_item_checkpoints WHERE batch_id = ?").get(a);return c?Number(c.c):0},"countBatches",0,function(a){let c=(0,b.getDbInstance)();if(a){let b=c.prepare("SELECT COUNT(*) as c FROM batches WHERE api_key_id = ?").get(a);return b?Number(b.c):0}{let a=c.prepare("SELECT COUNT(*) as c FROM batches").get();return a?Number(a.c):0}},"createBatch",0,function(a){let d=(0,b.getDbInstance)(),f="batch_"+(0,e.v4)().replaceAll("-","").substring(0,24),g=Math.floor(Date.now()/1e3),h={...a,id:f,createdAt:g,status:a.status||"validating",requestCountsTotal:0,requestCountsCompleted:0,requestCountsFailed:0,errors:a.errors||null,model:a.model||null,usage:a.usage||null,outputExpiresAfterSeconds:a.outputExpiresAfterSeconds||null,outputExpiresAfterAnchor:a.outputExpiresAfterAnchor||null},i=(0,c.objToSnake)({...h,metadata:h.metadata?JSON.stringify(h.metadata):null,errors:h.errors?JSON.stringify(h.errors):null,usage:h.usage?JSON.stringify(h.usage):null}),j=Object.keys(i),k=Object.values(i),l=j.map(()=>"?").join(", ");return d.prepare(`INSERT INTO batches (${j.join(", ")}) VALUES (${l})`).run(...k),h},"deleteBatch",0,function(a){let c=(0,b.getDbInstance)(),e=h(a);if(!e)return!1;if(c.prepare("DELETE FROM batch_item_checkpoints WHERE batch_id = ?").run(a),e.inputFileId)try{(0,d.deleteFile)(e.inputFileId)}catch{}if(e.outputFileId)try{(0,d.deleteFile)(e.outputFileId)}catch{}if(e.errorFileId)try{(0,d.deleteFile)(e.errorFileId)}catch{}return c.prepare("DELETE FROM batches WHERE id = ?").run(a).changes>0},"deleteCompletedBatches",0,function(){let a=(0,b.getDbInstance)(),c=a.prepare("SELECT input_file_id, output_file_id, error_file_id FROM batches WHERE status = 'completed'").all(),e=new Set;for(let a of c)a.input_file_id&&e.add(a.input_file_id),a.output_file_id&&e.add(a.output_file_id),a.error_file_id&&e.add(a.error_file_id);let f=0;for(let a of e)try{(0,d.deleteFile)(a)&&f++}catch{}return a.prepare("DELETE FROM batch_item_checkpoints WHERE batch_id IN (SELECT id FROM batches WHERE status = 'completed')").run(),{deletedBatches:a.prepare("DELETE FROM batches WHERE status = 'completed'").run().changes,deletedFiles:f}},"ensureBatchItemCheckpoints",0,function(a,c){if(0===c.length)return;let d=(0,b.getDbInstance)(),e=Math.floor(Date.now()/1e3),f=d.prepare(`
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
  `);d.transaction(()=>{for(let b of c)f.run(a,b.lineNumber,b.customId,e,e)})()},"getBatch",0,h,"getPendingBatches",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM batches WHERE status IN ('validating', 'in_progress', 'finalizing', 'cancelling')").all().map(a=>f(a))},"getTerminalBatches",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM batches WHERE status IN ('completed', 'failed', 'cancelled', 'expired') ORDER BY created_at ASC").all().map(a=>f(a))},"listBatchItemCheckpoints",0,function(a){return(0,b.getDbInstance)().prepare(`
      SELECT batch_id, line_number, custom_id, status, result_json, error_json, created_at, updated_at
      FROM batch_item_checkpoints
      WHERE batch_id = ?
      ORDER BY line_number ASC
    `).all(a).map(a=>({batchId:a.batch_id,lineNumber:Number(a.line_number),customId:a.custom_id??null,status:a.status,result:g(a.result_json),error:g(a.error_json),createdAt:Number(a.created_at),updatedAt:Number(a.updated_at)}))},"listBatches",0,function(a,c=20,d){let e=(0,b.getDbInstance)(),g=d?h(d):null;return(a?g?e.prepare("SELECT * FROM batches WHERE api_key_id = ? AND (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC LIMIT ?").all(a,g.createdAt,g.createdAt,d,c):e.prepare("SELECT * FROM batches WHERE api_key_id = ? ORDER BY created_at DESC, id DESC LIMIT ?").all(a,c):g?e.prepare("SELECT * FROM batches WHERE (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC LIMIT ?").all(g.createdAt,g.createdAt,d,c):e.prepare("SELECT * FROM batches ORDER BY created_at DESC, id DESC LIMIT ?").all(c)).map(a=>f(a))},"markBatchItemError",0,function(a,c,d){let e=(0,b.getDbInstance)(),f=Math.floor(Date.now()/1e3);e.prepare(`
    UPDATE batch_item_checkpoints
    SET custom_id = ?,
        status = 'errored',
        result_json = NULL,
        error_json = ?,
        updated_at = ?
    WHERE batch_id = ? AND line_number = ?
  `).run(c.customId,JSON.stringify(d),f,a,c.lineNumber)},"markBatchItemProcessing",0,function(a,c){let d=(0,b.getDbInstance)(),e=Math.floor(Date.now()/1e3);d.prepare(`
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
  `).run(a,c.lineNumber,c.customId,e,e)},"markBatchItemResult",0,function(a,c,d){let e=(0,b.getDbInstance)(),f=Math.floor(Date.now()/1e3);e.prepare(`
    UPDATE batch_item_checkpoints
    SET custom_id = ?,
        status = 'completed',
        result_json = ?,
        error_json = NULL,
        updated_at = ?
    WHERE batch_id = ? AND line_number = ?
  `).run(c.customId,JSON.stringify(d),f,a,c.lineNumber)},"updateBatch",0,function(a,d){let e=(0,b.getDbInstance)(),f=(0,c.objToSnake)(d);f.metadata&&"string"!=typeof f.metadata&&(f.metadata=JSON.stringify(f.metadata)),f.errors&&"string"!=typeof f.errors&&(f.errors=JSON.stringify(f.errors)),f.usage&&"string"!=typeof f.usage&&(f.usage=JSON.stringify(f.usage));let g=Object.keys(f);if(0===g.length)return!1;let h=g.map(a=>`${a} = ?`).join(", "),i=Object.values(f);return e.prepare(`UPDATE batches SET ${h} WHERE id = ?`).run(...i,a).changes>0}])},984827,a=>{"use strict";var b=a.i(738037),c=a.i(254799);function d(a){return{...a,kind:a.kind||"custom",events:JSON.parse(a.events||'["*"]'),enabled:1===a.enabled}}function e(a){let c=(0,b.getDbInstance)().prepare("SELECT * FROM webhooks WHERE id = ?").get(a);return c?d(c):null}a.s(["createWebhook",0,function(a){let d=(0,b.getDbInstance)(),f=c.default.randomUUID(),g=a.secret||`whsec_${c.default.randomBytes(24).toString("hex")}`,h=a.kind||"custom";return d.prepare(`INSERT INTO webhooks (id, url, events, secret, description, kind, metadata_encrypted)
       VALUES (?, ?, ?, ?, ?, ?, ?)`).run(f,a.url,JSON.stringify(a.events||["*"]),g,a.description||"",h,a.metadataEncrypted??null),e(f)},"deleteWebhook",0,function(a){return(0,b.getDbInstance)().prepare("DELETE FROM webhooks WHERE id = ?").run(a).changes>0},"disableWebhooksWithHighFailures",0,function(a=10){return(0,b.getDbInstance)().prepare("UPDATE webhooks SET enabled = 0 WHERE failure_count >= ? AND enabled = 1").run(a).changes},"getEnabledWebhooks",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM webhooks WHERE enabled = 1").all().map(d)},"getWebhook",0,e,"getWebhooks",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM webhooks ORDER BY created_at DESC").all().map(d)},"recordWebhookDelivery",0,function(a,c,d){let e=(0,b.getDbInstance)();d?e.prepare("UPDATE webhooks SET last_triggered_at = datetime('now'), last_status = ?, failure_count = 0 WHERE id = ?").run(c,a):e.prepare("UPDATE webhooks SET last_triggered_at = datetime('now'), last_status = ?, failure_count = failure_count + 1 WHERE id = ?").run(c,a)},"updateWebhook",0,function(a,c){let d=(0,b.getDbInstance)(),f=e(a);if(!f)return null;let g=[],h=[];return(void 0!==c.url&&(g.push("url = ?"),h.push(c.url)),void 0!==c.events&&(g.push("events = ?"),h.push(JSON.stringify(c.events))),void 0!==c.secret&&(g.push("secret = ?"),h.push(c.secret)),void 0!==c.enabled&&(g.push("enabled = ?"),h.push(+!!c.enabled)),void 0!==c.description&&(g.push("description = ?"),h.push(c.description)),void 0!==c.kind&&(g.push("kind = ?"),h.push(c.kind)),void 0!==c.metadataEncrypted&&(g.push("metadata_encrypted = ?"),h.push(c.metadataEncrypted)),0===g.length)?f:(h.push(a),d.prepare(`UPDATE webhooks SET ${g.join(", ")} WHERE id = ?`).run(...h),e(a))}])},282178,a=>{"use strict";var b=a.i(738037),c=a.i(908150);a.s(["getDeliveries",0,function(a,c){return(0,b.getDbInstance)().prepare(`SELECT id, webhook_id, event_type, status, http_status, latency_ms, error, created_at
       FROM webhook_deliveries
       WHERE webhook_id = ?
       ORDER BY created_at DESC, id DESC
       LIMIT ?`).all(a,c)},"insertDelivery",0,function(a){let d=(0,b.getDbInstance)(),e=d.prepare(`INSERT INTO webhook_deliveries
       (webhook_id, event_type, status, http_status, latency_ms, error, payload_snapshot)
     VALUES (?, ?, ?, ?, ?, ?, ?)`),f=d.prepare(`DELETE FROM webhook_deliveries
     WHERE webhook_id = ?
       AND id NOT IN (
         SELECT id FROM webhook_deliveries
         WHERE webhook_id = ?
         ORDER BY created_at DESC, id DESC
         LIMIT ?
       )`),g=null!=a.error&&(0,c.sanitizeErrorMessage)(a.error)||null;d.transaction(()=>{e.run(a.webhookId,a.eventType,a.status,a.httpStatus??null,a.latencyMs??null,g,a.payloadSnapshot??null),f.run(a.webhookId,a.webhookId,100)})()}])},431018,a=>{"use strict";var b=a.i(738037);function c(a){let b;if(a.models)try{let c=JSON.parse(a.models);Array.isArray(c)&&(b=c.map(String))}catch{b=void 0}return{id:a.id,providerId:a.provider_id,method:a.method,endpoint:a.endpoint,authType:a.auth_type??"none",models:b,rateLimit:a.rate_limit,feasibility:a.feasibility??0,riskLevel:a.risk_level??"none",status:a.status,notes:a.notes,discoveredAt:a.discovered_at,verifiedAt:a.verified_at}}function d(a){let d=(0,b.getDbInstance)().prepare("SELECT * FROM discovery_results WHERE id = ?").get(a);return d?c(d):null}a.s(["deleteDiscoveryResult",0,function(a){return(0,b.getDbInstance)().prepare("DELETE FROM discovery_results WHERE id = ?").run(a).changes>0},"getDiscoveryResultById",0,d,"getDiscoveryResults",0,function(a){let d=(0,b.getDbInstance)();return(a?d.prepare("SELECT * FROM discovery_results WHERE provider_id = ? ORDER BY discovered_at DESC, id DESC").all(a):d.prepare("SELECT * FROM discovery_results ORDER BY discovered_at DESC, id DESC").all()).map(c)},"markVerified",0,function(a){return 0===(0,b.getDbInstance)().prepare("UPDATE discovery_results SET status = 'verified', verified_at = datetime('now') WHERE id = ?").run(a).changes?null:d(a)},"upsertDiscoveryResult",0,function(a){let d=(0,b.getDbInstance)(),e=a.models?JSON.stringify(a.models):null;return d.prepare(`INSERT INTO discovery_results
       (provider_id, method, endpoint, auth_type, models, rate_limit, feasibility, risk_level, status, notes)
     VALUES (@provider_id, @method, @endpoint, @auth_type, @models, @rate_limit, @feasibility, @risk_level, @status, @notes)
     ON CONFLICT(provider_id, method, endpoint) DO UPDATE SET
       auth_type = excluded.auth_type,
       models = excluded.models,
       rate_limit = excluded.rate_limit,
       feasibility = excluded.feasibility,
       risk_level = excluded.risk_level,
       status = excluded.status,
       notes = excluded.notes`).run({provider_id:a.providerId,method:a.method,endpoint:a.endpoint??null,auth_type:a.authType,models:e,rate_limit:a.rateLimit??null,feasibility:a.feasibility,risk_level:a.riskLevel,status:a.status,notes:a.notes??null}),c(d.prepare(`SELECT * FROM discovery_results
       WHERE provider_id = ? AND method = ? AND ifnull(endpoint, '') = ifnull(?, '')`).get(a.providerId,a.method,a.endpoint??null))}])},177727,a=>{"use strict";var b=a.i(738037),c=a.i(144544);let d=0;a.s(["cleanupOldSnapshots",0,function(a=90){let c=Date.now();if(c-d<216e5)return 0;let e=(0,b.getDbInstance)(),f=new Date(Date.now()-24*a*36e5).toISOString();try{let a=e.prepare("DELETE FROM quota_snapshots WHERE created_at < ?").run(f);return d=c,a.changes}catch(a){if(a?.message?.includes("no such table"))return 0;throw a}},"getAggregatedSnapshots",0,function(a){let c=(0,b.getDbInstance)(),d=["created_at >= ?"],e=[a.since];a.provider&&(d.push("provider = ?"),e.push(a.provider)),a.until&&(d.push("created_at <= ?"),e.push(a.until));let f=60*Number(a.bucketMinutes);if(!Number.isFinite(f)||f<=0)throw Error("Invalid bucket size");let g="connection"===a.aggregateBy?"bucket, provider, connection_id, window_key":"bucket, provider, window_key",h="connection"===a.aggregateBy?"provider || ':' || connection_id as provider":"provider";try{let a=`
      SELECT
        datetime((strftime('%s', created_at) / ${f}) * ${f}, 'unixepoch') as bucket,
        ${h},
        AVG(remaining_percentage) as remainingPct,
        MAX(is_exhausted) as isExhausted,
        window_key
      FROM quota_snapshots
      WHERE ${d.join(" AND ")}
      GROUP BY ${g}
      ORDER BY bucket ASC
    `;return c.prepare(a).all(...e).map(a=>({timestamp:a.bucket,provider:a.provider,remainingPct:a.remainingPct??0,isExhausted:1===a.isExhausted,windowKey:a.windowKey}))}catch(a){if(a?.message?.includes("no such table"))return[];throw a}},"getQuotaSnapshots",0,function(a){let d=(0,b.getDbInstance)(),e=["created_at >= ?"],f=[a.since];a.provider&&(e.push("provider = ?"),f.push(a.provider)),a.connectionId&&(e.push("connection_id = ?"),f.push(a.connectionId)),a.until&&(e.push("created_at <= ?"),f.push(a.until));try{let a=`SELECT * FROM quota_snapshots WHERE ${e.join(" AND ")} ORDER BY created_at ASC`;return d.prepare(a).all(...f).map(a=>(0,c.rowToCamel)(a))}catch(a){if(a?.message?.includes("no such table"))return[];throw a}},"saveQuotaSnapshot",0,function(a){let c=(0,b.getDbInstance)(),d=new Date().toISOString();try{c.prepare(`INSERT INTO quota_snapshots
       (provider, connection_id, window_key, remaining_percentage, is_exhausted,
        next_reset_at, window_duration_ms, raw_data, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(a.provider,a.connection_id,a.window_key,a.remaining_percentage,a.is_exhausted,a.next_reset_at,a.window_duration_ms,a.raw_data,d)}catch(a){if(a?.message?.includes("no such table"))return void console.warn("[QuotaSnapshots] Skipping save: quota_snapshots table not found. Awaiting migration.");throw a}}])},638132,a=>{"use strict";var b=a.i(254799),c=a.i(738037);let d="session_account_affinity",e=null;function f(a){return Number.isFinite(a)&&Number(a)>0?Number(a):0}function g(a,c){let d=(0,b.createHash)("sha256").update(`${c}:${a}`).digest("hex");return`${c}:${d}`}function h(a){return new Date(a).toISOString()}function i(a){if("string"!=typeof a)return null;try{let b=JSON.parse(a);if("string"!=typeof b.connectionId||0===b.connectionId.trim().length||"string"!=typeof b.expiresAt||Number.isNaN(Date.parse(b.expiresAt)))return null;return{connectionId:b.connectionId,createdAt:"string"!=typeof b.createdAt||Number.isNaN(Date.parse(b.createdAt))?b.expiresAt:b.createdAt,lastUsedAt:"string"!=typeof b.lastUsedAt||Number.isNaN(Date.parse(b.lastUsedAt))?b.expiresAt:b.lastUsedAt,expiresAt:b.expiresAt}}catch{return null}}function j(a){(0,c.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(d,a)}function k(a,b,e=0,h=Date.now()){if(!a||!b||0>=f(e))return null;let l=g(a,b),m=(0,c.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(d,l),n=i(m?.value);return n?Date.parse(n.expiresAt)<=h?(j(l),null):n:null}function l(a,b,e,i=Date.now(),j=0){let m=f(j);if(!a||!b||!e||m<=0)return;let n=g(a,b),o=k(a,b,m,i),p=h(i),q={connectionId:e,createdAt:o?.createdAt??p,lastUsedAt:p,expiresAt:h(i+m)};(0,c.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(d,n,JSON.stringify(q))}function m(a=18e5,b=Date.now()){let e=(0,c.getDbInstance)(),f=e.prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(d),g=0;return e.transaction(()=>{for(let a of f){if("string"!=typeof a.key)continue;let c=i(a.value);(!c||Date.parse(c.expiresAt)<=b)&&(e.prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(d,a.key),g++)}})(),g}a.s(["cleanupStaleSessionAccountAffinities",0,m,"deleteSessionAccountAffinity",0,function(a,b){a&&b&&j(g(a,b))},"evictSessionAccountAffinityForConnection",0,function(a,b,e){if(!a||!b||!e)return!1;let f=g(a,b),h=(0,c.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(d,f),k=i(h?.value);return!!k&&k.connectionId===e&&(j(f),!0)},"getSessionAccountAffinity",0,k,"startSessionAccountAffinityCleanup",0,function(){if(!e){try{m()}catch(a){console.warn("[SESSION_AFFINITY] Startup cleanup failed:",a)}"object"==typeof(e=setInterval(()=>{try{m()}catch(a){console.warn("[SESSION_AFFINITY] Periodic cleanup failed:",a)}},3e5))&&"unref"in e&&e.unref?.()}},"stopSessionAccountAffinityCleanupForTests",0,function(){e&&(clearInterval(e),e=null)},"touchSessionAccountAffinity",0,function(a,b,c=Date.now(),d=0){let e=f(d);if(e<=0)return;let g=k(a,b,e,c);g&&l(a,b,g.connectionId,c,e)},"upsertSessionAccountAffinity",0,l])},784797,a=>{"use strict";var b=a.i(738037);function c(a){if("number"==typeof a&&Number.isFinite(a))return a;if("string"==typeof a&&a.trim()){let b=Number(a);return Number.isFinite(b)?b:null}return null}function d(a){return null!==a&&Number.isFinite(a)?Math.max(0,Math.min(100,a)):null}function e(a){let b=d(a);return null===b?null:Math.max(0,Math.min(100,100-b))}function f(a,b){return null!==a&&(b<=1&&a>b||a-b>=5)}function g(a){if(!a)return null;let b=Date.parse(a);return Number.isFinite(b)?new Date(b).toISOString():null}function h(a){let b=g(a);return b?b.slice(0,10):null}function i(a,c,j=Date.now()){let k=function(a,c,d=Date.now()){if(!a||!c)return null;let e=h(c);if(!e)return null;let f=(0,b.getDbInstance)(),i=new Date(d).toISOString();try{for(let b of f.prepare(`
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
      `).all({connectionId:a,nowIso:i}))if(h(b.windowResetsAt)===e)return g(b.windowStartedAt);return null}catch(a){if(a instanceof Error&&a.message.includes("no such table"))return null;throw a}}(a,c,j),l=function(a,c,i=Date.now()){if(!a||!c)return null;let j=h(c);if(!j)return null;let k=(0,b.getDbInstance)(),l=new Date(i).toISOString();try{let b=k.prepare(`
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
      `).all({connectionId:a,nowIso:l}),c=null,i=null,m=null;for(let a of b){let b=g(a.createdAt);if(!b||h(a.nextResetAt)!==j)continue;c||(c=b);let k=e(d(a.remainingPercentage));null!==k&&(f(m,k)&&(i=b),m=k)}if(i)return{windowStartIso:i,resetDrop:!0};if(c)return{windowStartIso:c,resetDrop:!1};return null}catch(a){if(a instanceof Error&&a.message.includes("no such table"))return null;throw a}}(a,c,j);if(!k&&!l)return null;if(!k&&l)return{windowStartIso:l.windowStartIso,source:"observed_snapshot_reset"};if(k&&!l)return{windowStartIso:k,source:"recorded_reset_event"};let m=Date.parse(k),n=Date.parse(l.windowStartIso);return l.resetDrop&&Number.isFinite(m)&&Number.isFinite(n)&&n>m?{windowStartIso:l.windowStartIso,source:"observed_snapshot_reset"}:{windowStartIso:k,source:"recorded_reset_event"}}a.s(["getProviderQuotaWindowStart",0,i,"getProviderQuotaWindowStartIso",0,function(a,b,c=Date.now()){return i(a,b,c)?.windowStartIso??null},"recordProviderQuotaResetEventIfChanged",0,function(a){let i;if(!a.connectionId||!a.windowKey||!(((i=a.windowKey.toLowerCase().replace(/[^a-z0-9]+/g," ").trim()).includes("weekly")||i.includes("7d"))&&!i.includes("sonnet")))return;let j=g(a.currentResetAt);if(!j)return;let k=a.previousObservation??function(a,d){let e=(0,b.getDbInstance)();try{let b=e.prepare(`
        SELECT
          next_reset_at as nextResetAt,
          remaining_percentage as remainingPercentage
        FROM quota_snapshots
        WHERE connection_id = ?
          AND LOWER(window_key) = LOWER(?)
          AND next_reset_at IS NOT NULL
        ORDER BY created_at DESC, id DESC
        LIMIT 1
      `).get(a,d);if(!b)return null;return{resetAt:b.nextResetAt,remainingPercentage:c(b.remainingPercentage)}}catch(a){if(a instanceof Error&&a.message.includes("no such table"))return null;throw a}}(a.connectionId,a.windowKey),l=g(k?.resetAt??null);if(!l)return;let m=Date.parse(l),n=Date.parse(j);if(!Number.isFinite(m)||!Number.isFinite(n))return;let o=d(c(k?.remainingPercentage)),p=d(c(a.currentRemainingPercentage)),q=g(a.observedAt??null)??new Date().toISOString(),r=e(o),s=e(p),t=n>m&&h(l)!==h(j),u=h(l)===h(j)&&null!==s&&f(r,s);if(!t&&!u)return;let v=t?l:q;try{(0,b.getDbInstance)().prepare(`
      INSERT OR IGNORE INTO provider_quota_reset_events
        (provider, connection_id, window_key, window_started_at, window_resets_at,
         observed_at, previous_remaining_percentage, new_remaining_percentage,
         previous_used_percentage, new_used_percentage, raw_data)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(a.provider,a.connectionId,a.windowKey,v,j,q,o,p,r,s,null)}catch(a){if(a instanceof Error&&a.message.includes("no such table"))return;throw a}}])},240597,a=>{"use strict";var b=a.i(738037);function c(a){if(null===a)return null;try{return JSON.stringify(a)}catch{return null}}function d(a){let b=a&&"object"==typeof a?a:{};return{id:"number"==typeof b.id?b.id:0,tool:"string"==typeof b.tool?b.tool:"",currentVersion:null===b.current_version?null:"string"==typeof b.current_version?b.current_version:null,installedVersion:null===b.installed_version?null:"string"==typeof b.installed_version?b.installed_version:null,pinnedVersion:null===b.pinned_version?null:"string"==typeof b.pinned_version?b.pinned_version:null,binaryPath:null===b.binary_path?null:"string"==typeof b.binary_path?b.binary_path:null,status:"string"==typeof b.status?b.status:"not_installed",pid:null===b.pid?null:"number"==typeof b.pid?b.pid:null,port:"number"==typeof b.port?b.port:8317,apiKey:null===b.api_key?null:"string"==typeof b.api_key?b.api_key:null,managementKey:null===b.management_key?null:"string"==typeof b.management_key?b.management_key:null,autoUpdate:1===b.auto_update||!0===b.auto_update||"1"===b.auto_update,autoStart:1===b.auto_start||!0===b.auto_start||"1"===b.auto_start,lastHealthCheck:null===b.last_health_check?null:"string"==typeof b.last_health_check?b.last_health_check:null,lastUpdateCheck:null===b.last_update_check?null:"string"==typeof b.last_update_check?b.last_update_check:null,healthStatus:"string"==typeof b.health_status?b.health_status:"unknown",configOverrides:function(a){if(!a||"string"!=typeof a||""===a.trim())return null;try{let b=JSON.parse(a);return"object"==typeof b&&null!==b?b:null}catch{return null}}(b.config_overrides),errorMessage:null===b.error_message?null:"string"==typeof b.error_message?b.error_message:null,createdAt:"string"==typeof b.created_at?b.created_at:"",updatedAt:"string"==typeof b.updated_at?b.updated_at:"",logsBufferPath:null===b.logs_buffer_path?null:"string"==typeof b.logs_buffer_path?b.logs_buffer_path:null,providerExpose:1===b.provider_expose||!0===b.provider_expose||"1"===b.provider_expose,lastSyncAt:null===b.last_sync_at?null:"string"==typeof b.last_sync_at?b.last_sync_at:null}}async function e(){return(0,b.getDbInstance)().prepare("SELECT * FROM version_manager").all().map(d)}async function f(a){let c=(0,b.getDbInstance)().prepare("SELECT * FROM version_manager WHERE tool = ?").get(a);return c?d(c):null}async function g(a){(0,b.getDbInstance)().prepare(`
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
  `).run(a.tool,a.currentVersion??null,a.installedVersion??null,a.pinnedVersion??null,a.binaryPath??null,a.status??"not_installed",a.pid??null,a.port??8317,a.apiKey??null,a.managementKey??null,void 0!==a.autoUpdate?+!!a.autoUpdate:1,void 0!==a.autoStart?+!!a.autoStart:0,a.healthStatus??"unknown",c(a.configOverrides??null),a.errorMessage??null);let d=await f(a.tool);if(!d)throw Error("Failed to retrieve inserted version manager tool");return d}async function h(a,d){let e=(0,b.getDbInstance)();if(!await f(a))return null;let g=new Set(["currentVersion","installedVersion","pinnedVersion","binaryPath","status","pid","port","apiKey","managementKey","autoUpdate","autoStart","healthStatus","configOverrides","errorMessage","logsBufferPath","providerExpose","lastSyncAt"]),h=["updated_at = datetime('now')"],i={tool:a};for(let[a,b]of Object.entries(d)){if(!g.has(a))continue;let d=a.replace(/([A-Z])/g,"_$1").toLowerCase();"configOverrides"===a?(h.push("config_overrides = @configOverrides"),i.configOverrides=c(b)):"autoUpdate"===a||"autoStart"===a||"providerExpose"===a?(h.push(`${d} = @${a}`),i[a]=+(!0===b)):null===b?h.push(`${d} = null`):(h.push(`${d} = @${a}`),i[a]=b)}return e.prepare(`UPDATE version_manager SET ${h.join(", ")} WHERE tool = @tool`).run(i),f(a)}async function i(a){return(0,b.getDbInstance)().prepare("DELETE FROM version_manager WHERE tool = ?").run(a).changes>0}async function j(a,c){return(0,b.getDbInstance)().prepare("UPDATE version_manager SET health_status = ?, last_health_check = datetime('now') WHERE tool = ?").run(c,a).changes>0}async function k(a,c,d){return(0,b.getDbInstance)().prepare(`UPDATE version_manager SET ${c} = ?, updated_at = datetime('now') WHERE tool = ?`).run(d,a).changes>0}async function l(a,c,d,e){return(0,b.getDbInstance)().prepare(void 0!==d?"UPDATE version_manager SET status = ?, pid = ?, error_message = ?, updated_at = datetime('now') WHERE tool = ?":"UPDATE version_manager SET status = ?, error_message = ?, updated_at = datetime('now') WHERE tool = ?").run(...void 0!==d?[c,d,e??null,a]:[c,e??null,a]).changes>0}async function m(a){return f(a)}let n=new Set(["logsBufferPath","providerExpose","lastSyncAt","status","pid","port","apiKey","autoStart","autoUpdate","healthStatus","errorMessage","currentVersion","installedVersion","binaryPath"]);async function o(a,b,c){if(!n.has(b))throw Error(`updateServiceField: field "${b}" is not in the allowed list`);return h(a,{[b]:c})}a.s(["deleteVersionManagerTool",0,i,"getServiceRow",0,m,"getVersionManagerStatus",0,e,"getVersionManagerTool",0,f,"setToolStatus",0,l,"updateServiceField",0,o,"updateToolHealth",0,j,"updateToolVersion",0,k,"updateVersionManagerTool",0,h,"upsertVersionManagerTool",0,g])},382140,a=>{"use strict";var b=a.i(772522),c=a.i(738037),d=a.i(144544),e=a.i(606373);function f(a){var b;let c=(b=(0,d.rowToCamel)(a))&&"object"==typeof b&&!Array.isArray(b)?b:{};return"string"!=typeof c.id||"string"!=typeof c.name?null:{id:c.id,name:c.name,tokenHash:"string"==typeof c.tokenHash?c.tokenHash:"",syncApiKeyId:"string"==typeof c.syncApiKeyId?c.syncApiKeyId:null,revokedAt:"string"==typeof c.revokedAt?c.revokedAt:null,lastUsedAt:"string"==typeof c.lastUsedAt?c.lastUsedAt:null,createdAt:"string"==typeof c.createdAt?c.createdAt:new Date().toISOString(),updatedAt:"string"==typeof c.updatedAt?c.updatedAt:new Date().toISOString()}}function g(a){a.exec(`
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
  `)}async function h(){let a=(0,c.getDbInstance)();return g(a),a.prepare("SELECT * FROM sync_tokens ORDER BY datetime(created_at) DESC, name COLLATE NOCASE ASC").all().map(a=>f(a)).filter(a=>null!==a)}async function i(a){let b=(0,c.getDbInstance)();return g(b),f(b.prepare("SELECT * FROM sync_tokens WHERE id = ?").get(a))}async function j(a){let b=(0,c.getDbInstance)();return g(b),f(b.prepare("SELECT * FROM sync_tokens WHERE token_hash = ?").get(a))}async function k(a){let d=(0,c.getDbInstance)();g(d);let f=new Date().toISOString(),h={id:(0,b.v4)(),name:a.name,tokenHash:a.tokenHash,syncApiKeyId:a.syncApiKeyId||null,revokedAt:null,lastUsedAt:null,createdAt:f,updatedAt:f};return d.prepare(`INSERT INTO sync_tokens (
      id, name, token_hash, sync_api_key_id, revoked_at, last_used_at, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(h.id,h.name,h.tokenHash,h.syncApiKeyId,h.revokedAt,h.lastUsedAt,h.createdAt,h.updatedAt),(0,e.backupDbFile)("pre-write"),h}async function l(a){let b=(0,c.getDbInstance)();g(b);let d=await i(a);if(!d)return null;if(d.revokedAt)return d;let f=new Date().toISOString();return b.prepare("UPDATE sync_tokens SET revoked_at = ?, updated_at = ? WHERE id = ?").run(f,f,a),(0,e.backupDbFile)("pre-write"),await i(a)}async function m(a,b=new Date().toISOString()){let d=(0,c.getDbInstance)();return g(d),Number(d.prepare("UPDATE sync_tokens SET last_used_at = ?, updated_at = ? WHERE id = ?").run(b,b,a).changes||0)>0}a.s(["createSyncTokenRecord",0,k,"getSyncTokenByHash",0,j,"getSyncTokenById",0,i,"listSyncTokens",0,h,"revokeSyncToken",0,l,"touchSyncTokenLastUsed",0,m])},393373,a=>{"use strict";var b=a.i(738037);function c(a){return a&&"object"==typeof a?a:{}}let d=["metadata.google.internal","169.254.169.254","metadata.aws.internal"];function e(a){let b=null;if(a.cliproxyapi_model_mapping&&"string"==typeof a.cliproxyapi_model_mapping)try{b=JSON.parse(a.cliproxyapi_model_mapping)}catch{b=null}return{id:a.id,providerId:a.provider_id,mode:a.mode,cliproxyapiModelMapping:b,nativePriority:a.native_priority,cliproxyapiPriority:a.cliproxyapi_priority,enabled:1===a.enabled||!0===a.enabled,family:"string"==typeof a.family?a.family:"auto",createdAt:a.created_at,updatedAt:a.updated_at}}async function f(){return(0,b.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config ORDER BY provider_id").all().map(a=>e(c(a)))}async function g(a){let d=(0,b.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config WHERE provider_id = ?").get(a);return d?e(c(d)):null}async function h(a){let c=(0,b.getDbInstance)(),d=a.mode??"native",e=void 0!==a.cliproxyapiModelMapping?JSON.stringify(a.cliproxyapiModelMapping):null,f=a.nativePriority??1,h=a.cliproxyapiPriority??2,i=+(!1!==a.enabled),j=a.family??"auto";return c.prepare(`INSERT INTO upstream_proxy_config
     (provider_id, mode, cliproxyapi_model_mapping, native_priority, cliproxyapi_priority, enabled, family, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
     ON CONFLICT(provider_id) DO UPDATE SET
       mode = excluded.mode,
       cliproxyapi_model_mapping = excluded.cliproxyapi_model_mapping,
       native_priority = excluded.native_priority,
       cliproxyapi_priority = excluded.cliproxyapi_priority,
       enabled = excluded.enabled,
       family = excluded.family,
       updated_at = datetime('now')`).run(a.providerId,d,e,f,h,i,j),g(a.providerId)}async function i(a,c){let d=(0,b.getDbInstance)();if(!await g(a))throw Error(`Provider ${a} not found`);let e=["updated_at = datetime('now')"],f=[];return void 0!==c.mode&&(e.push("mode = ?"),f.push(c.mode)),void 0!==c.cliproxyapiModelMapping&&(e.push("cliproxyapi_model_mapping = ?"),f.push(null===c.cliproxyapiModelMapping?null:JSON.stringify(c.cliproxyapiModelMapping))),void 0!==c.nativePriority&&(e.push("native_priority = ?"),f.push(c.nativePriority)),void 0!==c.cliproxyapiPriority&&(e.push("cliproxyapi_priority = ?"),f.push(c.cliproxyapiPriority)),void 0!==c.enabled&&(e.push("enabled = ?"),f.push(+(!0===c.enabled))),void 0!==c.family&&(e.push("family = ?"),f.push(c.family)),f.push(a),d.prepare(`UPDATE upstream_proxy_config SET ${e.join(", ")} WHERE provider_id = ?`).run(...f),g(a)}async function j(a){return(0,b.getDbInstance)().prepare("DELETE FROM upstream_proxy_config WHERE provider_id = ?").run(a).changes>0}async function k(a){return(0,b.getDbInstance)().prepare("SELECT * FROM upstream_proxy_config WHERE mode = ? AND enabled = 1 ORDER BY provider_id").all(a).map(a=>e(c(a)))}async function l(a){let b=await g(a);if(!b)return[];let c=[];return b.enabled&&(c.push({executor:"native",priority:b.nativePriority}),("cliproxyapi"===b.mode||"fallback"===b.mode)&&c.push({executor:"cliproxyapi",priority:b.cliproxyapiPriority})),c.sort((a,b)=>a.priority-b.priority),c}a.s(["deleteUpstreamProxyConfig",0,j,"getFallbackChainForProvider",0,l,"getProvidersByMode",0,k,"getUpstreamProxyConfig",0,g,"getUpstreamProxyConfigs",0,f,"updateUpstreamProxyConfig",0,i,"upsertUpstreamProxyConfig",0,h,"validateProxyUrl",0,function(a){try{var b;let c=new URL(a);if(!["http:","https:"].includes(c.protocol))return{valid:!1,error:`Unsupported protocol "${c.protocol}" — use http or https`};if(b=c.hostname,"localhost"!==b&&"127.0.0.1"!==b&&"::1"!==b&&(d.includes(b)||/^10\./.test(b)||/^172\.(1[6-9]|2\d|3[01])\./.test(b)||/^192\.168\./.test(b)||/^0\./.test(b)||/^127\./.test(b)||/^224\./.test(b)||/^169\.254\./.test(b)||0))return{valid:!1,error:`Proxy URL cannot point to private/internal address "${c.hostname}"`};return{valid:!0,url:a}}catch{return{valid:!1,error:`Invalid URL: "${a}"`}}}])},593870,a=>{"use strict";var b=a.i(738037);let c="providerLimitsCache";function d(a){try{return JSON.parse(a)}catch{return null}}function e(a){return a&&"object"==typeof a&&!Array.isArray(a)?a:null}function f(a){let b=e(a);if(!b)return null;let c="string"==typeof b.fetchedAt&&b.fetchedAt.trim()?b.fetchedAt:null;if(!c)return null;let d=Number(b.bankedResetCredits);return{quotas:e(b.quotas),plan:b.plan??null,message:"string"==typeof b.message?b.message:null,fetchedAt:c,source:"string"==typeof b.source?b.source:null,...Number.isFinite(d)?{bankedResetCredits:d}:{}}}a.s(["deleteProviderLimitsCache",0,function(a){b.isBuildPhase||b.isCloud||(0,b.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(c,a)},"getAllProviderLimitsCache",0,function(){if(b.isBuildPhase||b.isCloud)return{};let a=(0,b.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(c),e={};for(let b of a){let a=f(d(b.value));a&&(e[b.key]=a)}return e},"getProviderLimitsCache",0,function(a){if(b.isBuildPhase||b.isCloud)return null;let e=(0,b.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(c,a);return e?.value?f(d(e.value)):null},"setProviderLimitsCache",0,function(a,d){return b.isBuildPhase||b.isCloud||(0,b.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(c,a,JSON.stringify(d)),d},"setProviderLimitsCacheBatch",0,function(a){if(b.isBuildPhase||b.isCloud||0===a.length)return 0;let d=(0,b.getDbInstance)(),e=d.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)");return d.transaction(a=>{for(let b of a)e.run(c,b.connectionId,JSON.stringify(b.entry))})(a),a.length}])},752258,a=>{"use strict";var b=a.i(738037);let c="antigravityCreditBalance";function d(a){try{return JSON.parse(a)}catch{return null}}a.s(["getAllPersistedCreditBalances",0,function(){let a=new Map;if(b.isBuildPhase||b.isCloud)return a;for(let e of(0,b.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(c)){let b=d(e.value);b&&"number"==typeof b.balance&&a.set(e.key,b.balance)}return a},"getPersistedCreditBalance",0,function(a){if(b.isBuildPhase||b.isCloud)return null;let e=(0,b.getDbInstance)().prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(c,a);if(!e?.value)return null;let f=d(e.value);return f&&"number"==typeof f.balance?f.balance:null},"persistCreditBalance",0,function(a,d){if(b.isBuildPhase||b.isCloud)return;let e=(0,b.getDbInstance)(),f={balance:d,updatedAt:new Date().toISOString()};e.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(c,a,JSON.stringify(f))}])},220766,a=>{"use strict";var b=a.i(738037);let c=null,d=[["actual_prompt_tokens","INTEGER"],["actual_completion_tokens","INTEGER"],["actual_total_tokens","INTEGER"],["actual_cache_read_tokens","INTEGER"],["actual_cache_write_tokens","INTEGER"],["estimated_usd_saved","REAL"],["mcp_description_tokens_saved","INTEGER DEFAULT 0"],["multimodal_skip_count","INTEGER DEFAULT 0"],["receipt_source","TEXT"],["validation_fallback","INTEGER DEFAULT 0"],["output_mode","TEXT"],["compression_combo_id","TEXT"],["engine","TEXT"],["rtk_raw_output_pointer","TEXT"],["rtk_raw_output_bytes","INTEGER"],["rtk_raw_output_pointers","TEXT"],["rtk_raw_output_total_bytes","INTEGER"],["skip_reason","TEXT"]];function e(){let a=(0,b.getDbInstance)();if(c===a)return;let e=new Set(a.prepare("PRAGMA table_info(compression_analytics)").all().map(a=>a.name));for(let[b,c]of d)e.has(b)||a.exec(`ALTER TABLE compression_analytics ADD COLUMN ${b} ${c}`);c=a}function f(a,b){return a?`${a} AND ${b}`:`WHERE ${b}`}a.s(["getCompressionAnalyticsSummary",0,function(a){let c=(0,b.getDbInstance)();e();let d=null;"24h"===a?d=new Date(Date.now()-864e5).toISOString():"7d"===a?d=new Date(Date.now()-6048e5).toISOString():"30d"===a&&(d=new Date(Date.now()-2592e6).toISOString());let g=d?"WHERE timestamp >= ?":"",h=d?[d]:[],i=f(g,"skip_reason IS NULL"),j=c.prepare(`
    SELECT
      COUNT(*) as total,
      COALESCE(SUM(tokens_saved), 0) as totalSaved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct,
      COALESCE(AVG(duration_ms), 0) as avgDur
    FROM compression_analytics ${i}
  `).get(...h),k=c.prepare(`
    SELECT mode, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct
    FROM compression_analytics ${i}
    GROUP BY mode
  `).all(...h),l=c.prepare(`
    SELECT mode, COUNT(*) as cnt
    FROM compression_analytics ${f(g,"skip_reason IS NOT NULL")}
    GROUP BY mode
  `).all(...h),m={};for(let a of k)m[a.mode]={count:a.cnt,tokensSaved:a.saved,avgSavingsPct:Math.round(a.avgPct),skipped:0};for(let a of l)m[a.mode]?m[a.mode].skipped=a.cnt:m[a.mode]={count:0,tokensSaved:0,avgSavingsPct:0,skipped:a.cnt};let n=c.prepare(`
    SELECT COALESCE(engine, mode) as engine, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved,
      COALESCE(AVG(CASE WHEN original_tokens > 0 THEN CAST(tokens_saved AS REAL) / original_tokens * 100 ELSE 0 END), 0) as avgPct
    FROM compression_analytics ${i}
    GROUP BY COALESCE(engine, mode)
  `).all(...h),o={};for(let a of n)o[a.engine]={count:a.cnt,tokensSaved:a.saved,avgSavingsPct:Math.round(a.avgPct)};let p=c.prepare(`
    SELECT compression_combo_id as compressionComboId, COUNT(*) as cnt,
      COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics ${f(i,"compression_combo_id IS NOT NULL")}
    GROUP BY compression_combo_id ORDER BY cnt DESC
  `).all(...h),q={};for(let a of p)q[a.compressionComboId??"unknown"]={count:a.cnt,tokensSaved:a.saved};let r=c.prepare(`
    SELECT provider, COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics ${i}
    GROUP BY provider ORDER BY cnt DESC
  `).all(...h),s={};for(let a of r)s[a.provider??"unknown"]={count:a.cnt,tokensSaved:a.saved};let t=new Map,u=new Date;for(let a=23;a>=0;a--){let b=new Date(u.getTime()-60*a*6e4).toISOString().substring(0,14)+"00:00Z";t.set(b,{hour:b,count:0,tokensSaved:0})}for(let a of c.prepare(`
    SELECT strftime('%Y-%m-%dT%H:00:00Z', timestamp) as hour,
      COUNT(*) as cnt, COALESCE(SUM(tokens_saved), 0) as saved
    FROM compression_analytics
    WHERE timestamp >= ? AND skip_reason IS NULL
    GROUP BY hour ORDER BY hour ASC
  `).all(new Date(u.getTime()-864e5).toISOString()))t.has(a.hour)&&t.set(a.hour,{hour:a.hour,count:a.cnt,tokensSaved:a.saved});let v=Array.from(t.values()),w=c.prepare(`
    SELECT receipt_source as source, COUNT(*) as cnt,
      COALESCE(SUM(actual_prompt_tokens), 0) as prompt,
      COALESCE(SUM(actual_completion_tokens), 0) as completion,
      COALESCE(SUM(actual_total_tokens), 0) as total,
      COALESCE(SUM(actual_cache_read_tokens), 0) as cacheRead,
      COALESCE(SUM(actual_cache_write_tokens), 0) as cacheWrite,
      COALESCE(SUM(estimated_usd_saved), 0) as usdSaved
    FROM compression_analytics ${f(i,"receipt_source IS NOT NULL")}
    GROUP BY receipt_source
  `).all(...h),x={requestsWithReceipts:0,promptTokens:0,completionTokens:0,totalTokens:0,cacheReadTokens:0,cacheWriteTokens:0,estimatedUsdSaved:0,bySource:{}};for(let a of w){let b=a.source??"unknown";x.requestsWithReceipts+=a.cnt,x.promptTokens+=a.prompt,x.completionTokens+=a.completion,x.totalTokens+=a.total,x.cacheReadTokens+=a.cacheRead,x.cacheWriteTokens+=a.cacheWrite,x.estimatedUsdSaved+=a.usdSaved,x.bySource[b]=a.cnt}let y=c.prepare(`
    SELECT COUNT(*) as cnt
    FROM compression_analytics ${f(i,"validation_fallback = 1")}
  `).get(...h),z=c.prepare(`
    SELECT COUNT(*) as cnt, COALESCE(SUM(mcp_description_tokens_saved), 0) as saved
    FROM compression_analytics ${f(i,"mcp_description_tokens_saved > 0")}
  `).get(...h),A=c.prepare(`
    SELECT skip_reason as reason, COUNT(*) as cnt
    FROM compression_analytics ${f(g,"skip_reason IS NOT NULL")}
    GROUP BY skip_reason
  `).all(...h),B={},C=0;for(let a of A)B[a.reason??"unknown"]=a.cnt,C+=a.cnt;return{totalRequests:j?.total??0,totalTokensSaved:j?.totalSaved??0,avgSavingsPct:Math.round(j?.avgPct??0),avgDurationMs:Math.round(j?.avgDur??0),byMode:m,byEngine:o,byCompressionCombo:q,byProvider:s,last24h:v,totalSkipped:C,bySkipReason:B,validationFallbacks:y?.cnt??0,realUsage:x,mcpDescriptionCompression:{snapshots:z?.cnt??0,estimatedTokensSaved:z?.saved??0}}},"insertCompressionAnalyticsRow",0,function(a){let c=(0,b.getDbInstance)();e(),c.prepare(`
    INSERT INTO compression_analytics (
      timestamp, combo_id, compression_combo_id, engine, provider, mode, original_tokens, compressed_tokens, tokens_saved,
      duration_ms, request_id, actual_prompt_tokens, actual_completion_tokens,
      actual_total_tokens, actual_cache_read_tokens, actual_cache_write_tokens,
      estimated_usd_saved, mcp_description_tokens_saved, multimodal_skip_count,
      receipt_source, validation_fallback, output_mode, rtk_raw_output_pointer, rtk_raw_output_bytes,
      rtk_raw_output_pointers, rtk_raw_output_total_bytes, skip_reason
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(a.timestamp,a.combo_id??null,a.compression_combo_id??null,a.engine??a.mode,a.provider??null,a.mode,a.original_tokens,a.compressed_tokens,a.tokens_saved,a.duration_ms??null,a.request_id??null,a.actual_prompt_tokens??null,a.actual_completion_tokens??null,a.actual_total_tokens??null,a.actual_cache_read_tokens??null,a.actual_cache_write_tokens??null,a.estimated_usd_saved??null,a.mcp_description_tokens_saved??0,a.multimodal_skip_count??0,a.receipt_source??null,+!!a.validation_fallback,a.output_mode??null,a.rtk_raw_output_pointer??null,a.rtk_raw_output_bytes??null,a.rtk_raw_output_pointers??null,a.rtk_raw_output_total_bytes??null,a.skip_reason??null)}])},738242,a=>{"use strict";var b=a.i(254799),c=a.i(738037),d=a.i(606373);function e(a){return a&&"object"==typeof a?a:{}}function f(a){let b=e(a);return{id:"string"==typeof b.id?b.id:"",name:"string"==typeof b.name?b.name:"",type:"string"==typeof b.type?b.type:"http",host:"string"==typeof b.host?b.host:"",port:Number(b.port)||0,region:"string"==typeof b.region?b.region:null,notes:"string"==typeof b.notes?b.notes:null,status:"string"==typeof b.status?b.status:"active",source:"string"==typeof b.source?b.source:"oneproxy",qualityScore:"number"==typeof b.quality_score?b.quality_score:null,latencyMs:"number"==typeof b.latency_ms?b.latency_ms:null,anonymity:"string"==typeof b.anonymity?b.anonymity:null,googleAccess:1===b.google_access||!0===b.google_access,lastValidated:"string"==typeof b.last_validated?b.last_validated:null,countryCode:"string"==typeof b.country_code?b.country_code:null,createdAt:"string"==typeof b.created_at?b.created_at:"",updatedAt:"string"==typeof b.updated_at?b.updated_at:""}}async function g(a){let b=(0,c.getDbInstance)(),d="SELECT * FROM proxy_registry WHERE source = 'oneproxy' AND status = 'active'",e=[];return a?.protocol&&(d+=" AND type = ?",e.push(a.protocol)),a?.countryCode&&(d+=" AND country_code = ?",e.push(a.countryCode)),a?.minQuality!=null&&(d+=" AND quality_score >= ?",e.push(a.minQuality)),d+=" ORDER BY quality_score DESC, last_validated DESC",a?.limit&&(d+=" LIMIT ?",e.push(a.limit)),b.prepare(d).all(...e).map(f)}async function h(){let a,b=(0,c.getDbInstance)(),d={total:Number((a=e(b.prepare(`SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
        AVG(quality_score) as avg_quality,
        MAX(last_validated) as last_validated
       FROM proxy_registry WHERE source = 'oneproxy'`).get())).total)||0,active:Number(a.active)||0,avgQuality:null!==a.avg_quality&&void 0!==a.avg_quality?Math.round(100*Number(a.avg_quality))/100:null,lastValidated:"string"==typeof a.last_validated?a.last_validated:null},f=b.prepare("SELECT type as protocol, COUNT(*) as count FROM proxy_registry WHERE source = 'oneproxy' GROUP BY type ORDER BY count DESC").all(),g=b.prepare("SELECT country_code as countryCode, COUNT(*) as count FROM proxy_registry WHERE source = 'oneproxy' AND country_code IS NOT NULL GROUP BY country_code ORDER BY count DESC LIMIT 20").all();return{...d,byProtocol:f.map(a=>({protocol:String(a.protocol||"unknown"),count:Number(a.count)||0})),byCountry:g.map(a=>({countryCode:String(a.countryCode||"unknown"),count:Number(a.count)||0}))}}async function i(a){let e=(0,c.getDbInstance)(),f=new Date().toISOString(),g=`${a.protocol?.toUpperCase()||"HTTP"} - ${a.countryCode||"Unknown"} - ${a.ip}`,h=e.prepare("SELECT id FROM proxy_registry WHERE host = ? AND port = ? AND source = 'oneproxy'").get(a.ip,a.port);if(h?.id)return e.prepare(`UPDATE proxy_registry
       SET status = ?, quality_score = ?, latency_ms = ?, anonymity = ?,
           google_access = ?, last_validated = ?, country_code = ?, updated_at = ?
       WHERE id = ?`).run("active",a.qualityScore??null,a.latencyMs??null,a.anonymity??null,+!!a.googleAccess,a.lastValidated??f,a.countryCode??null,f,h.id),(0,d.backupDbFile)("pre-write"),{proxy:await j(h.id),action:"updated"};let i=(0,b.randomUUID)();return e.prepare(`INSERT INTO proxy_registry
     (id, name, type, host, port, region, notes, status, source,
      quality_score, latency_ms, anonymity, google_access, last_validated, country_code,
      created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(i,g,a.protocol||"http",a.ip,a.port,a.countryCode??null,null,"active","oneproxy",a.qualityScore??null,a.latencyMs??null,a.anonymity??null,+!!a.googleAccess,a.lastValidated??f,a.countryCode??null,f,f),(0,d.backupDbFile)("pre-write"),{proxy:await j(i),action:"created"}}async function j(a){let b=(0,c.getDbInstance)().prepare("SELECT * FROM proxy_registry WHERE id = ? AND source = 'oneproxy'").get(a);return b?f(b):null}async function k(a){let b=(0,c.getDbInstance)().prepare("DELETE FROM proxy_registry WHERE id = ? AND source = 'oneproxy'").run(a);return(0,d.backupDbFile)("pre-write"),b.changes>0}async function l(){let a=(0,c.getDbInstance)().prepare("DELETE FROM proxy_registry WHERE source = 'oneproxy'").run();return(0,d.backupDbFile)("pre-write"),a.changes}async function m(a){let b=(0,c.getDbInstance)(),d=a?.strategy||"quality",e="SELECT * FROM proxy_registry WHERE source = 'oneproxy' AND status = 'active'";switch(d){case"quality":e+=" ORDER BY quality_score DESC, latency_ms ASC LIMIT 1";break;case"random":e+=" ORDER BY RANDOM() LIMIT 1";break;case"sequential":e+=" ORDER BY last_validated ASC LIMIT 1"}let g=b.prepare(e).get();return g?f(g):null}async function n(a,b){let e=(0,c.getDbInstance)().prepare(`UPDATE proxy_registry
       SET quality_score = MAX(0, COALESCE(quality_score, 50) - 10),
           status = CASE WHEN COALESCE(quality_score, 50) <= 10 THEN 'inactive' ELSE status END,
           updated_at = datetime('now')
       WHERE host = ? AND port = ? AND source = 'oneproxy'`).run(a,b);return(0,d.backupDbFile)("pre-write"),e.changes>0}a.s(["clearAllOneproxyProxies",0,l,"deleteOneproxyProxy",0,k,"getOneproxyProxyById",0,j,"getOneproxyProxyForRotation",0,m,"getOneproxyStats",0,h,"listOneproxyProxies",0,g,"markOneproxyProxyFailed",0,n,"upsertOneproxyProxy",0,i])},97505,a=>{"use strict";var b=a.i(738037);function c(){return(0,b.getDbInstance)()}function d(a){let b=c().prepare("SELECT COALESCE(SUM(amount), 0) AS total FROM token_ledger WHERE to_api_key_id = ?").get(a),d=c().prepare("SELECT COALESCE(SUM(amount), 0) AS total FROM token_ledger WHERE from_api_key_id = ?").get(a);return b.total-d.total}a.s(["addXp",0,function(a,b,d,e){c().prepare(`INSERT INTO xp_audit_log (api_key_id, action, xp_earned, metadata)
     VALUES (?, ?, ?, ?)`).run(a,b,d,e??null),c().prepare(`INSERT INTO user_levels (api_key_id, total_xp, current_level, updated_at)
     VALUES (?, ?, ?, datetime('now'))
     ON CONFLICT(api_key_id)
     DO UPDATE SET total_xp = total_xp + excluded.total_xp, updated_at = datetime('now')`).run(a,d,d<=0?1:Math.max(1,Math.floor(Math.pow(2.5*d/100,.4))))},"connectServer",0,function(a,b,d,e){c().prepare(`INSERT OR REPLACE INTO community_servers (id, name, url, api_key_hash)
     VALUES (?, ?, ?, ?)`).run(a,b,d,e)},"createInviteToken",0,function(a,b,d,e,f,g){c().prepare(`INSERT INTO invite_tokens (id, code, token_hash, created_by, server_url, max_uses)
     VALUES (?, ?, ?, ?, ?, ?)`).run(a,b,d,e,f??null,g??1)},"disconnectServer",0,function(a){c().prepare("UPDATE community_servers SET status = 'disconnected' WHERE id = ?").run(a)},"getBadgeDefinitions",0,function(a){let b=a?"SELECT * FROM badge_definitions WHERE category = ?":"SELECT * FROM badge_definitions";return(a?c().prepare(b).all(a):c().prepare(b).all()).map(a=>({id:a.id,name:a.name,description:a.description,icon:a.icon,category:a.category,rarity:a.rarity,criteria:a.criteria,hidden:a.hidden,createdAt:a.created_at}))},"getBadges",0,function(a){return c().prepare(`SELECT ub.api_key_id, ub.badge_id, ub.unlocked_at,
            bd.name, bd.description, bd.icon, bd.category, bd.rarity
     FROM user_badges ub
     JOIN badge_definitions bd ON bd.id = ub.badge_id
     WHERE ub.api_key_id = ?`).all(a).map(a=>({apiKeyId:a.api_key_id,badgeId:a.badge_id,unlockedAt:a.unlocked_at,badgeName:a.name,badgeDescription:a.description,badgeIcon:a.icon,badgeCategory:a.category,badgeRarity:a.rarity}))},"getBalance",0,d,"getConnectedServerByKeyHash",0,function(a){return c().prepare("SELECT id FROM community_servers WHERE api_key_hash = ? AND status = 'connected'").get(a)},"getHistory",0,function(a,b){return c().prepare(`SELECT * FROM token_ledger
     WHERE from_api_key_id = ? OR to_api_key_id = ?
     ORDER BY created_at DESC LIMIT ?`).all(a,a,b).map(a=>({id:a.id,fromApiKeyId:a.from_api_key_id,toApiKeyId:a.to_api_key_id,amount:a.amount,reason:a.reason,idempotencyKey:a.idempotency_key,createdAt:a.created_at}))},"getInviteByCode",0,function(a){let b=c().prepare("SELECT * FROM invite_tokens WHERE code = ?").get(a);return b?{id:b.id,code:b.code,tokenHash:b.token_hash,createdBy:b.created_by,usedBy:b.used_by,serverUrl:b.server_url,maxUses:b.max_uses,useCount:b.use_count,expiresAt:b.expires_at,revokedAt:b.revoked_at,createdAt:b.created_at}:null},"getRank",0,function(a,b){let d=c().prepare("SELECT score FROM leaderboard WHERE api_key_id = ? AND scope = ?").get(a,b);return d?c().prepare("SELECT COUNT(*) + 1 AS rank FROM leaderboard WHERE scope = ? AND score > ?").get(b,d.score).rank:0},"getTopN",0,function(a,b,d=0){return c().prepare(`SELECT api_key_id, scope, score, updated_at FROM leaderboard
     WHERE scope = ? ORDER BY score DESC LIMIT ? OFFSET ?`).all(a,b,d).map(a=>({apiKeyId:a.api_key_id,scope:a.scope,score:a.score,updatedAt:a.updated_at}))},"getXp",0,function(a){let b=c().prepare("SELECT api_key_id, total_xp, current_level, updated_at FROM user_levels WHERE api_key_id = ?").get(a);return b?{apiKeyId:b.api_key_id,totalXp:b.total_xp,currentLevel:b.current_level,updatedAt:b.updated_at}:null},"hasBadge",0,function(a,b){return!!c().prepare("SELECT 1 FROM user_badges WHERE api_key_id = ? AND badge_id = ? LIMIT 1").get(a,b)},"listServers",0,function(){return c().prepare("SELECT id, name, url, connected_at, last_sync_at, status, error_message FROM community_servers").all().map(a=>({id:a.id,name:a.name,url:a.url,connectedAt:a.connected_at,lastSyncAt:a.last_sync_at,status:a.status,errorMessage:a.error_message}))},"redeemInvite",0,function(a,b){return c().prepare(`UPDATE invite_tokens
     SET use_count = use_count + 1, used_by = ?
     WHERE code = ? AND revoked_at IS NULL
       AND use_count < max_uses
       AND (expires_at IS NULL OR expires_at > datetime('now'))`).run(b,a).changes>0},"revokeInvite",0,function(a){c().prepare("UPDATE invite_tokens SET revoked_at = datetime('now') WHERE id = ?").run(a)},"transferTokens",0,function(a,c,e,f,g){let h=(0,b.getDbInstance)();return h.transaction(()=>h.prepare("SELECT id FROM token_ledger WHERE idempotency_key = ?").get(g)?{success:!0}:d(a)<e?{success:!1,error:"insufficient_balance"}:(h.prepare(`INSERT INTO token_ledger (from_api_key_id, to_api_key_id, amount, reason, idempotency_key)
         VALUES (?, ?, ?, ?, ?)`).run(a,c,e,f,g),{success:!0}))()},"unlockBadge",0,function(a,b){c().prepare("INSERT OR IGNORE INTO user_badges (api_key_id, badge_id) VALUES (?, ?)").run(a,b)},"updateLevel",0,function(a,b){c().prepare(`INSERT INTO user_levels (api_key_id, total_xp, current_level, updated_at)
     VALUES (?, 0, ?, datetime('now'))
     ON CONFLICT(api_key_id)
     DO UPDATE SET current_level = ?, updated_at = datetime('now')`).run(a,b,b)},"updateScore",0,function(a,b,d){c().prepare(`INSERT INTO leaderboard (api_key_id, scope, score, updated_at)
     VALUES (?, ?, ?, datetime('now'))
     ON CONFLICT(api_key_id, scope)
     DO UPDATE SET score = score + excluded.score, updated_at = datetime('now')`).run(a,b,d)}],97505)},199369,a=>{"use strict";var b=a.i(738037);function c(a){return{name:a.name,description:a.description,priority:a.priority,scope:"combo"===a.scope_type&&a.combo_id?{type:"combo",comboId:a.combo_id}:{type:"global"},enabled:1===a.enabled,code:a.code,createdAt:a.created_at,updatedAt:a.updated_at,runCount:a.run_count,lastError:a.last_error||void 0}}function d(a){return{name:a.name,description:a.description,priority:a.priority,scope_type:a.scope.type,combo_id:"combo"===a.scope.type?a.scope.comboId:null,enabled:+!!a.enabled,code:a.code,created_at:a.createdAt||new Date().toISOString(),updated_at:new Date().toISOString(),run_count:a.runCount||0,last_error:a.lastError}}function e(a){let d=(0,b.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE name = ?").get(a);return d?c(d):void 0}a.s(["cleanupHookLogs",0,function(a=1e4){return(0,b.getDbInstance)().prepare(`
    DELETE FROM middleware_logs WHERE id NOT IN (
      SELECT id FROM middleware_logs ORDER BY timestamp DESC LIMIT ?
    )
  `).run(a).changes},"createMiddlewareHook",0,function(a){let c=(0,b.getDbInstance)(),f=d(a);return f.created_at=new Date().toISOString(),f.updated_at=f.created_at,c.prepare(`
    INSERT INTO middleware_hooks (name, description, priority, scope_type, combo_id, enabled, code, created_at, updated_at, run_count, last_error)
    VALUES (@name, @description, @priority, @scope_type, @combo_id, @enabled, @code, @created_at, @updated_at, @run_count, @last_error)
  `).run(f),e(a.name)},"deleteMiddlewareHook",0,function(a){return(0,b.getDbInstance)().prepare("DELETE FROM middleware_hooks WHERE name = ?").run(a).changes>0},"getAllMiddlewareHooks",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM middleware_hooks ORDER BY priority ASC, name ASC").all().map(c)},"getComboMiddlewareHooks",0,function(a){return(0,b.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE enabled = 1 AND (scope_type = 'global' OR (scope_type = 'combo' AND combo_id = ?)) ORDER BY priority ASC").all(a).map(c)},"getEnabledMiddlewareHooks",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM middleware_hooks WHERE enabled = 1 ORDER BY priority ASC").all().map(c)},"getHookLogs",0,function(a,c=50){let d=(0,b.getDbInstance)();return(a?d.prepare("SELECT * FROM middleware_logs WHERE hook_name = ? ORDER BY timestamp DESC LIMIT ?").all(a,c):d.prepare("SELECT * FROM middleware_logs ORDER BY timestamp DESC LIMIT ?").all(c)).map(a=>({id:a.id,hookName:a.hook_name,requestId:a.request_id,durationMs:a.duration_ms,mutated:1===a.mutated,skipped:1===a.skipped,error:a.error,timestamp:a.timestamp}))},"getMiddlewareHook",0,e,"insertHookLog",0,function(a){(0,b.getDbInstance)().prepare(`
    INSERT INTO middleware_logs (id, hook_name, request_id, duration_ms, mutated, skipped, error, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(a.id,a.hookName,a.requestId,a.durationMs,+!!a.mutated,+!!a.skipped,a.error||null,a.timestamp)},"recordHookExecution",0,function(a,c){let d=(0,b.getDbInstance)();c?d.prepare("UPDATE middleware_hooks SET run_count = run_count + 1, last_error = ?, updated_at = datetime('now') WHERE name = ?").run(c,a):d.prepare("UPDATE middleware_hooks SET run_count = run_count + 1, last_error = NULL, updated_at = datetime('now') WHERE name = ?").run(a)},"updateMiddlewareHook",0,function(a,c){let f=e(a);if(!f)return;let g=d({...f,...c,updatedAt:new Date().toISOString()});return(0,b.getDbInstance)().prepare(`
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
  `).run(g),e(a)}])},517267,a=>{"use strict";var b=a.i(666680),c=a.i(738037),d=a.i(144544);function e(a){let b=(0,c.getDbInstance)().prepare("SELECT * FROM relay_tokens WHERE id = ?").get(a);return b?{...(0,d.rowToCamel)(b),enabled:1===b.enabled}:null}a.s(["checkRateLimit",0,function(a,b){let e=(0,c.getDbInstance)(),f=b;if(!f){let b=e.prepare("SELECT * FROM relay_tokens WHERE id = ?").get(a);if(!b)return{allowed:!1,remaining:0,resetIn:0};f=(0,d.rowToCamel)(b)}let g=Math.floor(Date.now()/1e3),h=60*Math.floor(g/60),i=86400*Math.floor(g/86400),j=e.prepare("SELECT request_count, cost FROM relay_rate_limits WHERE token_id = ? AND window_start = ?").get(a,h),k=j?.request_count||0;if(k>=f.maxRequestsPerMinute)return{allowed:!1,remaining:0,resetIn:60-g%60};let l=e.prepare("SELECT SUM(request_count) as total FROM relay_rate_limits WHERE token_id = ? AND window_start >= ?").get(a,i),m=l?.total||0;return m>=f.maxRequestsPerDay?{allowed:!1,remaining:0,resetIn:86400-g%86400}:{allowed:!0,remaining:Math.min(f.maxRequestsPerMinute-k,f.maxRequestsPerDay-m),resetIn:60-g%60}},"createRelayToken",0,function(e){let f=(0,c.getDbInstance)(),g="rl_"+(0,b.randomBytes)(16).toString("hex"),h="relay_"+(0,b.randomBytes)(24).toString("hex"),i=function(b){let{createHash:c}=a.r(666680);return c("sha256").update(b).digest("hex")}(h),j=Math.floor(Date.now()/1e3),k="rl_"+h.slice(6,14);f.prepare(`
    INSERT INTO relay_tokens (id, name, token_hash, token_prefix, description, combo_id, allowed_models,
      max_tokens_per_request, max_requests_per_minute, max_requests_per_day, max_cost_per_day,
      enabled, created_at, updated_at, expires_at, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
  `).run(g,e.name,i,k,e.description||"",e.comboId||null,JSON.stringify(e.allowedModels||["*"]),e.maxTokensPerRequest||128e3,e.maxRequestsPerMinute||60,e.maxRequestsPerDay||1e4,e.maxCostPerDay||0,j,j,e.expiresAt||null,JSON.stringify(e.metadata||{}));let l=f.prepare("SELECT * FROM relay_tokens WHERE id = ?").get(g);return{...(0,d.rowToCamel)(l),rawToken:h}},"deleteRelayToken",0,function(a){(0,c.getDbInstance)().prepare("DELETE FROM relay_tokens WHERE id = ?").run(a)},"getRelayLogs",0,function(a,b=50){let d=(0,c.getDbInstance)();return a?d.prepare("SELECT * FROM relay_logs WHERE token_id = ? ORDER BY created_at DESC LIMIT ?").all(a,b):d.prepare("SELECT * FROM relay_logs ORDER BY created_at DESC LIMIT ?").all(b)},"getRelayToken",0,e,"getRelayTokenByHash",0,function(a){let b=(0,c.getDbInstance)().prepare("SELECT * FROM relay_tokens WHERE token_hash = ? AND enabled = 1").get(a);return b?{...(0,d.rowToCamel)(b),enabled:1===b.enabled}:null},"getRelayTokens",0,function(){return(0,c.getDbInstance)().prepare("SELECT * FROM relay_tokens ORDER BY created_at DESC").all().map(a=>({...(0,d.rowToCamel)(a),enabled:1===a.enabled}))},"getRelayUsage",0,function(a,b){let d=(0,c.getDbInstance)().prepare("SELECT COUNT(*) as request_count, COALESCE(SUM(cost), 0) as total_cost FROM relay_logs WHERE token_id = ? AND created_at >= ?").get(a,b);return{requestCount:d.request_count,totalCost:d.total_cost}},"recordRelayUsage",0,function(a,b){let d=(0,c.getDbInstance)(),e=Math.floor(Date.now()/1e3),f=60*Math.floor(e/60);d.prepare(`
    INSERT INTO relay_rate_limits (token_id, window_start, request_count, cost)
    VALUES (?, ?, 1, ?)
    ON CONFLICT(token_id, window_start) DO UPDATE SET
      request_count = request_count + 1,
      cost = cost + ?
  `).run(a,f,b.cost||0,b.cost||0),d.prepare("UPDATE relay_tokens SET last_used_at = ? WHERE id = ?").run(e,a),d.prepare(`
    INSERT INTO relay_logs (token_id, request_id, model, prompt_tokens, completion_tokens, cost,
      status, status_code, latency_ms, client_ip, user_agent, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(a,b.requestId||null,b.model||null,b.promptTokens||0,b.completionTokens||0,b.cost||0,b.status||"success",b.statusCode||200,b.latencyMs||0,b.clientIp||null,b.userAgent||null,e)},"toggleRelayToken",0,function(a,b){let d=(0,c.getDbInstance)(),f=Math.floor(Date.now()/1e3);return d.prepare("UPDATE relay_tokens SET enabled = ?, updated_at = ? WHERE id = ?").run(+!!b,f,a),e(a)},"updateRelayToken",0,function(a,b){let d=(0,c.getDbInstance)(),f=Math.floor(Date.now()/1e3),g=["updated_at = ?"],h=[f];return void 0!==b.name&&(g.push("name = ?"),h.push(b.name)),void 0!==b.description&&(g.push("description = ?"),h.push(b.description)),void 0!==b.comboId&&(g.push("combo_id = ?"),h.push(b.comboId)),void 0!==b.allowedModels&&(g.push("allowed_models = ?"),h.push(JSON.stringify(b.allowedModels))),void 0!==b.maxTokensPerRequest&&(g.push("max_tokens_per_request = ?"),h.push(b.maxTokensPerRequest)),void 0!==b.maxRequestsPerMinute&&(g.push("max_requests_per_minute = ?"),h.push(b.maxRequestsPerMinute)),void 0!==b.maxRequestsPerDay&&(g.push("max_requests_per_day = ?"),h.push(b.maxRequestsPerDay)),void 0!==b.maxCostPerDay&&(g.push("max_cost_per_day = ?"),h.push(b.maxCostPerDay)),h.push(a),d.prepare(`UPDATE relay_tokens SET ${g.join(", ")} WHERE id = ?`).run(...h),e(a)}])},796486,a=>{"use strict";var b=a.i(254799),c=a.i(738037),d=a.i(606373);function e(a){return{id:String(a.id??""),source:String(a.source??"1proxy"),host:String(a.host??""),port:Number(a.port)||0,type:String(a.type??"http"),countryCode:null!=a.country_code?String(a.country_code):null,qualityScore:null!=a.quality_score?Number(a.quality_score):null,latencyMs:null!=a.latency_ms?Number(a.latency_ms):null,anonymity:null!=a.anonymity?String(a.anonymity):null,lastValidated:null!=a.last_validated?String(a.last_validated):null,inPool:1===a.in_pool||!0===a.in_pool,poolProxyId:null!=a.pool_proxy_id?String(a.pool_proxy_id):null,createdAt:String(a.created_at??""),updatedAt:String(a.updated_at??"")}}async function f(a){let d=(0,c.getDbInstance)(),e=new Date().toISOString(),f=d.prepare("SELECT id FROM free_proxies WHERE source = ? AND host = ? AND port = ?").get(a.source,a.host,a.port);if(f?.id)return d.prepare(`UPDATE free_proxies
       SET type = ?, country_code = ?, quality_score = ?, latency_ms = ?,
           anonymity = ?, last_validated = ?, updated_at = ?
       WHERE id = ?`).run(a.type,a.countryCode??null,a.qualityScore??null,a.latencyMs??null,a.anonymity??null,a.lastValidated??e,e,f.id),{id:f.id,action:"updated"};let g=(0,b.randomUUID)();return d.prepare(`INSERT INTO free_proxies
     (id, source, host, port, type, country_code, quality_score, latency_ms,
      anonymity, last_validated, in_pool, pool_proxy_id, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)`).run(g,a.source,a.host,a.port,a.type,a.countryCode??null,a.qualityScore??null,a.latencyMs??null,a.anonymity??null,a.lastValidated??e,e,e),{id:g,action:"created"}}async function g(a){let b=(0,c.getDbInstance)(),d=[],f="SELECT * FROM free_proxies WHERE 1=1";a?.sources?.length&&(f+=` AND source IN (${a.sources.map(()=>"?").join(",")})`,d.push(...a.sources)),a?.protocol&&(f+=" AND type = ?",d.push(a.protocol)),a?.country&&(f+=" AND country_code = ?",d.push(a.country.toUpperCase())),a?.minQuality!=null&&(f+=" AND quality_score >= ?",d.push(a.minQuality)),a?.onlyInPool&&(f+=" AND in_pool = 1"),a?.onlyNotInPool&&(f+=" AND in_pool = 0"),a?.search&&(f+=" AND host LIKE ?",d.push(`%${a.search}%`));let g=a?.sortBy==="latency"?"ORDER BY latency_ms IS NULL, latency_ms ASC":a?.sortBy==="recent"?"ORDER BY last_validated DESC":"ORDER BY quality_score DESC, last_validated DESC";return f+=` ${g}`,a?.limit&&(f+=" LIMIT ?",d.push(a.limit),a?.offset&&(f+=" OFFSET ?",d.push(a.offset))),b.prepare(f).all(...d).map(e)}async function h(a){let b=(0,c.getDbInstance)(),d=[],e="SELECT COUNT(*) AS count FROM free_proxies WHERE 1=1";a?.sources?.length&&(e+=` AND source IN (${a.sources.map(()=>"?").join(",")})`,d.push(...a.sources)),a?.protocol&&(e+=" AND type = ?",d.push(a.protocol)),a?.country&&(e+=" AND country_code = ?",d.push(a.country.toUpperCase())),a?.minQuality!=null&&(e+=" AND quality_score >= ?",d.push(a.minQuality)),a?.onlyInPool&&(e+=" AND in_pool = 1"),a?.onlyNotInPool&&(e+=" AND in_pool = 0"),a?.search&&(e+=" AND host LIKE ?",d.push(`%${a.search}%`));let f=b.prepare(e).get(...d),g=f?.count;return"number"==typeof g?g:Number(g??0)}async function i(a,b){return(await g({sources:[a],protocol:b.protocol,country:b.country,minQuality:b.minQuality,limit:b.limit})).map(a=>({source:a.source,host:a.host,port:a.port,type:a.type,countryCode:a.countryCode,qualityScore:a.qualityScore,latencyMs:a.latencyMs,anonymity:a.anonymity,lastValidated:a.lastValidated}))}async function j(a){let b=(0,c.getDbInstance)().prepare("SELECT * FROM free_proxies WHERE id = ?").get(a);return b?e(b):null}async function k(a,b){let e=(0,c.getDbInstance)(),f=new Date().toISOString();e.prepare("UPDATE free_proxies SET in_pool = 1, pool_proxy_id = ?, updated_at = ? WHERE id = ?").run(b,f,a),(0,d.backupDbFile)("pre-write")}async function l(a,e){let f=(0,c.getDbInstance)(),g=new Date().toISOString(),h=(0,b.randomUUID)(),i=f.transaction(()=>{let b=f.prepare("SELECT id, in_pool FROM free_proxies WHERE id = ? LIMIT 1").get(a);return b?.id?(f.prepare(`INSERT INTO proxy_registry
        (id, name, type, host, port, username, password, region, notes, status, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, '', '', NULL, NULL, 'active', ?, ?, ?)`).run(h,e.name,e.type,e.host,Number(e.port),e.source,g,g),f.prepare("UPDATE free_proxies SET in_pool = 1, pool_proxy_id = ?, updated_at = ? WHERE id = ?").run(h,g,a),h):null})();return i&&(0,d.backupDbFile)("pre-write"),i}async function m(a){let b=(0,c.getDbInstance)().prepare("DELETE FROM free_proxies WHERE id = ?").run(a);return(0,d.backupDbFile)("pre-write"),b.changes>0}async function n(a){let b=(0,c.getDbInstance)().prepare("DELETE FROM free_proxies WHERE source = ? AND in_pool = 0").run(a);return(0,d.backupDbFile)("pre-write"),b.changes}async function o(a,b){let e=(0,c.getDbInstance)(),f=e.prepare("SELECT id, host, port FROM free_proxies WHERE source = ? AND in_pool = 0").all(a).filter(a=>!b.has(`${a.host}:${a.port}`)).map(a=>a.id);if(0===f.length)return 0;let g=f.map(()=>"?").join(","),h=e.prepare(`DELETE FROM free_proxies WHERE id IN (${g})`).run(...f);return(0,d.backupDbFile)("pre-write"),h.changes}let p="free_proxies",q="last_sync_at";async function r(a){let b=(0,c.getDbInstance)(),e=a??new Date().toISOString();return b.prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)").run(p,q,e),(0,d.backupDbFile)("pre-write"),e}async function s(){let a,b=(0,c.getDbInstance)(),d=b.prepare(`SELECT COUNT(*) as total,
              SUM(CASE WHEN in_pool = 1 THEN 1 ELSE 0 END) as in_pool_count,
              AVG(quality_score) as avg_quality,
              MAX(last_validated) as last_sync_at
       FROM free_proxies`).get(),e=b.prepare("SELECT source, COUNT(*) as count FROM free_proxies GROUP BY source ORDER BY count DESC").all(),f=(a=b.prepare("SELECT value FROM key_value WHERE namespace = ? AND key = ?").get(p,q),a?.value!=null?String(a.value):null),g=null!=d.last_sync_at?String(d.last_sync_at):null;return{total:Number(d.total)||0,inPool:Number(d.in_pool_count)||0,avgQuality:null!=d.avg_quality?Math.round(Number(d.avg_quality)):null,bySource:e.map(a=>({source:String(a.source),count:Number(a.count)})),lastSyncAt:f??g}}async function t(a,b){let e=(0,c.getDbInstance)(),f=new Date().toISOString();e.prepare("INSERT OR REPLACE INTO free_proxy_sync_errors (source, errors, updated_at) VALUES (?, ?, ?)").run(a,JSON.stringify(b),f),(0,d.backupDbFile)("pre-write")}async function u(a){(0,c.getDbInstance)().prepare("DELETE FROM free_proxy_sync_errors WHERE source = ?").run(a),(0,d.backupDbFile)("pre-write")}async function v(){let a=(0,c.getDbInstance)().prepare("SELECT source, errors FROM free_proxy_sync_errors").all(),b={};for(let c of a)if(c.source)try{let a=JSON.parse(c.errors);b[c.source]=Array.isArray(a)?a.map(String):[String(c.errors)]}catch{b[c.source]=[String(c.errors)]}return b}a.s(["clearFreeProxiesBySource",0,n,"clearFreeProxySyncErrors",0,u,"countFreeProxies",0,h,"deleteFreeProxy",0,m,"getFreeProxyById",0,j,"getFreeProxyStats",0,s,"getFreeProxySyncErrors",0,v,"listFreeProxies",0,g,"listFreeProxiesBySource",0,i,"markFreeProxyInPool",0,k,"promoteFreeProxyToPool",0,l,"pruneStaleFreeProxies",0,o,"recordFreeProxySync",0,r,"recordFreeProxySyncErrors",0,t,"upsertFreeProxy",0,f])},244119,a=>{"use strict";var b=a.i(738037),c=a.i(666680);function d(a){let b={};try{let c=JSON.parse(a.params_json);null===c||"object"!=typeof c||Array.isArray(c)||(b=c)}catch{b={}}return{id:a.id,name:a.name,endpoint:a.endpoint,model:a.model,system:a.system,params:b,created_at:a.created_at}}function e(a){let c=(0,b.getDbInstance)().prepare("SELECT * FROM playground_presets WHERE id = ? LIMIT 1").get(a);return c?d(c):null}a.s(["createPlaygroundPreset",0,function(a){let d=(0,b.getDbInstance)(),f=(0,c.randomUUID)(),g=JSON.stringify(a.params??{}),h=a.system??null;return d.prepare("INSERT INTO playground_presets (id, name, endpoint, model, system, params_json) VALUES (?, ?, ?, ?, ?, ?)").run(f,a.name,a.endpoint,a.model,h,g),e(f)},"deletePlaygroundPreset",0,function(a){return(0,b.getDbInstance)().prepare("DELETE FROM playground_presets WHERE id = ?").run(a).changes>0},"getPlaygroundPreset",0,e,"listPlaygroundPresets",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM playground_presets ORDER BY created_at DESC").all().map(d)},"updatePlaygroundPreset",0,function(a,c){let d=(0,b.getDbInstance)(),f=e(a);if(!f)return null;let g=[],h=[];return(void 0!==c.name&&(g.push("name = ?"),h.push(c.name)),void 0!==c.endpoint&&(g.push("endpoint = ?"),h.push(c.endpoint)),void 0!==c.model&&(g.push("model = ?"),h.push(c.model)),"system"in c&&(g.push("system = ?"),h.push(c.system??null)),void 0!==c.params&&(g.push("params_json = ?"),h.push(JSON.stringify(c.params))),0===g.length)?f:(h.push(a),d.prepare(`UPDATE playground_presets SET ${g.join(", ")} WHERE id = ?`).run(...h),e(a))}])},363270,a=>{"use strict";var b=a.i(738037);function c(){let a=(0,b.getDbInstance)().prepare("SELECT active_dim, embedding_signature, last_reset_at, vec_loaded FROM memory_vec_meta WHERE id = 1").get();return a?{activeDim:a.active_dim,embeddingSignature:a.embedding_signature,lastResetAt:a.last_reset_at,vecLoaded:1===a.vec_loaded}:{activeDim:null,embeddingSignature:null,lastResetAt:null,vecLoaded:!1}}a.s(["countMemoryReindexPending",0,function(){return(0,b.getDbInstance)().prepare("SELECT COUNT(*) AS cnt FROM memories WHERE needs_reindex = 1").get().cnt},"getMemoryReindexQueue",0,function(a){return(0,b.getDbInstance)().prepare(`SELECT id, content, COALESCE(key, '') AS key
       FROM memories
       WHERE needs_reindex = 1
       ORDER BY created_at ASC
       LIMIT ?`).all(a)},"getMemoryVecMeta",0,c,"markAllMemoriesNeedReindex",0,function(){return(0,b.getDbInstance)().prepare("UPDATE memories SET needs_reindex = 1").run().changes},"markMemoryNeedsReindex",0,function(a,c){(0,b.getDbInstance)().prepare("UPDATE memories SET needs_reindex = ? WHERE id = ?").run(+!!c,a)},"setMemoryVecMeta",0,function(a){let d=(0,b.getDbInstance)(),e=c(),f="activeDim"in a?a.activeDim??null:e.activeDim,g="embeddingSignature"in a?a.embeddingSignature??null:e.embeddingSignature,h="lastResetAt"in a?a.lastResetAt??null:e.lastResetAt,i="vecLoaded"in a?+!!a.vecLoaded:+!!e.vecLoaded;d.prepare(`INSERT OR REPLACE INTO memory_vec_meta
       (id, active_dim, embedding_signature, last_reset_at, vec_loaded)
     VALUES (1, ?, ?, ?, ?)`).run(f,g,h,i)}])},17743,a=>{"use strict";var b=a.i(738037);function c(a){return{agent_id:a.agent_id,dns_enabled:1===a.dns_enabled,cert_trusted:1===a.cert_trusted,setup_completed:1===a.setup_completed,last_started_at:a.last_started_at,last_error:a.last_error}}function d(a){let d=(0,b.getDbInstance)().prepare("SELECT * FROM agent_bridge_state WHERE agent_id = ?").get(a);return d?c(d):null}a.s(["getAgentBridgeState",0,d,"getAllAgentBridgeStates",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM agent_bridge_state ORDER BY agent_id ASC").all().map(c)},"setLastError",0,function(a,c){(0,b.getDbInstance)().prepare(`INSERT INTO agent_bridge_state (agent_id, last_error)
     VALUES (?, ?)
     ON CONFLICT(agent_id) DO UPDATE SET last_error = excluded.last_error`).run(a,c)},"setLastStarted",0,function(a,c){(0,b.getDbInstance)().prepare(`INSERT INTO agent_bridge_state (agent_id, last_started_at)
     VALUES (?, ?)
     ON CONFLICT(agent_id) DO UPDATE SET last_started_at = excluded.last_started_at`).run(a,c)},"upsertAgentBridgeState",0,function(a){let c=(0,b.getDbInstance)();if(d(a.agent_id)){let b=[],d=[];if(void 0!==a.dns_enabled&&(b.push("dns_enabled = ?"),d.push(+!!a.dns_enabled)),void 0!==a.cert_trusted&&(b.push("cert_trusted = ?"),d.push(+!!a.cert_trusted)),void 0!==a.setup_completed&&(b.push("setup_completed = ?"),d.push(+!!a.setup_completed)),void 0!==a.last_started_at&&(b.push("last_started_at = ?"),d.push(a.last_started_at)),void 0!==a.last_error&&(b.push("last_error = ?"),d.push(a.last_error)),0===b.length)return;d.push(a.agent_id),c.prepare(`UPDATE agent_bridge_state SET ${b.join(", ")} WHERE agent_id = ?`).run(...d)}else c.prepare(`INSERT INTO agent_bridge_state
         (agent_id, dns_enabled, cert_trusted, setup_completed, last_started_at, last_error)
       VALUES (?, ?, ?, ?, ?, ?)`).run(a.agent_id,void 0!==a.dns_enabled?+!!a.dns_enabled:0,void 0!==a.cert_trusted?+!!a.cert_trusted:0,void 0!==a.setup_completed?+!!a.setup_completed:0,a.last_started_at??null,a.last_error??null)}])},792497,a=>{"use strict";var b=a.i(738037);a.s(["deleteMapping",0,function(a,c){(0,b.getDbInstance)().prepare("DELETE FROM agent_bridge_mappings WHERE agent_id = ? AND source_model = ?").run(a,c)},"getMappingsForAgent",0,function(a){return(0,b.getDbInstance)().prepare("SELECT agent_id, source_model, target_model, updated_at FROM agent_bridge_mappings WHERE agent_id = ? ORDER BY source_model ASC").all(a)},"setMappings",0,function(a,c){let d=(0,b.getDbInstance)(),e=new Date().toISOString(),f=d.prepare("DELETE FROM agent_bridge_mappings WHERE agent_id = ?"),g=d.prepare(`INSERT INTO agent_bridge_mappings (agent_id, source_model, target_model, updated_at)
     VALUES (?, ?, ?, ?)`);d.transaction(()=>{for(let b of(f.run(a),c))g.run(a,b.source,b.target,e)})()}])},536134,a=>{"use strict";var b=a.i(738037);function c(a){return{pattern:a.pattern,source:a.source,created_at:a.created_at}}a.s(["getAllBypassPatterns",0,function(){return(0,b.getDbInstance)().prepare("SELECT pattern, source, created_at FROM agent_bridge_bypass ORDER BY source ASC, pattern ASC").all().map(c)},"getUserBypassPatterns",0,function(){return(0,b.getDbInstance)().prepare("SELECT pattern FROM agent_bridge_bypass WHERE source = 'user' ORDER BY pattern ASC").all().map(a=>a.pattern)},"replaceUserBypassPatterns",0,function(a){let c=(0,b.getDbInstance)(),d=new Date().toISOString(),e=c.prepare("DELETE FROM agent_bridge_bypass WHERE source = 'user'"),f=c.prepare("INSERT INTO agent_bridge_bypass (pattern, source, created_at) VALUES (?, 'user', ?)");c.transaction(()=>{for(let b of(e.run(),a))f.run(b,d)})()},"seedDefaultBypassPatterns",0,function(a){let c=(0,b.getDbInstance)(),d=new Date().toISOString(),e=c.prepare("INSERT OR IGNORE INTO agent_bridge_bypass (pattern, source, created_at) VALUES (?, 'default', ?)");c.transaction(()=>{for(let b of a)e.run(b,d)})()}])},128312,a=>a.a(async(b,c)=>{try{var d=a.i(677850),e=b([d]);[d]=e.then?(await e)():e;let f=d.z.object({id:d.z.string().uuid(),source:d.z.enum(["agent-bridge","custom-host","http-proxy","system-proxy","tproxy"]),agent:d.z.string().optional(),timestamp:d.z.string().datetime(),method:d.z.string(),host:d.z.string(),path:d.z.string(),requestHeaders:d.z.record(d.z.string(),d.z.string()),requestBody:d.z.string().nullable(),requestSize:d.z.number().int().nonnegative(),responseHeaders:d.z.record(d.z.string(),d.z.string()),responseBody:d.z.string().nullable(),responseSize:d.z.number().int().nonnegative(),status:d.z.union([d.z.number().int(),d.z.literal("in-flight"),d.z.literal("error")]),proxyLatencyMs:d.z.number().nonnegative().optional(),upstreamLatencyMs:d.z.number().nonnegative().optional(),totalLatencyMs:d.z.number().nonnegative().optional(),error:d.z.string().optional(),sourceModel:d.z.string().nullable().optional(),mappedModel:d.z.string().nullable().optional(),detectedKind:d.z.enum(["llm","app","unknown"]).optional(),contextKey:d.z.string().optional(),annotation:d.z.string().optional(),sessionId:d.z.string().uuid().optional(),note:d.z.string().optional(),pid:d.z.number().int().nonnegative().optional(),processName:d.z.string().optional()});a.s(["InterceptedRequestSchema",0,f]),c()}catch(a){c(a)}},!1),101328,a=>a.a(async(b,c)=>{try{var d=a.i(254799),e=a.i(738037),f=a.i(128312),g=b([f]);function h(a){return{id:a.id,name:a.name,started_at:a.started_at,ended_at:a.ended_at,request_count:a.request_count,profile:a.profile}}function i(a){let b=(0,e.getDbInstance)().prepare("SELECT * FROM inspector_sessions WHERE id = ?").get(a);return b?h(b):null}function j(a){return(0,e.getDbInstance)().prepare("SELECT seq, payload FROM inspector_session_requests WHERE session_id = ? ORDER BY seq ASC").all(a).map(a=>({seq:a.seq,payload:a.payload}))}[f]=g.then?(await g)():g,a.s(["appendSessionRequest",0,function(a,b){let c=(0,e.getDbInstance)(),d=0;return c.transaction(()=>{let e=c.prepare("SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM inspector_session_requests WHERE session_id = ?").get(a).next_seq;c.prepare("INSERT INTO inspector_session_requests (session_id, seq, payload) VALUES (?, ?, ?)").run(a,e,b),c.prepare("UPDATE inspector_sessions SET request_count = request_count + 1 WHERE id = ?").run(a),d=e})(),d},"createSession",0,function(a){let b=(0,e.getDbInstance)(),c=(0,d.randomUUID)(),f=new Date().toISOString();return b.prepare("INSERT INTO inspector_sessions (id, name, started_at, profile) VALUES (?, ?, ?, ?)").run(c,a?.name??null,f,a?.profile??null),{id:c,started_at:f}},"deleteSession",0,function(a){(0,e.getDbInstance)().prepare("DELETE FROM inspector_sessions WHERE id = ?").run(a)},"getSession",0,i,"getSessionRequests",0,j,"listSessions",0,function(){return(0,e.getDbInstance)().prepare("SELECT * FROM inspector_sessions ORDER BY started_at DESC").all().map(h)},"renameSession",0,function(a,b){(0,e.getDbInstance)().prepare("UPDATE inspector_sessions SET name = ? WHERE id = ?").run(b,a)},"snapshotSession",0,function(a){let b=i(a);if(null===b)return null;let c=j(a),d=[];for(let a of c){let b;try{b=JSON.parse(a.payload)}catch{continue}let c=f.InterceptedRequestSchema.safeParse(b);c.success&&d.push(c.data)}return d},"stopSession",0,function(a){let b=(0,e.getDbInstance)(),c=new Date().toISOString();b.prepare("UPDATE inspector_sessions SET ended_at = ? WHERE id = ?").run(c,a)}]),c()}catch(a){c(a)}},!1),388292,a=>{"use strict";var b=a.i(446786),c=a.i(814747),d=a.i(785148);let e=()=>c.default.join(c.default.join(b.default.homedir(),".omp","agent"),"agent.db");a.s(["deleteOmpCredentials",0,function(a){let b=e(),c=new d.default(b);c.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(a),c.close()},"getOmpCredentials",0,function(a){let b=e();try{let c=new d.default(b,{readonly:!0}),e=c.prepare("SELECT data FROM auth_credentials WHERE provider = ? AND credential_type = 'api_key'").get(a);if(c.close(),e?.data){let a=JSON.parse(e.data);return{hasOmniRoute:!0,baseUrl:a.baseUrl||null,apiKey:a.apiKey||null}}return{hasOmniRoute:!1,baseUrl:null,apiKey:null}}catch{return{hasOmniRoute:!1,baseUrl:null,apiKey:null}}},"saveOmpCredentials",0,function(a,b,c){let f=e(),g=new d.default(f);g.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(a),g.prepare("INSERT INTO auth_credentials (provider, credential_type, data, disabled_cause, identity_key, created_at, updated_at) VALUES (?, ?, ?, NULL, NULL, ?, ?)").run(a,"api_key",JSON.stringify({apiKey:b,baseUrl:c}),Math.floor(Date.now()/1e3),Math.floor(Date.now()/1e3)),g.close()}])},163880,a=>{"use strict";var b=a.i(738037);function c(a){return{poolId:a.pool_id,apiKeyId:a.api_key_id,model:a.model,capValue:a.cap_value,capUnit:a.cap_unit}}function d(){return(0,b.getDbInstance)()}a.s(["deleteModelCap",0,function(a,b,c){d().prepare(`DELETE FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ? AND model = ?`).run(a,b,c)},"getModelCap",0,function(a,b,e){let f=d().prepare(`SELECT pool_id, api_key_id, model, cap_value, cap_unit
       FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ? AND model = ?`).get(a,b,e);return f?c(f):null},"listModelCaps",0,function(a,b){return d().prepare(`SELECT pool_id, api_key_id, model, cap_value, cap_unit
       FROM quota_allocation_model_caps
       WHERE pool_id = ? AND api_key_id = ?`).all(a,b).map(c)},"setModelCap",0,function(a){d().prepare(`INSERT INTO quota_allocation_model_caps
         (pool_id, api_key_id, model, cap_value, cap_unit)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(pool_id, api_key_id, model) DO UPDATE SET
         cap_value = excluded.cap_value,
         cap_unit  = excluded.cap_unit`).run(a.poolId,a.apiKeyId,a.model,a.capValue,a.capUnit)}])},730699,a=>{"use strict";var b=a.i(738037);function c(){return(0,b.getDbInstance)()}a.s(["gcOlderThan",0,function(a){return c().prepare("DELETE FROM quota_consumption WHERE updated_at < ?").run(a).changes},"getBucket",0,function(a,b,d){let e=c().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(a,b,d);return e?.consumed??0},"getPair",0,function(a,b,d){let e=c().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(a,b,d),f=c().prepare(`SELECT consumed FROM quota_consumption
       WHERE api_key_id = ? AND dimension_key = ? AND bucket_index = ?`).get(a,b,d-1);return{curr:e?.consumed??0,prev:f?.consumed??0}},"incrementBucket",0,function(a,b,d,e,f){c().prepare(`INSERT INTO quota_consumption (api_key_id, dimension_key, bucket_index, consumed, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(api_key_id, dimension_key, bucket_index)
       DO UPDATE SET
         consumed = consumed + excluded.consumed,
         updated_at = excluded.updated_at`).run(a,b,d,e,f)},"sumPoolDimension",0,function(a,b){let d=c().prepare(`SELECT COALESCE(SUM(consumed), 0) AS total
       FROM quota_consumption
       WHERE dimension_key = ? AND bucket_index = ?`).get(a,b),e=c().prepare(`SELECT COALESCE(SUM(consumed), 0) AS total
       FROM quota_consumption
       WHERE dimension_key = ? AND bucket_index = ?`).get(a,b-1);return{currTotal:d?.total??0,prevTotal:e?.total??0}}])},519260,a=>{"use strict";var b=a.i(738037);function c(){return(0,b.getDbInstance)()}function d(a){let b=[];try{b=JSON.parse(a.dimensions_json)}catch{b=[]}return{connectionId:a.connection_id,provider:a.provider,dimensions:b,source:a.source}}a.s(["deletePlan",0,function(a){return c().prepare("DELETE FROM provider_plans WHERE connection_id = ?").run(a).changes>0},"getPlan",0,function(a){let b=c().prepare(`SELECT connection_id, provider, dimensions_json, source, updated_at
       FROM provider_plans WHERE connection_id = ?`).get(a);return b?d(b):null},"listPlans",0,function(){return c().prepare(`SELECT connection_id, provider, dimensions_json, source, updated_at
       FROM provider_plans ORDER BY provider ASC`).all().map(d)},"upsertPlan",0,function(a,b,d,e){let f=new Date().toISOString(),g=JSON.stringify(d);c().prepare(`INSERT INTO provider_plans (connection_id, provider, dimensions_json, source, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(connection_id)
       DO UPDATE SET
         provider = excluded.provider,
         dimensions_json = excluded.dimensions_json,
         source = excluded.source,
         updated_at = excluded.updated_at`).run(a,b,g,e,f)}])},366442,a=>{"use strict";var b=a.i(738037);let c=!1;function d(a){return a&&"object"==typeof a&&!Array.isArray(a)?a:{}}function e(a,b=0){if("number"==typeof a&&Number.isFinite(a))return a;if("string"==typeof a&&a.trim().length>0){let c=Number(a);return Number.isFinite(c)?c:b}return b}a.s(["batchSaveCostEntries",0,function(a){if(!function(){if(c)return;let a=(0,b.getDbInstance)(),e=new Set(a.prepare("PRAGMA table_info(domain_budgets)").all().map(a=>{let b=d(a);return"string"==typeof b.name?b.name:""}).filter(Boolean));e.has("weekly_limit_usd")||a.exec("ALTER TABLE domain_budgets ADD COLUMN weekly_limit_usd REAL DEFAULT 0"),e.has("reset_interval")||a.exec("ALTER TABLE domain_budgets ADD COLUMN reset_interval TEXT DEFAULT 'daily'"),e.has("reset_time")||a.exec("ALTER TABLE domain_budgets ADD COLUMN reset_time TEXT DEFAULT '00:00'"),e.has("budget_reset_at")||a.exec("ALTER TABLE domain_budgets ADD COLUMN budget_reset_at INTEGER"),e.has("last_budget_reset_at")||a.exec("ALTER TABLE domain_budgets ADD COLUMN last_budget_reset_at INTEGER"),e.has("warning_emitted_at")||a.exec("ALTER TABLE domain_budgets ADD COLUMN warning_emitted_at INTEGER"),e.has("warning_period_start")||a.exec("ALTER TABLE domain_budgets ADD COLUMN warning_period_start INTEGER"),a.exec(`
    CREATE TABLE IF NOT EXISTS domain_budget_reset_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      api_key_id TEXT NOT NULL,
      reset_interval TEXT NOT NULL,
      previous_spend REAL NOT NULL DEFAULT 0,
      reset_at INTEGER NOT NULL,
      next_reset_at INTEGER NOT NULL,
      period_start INTEGER NOT NULL,
      period_end INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_dbrl_key_reset
      ON domain_budget_reset_logs(api_key_id, reset_at DESC);
  `),c=!0}(),!Array.isArray(a)||0===a.length)return;let e=(0,b.getDbInstance)(),f=e.prepare("INSERT INTO domain_cost_history (api_key_id, cost, timestamp) VALUES (?, ?, ?)");e.transaction(a=>{for(let b of a)f.run(b.apiKeyId,b.cost,b.timestamp)})(a)},"deleteCircuitBreakerState",0,function(a){(0,b.getDbInstance)().prepare("DELETE FROM domain_circuit_breakers WHERE name = ?").run(a)},"loadCircuitBreakerState",0,function(a){let c=(0,b.getDbInstance)().prepare("SELECT * FROM domain_circuit_breakers WHERE name = ?").get(a);if(!c)return null;let f=d(c),g="string"==typeof f.options?JSON.parse(f.options):null;return{state:"string"==typeof f.state?f.state:"CLOSED",failureCount:e(f.failure_count),lastFailureTime:e(f.last_failure_time,0)||null,options:g}},"saveCircuitBreakerState",0,function(a,c){(0,b.getDbInstance)().prepare(`INSERT OR REPLACE INTO domain_circuit_breakers (name, state, failure_count, last_failure_time, options)
     VALUES (?, ?, ?, ?, ?)`).run(a,c.state,c.failureCount,c.lastFailureTime,c.options?JSON.stringify(c.options):null)}])},639367,a=>{"use strict";var b=a.i(254799),c=a.i(738037),d=a.i(366442);class e{buffer=[];inFlightEntries=[];discardedApiKeyIds=new Set;timer=null;started=!1;flushPromise=null;persistEntries;logger;flushIntervalMs;maxBufferSize;constructor(a={}){this.persistEntries=a.persistEntries||d.batchSaveCostEntries,this.logger=a.logger||console,this.flushIntervalMs=a.flushIntervalMs??function(){let a=Number.parseInt(process.env.OMNIROUTE_SPEND_FLUSH_INTERVAL_MS||"",10);return Number.isFinite(a)&&a>0?a:6e4}(),this.maxBufferSize=a.maxBufferSize??function(){let a=Number.parseInt(process.env.OMNIROUTE_SPEND_MAX_BUFFER_SIZE||"",10);return Number.isFinite(a)&&a>0?a:1e3}()}start(){this.started||(this.started=!0,this.timer=setInterval(()=>{this.flush()},this.flushIntervalMs),this.timer.unref?.())}increment(a,b,c=Date.now()){var d;let e=(d={apiKeyId:a,cost:b,timestamp:c},d?.apiKeyId&&Number.isFinite(d.cost)&&!(d.cost<=0)?{apiKeyId:d.apiKeyId,cost:d.cost,timestamp:Number.isFinite(d.timestamp)?d.timestamp:Date.now()}:null);e&&(this.start(),this.discardedApiKeyIds.delete(e.apiKeyId),this.buffer.push(e),this.buffer.length>=this.maxBufferSize&&this.flush())}getBufferedEntries(a,b=0,c=1/0){return[...this.inFlightEntries,...this.buffer].filter(d=>d.apiKeyId===a&&d.timestamp>=b&&d.timestamp<c)}getPendingCostTotal(a,b=0,c=1/0){return this.getBufferedEntries(a,b,c).reduce((a,b)=>a+b.cost,0)}discardEntries(a){this.discardedApiKeyIds.add(a),this.buffer=this.buffer.filter(b=>b.apiKeyId!==a),this.inFlightEntries=this.inFlightEntries.filter(b=>b.apiKeyId!==a)}async flush(){if(this.flushPromise)return this.flushPromise;if(0===this.buffer.length)return{flushedEntries:0,uniqueKeys:0,requeued:!1};let a=[...this.buffer];return this.buffer=[],this.inFlightEntries=a,this.flushPromise=(async()=>{let b=a.filter(a=>!this.discardedApiKeyIds.has(a.apiKeyId)),c=new Set(b.map(a=>a.apiKeyId)).size;try{return b.length>0&&await this.persistEntries(b),this.logger.log(`[SpendWriter] Flushed ${b.length} cost entr${1===b.length?"y":"ies"} across ${c} key(s)`),{flushedEntries:b.length,uniqueKeys:c,requeued:!1}}catch(d){this.buffer=[...b,...this.buffer];let a=d instanceof Error?d.message:String(d);return this.logger.error(`[SpendWriter] Flush error: ${a}`),{flushedEntries:0,uniqueKeys:c,requeued:!0}}finally{this.inFlightEntries=[],this.flushPromise=null}})(),this.flushPromise}async stop(){return this.timer&&(clearInterval(this.timer),this.timer=null),this.started=!1,this.flush()}resetForTests(){this.timer&&(clearInterval(this.timer),this.timer=null),this.started=!1,this.buffer=[],this.inFlightEntries=[],this.discardedApiKeyIds.clear(),this.flushPromise=null}}new e;let f=/^(\d{2}):(\d{2})$/;function g(a,b,c,d,e){return Date.UTC(a,b,c,d,e,0,0)}let h=!1;function i(a){return a&&"object"==typeof a&&!Array.isArray(a)?a:{}}function j(a,b=0){if("number"==typeof a&&Number.isFinite(a))return a;if("string"==typeof a&&a.trim().length>0){let c=Number(a);return Number.isFinite(c)?c:b}return b}function k(a){return"model"===a||"provider"===a||"global"===a?a:"global"}function l(a){return"daily"===a||"weekly"===a||"monthly"===a?a:"monthly"}function m(){h||((0,c.getDbInstance)().exec(`
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
  `),h=!0)}function n(a){let b=i(a);return{id:"string"==typeof b.id?b.id:"",apiKeyId:"string"==typeof b.api_key_id?b.api_key_id:"",scopeType:k(b.scope_type),scopeValue:"string"==typeof b.scope_value?b.scope_value:"",tokenLimit:j(b.token_limit),resetInterval:l(b.reset_interval),resetTime:"string"==typeof b.reset_time&&b.reset_time?b.reset_time:"00:00",enabled:0!==j(b.enabled,1),createdAt:"string"==typeof b.created_at?b.created_at:"",updatedAt:"string"==typeof b.updated_at?b.updated_at:""}}function o(a,b=Date.now()){let c=function(a,b="00:00",c=Date.now()){let d,e=new Date(c),[h,i]=(d=(function(a){if("string"==typeof a){let b=a.trim().match(f);if(b){let a=Math.min(Math.max(parseInt(b[1],10),0),23),c=Math.min(Math.max(parseInt(b[2],10),0),59);return`${String(a).padStart(2,"0")}:${String(c).padStart(2,"0")}`}}return"00:00"})(b).match(f))?[parseInt(d[1],10),parseInt(d[2],10)]:[0,0],j=e.getUTCFullYear(),k=e.getUTCMonth(),l=e.getUTCDate();if("weekly"===a){let a=(e.getUTCDay()+6)%7,b=g(j,k,l-a,h,i);return c>=b?{periodStartAt:b,nextResetAt:g(j,k,l-a+7,h,i)}:{periodStartAt:g(j,k,l-a-7,h,i),nextResetAt:b}}if("monthly"===a){let a=g(j,k,1,h,i);return c>=a?{periodStartAt:a,nextResetAt:g(j,k+1,1,h,i)}:{periodStartAt:g(j,k-1,1,h,i),nextResetAt:a}}let m=g(j,k,l,h,i);return c>=m?{periodStartAt:m,nextResetAt:g(j,k,l+1,h,i)}:{periodStartAt:g(j,k,l-1,h,i),nextResetAt:m}}(a.resetInterval,a.resetTime,b);return{windowStart:String(c.periodStartAt),didReset:!1,periodStartAt:c.periodStartAt,nextResetAt:c.nextResetAt}}a.s(["deleteTokenLimit",0,function(a){m();let b=(0,c.getDbInstance)();return b.prepare("DELETE FROM api_key_token_counters WHERE limit_id = ?").run(a),b.prepare("DELETE FROM api_key_token_limit_reset_logs WHERE limit_id = ?").run(a),b.prepare("DELETE FROM api_key_token_limits WHERE id = ?").run(a).changes>0},"getTokenLimitsForRequest",0,function(a,b,d){return m(),(0,c.getDbInstance)().prepare(`SELECT * FROM api_key_token_limits
       WHERE api_key_id = @apiKeyId
         AND enabled = 1
         AND (
           (scope_type = 'global')
           OR (scope_type = 'model' AND scope_value = @model)
           OR (scope_type = 'provider' AND scope_value = @provider)
         )`).all({apiKeyId:a,model:d||"",provider:b||""}).map(n)},"getWindowUsage",0,function(a,b=Date.now()){m();let d=(0,c.getDbInstance)(),{windowStart:e}=o(a,b);return j(i(d.prepare("SELECT tokens_used FROM api_key_token_counters WHERE limit_id = ? AND window_start = ?").get(a.id,e)).tokens_used)},"incrementWindowTokens",0,function(a,b,d){m();let e=(0,c.getDbInstance)(),f=Math.max(0,Math.floor(j(d)));return j(i(e.prepare(`INSERT INTO api_key_token_counters (limit_id, window_start, tokens_used, updated_at)
       VALUES (@limitId, @windowStart, @tokens, datetime('now'))
       ON CONFLICT(limit_id, window_start)
       DO UPDATE SET tokens_used = tokens_used + excluded.tokens_used,
                     updated_at  = datetime('now')
       RETURNING tokens_used`).get({limitId:a,windowStart:b,tokens:f})).tokens_used)},"listTokenLimits",0,function(a){return m(),(0,c.getDbInstance)().prepare(`SELECT * FROM api_key_token_limits
       WHERE api_key_id = ?
       ORDER BY CASE scope_type WHEN 'model' THEN 0 WHEN 'provider' THEN 1 ELSE 2 END, scope_value`).all(a).map(n)},"logTokenLimitReset",0,function(a,b,d){m(),(0,c.getDbInstance)().prepare(`INSERT INTO api_key_token_limit_reset_logs (limit_id, reset_at, prev_tokens, window_start)
     VALUES (?, datetime('now'), ?, ?)`).run(a,Math.max(0,Math.floor(j(b))),d)},"resetWindowIfElapsed",0,o,"upsertTokenLimit",0,function(a){m();let d=(0,c.getDbInstance)(),e=k(a.scopeType),f="global"===e?"":(a.scopeValue??"").trim(),g=l(a.resetInterval),h="string"==typeof a.resetTime&&a.resetTime?a.resetTime:"00:00",i=+(!1!==a.enabled),o=Math.floor(j(a.tokenLimit)),p=a.id&&a.id.trim()?a.id.trim():(0,b.randomUUID)();return d.prepare(`INSERT INTO api_key_token_limits
       (id, api_key_id, scope_type, scope_value, token_limit, reset_interval, reset_time, enabled, created_at, updated_at)
     VALUES (@id, @apiKeyId, @scopeType, @scopeValue, @tokenLimit, @resetInterval, @resetTime, @enabled, datetime('now'), datetime('now'))
     ON CONFLICT(api_key_id, scope_type, scope_value)
     DO UPDATE SET token_limit    = excluded.token_limit,
                   reset_interval = excluded.reset_interval,
                   reset_time     = excluded.reset_time,
                   enabled        = excluded.enabled,
                   updated_at     = datetime('now')`).run({id:p,apiKeyId:a.apiKeyId,scopeType:e,scopeValue:f,tokenLimit:o,resetInterval:g,resetTime:h,enabled:i}),n(d.prepare("SELECT * FROM api_key_token_limits WHERE api_key_id = ? AND scope_type = ? AND scope_value = ?").get(a.apiKeyId,e,f))}],639367)},27886,a=>{"use strict";let b;var c,d=a.i(738037),e=a.i(433965);let f={debug:0,info:1,warn:2,error:3},g=(0,e.getAppLogLevel)("info").toLowerCase(),h=Object.prototype.hasOwnProperty.call(f,g)?f[g]:f.info,i="json"===(0,e.getAppLogFormat)("text");function j(a){switch(a){case"debug":return console.debug;case"warn":return console.warn;case"error":return console.error;default:return console.log}}function k(a){if(!a||"object"!=typeof a)return"";let b={};for(let[c,d]of Object.entries(a))null!=d&&(b[c]=d);return Object.keys(b).length>0?` ${JSON.stringify(b)}`:""}!function(a=null){}();let l=(c="DB_PLUGINS",b=(a,b,d)=>{if(f[a]<h)return;let e=j(a);if(i){let f={ts:new Date().toISOString(),level:a,tag:c,msg:b};d&&"object"==typeof d&&Object.keys(d).length>0&&(f.data=d),e(JSON.stringify(f))}else e(`[${a.toUpperCase()}] [${c}] ${b}${k(d)}`)},{debug:(a,c)=>b("debug",a,c),info:(a,c)=>b("info",a,c),warn:(a,c)=>b("warn",a,c),error:(a,c)=>b("error",a,c)});function m(a){return{id:a.id,name:a.name,version:a.version,description:a.description,author:a.author,license:a.license,main:a.main,source:a.source,tags:a.tags,status:a.status,enabled:a.enabled,manifest:a.manifest,config:a.config,configSchema:a.config_schema,hooks:a.hooks,permissions:a.permissions,pluginDir:a.plugin_dir,errorMessage:a.error_message,installedAt:a.installed_at,updatedAt:a.updated_at,activatedAt:a.activated_at}}function n(a){let b=(0,d.getDbInstance)().prepare("SELECT * FROM plugins WHERE name = ?").get(a);return b?m(b):null}a.s(["deletePlugin",0,function(a){let b=(0,d.getDbInstance)().prepare("DELETE FROM plugins WHERE name = ?").run(a);return b.changes>0&&l.info("plugin.deleted",{name:a}),b.changes>0},"getPluginById",0,function(a){let b=(0,d.getDbInstance)().prepare("SELECT * FROM plugins WHERE id = ?").get(a);return b?m(b):null},"getPluginByName",0,n,"insertPlugin",0,function(a){let b=(0,d.getDbInstance)(),c=new Date().toISOString();b.prepare(`INSERT INTO plugins (
      id, name, version, description, author, license, main, source, tags,
      status, enabled, manifest, config, config_schema, hooks, permissions,
      plugin_dir, installed_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(a.id,a.name,a.version,a.description??null,a.author??null,a.license??"MIT",a.main,a.source??"local",JSON.stringify(a.tags??[]),a.status??"installed",+!!a.enabled,JSON.stringify(a.manifest),JSON.stringify(a.config??{}),JSON.stringify(a.configSchema??{}),JSON.stringify(a.hooks??[]),JSON.stringify(a.permissions??[]),a.pluginDir,c,c),l.info("plugin.inserted",{id:a.id,name:a.name});let e=n(a.name);if(!e)throw Error(`Failed to retrieve plugin '${a.name}' after insertion`);return e},"listPlugins",0,function(a){let b=(0,d.getDbInstance)();return(a?b.prepare("SELECT * FROM plugins WHERE status = ? ORDER BY name").all(a):b.prepare("SELECT * FROM plugins ORDER BY name").all()).map(m)},"pluginExists",0,function(a){return!!(0,d.getDbInstance)().prepare("SELECT 1 FROM plugins WHERE name = ?").get(a)},"updatePluginConfig",0,function(a,b){let c=(0,d.getDbInstance)(),e=new Date().toISOString();return c.prepare("UPDATE plugins SET config = ?, updated_at = ? WHERE name = ?").run(JSON.stringify(b),e,a).changes>0},"updatePluginStatus",0,function(a,b,c){let e=(0,d.getDbInstance)(),f=new Date().toISOString(),g="active"===b?f:null,h=e.prepare(`UPDATE plugins SET status = ?, enabled = ?, error_message = ?,
       updated_at = ?, activated_at = COALESCE(?, activated_at)
       WHERE name = ?`).run(b,+("active"===b),c??null,f,g,a);return h.changes>0&&l.info("plugin.status_updated",{name:a,status:b}),h.changes>0}],27886)},799229,a=>{"use strict";var b=a.i(738037);function c(a){return{apiKeyId:a.api_key_id,sourceType:a.source_type,token:a.token,baseUrl:a.base_url,vaultPath:a.vault_path,enabled:1===a.enabled}}a.s(["deleteApiKeyContextSource",0,function(a,c){(0,b.getDbInstance)().prepare("DELETE FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ?").run(a,c)},"getApiKeyContextSource",0,function(a,d){if(!a)return null;let e=(0,b.getDbInstance)().prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ? AND enabled = 1").get(a,d);return e?c(e):null},"listApiKeyContextSources",0,function(a){return(0,b.getDbInstance)().prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ?").all(a).map(c)},"setApiKeyContextSource",0,function(a,c,d){let e=(0,b.getDbInstance)(),f=e.prepare("SELECT * FROM api_key_context_sources WHERE api_key_id = ? AND source_type = ?").get(a,c),g=new Date().toISOString();f?e.prepare(`UPDATE api_key_context_sources SET
        token = COALESCE(?, token),
        base_url = COALESCE(?, base_url),
        vault_path = COALESCE(?, vault_path),
        enabled = COALESCE(?, enabled),
        updated_at = ?
      WHERE api_key_id = ? AND source_type = ?`).run(d.token??null,d.baseUrl??null,d.vaultPath??null,void 0!==d.enabled?+!!d.enabled:null,g,a,c):e.prepare(`INSERT INTO api_key_context_sources
        (api_key_id, source_type, token, base_url, vault_path, enabled, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(a,c,d.token??null,d.baseUrl??null,d.vaultPath??null,void 0!==d.enabled?+!!d.enabled:1,g,g)}])},163772,a=>{"use strict";var b=a.i(738037);a.s(["sumUsageTokensThisMonth",0,function(a=(0,b.getDbInstance)()){try{let b=a.prepare(`SELECT COALESCE(SUM(total_input_tokens + total_output_tokens), 0) AS used
         FROM daily_usage_summary
         WHERE date >= strftime('%Y-%m-01','now')`).get();return b?.used??0}catch{return 0}}])},489874,a=>{"use strict";var b=a.i(738037),c=a.i(144544);function d(a){let b=(0,c.rowToCamel)(a)??{};return{model:String(b.model??""),source:String(b.source??""),category:String(b.category??""),score:"number"==typeof b.score?b.score:0,eloRaw:"number"==typeof b.eloRaw?b.eloRaw:null,confidence:"string"==typeof b.confidence?b.confidence:null,syncedAt:String(b.syncedAt??""),expiresAt:"string"==typeof b.expiresAt?b.expiresAt:null}}function e(a,c){let e=(0,b.getDbInstance)().prepare(`SELECT * FROM model_intelligence
       WHERE model = ? AND category = ?
         AND source IN ('user_override', 'arena_elo', 'models_dev_tier')
         AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))
       ORDER BY CASE source
         WHEN 'user_override' THEN 1
         WHEN 'arena_elo' THEN 2
         WHEN 'models_dev_tier' THEN 3
       END
       LIMIT 1`).get(a,c);return e?d(e):null}function f(a){(0,b.getDbInstance)().prepare(`INSERT OR REPLACE INTO model_intelligence
       (model, source, category, score, elo_raw, confidence, synced_at, expires_at)
     VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)`).run(a.model,a.source,a.category,a.score,a.eloRaw??null,a.confidence??null,a.expiresAt??null)}function g(a,c,d){return((0,b.getDbInstance)().prepare(`DELETE FROM model_intelligence
       WHERE model = ? AND source = ? AND category = ?`).run(a,c,d).changes??0)>0}a.s(["bulkUpsertModelIntelligence",0,function(a){if(0===a.length)return 0;let c=(0,b.getDbInstance)(),d=c.prepare(`INSERT OR REPLACE INTO model_intelligence
       (model, source, category, score, elo_raw, confidence, synced_at, expires_at)
     VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)`);return c.transaction(()=>{let b=0;for(let c of a)d.run(c.model,c.source,c.category,c.score,c.eloRaw??null,c.confidence??null,c.expiresAt??null),b++;return b})()},"deleteExpiredIntelligence",0,function(a){let c=(0,b.getDbInstance)(),d=["expires_at IS NOT NULL","datetime(expires_at) < datetime('now')"],e=[];a&&(d.push("source = ?"),e.push(a));let f=d.join(" AND ");return c.prepare(`DELETE FROM model_intelligence WHERE ${f}`).run(...e).changes??0},"deleteModelIntelligence",0,g,"deleteModelIntelligenceBySource",0,function(a){return(0,b.getDbInstance)().prepare("DELETE FROM model_intelligence WHERE source = ?").run(a).changes??0},"deleteUserFitnessOverrideEntry",0,function(a,b){return g(a.toLowerCase(),"user_override",b.toLowerCase())},"getModelIntelligence",0,e,"getModelIntelligenceBySource",0,function(a,c,e){let f=(0,b.getDbInstance)().prepare(`SELECT * FROM model_intelligence
       WHERE model = ? AND source = ? AND category = ?
         AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))`).get(a,c,e);return f?d(f):null},"getResolvedTaskFitness",0,function(a,b){let c=e(a,b);return c?c.score:null},"listModelIntelligence",0,function(a){let c=(0,b.getDbInstance)(),e=[],f=[];a?.source&&(e.push("source = ?"),f.push(a.source)),a?.category&&(e.push("category = ?"),f.push(a.category));let g=e.length>0?`WHERE ${e.join(" AND ")}`:"",h=`SELECT * FROM model_intelligence ${g} ORDER BY model ASC, source ASC, category ASC`;return c.prepare(h).all(...f).map(d)},"setUserFitnessOverrideEntry",0,function(a,b,c){f({model:a.toLowerCase(),source:"user_override",category:b.toLowerCase(),score:Math.max(0,Math.min(1,c)),eloRaw:null,confidence:null,expiresAt:null})},"upsertModelIntelligence",0,f])},913437,a=>{"use strict";var b=a.i(738037);a.s(["getFallbackStats",0,function(a,c){return(0,b.getDbInstance)().prepare(`
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
      ${a}
    `).get(c)??{total:0,with_requested:0,fallback_eligible:0,fallbacks:0}},"getProviderMetrics",0,function(){return(0,b.getDbInstance)().prepare(`SELECT
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
        GROUP BY c.provider`).all()},"getRecentSearchLogs",0,function(){return(0,b.getDbInstance)().prepare(`
        SELECT request_summary, provider, timestamp
        FROM call_logs
        WHERE request_type = 'search'
        ORDER BY timestamp DESC
        LIMIT 10
      `).all()},"getSearchAggregateStats",0,function(a){return(0,b.getDbInstance)().prepare(`SELECT
          COUNT(*) as total,
          COALESCE(SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END), 0) as today,
          COALESCE(SUM(CASE WHEN status >= 400 OR error_summary IS NOT NULL THEN 1 ELSE 0 END), 0) as errors,
          AVG(CASE WHEN duration > 0 THEN duration END) as avg_duration,
          COALESCE(SUM(CASE WHEN duration > 0 AND duration < 5 THEN 1 ELSE 0 END), 0) as cached
         FROM call_logs
         WHERE request_type = 'search'`).get(a)??{total:0,today:0,errors:0,avg_duration:null,cached:0}},"getSearchProviderCounts",0,function(){return(0,b.getDbInstance)().prepare(`SELECT provider, COUNT(*) as cnt
         FROM call_logs WHERE request_type = 'search'
         GROUP BY provider ORDER BY cnt DESC`).all()},"getSearchProviderStats",0,function(){return(0,b.getDbInstance)().prepare(`
        SELECT provider, COUNT(*) as requests,
          CAST(AVG(duration) AS INTEGER) as avg_latency_ms
        FROM call_logs
        WHERE request_type = 'search'
        GROUP BY provider
      `).all()}])},227257,a=>{"use strict";var b=a.i(738037);a.s(["getAccountCostRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
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
      ${a}
      GROUP BY account, LOWER(usage_history.provider), LOWER(usage_history.model), serviceTier
    `).all(c)},"getAccountUsageRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
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
      ${a}
      GROUP BY account
      ORDER BY requests DESC
      LIMIT 50
    `).all(c)},"getAllDomainBudgets",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM domain_budgets").all()},"getAllDomainCostHistory",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM domain_cost_history").all()},"getAllUsageHistory",0,function(){return(0,b.getDbInstance)().prepare("SELECT * FROM usage_history").all()},"getApiKeyMetadataRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
      SELECT
        NULLIF(api_key_id, '') as apiKeyId,
        NULLIF(api_key_name, '') as apiKeyName,
        COALESCE(NULLIF(api_key_id, ''), NULLIF(api_key_name, ''), 'unknown') as apiKeyGroupKey,
        MAX(timestamp) as lastUsed
      FROM usage_history
      ${a}
      GROUP BY NULLIF(api_key_id, ''), NULLIF(api_key_name, '')
      ORDER BY lastUsed DESC
    `).all(c)},"getApiKeyUsageRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
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
      ${a}
      GROUP BY COALESCE(NULLIF(api_key_id, ''), NULLIF(api_key_name, ''), 'unknown'), NULLIF(api_key_id, ''), LOWER(provider), LOWER(model), serviceTier
    `).all(c)},"getDailyCostRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
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
      FROM ${a} AS _u
      GROUP BY DATE(timestamp), LOWER(provider), LOWER(model), serviceTier
      ORDER BY date ASC
    `).all(c)},"getDailyUsage",0,function(a,c){return(0,b.getDbInstance)().prepare(`
      SELECT
        DATE(timestamp) as date,
        COUNT(*) as requests,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens
      FROM ${a} AS _u
      GROUP BY DATE(timestamp)
      ORDER BY date ASC
    `).all(c)},"getHeatmapRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
      SELECT
        DATE(timestamp) as date,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens
      FROM usage_history
      WHERE ${a.join(" AND ")}
      GROUP BY DATE(timestamp)
      ORDER BY date ASC
    `).all(c)},"getModelUsageRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
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
      FROM ${a} AS _u
      GROUP BY LOWER(model), LOWER(provider), serviceTier
      ORDER BY requests DESC
    `).all(c)},"getPresetCostModelRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
      SELECT
        LOWER(model) as model,
        LOWER(provider) as provider,
        COALESCE(NULLIF(service_tier, ''), 'standard') as serviceTier,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_cache_read), 0) as cacheReadTokens,
        COALESCE(SUM(tokens_cache_creation), 0) as cacheCreationTokens,
        COALESCE(SUM(tokens_reasoning), 0) as reasoningTokens
      FROM ${a} AS _pu
      GROUP BY LOWER(model), LOWER(provider), serviceTier
    `).all(c)},"getProviderCostRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
      SELECT
        LOWER(provider) as provider,
        LOWER(model) as model,
        COALESCE(NULLIF(service_tier, ''), 'standard') as serviceTier,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_cache_read), 0) as cacheReadTokens,
        COALESCE(SUM(tokens_cache_creation), 0) as cacheCreationTokens,
        COALESCE(SUM(tokens_reasoning), 0) as reasoningTokens
      FROM ${a} AS _u
      GROUP BY LOWER(provider), LOWER(model), serviceTier
    `).all(c)},"getProviderUsageRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
      SELECT
        LOWER(provider) as provider,
        COUNT(*) as requests,
        COALESCE(SUM(tokens_input), 0) as promptTokens,
        COALESCE(SUM(tokens_output), 0) as completionTokens,
        COALESCE(SUM(tokens_input + tokens_output), 0) as totalTokens,
        COALESCE(AVG(latency_ms), 0) as avgLatencyMs,
        COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as successfulRequests
      FROM ${a} AS _u
      GROUP BY LOWER(provider)
      ORDER BY requests DESC
    `).all(c)},"getServiceTierUsageRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
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
      FROM ${a} AS _u
      GROUP BY serviceTier, LOWER(provider), LOWER(model)
    `).all(c)},"getUsageSummary",0,function(a,c){return(0,b.getDbInstance)().prepare(`
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
      FROM ${a} AS _u
    `).get(c)??{totalRequests:0,promptTokens:0,completionTokens:0,totalTokens:0,uniqueModels:0,uniqueAccounts:0,uniqueApiKeys:0,successfulRequests:0,avgLatencyMs:0,firstRequest:"",lastRequest:""}},"getWeeklyPatternRows",0,function(a,c){return(0,b.getDbInstance)().prepare(`
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
        FROM ${a} AS _u
        GROUP BY DATE(timestamp), strftime('%w', timestamp)
      )
      GROUP BY dayOfWeek
      ORDER BY dayOfWeek ASC
    `).all(c)}])},894810,a=>{"use strict";var b=a.i(738037);a.s(["getAutoRoutingTopProviders",0,function(){return(0,b.getDbInstance)().prepare(`
      SELECT provider, COUNT(*) as count
      FROM usage_logs
      WHERE model = 'auto' OR model LIKE 'auto/%'
      GROUP BY provider
      ORDER BY count DESC
      LIMIT 10
      `).all()},"getAutoRoutingTotalCount",0,function(){return(0,b.getDbInstance)().prepare(`
      SELECT COUNT(*) as count
      FROM usage_logs
      WHERE model = 'auto' OR model LIKE 'auto/%'
    `).get()??{count:0}},"getAutoRoutingVariantBreakdown",0,function(){return(0,b.getDbInstance)().prepare(`
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
    `).all()}])},201277,a=>{"use strict";var b=a.i(738037);let c=["created_at","expires_at","hit_count","tokens_saved","model"];a.s(["deleteSemanticCacheByModel",0,function(a){return{deleted:(0,b.getDbInstance)().prepare("DELETE FROM semantic_cache WHERE model = ?").run(a).changes}},"deleteSemanticCacheBySignature",0,function(a){return(0,b.getDbInstance)().prepare("DELETE FROM semantic_cache WHERE signature = ?").run(a),{deleted:1}},"listSemanticCacheEntries",0,function(a){let d=(0,b.getDbInstance)(),{page:e,limit:f,search:g,model:h,sortBy:i,sortOrder:j}=a,k=[],l=[];g&&(k.push("(signature LIKE ? OR model LIKE ?)"),l.push(`%${g}%`,`%${g}%`)),h&&(k.push("model = ?"),l.push(h));let m=k.length>0?`WHERE ${k.join(" AND ")}`:"",n=c.includes(i)?i:"created_at",o=d.prepare(`SELECT COUNT(*) as total FROM semantic_cache ${m}`).get(...l);return{entries:d.prepare(`SELECT id, signature, model, hit_count, tokens_saved, created_at, expires_at
       FROM semantic_cache ${m}
       ORDER BY ${n} ${"asc"===j?"ASC":"DESC"}
       LIMIT ? OFFSET ?`).all(...l,f,(e-1)*f),total:o?.total||0}}])},100479,a=>{"use strict";var b=a.i(738037);a.s(["exportProxyLogsSince",0,function(a){return(0,b.getDbInstance)().prepare("SELECT * FROM proxy_logs WHERE timestamp >= @since ORDER BY timestamp DESC").all({since:a})}])},174222,a=>{"use strict";var b=a.i(738037);let c="provider_param_filters",d=null,e=0;function f(){e++,d=null}function g(a){return null!==a&&"object"==typeof a&&!Array.isArray(a)}function h(a){return"string"==typeof a&&a.length>0?a:null}function i(a){return Array.isArray(a)?a.filter(a=>"string"==typeof a):[]}function j(){return null===d&&(d=function(){let a=function(a){let c=(0,b.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(a),d={};for(let a of c)d[a.key]=function(a){if("string"!=typeof a)return a;try{return JSON.parse(a)}catch{return a}}(a.value);return d}(c),d=new Map;for(let[b,c]of Object.entries(a)){let a=function(a){if(!g(a))return null;let b=i(a.block),c=i(a.allow),d=function(a){let b={};if(!g(a))return b;for(let[c,d]of Object.entries(a)){if(!g(d))continue;let a=function(a){let b=i(a.block),c=i(a.allow);if(0===b.length&&0===c.length)return null;let d={};return b.length>0&&(d.block=b),c.length>0&&(d.allow=c),d}(d);a&&(b[c]=a)}return b}(a.models),e="boolean"==typeof a.autoLearn&&a.autoLearn;return{block:b,allow:c,models:Object.keys(d).length>0?d:void 0,autoLearn:e}}(c);a&&d.set(b,a)}return d}()),d}function k(a){return h(a)?j().get(a)??null:null}function l(a,d){if(!h(a))return;let e=(0,b.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)"),g={block:d.block??[],allow:d.allow??[],autoLearn:d.autoLearn??!1,models:d.models&&Object.keys(d.models).length>0?d.models:void 0};e.run(c,a,JSON.stringify(g)),f()}let m="__global__";a.s(["addParamToBlocklist",0,function(a,b,c){if(!h(a)||!h(b))return;let d=k(a)??{block:[],allow:[],autoLearn:!1};if(c){let a=d.models??{},e=a[c]??{};if(Array.isArray(e.block)&&e.block.includes(b))return;let f=[...e.block??[],b];a[c]={...e,block:f},d.models=a}else{if(d.block.includes(b))return;d.block=[...d.block,b]}l(a,d)},"deleteParamFilterConfig",0,function(a){h(a)&&((0,b.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(c,a),f())},"getParamFilterConfig",0,k,"isAutoLearnGloballyEnabled",0,function(){let a=k(m);return a?.autoLearn===!0},"loadParamFilterConfigs",0,j,"setGlobalAutoLearnEnabled",0,function(a){let b=k(m);l(m,{block:b?.block??[],allow:b?.allow??[],autoLearn:a})},"setParamFilterConfig",0,l])},570481,a=>{"use strict";var b=a.i(738037);let c="interception_rules",d=null;function e(a){return null!==a&&"object"==typeof a&&!Array.isArray(a)}function f(a){return"string"==typeof a&&a.trim().length>0?a.trim():null}function g(a){return"boolean"==typeof a?a:void 0}function h(a){return"firecrawl"===a||"jina"===a||"tavily"===a?a:void 0}function i(a){return f(a)?(null===d&&(d=function(){let a=function(a){let c=(0,b.getDbInstance)().prepare("SELECT key, value FROM key_value WHERE namespace = ?").all(a),d={};for(let a of c)d[a.key]=function(a){if("string"!=typeof a)return a;try{return JSON.parse(a)}catch{return a}}(a.value);return d}(c),d=new Map;for(let[b,c]of Object.entries(a)){let a=function(a){if(!e(a))return null;let b=function(a){let b={};if(!e(a))return b;for(let[c,d]of Object.entries(a)){let a=function(a){if(!e(a))return null;let b={interceptSearch:g(a.interceptSearch),interceptFetch:g(a.interceptFetch),fetchBackend:h(a.fetchBackend),fetchProxyUrl:f(a.fetchProxyUrl)??void 0};return Object.values(b).some(a=>void 0!==a)?b:null}(d);a&&(b[c]=a)}return b}(a.models);return{interceptSearch:g(a.interceptSearch),interceptFetch:g(a.interceptFetch),fetchBackend:h(a.fetchBackend),fetchProxyUrl:f(a.fetchProxyUrl)??void 0,models:Object.keys(b).length>0?b:void 0}}(c);a&&d.set(b,a)}return d}()),d).get(a)??null:null}a.s(["deleteInterceptionRules",0,function(a){let e=f(a);e&&((0,b.getDbInstance)().prepare("DELETE FROM key_value WHERE namespace = ? AND key = ?").run(c,e),d=null)},"getInterceptionRules",0,i,"resolveInterceptSearch",0,function(a,b){let c=f(a);if(!c)return;let d=i(c);if(!d)return;let e=f(b);return e&&d.models?.[e]?.interceptSearch!==void 0?d.models[e].interceptSearch:d.interceptSearch},"setInterceptionRules",0,function(a,e){let g=f(a);if(!g)return;let h=(0,b.getDbInstance)().prepare("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES (?, ?, ?)"),i={interceptSearch:e.interceptSearch,interceptFetch:e.interceptFetch,fetchBackend:e.fetchBackend,fetchProxyUrl:e.fetchProxyUrl,models:e.models&&Object.keys(e.models).length>0?e.models:void 0};h.run(c,g,JSON.stringify(i)),d=null}])},147921,a=>a.a(async(b,c)=>{try{var d=a.i(949908);a.i(913754),a.i(18294),a.i(364299),a.i(585868),a.i(446801),a.i(518501),a.i(743255),a.i(426720);var e=a.i(215779);a.i(241897),a.i(266054),a.i(273294),a.i(606373),a.i(913555),a.i(112496),a.i(651316),a.i(724738),a.i(441114),a.i(132758),a.i(984827),a.i(282178),a.i(431018),a.i(177727),a.i(638132),a.i(784797),a.i(240597),a.i(382140),a.i(393373),a.i(593870),a.i(752258),a.i(220766),a.i(112135),a.i(738242),a.i(97505),a.i(595370),a.i(776279),a.i(199369),a.i(63170),a.i(517267),a.i(796486),a.i(244119),a.i(363270),a.i(17743),a.i(792497),a.i(536134),a.i(226786);var f=a.i(101328);a.i(388292),a.i(86683),a.i(163880),a.i(189484),a.i(730699),a.i(519260),a.i(639367),a.i(27886),a.i(799229),a.i(163772),a.i(489874),a.i(913437),a.i(227257),a.i(894810),a.i(201277),a.i(100479),a.i(174222),a.i(570481);var g=b([d,e,f]);[d,e,f]=g.then?(await g)():g,a.s([]),c()}catch(a){c(a)}},!1)];

//# sourceMappingURL=src_1a1pvp-._.js.map