module.exports=[766511,e=>e.a(async(t,r)=>{try{var a=e.i(254799),n=e.i(15658),s=e.i(858235),o=e.i(200392),i=e.i(860598),l=e.i(245272),u=e.i(33770),d=e.i(507238),c=e.i(51903),p=t([n,i,l,c]);[n,i,l,c]=p.then?(await p)():p;let R=process.env.VERCEL_API_BASE||"https://api.vercel.com";function h(e){return`export const config = { runtime: "edge" };

const resolveRelayTarget = ${c.resolveRelayTarget.toString()};

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
    if (a === 169 && b === 254) return true;
    if (a === 192 && b === 168) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 100 && b >= 64 && b <= 127) return true;
    return false;
  }
  if (host.includes(":")) {
    return host === "::1" || host.startsWith("fc") || host.startsWith("fd") || host.startsWith("fe80:");
  }
  return false;
}

export default async function handler(req) {
  const auth = req.headers.get("x-relay-auth");
  if (auth !== "${e}") return new Response("Unauthorized", { status: 401 });
  const target = req.headers.get("x-relay-target");
  if (!target) return new Response("missing x-relay-target", { status: 400 });
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
  const relayPath = req.headers.get("x-relay-path") || "/";
  const resolved = resolveRelayTarget(target, relayPath);
  if (!resolved.ok) {
    return new Response(resolved.reason, { status: resolved.status });
  }
  const headers = new Headers(req.headers);
  ["x-relay-target", "x-relay-path", "x-relay-auth", "host"].forEach(h => headers.delete(h));
  const upstream = await fetch(resolved.url, {
    method: req.method,
    headers,
    body: req.method !== "GET" && req.method !== "HEAD" ? req.body : undefined,
    duplex: "half",
  });
  return new Response(upstream.body, { status: upstream.status, headers: upstream.headers });
}`}async function y(e,t){for(let r=0;r<40;r++){await new Promise(e=>setTimeout(e,3e3));try{let r=await fetch(e,{headers:{Authorization:`Bearer ${t}`}});if(!r.ok)continue;let a=await r.json();if("READY"===a.readyState)return"READY";if("ERROR"===a.readyState)break}catch{}}return"ERROR"}async function f(e){let t=await (0,n.requireManagementAuth)(e);if(t)return t;let r={};try{r=await e.json()}catch{return(0,s.createErrorResponse)({status:400,message:"Invalid JSON body",type:"invalid_request"})}let l=(0,o.validateBody)(i.vercelDeploySchema,r);if((0,o.isValidationFailure)(l))return(0,s.createErrorResponse)({status:400,message:l.error.message,type:"invalid_request"});let{token:c,projectName:p}=l.data,f=(0,a.randomBytes)(24).toString("hex"),g=h(f);try{let e=await fetch(`${R}/v13/deployments`,{method:"POST",headers:{Authorization:`Bearer ${c}`,"Content-Type":"application/json"},body:JSON.stringify({name:p,files:[{file:"api/relay.js",data:g},{file:"package.json",data:JSON.stringify({name:p,version:"1.0.0"})},{file:"vercel.json",data:JSON.stringify({rewrites:[{source:"/(.*)",destination:"/api/relay"}]})}],projectSettings:{framework:null},target:"production"})});if(!e.ok){let t="Vercel API rejected the deployment";try{let r=await e.json().catch(()=>null),a=r?.error?.message;"string"==typeof a&&a.trim()&&(t=a.trim().slice(0,200))}catch{}return(0,s.createErrorResponse)({status:e.status,message:`Vercel deployment failed: ${t}`,type:"upstream_error"})}let t=await e.json();if(!t.url)return(0,s.createErrorResponse)({status:502,message:"Vercel returned no deployment URL",type:"upstream_error"});t.projectId&&await fetch(`${R}/v9/projects/${t.projectId}`,{method:"PATCH",headers:{Authorization:`Bearer ${c}`,"Content-Type":"application/json"},body:JSON.stringify({ssoProtection:null})}).catch(()=>{});let r=`${R}/v13/deployments/${t.id}`,a=await y(r,c);if("READY"!==a)return(0,s.createErrorResponse)({status:504,message:"Deployment did not reach READY state within 2 minutes. Check your Vercel dashboard.",type:"timeout"});let n=(0,d.encrypt)(f),o=n&&n!==f?{relayAuthEnc:n}:{relayAuth:f},i=await (0,u.createProxy)({name:`Vercel Relay (${p})`,type:"vercel",host:t.url,port:443,notes:JSON.stringify(o),source:"vercel-relay"});return Response.json({success:!0,relayUrl:`https://${t.url}`,poolProxyId:i?.id})}catch(e){return(0,s.createErrorResponseFromUnknown)(e,"Vercel deploy failed")}}e.s(["POST",0,f,"__buildRelayFunctionForTest",0,h]),r()}catch(e){r(e)}},!1),339261,e=>e.a(async(t,r)=>{try{var a=e.i(747909),n=e.i(174017),s=e.i(996250),o=e.i(759756),i=e.i(561916),l=e.i(174677),u=e.i(869741),d=e.i(316795),c=e.i(487718),p=e.i(995169),h=e.i(47587),y=e.i(666012),f=e.i(570101),R=e.i(626937),g=e.i(10372),v=e.i(193695);e.i(820232);var m=e.i(600220),w=e.i(766511),E=t([w]);[w]=E.then?(await E)():E;let b=new a.AppRouteRouteModule({definition:{kind:n.RouteKind.APP_ROUTE,page:"/api/settings/proxy/vercel-deploy/route",pathname:"/api/settings/proxy/vercel-deploy",filename:"route",bundlePath:""},distDir:".build/next",relativeProjectDir:"",resolvedPagePath:"[project]/src/app/api/settings/proxy/vercel-deploy/route.ts",nextConfigOutput:"standalone",userland:w,...{}}),{workAsyncStorage:A,workUnitAsyncStorage:C,serverHooks:P}=b;async function x(e,t,r){r.requestMeta&&(0,o.setRequestMeta)(e,r.requestMeta),b.isDev&&(0,o.addRequestMeta)(e,"devRequestTimingInternalsEnd",process.hrtime.bigint());let a="/api/settings/proxy/vercel-deploy/route";a=a.replace(/\/index$/,"")||"/";let s=await b.prepare(e,t,{srcPage:a,multiZoneDraftMode:!1});if(!s)return t.statusCode=400,t.end("Bad Request"),null==r.waitUntil||r.waitUntil.call(r,Promise.resolve()),null;let{buildId:w,deploymentId:E,params:x,nextConfig:A,parsedUrl:C,isDraftMode:P,prerenderManifest:S,routerServerContext:T,isOnDemandRevalidate:N,revalidateOnlyGenerated:O,resolvedPathname:q,clientReferenceManifest:_,serverActionsManifest:U}=s,$=(0,u.normalizeAppPath)(a),j=!!(S.dynamicRoutes[$]||S.routes[q]),k=async()=>((null==T?void 0:T.render404)?await T.render404(e,t,C,!1):t.end("This page could not be found"),null);if(j&&!P){let e=!!S.routes[q],t=S.dynamicRoutes[$];if(t&&!1===t.fallback&&!e){if(A.adapterPath)return await k();throw new v.NoFallbackError}}let H=null;!j||b.isDev||P||(H=q,H="/index"===H?"/":H);let I=!0===b.isDev||!j,D=j&&!I;U&&_&&(0,l.setManifestsSingleton)({page:a,clientReferenceManifest:_,serverActionsManifest:U});let M=e.method||"GET",B=(0,i.getTracer)(),F=B.getActiveScopeSpan(),V=!!(null==T?void 0:T.isWrappedByNextServer),W=!!(0,o.getRequestMeta)(e,"minimalMode"),L=(0,o.getRequestMeta)(e,"incrementalCache")||await b.getIncrementalCache(e,A,S,W);null==L||L.resetRequestCache(),globalThis.__incrementalCache=L;let K={params:x,previewProps:S.preview,renderOpts:{experimental:{authInterrupts:!!A.experimental.authInterrupts},cacheComponents:!!A.cacheComponents,supportsDynamicResponse:I,incrementalCache:L,cacheLifeProfiles:A.cacheLife,waitUntil:r.waitUntil,onClose:e=>{t.on("close",e)},onAfterTaskError:void 0,onInstrumentationRequestError:(t,r,a,n)=>b.onRequestError(e,t,a,n,T)},sharedContext:{buildId:w,deploymentId:E}},J=new d.NodeNextRequest(e),z=new d.NodeNextResponse(t),G=c.NextRequestAdapter.fromNodeNextRequest(J,(0,c.signalFromNodeResponse)(t));try{let s,o=async e=>b.handle(G,K).finally(()=>{if(!e)return;e.setAttributes({"http.status_code":t.statusCode,"next.rsc":!1});let r=B.getRootSpanAttributes();if(!r)return;if(r.get("next.span_type")!==p.BaseServerSpan.handleRequest)return void console.warn(`Unexpected root span type '${r.get("next.span_type")}'. Please report this Next.js issue https://github.com/vercel/next.js`);let n=r.get("next.route");if(n){let t=`${M} ${n}`;e.setAttributes({"next.route":n,"http.route":n,"next.span_name":t}),e.updateName(t),s&&s!==e&&(s.setAttribute("http.route",n),s.updateName(t))}else e.updateName(`${M} ${a}`)}),l=async s=>{var i,l;let u=async({previousCacheEntry:n})=>{try{if(!W&&N&&O&&!n)return t.statusCode=404,t.setHeader("x-nextjs-cache","REVALIDATED"),t.end("This page could not be found"),null;let a=await o(s);e.fetchMetrics=K.renderOpts.fetchMetrics;let i=K.renderOpts.pendingWaitUntil;i&&r.waitUntil&&(r.waitUntil(i),i=void 0);let l=K.renderOpts.collectedTags;if(!j)return await (0,y.sendResponse)(J,z,a,K.renderOpts.pendingWaitUntil),null;{let e=await a.blob(),t=(0,f.toNodeOutgoingHttpHeaders)(a.headers);l&&(t[g.NEXT_CACHE_TAGS_HEADER]=l),!t["content-type"]&&e.type&&(t["content-type"]=e.type);let r=void 0!==K.renderOpts.collectedRevalidate&&!(K.renderOpts.collectedRevalidate>=g.INFINITE_CACHE)&&K.renderOpts.collectedRevalidate,n=void 0===K.renderOpts.collectedExpire||K.renderOpts.collectedExpire>=g.INFINITE_CACHE?void 0:K.renderOpts.collectedExpire;return{value:{kind:m.CachedRouteKind.APP_ROUTE,status:a.status,body:Buffer.from(await e.arrayBuffer()),headers:t},cacheControl:{revalidate:r,expire:n}}}}catch(t){throw(null==n?void 0:n.isStale)&&await b.onRequestError(e,t,{routerKind:"App Router",routePath:a,routeType:"route",revalidateReason:(0,h.getRevalidateReason)({isStaticGeneration:D,isOnDemandRevalidate:N})},!1,T),t}},d=await b.handleResponse({req:e,nextConfig:A,cacheKey:H,routeKind:n.RouteKind.APP_ROUTE,isFallback:!1,prerenderManifest:S,isRoutePPREnabled:!1,isOnDemandRevalidate:N,revalidateOnlyGenerated:O,responseGenerator:u,waitUntil:r.waitUntil,isMinimalMode:W});if(!j)return null;if((null==d||null==(i=d.value)?void 0:i.kind)!==m.CachedRouteKind.APP_ROUTE)throw Object.defineProperty(Error(`Invariant: app-route received invalid cache entry ${null==d||null==(l=d.value)?void 0:l.kind}`),"__NEXT_ERROR_CODE",{value:"E701",enumerable:!1,configurable:!0});W||t.setHeader("x-nextjs-cache",N?"REVALIDATED":d.isMiss?"MISS":d.isStale?"STALE":"HIT"),P&&t.setHeader("Cache-Control","private, no-cache, no-store, max-age=0, must-revalidate");let c=(0,f.fromNodeOutgoingHttpHeaders)(d.value.headers);return W&&j||c.delete(g.NEXT_CACHE_TAGS_HEADER),!d.cacheControl||t.getHeader("Cache-Control")||c.get("Cache-Control")||c.set("Cache-Control",(0,R.getCacheControlHeader)(d.cacheControl)),await (0,y.sendResponse)(J,z,new Response(d.value.body,{headers:c,status:d.value.status||200})),null};V&&F?await l(F):(s=B.getActiveScopeSpan(),await B.withPropagatedContext(e.headers,()=>B.trace(p.BaseServerSpan.handleRequest,{spanName:`${M} ${a}`,kind:i.SpanKind.SERVER,attributes:{"http.method":M,"http.target":e.url}},l),void 0,!V))}catch(t){if(t instanceof v.NoFallbackError||await b.onRequestError(e,t,{routerKind:"App Router",routePath:$,routeType:"route",revalidateReason:(0,h.getRevalidateReason)({isStaticGeneration:D,isOnDemandRevalidate:N})},!1,T),j)throw t;return await (0,y.sendResponse)(J,z,new Response(null,{status:500})),null}}e.s(["handler",0,x,"patchFetch",0,function(){return(0,s.patchFetch)({workAsyncStorage:A,workUnitAsyncStorage:C})},"routeModule",0,b,"serverHooks",0,P,"workAsyncStorage",0,A,"workUnitAsyncStorage",0,C]),r()}catch(e){r(e)}},!1)];

//# sourceMappingURL=_0vqhoqi._.js.map