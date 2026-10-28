# App Validation — NEXA vs FOCUS

Experimento comercial, no desarrollo de producto. Objetivo: evidencia de problema + uso + retorno + intención de pago.

## Estructura
```
app-validation/
  experiments/
    shared/analytics.js  # 7 eventos + email + return visit
    nexa/  # Turn goals into daily actions
    focus/ # Plan day without fighting brain
  CONTENT_CALENDAR.md
  README.md (este archivo)
```

## Deploy $0 (3 min por landing)
1. **Netlify:** drag folder `nexa/` → site live. Forms: enabled by default if `netlify` attr, o usa Formspree.
2. Reemplaza `https://formspree.io/f/REPLACE_ME` en `app.js` (ambos) por tu endpoint Formspree.
3. Alternativa: Vercel `vercel --cwd experiments/nexa`, GitHub Pages desde `/docs`.

## Eventos (7 + email)
`landing_view, demo_started, goal_created, plan_generated, plan_saved, return_visit, price_intent, email_signup`
Ver en consola con `debug:true` o POST a endpoint.

## Demand Score (hipótesis, no ley)
```
0.25*demo_engagement + 0.20*creation + 0.20*save/signup + 0.15*return + 0.20*pay_intent
```
Gana quien produzca más `plan_saved + price_intent=clicked_pro`.

## Regla kill
2 semanas tráfico real sin `plan_saved` ni emails → KILL. $0 perdido.
