module.exports=[112110,e=>{"use strict";let t=new Map;e.s(["createBadgeNotificationStream",0,function(e,a){return new ReadableStream({start(n){let l=new TextEncoder,r=!1,d=e=>{if(!r)try{n.enqueue(e)}catch{r=!0,clearInterval(o),clearInterval(c)}},o=setInterval(()=>{let a;for(let n of(a=t.get(e)||[],t.delete(e),a.map(e=>e.event)))d(l.encode(`event: badge_unlock
data: ${JSON.stringify(n)}

`))},2e3),c=setInterval(()=>{d(l.encode(`: heartbeat ${Date.now()}

`))},15e3);a&&a.addEventListener("abort",()=>{r=!0,clearInterval(o),clearInterval(c);try{n.close()}catch{}})}})},"recordBadgeUnlock",0,function(e,a){t.has(e)||t.set(e,[]);let n=t.get(e);n.push({event:a,addedAt:Date.now()});let l=Date.now()-6e4;for(;n.length>0&&n[0].addedAt<l;)n.shift();n.length>50&&n.splice(0,n.length-50);let r=Date.now()-12e4;for(let[e,a]of t){let n=a.filter(e=>e.addedAt>=r);0===n.length?t.delete(e):n.length!==a.length&&t.set(e,n)}}])}];

//# sourceMappingURL=src_lib_gamification_notifications_ts_0chzh4j._.js.map