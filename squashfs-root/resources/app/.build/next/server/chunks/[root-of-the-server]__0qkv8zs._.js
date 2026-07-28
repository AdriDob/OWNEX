module.exports=[130146,(e,t,r)=>{t.exports=e.x("pino-28069d5257187539",()=>require("pino-28069d5257187539"))},918622,(e,t,r)=>{t.exports=e.x("next/dist/compiled/next-server/app-page-turbo.runtime.prod.js",()=>require("next/dist/compiled/next-server/app-page-turbo.runtime.prod.js"))},556704,(e,t,r)=>{t.exports=e.x("next/dist/server/app-render/work-async-storage.external.js",()=>require("next/dist/server/app-render/work-async-storage.external.js"))},832319,(e,t,r)=>{t.exports=e.x("next/dist/server/app-render/work-unit-async-storage.external.js",()=>require("next/dist/server/app-render/work-unit-async-storage.external.js"))},324725,(e,t,r)=>{t.exports=e.x("next/dist/server/app-render/after-task-async-storage.external.js",()=>require("next/dist/server/app-render/after-task-async-storage.external.js"))},270406,(e,t,r)=>{t.exports=e.x("next/dist/compiled/@opentelemetry/api",()=>require("next/dist/compiled/@opentelemetry/api"))},496425,e=>{"use strict";var t=e.i(899378);e.s(["getFallbackStats",0,function(e,r){return(0,t.getDbInstance)().prepare(`
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
      `).all()}])},283041,e=>{"use strict";var t=e.i(747909),r=e.i(174017),s=e.i(996250),a=e.i(759756),n=e.i(561916),o=e.i(174677),i=e.i(869741),l=e.i(316795),u=e.i(487718),c=e.i(995169),d=e.i(47587),p=e.i(666012),E=e.i(570101),m=e.i(626937),_=e.i(10372),v=e.i(193695);e.i(820232);var N=e.i(600220),h=e.i(89171),R=e.i(130146),S=e.i(719201),g=e.i(496425);let A=(0,R.default)({name:"provider-metrics-api"});function C(e){if("number"==typeof e&&Number.isFinite(e))return e;if("string"==typeof e&&e.trim().length>0){let t=Number(e);return Number.isFinite(t)?t:0}return 0}async function b(){try{let e=(0,g.getProviderMetrics)(),t={},r="",s=0,a="",n=0;for(let o of e){let e="string"==typeof o.provider&&o.provider.trim().length>0?o.provider:"unknown",i=C(o.totalRequests),l=C(o.totalSuccesses),u=C(o.avgLatencyMs),c="string"==typeof o.lastRequestAt?o.lastRequestAt:null,d="string"==typeof o.lastErrorAt?o.lastErrorAt:null,p=null==o.lastStatus?null:C(o.lastStatus),E=null==o.lastErrorStatus?null:C(o.lastErrorStatus);t[e]={totalRequests:i,totalSuccesses:l,successRate:i>0?Math.round(l/i*100):0,avgLatencyMs:u,lastRequestAt:c,lastErrorAt:d,lastStatus:p,lastErrorStatus:E};let m=c?Date.parse(c):0;Number.isFinite(m)&&m>s&&(r=e,s=m);let _=null!==p&&(p<200||p>=400)&&d?Date.parse(d):0;Number.isFinite(_)&&_>n&&(a=e,n=_)}return h.NextResponse.json({metrics:t,topology:{providers:Object.keys(t),lastProvider:r,errorProvider:a}})}catch(e){return A.error({err:e},"Failed to load provider metrics"),h.NextResponse.json((0,S.buildErrorBody)(500,"Failed to load provider metrics"),{status:500})}}e.s(["GET",0,b],750015);var f=e.i(750015);let x=new t.AppRouteRouteModule({definition:{kind:r.RouteKind.APP_ROUTE,page:"/api/provider-metrics/route",pathname:"/api/provider-metrics",filename:"route",bundlePath:""},distDir:".build/next",relativeProjectDir:"",resolvedPagePath:"[project]/src/app/api/provider-metrics/route.ts",nextConfigOutput:"standalone",userland:f,...{}}),{workAsyncStorage:O,workUnitAsyncStorage:L,serverHooks:T}=x;async function D(e,t,s){s.requestMeta&&(0,a.setRequestMeta)(e,s.requestMeta),x.isDev&&(0,a.addRequestMeta)(e,"devRequestTimingInternalsEnd",process.hrtime.bigint());let h="/api/provider-metrics/route";h=h.replace(/\/index$/,"")||"/";let R=await x.prepare(e,t,{srcPage:h,multiZoneDraftMode:!1});if(!R)return t.statusCode=400,t.end("Bad Request"),null==s.waitUntil||s.waitUntil.call(s,Promise.resolve()),null;let{buildId:S,deploymentId:g,params:A,nextConfig:C,parsedUrl:b,isDraftMode:f,prerenderManifest:O,routerServerContext:L,isOnDemandRevalidate:T,revalidateOnlyGenerated:D,resolvedPathname:y,clientReferenceManifest:w,serverActionsManifest:k}=R,q=(0,i.normalizeAppPath)(h),U=!!(O.dynamicRoutes[q]||O.routes[y]),H=async()=>((null==L?void 0:L.render404)?await L.render404(e,t,b,!1):t.end("This page could not be found"),null);if(U&&!f){let e=!!O.routes[y],t=O.dynamicRoutes[q];if(t&&!1===t.fallback&&!e){if(C.adapterPath)return await H();throw new v.NoFallbackError}}let I=null;!U||x.isDev||f||(I="/index"===(I=y)?"/":I);let j=!0===x.isDev||!U,M=U&&!j;k&&w&&(0,o.setManifestsSingleton)({page:h,clientReferenceManifest:w,serverActionsManifest:k});let P=e.method||"GET",F=(0,n.getTracer)(),W=F.getActiveScopeSpan(),B=!!(null==L?void 0:L.isWrappedByNextServer),G=!!(0,a.getRequestMeta)(e,"minimalMode"),$=(0,a.getRequestMeta)(e,"incrementalCache")||await x.getIncrementalCache(e,C,O,G);null==$||$.resetRequestCache(),globalThis.__incrementalCache=$;let K={params:A,previewProps:O.preview,renderOpts:{experimental:{authInterrupts:!!C.experimental.authInterrupts},cacheComponents:!!C.cacheComponents,supportsDynamicResponse:j,incrementalCache:$,cacheLifeProfiles:C.cacheLife,waitUntil:s.waitUntil,onClose:e=>{t.on("close",e)},onAfterTaskError:void 0,onInstrumentationRequestError:(t,r,s,a)=>x.onRequestError(e,t,s,a,L)},sharedContext:{buildId:S,deploymentId:g}},Y=new l.NodeNextRequest(e),V=new l.NodeNextResponse(t),X=u.NextRequestAdapter.fromNodeNextRequest(Y,(0,u.signalFromNodeResponse)(t));try{let a,o=async e=>x.handle(X,K).finally(()=>{if(!e)return;e.setAttributes({"http.status_code":t.statusCode,"next.rsc":!1});let r=F.getRootSpanAttributes();if(!r)return;if(r.get("next.span_type")!==c.BaseServerSpan.handleRequest)return void console.warn(`Unexpected root span type '${r.get("next.span_type")}'. Please report this Next.js issue https://github.com/vercel/next.js`);let s=r.get("next.route");if(s){let t=`${P} ${s}`;e.setAttributes({"next.route":s,"http.route":s,"next.span_name":t}),e.updateName(t),a&&a!==e&&(a.setAttribute("http.route",s),a.updateName(t))}else e.updateName(`${P} ${h}`)}),i=async a=>{var n,i;let l=async({previousCacheEntry:r})=>{try{if(!G&&T&&D&&!r)return t.statusCode=404,t.setHeader("x-nextjs-cache","REVALIDATED"),t.end("This page could not be found"),null;let n=await o(a);e.fetchMetrics=K.renderOpts.fetchMetrics;let i=K.renderOpts.pendingWaitUntil;i&&s.waitUntil&&(s.waitUntil(i),i=void 0);let l=K.renderOpts.collectedTags;if(!U)return await (0,p.sendResponse)(Y,V,n,K.renderOpts.pendingWaitUntil),null;{let e=await n.blob(),t=(0,E.toNodeOutgoingHttpHeaders)(n.headers);l&&(t[_.NEXT_CACHE_TAGS_HEADER]=l),!t["content-type"]&&e.type&&(t["content-type"]=e.type);let r=void 0!==K.renderOpts.collectedRevalidate&&!(K.renderOpts.collectedRevalidate>=_.INFINITE_CACHE)&&K.renderOpts.collectedRevalidate,s=void 0===K.renderOpts.collectedExpire||K.renderOpts.collectedExpire>=_.INFINITE_CACHE?void 0:K.renderOpts.collectedExpire;return{value:{kind:N.CachedRouteKind.APP_ROUTE,status:n.status,body:Buffer.from(await e.arrayBuffer()),headers:t},cacheControl:{revalidate:r,expire:s}}}}catch(t){throw(null==r?void 0:r.isStale)&&await x.onRequestError(e,t,{routerKind:"App Router",routePath:h,routeType:"route",revalidateReason:(0,d.getRevalidateReason)({isStaticGeneration:M,isOnDemandRevalidate:T})},!1,L),t}},u=await x.handleResponse({req:e,nextConfig:C,cacheKey:I,routeKind:r.RouteKind.APP_ROUTE,isFallback:!1,prerenderManifest:O,isRoutePPREnabled:!1,isOnDemandRevalidate:T,revalidateOnlyGenerated:D,responseGenerator:l,waitUntil:s.waitUntil,isMinimalMode:G});if(!U)return null;if((null==u||null==(n=u.value)?void 0:n.kind)!==N.CachedRouteKind.APP_ROUTE)throw Object.defineProperty(Error(`Invariant: app-route received invalid cache entry ${null==u||null==(i=u.value)?void 0:i.kind}`),"__NEXT_ERROR_CODE",{value:"E701",enumerable:!1,configurable:!0});G||t.setHeader("x-nextjs-cache",T?"REVALIDATED":u.isMiss?"MISS":u.isStale?"STALE":"HIT"),f&&t.setHeader("Cache-Control","private, no-cache, no-store, max-age=0, must-revalidate");let c=(0,E.fromNodeOutgoingHttpHeaders)(u.value.headers);return G&&U||c.delete(_.NEXT_CACHE_TAGS_HEADER),!u.cacheControl||t.getHeader("Cache-Control")||c.get("Cache-Control")||c.set("Cache-Control",(0,m.getCacheControlHeader)(u.cacheControl)),await (0,p.sendResponse)(Y,V,new Response(u.value.body,{headers:c,status:u.value.status||200})),null};B&&W?await i(W):(a=F.getActiveScopeSpan(),await F.withPropagatedContext(e.headers,()=>F.trace(c.BaseServerSpan.handleRequest,{spanName:`${P} ${h}`,kind:n.SpanKind.SERVER,attributes:{"http.method":P,"http.target":e.url}},i),void 0,!B))}catch(t){if(t instanceof v.NoFallbackError||await x.onRequestError(e,t,{routerKind:"App Router",routePath:q,routeType:"route",revalidateReason:(0,d.getRevalidateReason)({isStaticGeneration:M,isOnDemandRevalidate:T})},!1,L),U)throw t;return await (0,p.sendResponse)(Y,V,new Response(null,{status:500})),null}}e.s(["handler",0,D,"patchFetch",0,function(){return(0,s.patchFetch)({workAsyncStorage:O,workUnitAsyncStorage:L})},"routeModule",0,x,"serverHooks",0,T,"workAsyncStorage",0,O,"workUnitAsyncStorage",0,L],283041)},500929,e=>{e.v(t=>Promise.all(["server/chunks/_0u_-rcv._.js"].map(t=>e.l(t))).then(()=>t(854474)))},606102,e=>{e.v(t=>Promise.all(["server/chunks/[root-of-the-server]__14m_qw3._.js","server/chunks/_19fi1-5._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/src_lib_db_1cebbnr._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/_1ajfw-k._.js","server/chunks/open-sse_1exxloq._.js"].map(t=>e.l(t))).then(()=>t(548941)))},789543,e=>{e.v(t=>Promise.all(["server/chunks/_04bwks4._.js","server/chunks/_19fi1-5._.js","server/chunks/open-sse_config_0brj63s._.js","server/chunks/[root-of-the-server]__1we3fgj._.js","server/chunks/_1ajfw-k._.js","server/chunks/src_shared_1p2xeml._.js","server/chunks/src_lib_db_0pm239y._.js","server/chunks/open-sse_1exxloq._.js","server/chunks/src_lib_db_1k7t86u._.js","server/chunks/src_lib_db_1cebbnr._.js"].map(t=>e.l(t))).then(()=>t(385498)))}];

//# sourceMappingURL=%5Broot-of-the-server%5D__0qkv8zs._.js.map