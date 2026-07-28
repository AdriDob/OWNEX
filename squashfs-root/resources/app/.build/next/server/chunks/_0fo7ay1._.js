module.exports=[95638,684076,730901,e=>{"use strict";let t=new Uint8Array(16);e.s(["default",0,function(){return crypto.getRandomValues(t)}],95638);let o=/^(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/i;e.s(["default",0,function(e){return"string"==typeof e&&o.test(e)}],684076);let r=[];for(let e=0;e<256;++e)r.push((e+256).toString(16).slice(1));e.s(["unsafeStringify",0,function(e,t=0){return(r[e[t+0]]+r[e[t+1]]+r[e[t+2]]+r[e[t+3]]+"-"+r[e[t+4]]+r[e[t+5]]+"-"+r[e[t+6]]+r[e[t+7]]+"-"+r[e[t+8]]+r[e[t+9]]+"-"+r[e[t+10]]+r[e[t+11]]+r[e[t+12]]+r[e[t+13]]+r[e[t+14]]+r[e[t+15]]).toLowerCase()}],730901)},689960,e=>{"use strict";var t=e.i(95638),o=e.i(730901);e.s(["v4",0,function(e,r,n){return r||e||!crypto.randomUUID?function(e,r,n){let a=(e=e||{}).random??e.rng?.()??(0,t.default)();if(a.length<16)throw Error("Random bytes length must be >= 16");if(a[6]=15&a[6]|64,a[8]=63&a[8]|128,r){if((n=n||0)<0||n+16>r.length)throw RangeError(`UUID byte range ${n}:${n+15} is out of buffer bounds`);for(let e=0;e<16;++e)r[n+e]=a[e];return r}return(0,o.unsafeStringify)(a)}(e,r,n):crypto.randomUUID()}],689960)},68392,e=>{"use strict";var t=e.i(689960),o=e.i(899378);function r(e){return{id:e.id,pattern:e.pattern,comboId:e.combo_id,comboName:e.combo_name||void 0,priority:e.priority,enabled:1===e.enabled,description:e.description||"",createdAt:e.created_at,updatedAt:e.updated_at}}async function n(){return(0,o.getDbInstance)().prepare(`SELECT m.id, m.pattern, m.combo_id, c.name AS combo_name,
              m.priority, m.enabled, m.description,
              m.created_at, m.updated_at
       FROM model_combo_mappings m
       LEFT JOIN combos c ON c.id = m.combo_id
       ORDER BY m.priority DESC, m.created_at ASC`).all().map(r)}async function a(e){let t=(0,o.getDbInstance)().prepare(`SELECT m.id, m.pattern, m.combo_id, c.name AS combo_name,
              m.priority, m.enabled, m.description,
              m.created_at, m.updated_at
       FROM model_combo_mappings m
       LEFT JOIN combos c ON c.id = m.combo_id
       WHERE m.id = ?`).get(e);return t?r(t):null}async function i(e){let r=(0,o.getDbInstance)(),n=new Date().toISOString(),a=(0,t.v4)();return r.prepare(`INSERT INTO model_combo_mappings
     (id, pattern, combo_id, priority, enabled, description, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`).run(a,e.pattern,e.comboId,e.priority??0,+(!1!==e.enabled),e.description||"",n,n),{id:a,pattern:e.pattern,comboId:e.comboId,priority:e.priority??0,enabled:!1!==e.enabled,description:e.description||"",createdAt:n,updatedAt:n}}async function d(e,t){let r=await a(e);if(!r)return null;let n=(0,o.getDbInstance)(),i=new Date().toISOString(),d={pattern:t.pattern??r.pattern,combo_id:t.comboId??r.comboId,priority:t.priority??r.priority,enabled:void 0!==t.enabled?+!!t.enabled:+!!r.enabled,description:t.description??r.description};return n.prepare(`UPDATE model_combo_mappings
     SET pattern = ?, combo_id = ?, priority = ?, enabled = ?,
         description = ?, updated_at = ?
     WHERE id = ?`).run(d.pattern,d.combo_id,d.priority,d.enabled,d.description,i,e),a(e)}async function c(e){return((0,o.getDbInstance)().prepare("DELETE FROM model_combo_mappings WHERE id = ?").run(e).changes??0)>0}async function p(e){for(let t of(0,o.getDbInstance)().prepare(`SELECT m.pattern, m.combo_id, c.data AS combo_data
       FROM model_combo_mappings m
       JOIN combos c ON c.id = m.combo_id
       WHERE m.enabled = 1
       ORDER BY m.priority DESC, m.created_at ASC`).all())if((function(e){let t=e.replace(/[.+^${}()|[\]\\]/g,"\\$&").replace(/\*/g,".*").replace(/\?/g,".");return RegExp(`^${t}$`,"i")})(t.pattern).test(e))try{let e=JSON.parse(t.combo_data);if(!1===e.isActive)continue;return e}catch{continue}return null}e.s(["createModelComboMapping",0,i,"deleteModelComboMapping",0,c,"getModelComboMappingById",0,a,"getModelComboMappings",0,n,"resolveComboForModel",0,p,"updateModelComboMapping",0,d])}];

//# sourceMappingURL=_0fo7ay1._.js.map