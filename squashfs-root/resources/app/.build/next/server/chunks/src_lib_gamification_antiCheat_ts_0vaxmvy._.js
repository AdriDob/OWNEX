module.exports=[616729,t=>{"use strict";var a=t.i(899378);function e(){return(0,a.getDbInstance)()}async function r(){let t=e().prepare(`SELECT api_key_id, SUM(xp_earned) AS hourly_total
       FROM xp_audit_log
       WHERE created_at > datetime('now', '-1 hour')
       GROUP BY api_key_id
       HAVING hourly_total > 1000`).all(),a=[];for(let e of t){let t=await o(e.api_key_id);a.push({apiKeyId:e.api_key_id,xpLastHour:e.hourly_total,zScore:t??0})}return a}async function o(t){let a=e(),r=a.prepare(`SELECT COALESCE(SUM(xp_earned), 0) AS total
       FROM xp_audit_log
       WHERE api_key_id = ? AND created_at > datetime('now', '-1 hour')`).get(t),o=a.prepare(`SELECT AVG(hourly_total) AS mean,
              CASE WHEN AVG(hourly_total) = 0 THEN 1
                   ELSE AVG(hourly_total * hourly_total) - AVG(hourly_total) * AVG(hourly_total)
              END AS variance
       FROM (
         SELECT api_key_id, SUM(xp_earned) AS hourly_total
         FROM xp_audit_log
         WHERE created_at > datetime('now', '-1 hour')
         GROUP BY api_key_id
       )`).get();if(!o||o.variance<=0)return null;let l=Math.sqrt(o.variance);return(r.total-o.mean)/l}t.s(["getAnomalies",0,r])}];

//# sourceMappingURL=src_lib_gamification_antiCheat_ts_0vaxmvy._.js.map