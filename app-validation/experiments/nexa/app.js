/* NEXA demo: deterministic goal -> today plan, no backend, no AI calls */
(function(){
  AppAnalytics.init({ experiment: 'nexa', endpoint: 'https://formspree.io/f/REPLACE_ME', debug: false });

  const input = document.getElementById('goal-input');
  const btn = document.getElementById('build-btn');
  const result = document.getElementById('result');
  const emailStep = document.getElementById('email-step');
  const pricingStep = document.getElementById('pricing-step');
  let started = false, currentPlan = null;

  function cat(g){
    g=(g||'').toLowerCase();
    if(/python|program|code|software|job|empleo|trabajo|developer/.test(g)) return 'career';
    if(/ahorr|save|dinero|money|deuda|debt|presupuesto/.test(g)) return 'finance';
    if(/aprender|estud|learn|study|ingles|idioma/.test(g)) return 'learning';
    if(/salud|gym|fitness|peso|health|correr|dormir/.test(g)) return 'health';
    if(/viaj|travel|brasil|vacacion/.test(g)) return 'travel';
    return 'general';
  }
  function planFor(goal){
    const c = cat(goal), short = goal.trim().slice(0,60);
    const base = {
      career: [`Improve 1 proof-of-work item for: ${short}`, 'Apply to 2 real opportunities (15 min)', 'Practice 30 min focused skill work'],
      finance: [`Log today's spending (5 min)`, `Identify $ equivalent avoidable expense for: ${short}`, 'Move fixed amount to separate goal bucket'],
      learning: [`Complete 1 basics lesson for: ${short}`, 'Solve 3 small exercises (20 min)', 'Write 3-line summary of what you learned'],
      health: ['Do 20-min walk or workout', 'Log food/sleep in 2 lines', 'Prep tomorrow healthy default'],
      travel: ['Define budget ceiling + dates', 'List 3 cost levers (flight/stay/food)', 'Book or price 1 leg today'],
      general: [`Define done-state for: ${short}`, 'Do smallest 25-min action now', 'Schedule next action for tomorrow']
    };
    return { category: c, steps: base[c]||base.general, total_time: 35, today_action: (base[c]||base.general)[1] };
  }

  btn.addEventListener('click', ()=>{
    const goal = input.value.trim();
    if(!goal){ input.focus(); return; }
    if(!started){ AppAnalytics.demoStarted(goal); started = true; }
    AppAnalytics.goalCreated(goal);
    currentPlan = planFor(goal);
    AppAnalytics.planGenerated(currentPlan);
    result.classList.remove('hidden');
    result.innerHTML = `<h3>🎯 ${escapeHtml(goal.slice(0,80))}</h3>
      <p><strong>TODAY (~${currentPlan.total_time} min)</strong></p>
      <ul>${currentPlan.steps.map(s=>`<li>${escapeHtml(s)}</li>`).join('')}</ul>
      <button id="do-btn" class="primary">I'm doing this</button>`;
    result.scrollIntoView({behavior:'smooth', block:'center'});
    document.getElementById('do-btn').addEventListener('click', ()=>{
      AppAnalytics.planSaved(currentPlan);
      emailStep.classList.remove('hidden');
      pricingStep.classList.remove('hidden');
      emailStep.scrollIntoView({behavior:'smooth', block:'center'});
    });
  });

  document.getElementById('email-form').addEventListener('submit', async (e)=>{
    e.preventDefault();
    const email = document.getElementById('email-input').value.trim();
    if(!email) return;
    await AppAnalytics.submitEmail(email, 'demo_save', { plan: currentPlan });
    document.getElementById('email-ok').classList.remove('hidden');
  });
  document.querySelectorAll('[data-intent]').forEach(b=>b.addEventListener('click', ()=>{
    AppAnalytics.priceIntent('nexa', b.dataset.intent);
    document.getElementById('price-thanks').classList.remove('hidden');
  }));
  document.getElementById('footer-email').addEventListener('submit', async (e)=>{
    e.preventDefault();
    const em = e.target.querySelector('input').value.trim();
    if(!em) return;
    await AppAnalytics.submitEmail(em, 'footer', {});
    e.target.innerHTML = '<p class="ok">On the list.</p>';
  });

  function escapeHtml(s){ return s.replace(/[&<>"']/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
})();
