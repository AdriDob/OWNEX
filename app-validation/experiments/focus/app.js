/* FOCUS demo: capture -> prioritize (max 3) -> time/energy -> next */
(function(){
  AppAnalytics.init({ experiment: 'focus', endpoint: 'https://formspree.io/f/REPLACE_ME', debug: false });
  const input=document.getElementById('tasks-input'), btn=document.getElementById('plan-btn'),
    result=document.getElementById('result'), emailStep=document.getElementById('email-step'),
    pricing=document.getElementById('pricing-step');
  let started=false, cur=null;

  function splitTasks(s){
    return s.split(/[,;\n]+| y | and /i).map(t=>t.trim()).filter(Boolean).slice(0,6);
  }
  function prio(t){
    t=t.toLowerCase();
    if(/trabaj|work|job|client|reunion|meeting|entrega/.test(t)) return {level:'🔴',label:'High energy',slot:'09:00–11:00',min:25};
    if(/estud|study|learn|curso|examen|leer|python/.test(t)) return {level:'🟡',label:'Medium energy',slot:'11:30–12:00',min:25};
    return {level:'🟢',label:'Low energy',slot:'17:00–17:15',min:15};
  }
  btn.addEventListener('click', ()=>{
    const raw=input.value.trim(); if(!raw){input.focus();return;}
    if(!started){AppAnalytics.demoStarted(raw);started=true;}
    AppAnalytics.goalCreated(raw);
    const tasks=splitTasks(raw).slice(0,3).map((t,i)=>({text:t,...prio(t),order:i+1}));
    cur={steps:tasks,total_time:tasks.reduce((a,b)=>a+b.min,0),today_action:tasks[0]?.text||''};
    AppAnalytics.planGenerated(cur);
    result.classList.remove('hidden');
    result.innerHTML=`<h3>TODAY — max 3</h3>`+tasks.map(t=>`<div class="task">${t.order}. ${t.level} ${escapeHtml(t.text)}<br><small>${t.slot} · ${t.label} · ${t.min} min</small></div>`).join('')+
      (tasks[0]?`<div class="next"><strong>NEXT:</strong> → ${escapeHtml(tasks[0].text)} for ${tasks[0].min} minutes<br><button id="start-btn" class="primary">Start focus</button></div>`:'');
    result.scrollIntoView({behavior:'smooth',block:'center'});
    const sb=document.getElementById('start-btn');
    if(sb) sb.addEventListener('click', ()=>{
      AppAnalytics.planSaved(cur);
      emailStep.classList.remove('hidden'); pricing.classList.remove('hidden');
      emailStep.scrollIntoView({behavior:'smooth',block:'center'});
    });
  });
  document.getElementById('email-form').addEventListener('submit', async e=>{
    e.preventDefault();
    const em=document.getElementById('email-input').value.trim(); if(!em) return;
    await AppAnalytics.submitEmail(em,'demo_save',{plan:cur});
    document.getElementById('email-ok').classList.remove('hidden');
  });
  document.querySelectorAll('[data-intent]').forEach(b=>b.addEventListener('click', ()=>{
    AppAnalytics.priceIntent('focus',b.dataset.intent);
    document.getElementById('price-thanks').classList.remove('hidden');
  }));
  document.getElementById('footer-email').addEventListener('submit', async e=>{
    e.preventDefault(); const em=e.target.querySelector('input').value.trim(); if(!em) return;
    await AppAnalytics.submitEmail(em,'footer',{}); e.target.innerHTML='<p class="ok">On the list.</p>';
  });
  function escapeHtml(s){return s.replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
})();
