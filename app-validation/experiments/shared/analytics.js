/**
 * Shared Analytics Module for NEXA/FOCUS Validation Experiments
 * Tracks 7 core metrics + email signup + return visit
 * Privacy-first: no PII, localStorage for return visit, configurable endpoint
 */

(function() {
  'use strict';

  const CONFIG = {
    experiment: 'nexa', // overridden per landing
    endpoint: 'https://your-formspree-endpoint.formspree.io/analytics', // replace
    debug: true,
    sessionTimeout: 30 * 60 * 1000, // 30 min
  };

  const STATE = {
    sessionId: null,
    isReturnVisitor: false,
    eventsSent: new Set(),
  };

  // ---- Utilities ----

  function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  function getSessionId() {
    let sid = sessionStorage.getItem('av_session_id');
    if (!sid) {
      sid = generateId();
      sessionStorage.setItem('av_session_id', sid);
    }
    return sid;
  }

  function isReturnVisitor() {
    const lastVisit = localStorage.getItem('av_last_visit');
    const now = Date.now();
    if (lastVisit && (now - parseInt(lastVisit, 10)) < CONFIG.sessionTimeout) {
      return true;
    }
    localStorage.setItem('av_last_visit', now.toString());
    return false;
  }

  function getBasePayload() {
    return {
      experiment: CONFIG.experiment,
      session_id: getSessionId(),
      timestamp: new Date().toISOString(),
      url: window.location.href,
      referrer: document.referrer || 'direct',
      user_agent: navigator.userAgent,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      is_return_visitor: STATE.isReturnVisitor,
    };
  }

  function log(...args) {
    if (CONFIG.debug) console.log('[Analytics]', ...args);
  }

  // ---- Core Event Tracking ----

  async function track(eventName, properties = {}) {
    const eventKey = `${eventName}:${JSON.stringify(properties)}`;
    if (STATE.eventsSent.has(eventKey)) return; // dedupe per session
    STATE.eventsSent.add(eventKey);

    const payload = {
      ...getBasePayload(),
      event: eventName,
      properties,
    };

    log('track', eventName, properties);

    try {
      await fetch(CONFIG.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true,
      });
    } catch (e) {
      log('track failed', e);
      // queue for retry could be added here
    }
  }

  // ---- 7 Core Metrics + Extras ----

  function trackLandingView() {
    track('landing_view', {
      hero_visible: true,
      cta_visible: true,
    });
  }

  function trackDemoStarted(inputValue) {
    track('demo_started', {
      input_length: inputValue?.length || 0,
      input_type: detectInputType(inputValue),
    });
  }

  function trackGoalCreated(goalText) {
    track('goal_created', {
      goal_length: goalText?.length || 0,
      goal_category: categorizeGoal(goalText),
    });
  }

  function trackPlanGenerated(planData) {
    track('plan_generated', {
      steps_count: planData?.steps?.length || 0,
      estimated_time: planData?.total_time || 0,
      has_today_action: !!planData?.today_action,
    });
  }

  function trackPlanSaved(planData) {
    track('plan_saved', {
      steps_count: planData?.steps?.length || 0,
      has_today_action: !!planData?.today_action,
    });
  }

  function trackReturnVisit() {
    if (STATE.isReturnVisitor) {
      track('return_visit', {
        days_since_last: calculateDaysSinceLastVisit(),
      });
    }
  }

  function trackPriceIntent(plan, action) {
    track('price_intent', {
      plan,
      action, // 'clicked_pro' | 'clicked_notify' | 'clicked_not_interested'
      price_monthly: getPrice(plan, 'monthly'),
      price_yearly: getPrice(plan, 'yearly'),
      price_lifetime: getPrice(plan, 'lifetime'),
    });
  }

  function trackEmailSignup(source) {
    track('email_signup', {
      source, // 'demo_save' | 'price_intent' | 'footer' | 'exit_intent'
    });
  }

  // ---- Helpers ----

  function detectInputType(input) {
    if (!input) return 'empty';
    const lower = input.toLowerCase();
    if (lower.includes('aprender') || lower.includes('estudiar') || lower.includes('learn') || lower.includes('study')) return 'learning';
    if (lower.includes('ahorrar') || lower.includes('save') || lower.includes('dinero') || lower.includes('money')) return 'finance';
    if (lower.includes('trabajo') || lower.includes('job') || lower.includes('empleo') || lower.includes('carrera')) return 'career';
    if (lower.includes('salud') || lower.includes('fitness') || lower.includes('ejercicio') || lower.includes('health')) return 'health';
    if (lower.includes('viajar') || lower.includes('travel') || lower.includes('vacaciones')) return 'travel';
    return 'other';
  }

  function categorizeGoal(goal) {
    return detectInputType(goal);
  }

  function calculateDaysSinceLastVisit() {
    const lastVisit = localStorage.getItem('av_last_visit');
    if (!lastVisit) return null;
    const diff = Date.now() - parseInt(lastVisit, 10);
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  }

  function getPrice(experiment, period) {
    const prices = {
      nexa: { monthly: 3.99, yearly: 39.99, lifetime: 79.99 },
      focus: { monthly: 4.99, yearly: 49.99, lifetime: 99.00 },
    };
    return prices[experiment]?.[period] || 0;
  }

  // ---- Form Handler ----

  async function submitEmail(email, source, metadata = {}) {
    const payload = {
      ...getBasePayload(),
      event: 'email_signup',
      email,
      source,
      metadata,
    };

    try {
      const res = await fetch(CONFIG.endpoint.replace('/analytics', '/email'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        trackEmailSignup(source);
        return { success: true };
      }
      return { success: false, error: 'Submission failed' };
    } catch (e) {
      log('email submit failed', e);
      return { success: false, error: e.message };
    }
  }

  // ---- Public API ----

  window.AppAnalytics = {
    init: function(options) {
      Object.assign(CONFIG, options);
      STATE.sessionId = getSessionId();
      STATE.isReturnVisitor = isReturnVisitor();
      trackLandingView();
      trackReturnVisit();
      log('initialized', CONFIG.experiment, { sessionId: STATE.sessionId, returnVisitor: STATE.isReturnVisitor });
    },

    // Core funnel
    demoStarted: (input) => trackDemoStarted(input),
    goalCreated: (goal) => trackGoalCreated(goal),
    planGenerated: (plan) => trackPlanGenerated(plan),
    planSaved: (plan) => trackPlanSaved(plan),

    // Monetization
    priceIntent: (plan, action) => trackPriceIntent(plan, action),

    // Email
    submitEmail,

    // Utility
    track: (name, props) => track(name, props),
  };
})();