module.exports=[486095,e=>{"use strict";var t=e.i(233405),r=e.i(522734),o=e.i(446786),n=e.i(814747),i=e.i(254799);function s(e){return e instanceof Error?e.message:String(e)}function c(){try{return!!(process.getuid&&0===process.getuid())}catch{return!1}}function d(e,r){return new Promise((o,n)=>{(0,t.execFile)(e,r,{encoding:"utf8"},(e,t,r)=>{e?n(Error(s(e)+(r?`
${r}`:""))):o(t)})})}function u(e){return`'${e.replace(/'/g,"''")}'`}async function a(e){let t=r.default.mkdtempSync(n.default.join(o.default.tmpdir(),"omniroute-elevate-")),s=`omniroute-elevate-${i.default.randomUUID()}.ps1`,c=n.default.join(t,s);r.default.writeFileSync(c,e,{encoding:"utf8",mode:384});try{var a;return await (a=`
    $proc = Start-Process powershell -ArgumentList @(
      '-NoProfile',
      '-NonInteractive',
      '-ExecutionPolicy',
      'Bypass',
      '-File',
      ${u(c)}
    ) -Verb RunAs -Wait -PassThru;
    if ($proc.ExitCode -ne 0) {
      throw "Elevated command exited with code $($proc.ExitCode)"
    }
  `,d("powershell",["-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-Command",a]))}finally{try{r.default.rmSync(t,{recursive:!0,force:!0})}catch{}}}e.s(["execFileText",0,d,"execFileWithPassword",0,function(e,r,o,n=""){let{finalCommand:i,finalArgs:d,needsPassword:u}=function(e,r,o={}){let n,i=o.root??c(),s=o.sudoAvailable??function(){try{return(0,t.execFileSync)("sh",["-c","command -v sudo"],{stdio:"ignore"}),!0}catch{return!1}}(),d=o.noSudo??("string"==typeof(n=process.env.OMNIROUTE_NO_SUDO)&&/^(1|true|yes|on)$/i.test(n.trim())),u="sudo"===e&&(i||!s||d),a=e,l=r;if(u){let e=r.findIndex(e=>!e.startsWith("-"));-1!==e&&(a=r[e],l=r.slice(e+1))}return{finalCommand:a,finalArgs:l,stripSudo:u,needsPassword:!u&&"sudo"===e}}(e,r);return new Promise((e,r)=>{let c=(0,t.spawn)(i,d,{stdio:["pipe","pipe","pipe"]}),a="",l="",f=!1,m=t=>{if(!f){if(f=!0,t)return void r(t);e(a)}};c.stdout?.on("data",e=>{a+=e.toString()}),c.stderr?.on("data",e=>{l+=e.toString()}),c.on("error",e=>{m(Error(`Command failed: ${s(e)}
${l}`))}),c.on("close",e=>{0===e?m(null):m(Error(`Command failed with code ${e}
${l}`))});let p=u?`${o}
${n}`:n||"";p&&c.stdin?.write(p),c.stdin?.end()})},"getErrorMessage",0,s,"isRoot",0,c,"quotePowerShell",0,u,"runElevatedPowerShell",0,a])}];

//# sourceMappingURL=src_mitm_systemCommands_ts_1p5yvvb._.js.map