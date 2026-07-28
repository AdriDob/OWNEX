module.exports=[232485,e=>{"use strict";var t=e.i(254799);e.s(["buildCloudflareWorkerScript",0,function(e){return`// OmniRoute Cloudflare Worker proxy relay — generated at deploy time.
function isPrivateHostname(h) {
  if (!h) return true;
  const host = h.trim().toLowerCase().replace(/^\\[|\\]$/g, "");
  if (
    host === "localhost" ||
    host === "0.0.0.0" ||
    host === "127.0.0.1" ||
    host === "::1" ||
    host.endsWith(".localhost") ||
    host.endsWith(".local") ||
    host.endsWith(".internal") ||
    host.startsWith("::ffff:")
  ) return true;
  const v4 = host.match(/^(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})$/);
  if (v4) {
    const a = +v4[1], b = +v4[2];
    if (a === 0 || a === 10 || a === 127) return true;
    if (a === 169 && b === 254) return true; // link-local IPv4
    if (a === 192 && b === 168) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 100 && b >= 64 && b <= 127) return true;
    return false;
  }
  if (host.includes(":")) {
    // IPv6 loopback/ULA/link-local (fe80::/10)
    return host === "::1" || host.startsWith("fc") || host.startsWith("fd") || host.startsWith("fe80:");
  }
  return false;
}

async function handleRelay(request) {
  const auth = request.headers.get("x-relay-auth");
  if (auth !== "${e}") {
    return new Response("Unauthorized", { status: 401 });
  }
  const target = request.headers.get("x-relay-target");
  if (!target) {
    return new Response("missing x-relay-target", { status: 400 });
  }
  let targetUrl;
  try { targetUrl = new URL(target); } catch { return new Response("invalid x-relay-target", { status: 400 }); }
  if (targetUrl.protocol !== "http:" && targetUrl.protocol !== "https:") {
    return new Response("forbidden x-relay-target protocol", { status: 403 });
  }
  if (targetUrl.username || targetUrl.password) {
    return new Response("forbidden x-relay-target (embedded credentials)", { status: 403 });
  }
  if (isPrivateHostname(targetUrl.hostname)) {
    return new Response("forbidden x-relay-target (private/loopback host)", { status: 403 });
  }
  const relayPath = request.headers.get("x-relay-path") || "/";
  const headers = new Headers(request.headers);
  ["x-relay-target", "x-relay-path", "x-relay-auth", "host"].forEach((h) => headers.delete(h));
  const init = {
    method: request.method,
    headers,
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
    init.duplex = "half";
  }
  try {
    const upstream = await fetch(target.replace(/\\\\/$/, "") + relayPath, init);
    return new Response(upstream.body, {
      status: upstream.status,
      headers: upstream.headers,
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error && error.message ? error.message : "relay error" }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
  }
}

addEventListener("fetch", (event) => {
  event.respondWith(handleRelay(event.request));
});
`},"buildCloudflareWorkerUploadRequest",0,function(e,r){let a=`----OmniRouteCFWorker${(0,t.randomUUID)().replace(/-/g,"")}`,o=[Buffer.from(`--${a}\r
Content-Disposition: form-data; name="index.js"; filename="index.js"\r
Content-Type: application/javascript\r
\r
`),Buffer.from(e,"utf8"),Buffer.from("\r\n"),Buffer.from(`--${a}\r
Content-Disposition: form-data; name="metadata"; filename="metadata.json"\r
Content-Type: application/json\r
\r
${JSON.stringify(r)}\r
`),Buffer.from(`--${a}--\r
`)];return{headers:{"Content-Type":`multipart/form-data; boundary=${a}`},body:Buffer.concat(o)}}])},668427,e=>e.a(async(t,r)=>{try{var a=e.i(254799),o=e.i(15658),n=e.i(858235),s=e.i(200392),i=e.i(860598),l=e.i(245272),u=e.i(33770),d=e.i(507238),c=e.i(232485),p=t([o,i,l]);[o,i,l]=p.then?(await p)():p;let f=process.env.CLOUDFLARE_API_BASE||"https://api.cloudflare.com/client/v4";async function h(e){let t=await (0,o.requireManagementAuth)(e);if(t)return t;let r={};try{r=await e.json()}catch{return(0,n.createErrorResponse)({status:400,message:"Invalid JSON body",type:"invalid_request"})}let l=(0,s.validateBody)(i.cloudflareDeploySchema,r);if((0,s.isValidationFailure)(l))return(0,n.createErrorResponse)({status:400,message:l.error.message,type:"invalid_request"});let{accountId:p,apiToken:h,projectName:y}=l.data,m=(0,a.randomBytes)(24).toString("hex"),g=(0,c.buildCloudflareWorkerScript)(m);try{let e=`${f}/accounts/${p}/workers/scripts/${y}`,{headers:t,body:r}=(0,c.buildCloudflareWorkerUploadRequest)(g,{body_part:"index.js",compatibility_date:"2026-03-20",observability:{enabled:!0}}),a=await fetch(e,{method:"PUT",headers:{Authorization:`Bearer ${h}`,...t},body:r});if(!a.ok){let e="Cloudflare API rejected the Worker upload";try{let t=await a.json().catch(()=>null),r=t?.errors?.[0]?.message;"string"==typeof r&&r.trim()&&(e=r.trim().slice(0,200))}catch{}return(0,n.createErrorResponse)({status:a.status,message:`Cloudflare Worker upload failed: ${e}`,type:"upstream_error"})}await fetch(`${e}/subdomain`,{method:"POST",headers:{Authorization:`Bearer ${h}`,"Content-Type":"application/json"},body:JSON.stringify({enabled:!0})}).catch(()=>{});let o=await fetch(`${f}/accounts/${p}/workers/subdomain`,{method:"GET",headers:{Authorization:`Bearer ${h}`,"Content-Type":"application/json"}}),s="";if(o.ok){let e=await o.json().catch(()=>null),t=e?.result?.subdomain;"string"==typeof t&&t&&(s=`https://${y}.${t}.workers.dev`)}if(!s)return(0,n.createErrorResponse)({status:400,message:"Worker deployed but failed to retrieve workers.dev subdomain. Set up a workers.dev subdomain in the Cloudflare dashboard first.",type:"upstream_error"});let i=(0,d.encrypt)(m),l=i&&i!==m?{relayAuthEnc:i}:{relayAuth:m},R=s.replace(/^https?:\/\//,""),v=await (0,u.createProxy)({name:`Cloudflare Relay (${y})`,type:"cloudflare",host:R,port:443,notes:JSON.stringify(l),source:"cloudflare-relay"});return Response.json({success:!0,relayUrl:s,poolProxyId:v?.id})}catch(e){return(0,n.createErrorResponseFromUnknown)(e,"Cloudflare deploy failed")}}e.s(["POST",0,h]),r()}catch(e){r(e)}},!1),363547,e=>e.a(async(t,r)=>{try{var a=e.i(747909),o=e.i(174017),n=e.i(996250),s=e.i(759756),i=e.i(561916),l=e.i(174677),u=e.i(869741),d=e.i(316795),c=e.i(487718),p=e.i(995169),h=e.i(47587),f=e.i(666012),y=e.i(570101),m=e.i(626937),g=e.i(10372),R=e.i(193695);e.i(820232);var v=e.i(600220),w=e.i(668427),b=t([w]);[w]=b.then?(await b)():b;let x=new a.AppRouteRouteModule({definition:{kind:o.RouteKind.APP_ROUTE,page:"/api/settings/proxy/cloudflare-deploy/route",pathname:"/api/settings/proxy/cloudflare-deploy",filename:"route",bundlePath:""},distDir:".build/next",relativeProjectDir:"",resolvedPagePath:"[project]/src/app/api/settings/proxy/cloudflare-deploy/route.ts",nextConfigOutput:"standalone",userland:w,...{}}),{workAsyncStorage:E,workUnitAsyncStorage:A,serverHooks:P}=x;async function C(e,t,r){r.requestMeta&&(0,s.setRequestMeta)(e,r.requestMeta),x.isDev&&(0,s.addRequestMeta)(e,"devRequestTimingInternalsEnd",process.hrtime.bigint());let a="/api/settings/proxy/cloudflare-deploy/route";a=a.replace(/\/index$/,"")||"/";let n=await x.prepare(e,t,{srcPage:a,multiZoneDraftMode:!1});if(!n)return t.statusCode=400,t.end("Bad Request"),null==r.waitUntil||r.waitUntil.call(r,Promise.resolve()),null;let{buildId:w,deploymentId:b,params:C,nextConfig:E,parsedUrl:A,isDraftMode:P,prerenderManifest:S,routerServerContext:T,isOnDemandRevalidate:k,revalidateOnlyGenerated:U,resolvedPathname:q,clientReferenceManifest:$,serverActionsManifest:O}=n,N=(0,u.normalizeAppPath)(a),_=!!(S.dynamicRoutes[N]||S.routes[q]),I=async()=>((null==T?void 0:T.render404)?await T.render404(e,t,A,!1):t.end("This page could not be found"),null);if(_&&!P){let e=!!S.routes[q],t=S.dynamicRoutes[N];if(t&&!1===t.fallback&&!e){if(E.adapterPath)return await I();throw new R.NoFallbackError}}let j=null;!_||x.isDev||P||(j=q,j="/index"===j?"/":j);let H=!0===x.isDev||!_,W=_&&!H;O&&$&&(0,l.setManifestsSingleton)({page:a,clientReferenceManifest:$,serverActionsManifest:O});let D=e.method||"GET",B=(0,i.getTracer)(),M=B.getActiveScopeSpan(),F=!!(null==T?void 0:T.isWrappedByNextServer),L=!!(0,s.getRequestMeta)(e,"minimalMode"),K=(0,s.getRequestMeta)(e,"incrementalCache")||await x.getIncrementalCache(e,E,S,L);null==K||K.resetRequestCache(),globalThis.__incrementalCache=K;let z={params:C,previewProps:S.preview,renderOpts:{experimental:{authInterrupts:!!E.experimental.authInterrupts},cacheComponents:!!E.cacheComponents,supportsDynamicResponse:H,incrementalCache:K,cacheLifeProfiles:E.cacheLife,waitUntil:r.waitUntil,onClose:e=>{t.on("close",e)},onAfterTaskError:void 0,onInstrumentationRequestError:(t,r,a,o)=>x.onRequestError(e,t,a,o,T)},sharedContext:{buildId:w,deploymentId:b}},G=new d.NodeNextRequest(e),J=new d.NodeNextResponse(t),V=c.NextRequestAdapter.fromNodeNextRequest(G,(0,c.signalFromNodeResponse)(t));try{let n,s=async e=>x.handle(V,z).finally(()=>{if(!e)return;e.setAttributes({"http.status_code":t.statusCode,"next.rsc":!1});let r=B.getRootSpanAttributes();if(!r)return;if(r.get("next.span_type")!==p.BaseServerSpan.handleRequest)return void console.warn(`Unexpected root span type '${r.get("next.span_type")}'. Please report this Next.js issue https://github.com/vercel/next.js`);let o=r.get("next.route");if(o){let t=`${D} ${o}`;e.setAttributes({"next.route":o,"http.route":o,"next.span_name":t}),e.updateName(t),n&&n!==e&&(n.setAttribute("http.route",o),n.updateName(t))}else e.updateName(`${D} ${a}`)}),l=async n=>{var i,l;let u=async({previousCacheEntry:o})=>{try{if(!L&&k&&U&&!o)return t.statusCode=404,t.setHeader("x-nextjs-cache","REVALIDATED"),t.end("This page could not be found"),null;let a=await s(n);e.fetchMetrics=z.renderOpts.fetchMetrics;let i=z.renderOpts.pendingWaitUntil;i&&r.waitUntil&&(r.waitUntil(i),i=void 0);let l=z.renderOpts.collectedTags;if(!_)return await (0,f.sendResponse)(G,J,a,z.renderOpts.pendingWaitUntil),null;{let e=await a.blob(),t=(0,y.toNodeOutgoingHttpHeaders)(a.headers);l&&(t[g.NEXT_CACHE_TAGS_HEADER]=l),!t["content-type"]&&e.type&&(t["content-type"]=e.type);let r=void 0!==z.renderOpts.collectedRevalidate&&!(z.renderOpts.collectedRevalidate>=g.INFINITE_CACHE)&&z.renderOpts.collectedRevalidate,o=void 0===z.renderOpts.collectedExpire||z.renderOpts.collectedExpire>=g.INFINITE_CACHE?void 0:z.renderOpts.collectedExpire;return{value:{kind:v.CachedRouteKind.APP_ROUTE,status:a.status,body:Buffer.from(await e.arrayBuffer()),headers:t},cacheControl:{revalidate:r,expire:o}}}}catch(t){throw(null==o?void 0:o.isStale)&&await x.onRequestError(e,t,{routerKind:"App Router",routePath:a,routeType:"route",revalidateReason:(0,h.getRevalidateReason)({isStaticGeneration:W,isOnDemandRevalidate:k})},!1,T),t}},d=await x.handleResponse({req:e,nextConfig:E,cacheKey:j,routeKind:o.RouteKind.APP_ROUTE,isFallback:!1,prerenderManifest:S,isRoutePPREnabled:!1,isOnDemandRevalidate:k,revalidateOnlyGenerated:U,responseGenerator:u,waitUntil:r.waitUntil,isMinimalMode:L});if(!_)return null;if((null==d||null==(i=d.value)?void 0:i.kind)!==v.CachedRouteKind.APP_ROUTE)throw Object.defineProperty(Error(`Invariant: app-route received invalid cache entry ${null==d||null==(l=d.value)?void 0:l.kind}`),"__NEXT_ERROR_CODE",{value:"E701",enumerable:!1,configurable:!0});L||t.setHeader("x-nextjs-cache",k?"REVALIDATED":d.isMiss?"MISS":d.isStale?"STALE":"HIT"),P&&t.setHeader("Cache-Control","private, no-cache, no-store, max-age=0, must-revalidate");let c=(0,y.fromNodeOutgoingHttpHeaders)(d.value.headers);return L&&_||c.delete(g.NEXT_CACHE_TAGS_HEADER),!d.cacheControl||t.getHeader("Cache-Control")||c.get("Cache-Control")||c.set("Cache-Control",(0,m.getCacheControlHeader)(d.cacheControl)),await (0,f.sendResponse)(G,J,new Response(d.value.body,{headers:c,status:d.value.status||200})),null};F&&M?await l(M):(n=B.getActiveScopeSpan(),await B.withPropagatedContext(e.headers,()=>B.trace(p.BaseServerSpan.handleRequest,{spanName:`${D} ${a}`,kind:i.SpanKind.SERVER,attributes:{"http.method":D,"http.target":e.url}},l),void 0,!F))}catch(t){if(t instanceof R.NoFallbackError||await x.onRequestError(e,t,{routerKind:"App Router",routePath:N,routeType:"route",revalidateReason:(0,h.getRevalidateReason)({isStaticGeneration:W,isOnDemandRevalidate:k})},!1,T),_)throw t;return await (0,f.sendResponse)(G,J,new Response(null,{status:500})),null}}e.s(["handler",0,C,"patchFetch",0,function(){return(0,n.patchFetch)({workAsyncStorage:E,workUnitAsyncStorage:A})},"routeModule",0,x,"serverHooks",0,P,"workAsyncStorage",0,E,"workUnitAsyncStorage",0,A]),r()}catch(e){r(e)}},!1)];

//# sourceMappingURL=_05gd49m._.js.map