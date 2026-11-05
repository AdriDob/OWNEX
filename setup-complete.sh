#!/bin/bash
# OWNEX 9.0.0 - COMPLETE SETUP: 7 Crypto IA Platforms + Argentina Infrastructure
# Ejecutar con: bash /home/adriel/projects/Rastro/setup-complete.sh

set -e

echo "============================================"
echo "🚀 OWNEX 9.0.0 - CONFIGURATION COMPLETE"
echo "============================================"
echo ""
echo "📦 Incluyendo: 7 plataformas + Airtm + GitHub + MetaMask"
echo ""

# ============================================
# PASO 1: GitHub Profile Optimization
# ============================================
echo "1️⃣ PASO 1: Optimizando GitHub Profile..."
mkdir -p ~/github-setup

cat > ~/github-setup/README.md << 'GITEOF'
# OWNEX Crypto IA & Bounties Profile

## Bio (160 chars max)
```
Bug Bounty | AI Training | Web3 Developer 🇦🇷
Gitcoin | Immunefi | Outlier | Sahara | CODEFORAI | DATAANNOTATION
💰 Crypto payments USDC/USDT | Airtm | MetaMask
📧 Email: tu-email@dominio.com
```

## Skills Tags
- solidity
- python
- javascript
- typescript
- api-integration
- automation
- web3
- blockchain
- bug-bounty
- smart-contracts
- ethereum
- polygon
- machine-learning
- data-annotation
- nlp

## Pinned Repos (3 max)
1. **skill-demonstrator**: Ejemplos automation & API integration
2. **crypto-bounty-solver**: 2-3 solved bounties/PoC
3. **automation-scripts**: Workflow automations
GITEOF

echo "   ✅ GitHub README creado en ~/github-setup/README.md"
echo "   → Subí esto a tu GitHub profile repository"
echo ""

# ============================================
# PASO 2: MetaMask Setup
# ============================================
echo "2️⃣ PASO 2: Configurando MetaMask Universal..."
mkdir -p ~/wallet-setup

cat > ~/wallet-setup/metamask-guide.md << 'METAEOF'
# MetaMask Setup Universal para Plataformas Crypto

## Crear Nueva Wallet
1. Install MetaMask browser extension (Chrome/Firefox/Edge)
2. Click extension icon → "Create a wallet"
3. Read & accept Terms of Use
4. **Create a password** (master password for extension)
5. **CRITICAL**: Save the 12-word recovery phrase
   - Write it on PAPER (NOT digital!)
   - Store in safe location
   - Never share with anyone
6. Confirm the words in correct order
7. Wallet creado ¡!

## Agregar Redes Necesarias (bajas fees)
Por defecto viene Ethereum mainnet (costoso). Agregar:

### Red Polygon (MATIC) - Recomendada
- Network Name: Polygon Mainnet
- RPC URL: https://polygon-rpc.com/
- Chain ID: 137
- Symbol: MATIC
- Block Explorer: https://polygonscan.com

### Red Arbitrum
- Network Name: Arbitrum One
- RPC URL: https://arb1.arbitrum.io/rpc
- Chain ID: 42161
- Symbol: ETH
- Block Explorer: https://arbiscan.io

## Obtener Tu Address Público
1. En MetaMask, selecciona "Account 1"
2. Click en el address (0x...)
3. Copy address
4. Este address compartir en:
   - Todas las plataformas (Sahara, Outlier, Gitcoin, etc.)
   - Airtm para recibir pagos
   - Perfiles de Gitcoin/Immunefi

## Redes a EVITAR (fees altos)
- Ethereum mainnet durante congestión ($5-50 por transferencia)
- Usar siempre Polygon o Arbitrum ($0.01-0.50)

## Múltiples Accounts (opcional)
- Crear "Account 2", "Account 3" dentro de misma extensión
- Útil separar: fondos operativos vs. ahorro
METAEOF

echo "   ✅ MetaMask guide creado en ~/wallet-setup/metamask-guide.md"
echo "   → Open y seguí los pasos"
echo ""

# ============================================
# PASO 3: Airtm Argentina KYC
# ============================================
echo "3️⃣ PASO 3: Configurando Airtm Argentina KYC..."
mkdir -p ~/airtm-setup

cat > ~/airtm-setup/kyc-guide.md << 'AIROF'
# Airtm Setup para Argentinos - Guía KYC

## Paso 1: Crear Cuenta
1. Ir a: https://airtm.com/signup
2. Registrarse con email Gmail/Outlook verificado
3. Completo registro básico (nombre, apellido, país Argentina)

## Paso 2: KYC/KYL (Obligatorio para retiros a pesos)
Este paso es CRÍTICO - sin KYC no podés retirar a cuenta bancaria.

1. Ir a "My Account" → "KYC Verification"
2. Subir documento:
   - DNI (frente y verso) - Foto clara, sin reflejos
   - Comprobante de domicilio:
     - Factura de luz/agua/termo (máx. 3 meses antigüedad)
     - Declaración jurada de ingresos (opcional)
   - Selfie con documento:
     - Tomando foto sosteniendo DNI al lado de tu cara
     - Cara visible y documento legible

3. Esperar aprobación (24-48 horas hábiles)
   - Durante este tiempo SÍ podés recibir USDC/USDT
   - Solo para RETIRAR a pesos es necesario KYC aprobado

## Paso 3: Configurar Método de Retiro a ARS
1. Ir a "My Wallet" → "Add Local Currency Wallet"
2. Seleccionar "Argentine Peso (ARS)"
3. Elegir tipo de retirada:
   - **Bank Transfer**: Transferencia a tu cuenta bancaria
   - **PagoFácil/Quirofácil**: Retiro en efectivo en comercios
4. Ingresar datos:
   - **Bank**: Tu CBU/CVU completo
   - **o PagoFácil**: Tu número de teléfono/alias
5. Guardar configuración

## Paso 4: Probar Retiro Mínimo (CRÍTICO)
1. Obtener USDC/USDT en tu wallet MetaMask (desde cualquiera de las 7 plataformas)
2. Transferir a Airtm:
   - En Airtm: "Add Funds" → "Crypto" → Seleccionar USDC/USDT
   - Copiar tu dirección única de Airtm para cada moneda
   - Transferir desde MetaMask: Send → Address de Airtm → Amount
3. En Airtm, ver que USDT/USDC aparece en "My Wallet"
4. Solicitar retiro:
   - Monto: $10 USDT/USDC (mínimo recomendado para prueba)
   - Método: Tu cuenta bancaria o PagoFácil
5. Verificar llegada:
   - Banco: Verificar en home banking (1-2 días hábiles)
   - PagoFácil: Retirar en efectivo inmediato (horario comercio)
6. **Anotar**: Tiempo que tomó, fees descontados, tipo de cambio oficial/blue

## Paso 5: Vincular con Plataformas de IA/Crypto
1. En cada plataforma (Sahara, Outlier, Gitcoin, etc.):
   - Ir a configuración de pagos/retiros
   - Seleccionar "Retirar a Airtm"
   - Ingresar tu handle/email de Airtm
   - Configurar moneda: USDT o USDC
2. Las plataformas enviarán USDC/USDT a tu wallet
3. Vos transferís a Airtm y retirás a pesos

## Costos y Tiempos Estimados (Argentina)
| Servicio | Fee | Tiempo |
|----------|-----|--------|
| KYC aprobación | Gratis | 24-48 horas |
| Retiro Airtm → Banco | 1-2% | 1-2 días hábiles |
| Retiro Airtm → PagoFácil | 1-2% | Inmediato (horario) |
| Red Polygon transfer | $0.001-0.10 | Inmediato |
| Red Ethereum transfer | $5-50 (varia) | 30 min - 2 horas |

## Tips Especiales Argentina
- **Tipo de cambio**: El rate que ofrecen es sobre el blue/oficial. Compará antes de retirar.
- **Horarios PagoFácil**: Lunes a Viernes 8:00-20:00, Sábados 9:00-14:00
- **Domicilio exacto**: Asegurate que tu CBU tenga la dirección correcta para bank transfer
- **Email verificado**: Airtm requiere email verificado para retirar a bancos
- **Primer retiro**: Podría tardar más (hasta 3 días) por verificación inicial

🎯 Objetivo: Completar KYC y hacer primer retiro $10 para validar todo el flujo.
AIROF

echo "   ✅ Airtm KYC guide creado en ~/airtm-setup/kyc-guide.md"
echo "   → Leé detalladamente antes de comenzar"
echo ""

# ============================================
# PASO 4: Registros en 7 Plataformas
# ============================================
echo "4️⃣ PASO 4: Scripts de Registro en 7 Plataformas..."

# 4a: Sahara AI
echo "   📡 4a. Sahara AI - Registración optimizada..."
cat > ~/platform-setup/sahara-register.md << 'SAHAEOF'
# Sahara AI Registration (Argentina)

1. Ir a: https://sahara.ai/join
2. Registrarse con email Gmail/Outlook (más rápido que otros)
3. **Inmediatamente conectar wallet MetaMask**
4. Seleccionar país: Argentina
5. Perfil completado:
   - Habilitar: Natural Language Processing, Code, Data Annotation
   - Estas tags determinan qué tareas ves disponibles
6. Configurar pago:
   - Wallet: MetaMask address
   - Red: Polygon (MATIC) - bajas fees
   - Token: USDC o USDT
7. Activar notificaciones de tarea

⏱️ Tiempo estimado: 10-15 minutos
SAHAEOF

# 4b: Outlier AI (Argentina optimizado)
echo "   📡 4b. Outlier AI - Argentina payment method..."
cat > ~/platform-setup/outlier-register.md << 'OUTEOF'
# Outlier AI Registration Argentina

1. Ir a: https://outlier.ai/register
2. Durante registro:
   - País: Seleccionar "Argentina" (importante para Airtm)
   - Payment method: Elegir "Airtm" o "Crypto wallet"
   - Si es Airm: Tener cuenta Airtm lista (ideal KYC ya completado)
3. Conectar wallet: MetaMask
4. Seleccionar skills tags:
   - NLP, text annotation, code review, data classification
   - Cuantas más tags, más tareas disponibles
5. Aceptar términos y verificar email
6. Completed profile

⏱️ Tiempo estimado: 10-15 minutos
OUTEOF

# 4c: Gitcoin
echo "   📡 4c. Gitcoin - Profile optimization..."
cat > ~/platform-setup/gitcoin-setup.md << 'GITEOF'
# Gitcoin Setup para Bounties

1. Perfil GitHub optimizado (ya creado en paso 1):
   - Repository README con bio y skills tags
   - 2-3 repos pinned demostrando habilidades

2. Ir a: https://gitcoin.com/explore

3. Filtrar bounties:
   - Tags: solidity, python, javascript, bug-bounty, etc.
   - Level: "Good first issue" para empezar ($50-200)
   - Category: "Security", "Documentation", "Integration"

4. Flujo para cada bounty:
   - Seleccionar bounty interesante
   - Fork el repository
   - Crear branch: `fix/issue-num` o `solution/description`
   - Resolver el problema
   - Subir Pull Request con:
     * Descripción detallada del fix
     * Cómo probar el cambio
     * Capturas de pantalla si aplica
   - Wait validation (puede tomar 1-14 días)
   - Si aprobado: fondos a tu wallet Ethereum
   - Retirada a Airtm o mantener en wallet

⏱️ Tiempo estimado: 
   - Registro: 5 minutos
   - Primera búsqueda bounties: 15 minutos
   - Primer bounty completion: 1-5 horas dependiendo complejidad
GITEOF

# 4d: Immunefi
echo "   📡 4d. Immunefi - Auditorías Smart Contracts..."
cat > ~/platform-setup/immunefi-register.md << 'IMMEOF'
# Immunefi Registration

1. Ir a: https://immunefi.com/bounties/

2. Registrarse con:
   - Email verificado
   - MetaMask wallet address
   - Portfolio: 2-3 repositorios GitHub o reports de auditoría

3. Perfil técnico:
   - Skills: Solidity, Smart Contract Security, Rust (opcional)
   - Languages: English technical writing (importante - los reports son en inglés)
   - Experience level: Beginner, Intermediate, Expert

4. Tipos de bounties disponibles:
   - **Finding**: Vulnerabilidades menores ($500-5,000)
   - **Exploit**: Proof of concept de explotación ($5,000-20,000)
   - **Critical**: Admin takeover, $20,000+

5. Flujo de auditoría:
   - Buscar programas abiertos: "Browse Programs"
   - Filtrar por: Discipline (Solidity, Rust, etc.), Payout range
   - Leer "Program Guide" y reglas específicas
   - Auditoría profunda del smart contract
   - Generar reporte técnico en inglés:
     * Descripción de la vulnerabilidad
     * Proof of concept (PoC)
     * Impacto en el sistema
     * Código de evidencia
   - Subir reporte por plataforma
   - Esperar validación del proyecto (1-4 semanas típicamente)
   - Si validado: Pago masivo en cripto (USDC/ETH/etc.)

⏱️ Tiempo estimado:
   - Registro: 10 minutos
   - Primer audit simple: 5-10 horas
   - Primer reporte enviado: 1-2 semanas validación

💡 Consejo: Empezar buscando programas con payouts $500-2,000 para primeros experiences.
IMMEOF

# 4e: PublicAI y Sapien
echo "   📡 4e. PublicAI y Sapien..."
cat > ~/platform-setup/publicai-sapien.md << 'PAIEOF'
# PublicAI y Sapien Registro

## PublicAI (publicai.com)
1. Ir a: https://publicai.com/join
2. Registro rápido con email
3. Conectar wallet crypto (MetaMask) opcional durante onboarding
4. Seleccionar habilidades/intereses:
   - NLP, code review, data annotation, mathematics
5. Acceder al dashboard de tareas
6. Tareas asíncronas - sin presión de deadline inmediata
7. Pago por tarea completada y validada por red
8. Retiro mínimo: $25-50 USD en USDC
9. Redes soportadas: Ethereum, Polygon, BSC

## Sapien (sapien.io)
1. Ir a: https://sapien.io/join
2. Registro con email + wallet crypto
3. Perfil de contribución:
   - Type of data: Text, Images, Audio, Code
   - Your expertise areas
4. Complete verification tests en plataforma
5. Acceso a tareas de entrenamiento de IA
6. Pago directo a wallet cada vez que contribuciones validadas
7. Redes compatibles: Cualquier wallet EVM-compatible

⏱️ Tiempo estimado: 10 minutos cada una
PAIEOF

# 4f: CODEFORAI.tech
echo "   📡 4f. CODEFORAI.tech..."
cat > ~/platform-setup/codeforai-register.md << 'CFAEOF'
# CODEFORAI.tech Registration

1. Ir a: https://codeforai.tech/register

2. Durante registro:
   - País: Argentina (seleccionable en dropdown)
   - Payment method: Wallet crypto (MetaMask) o Airtm
   - GitHub import: Opcional pero recomendado

3. Perfil de habilidades:
   - Programming languages: Solidity, Python, JS/TS, etc.
   - Areas: Smart contracts, API integration, Automation, Web3
   - Experience level: Beginner/Intermediate/Expert

4. Explorar tareas disponibles:
   - Code reviews and audits
   - API integration tasks
   - Smart contract debugging
   - Automation script writing

5. Flujo de trabajo:
   - Seleccionar tarea que coincida con tus skills
   - Desarrollo/solución en tu entorno local
   - Subir solución por plataforma (generalmente PR o reporte)
   - Validación algorítmica (sistema automático, sin entrevistas humanas)
   - Si validado: Pago en USDC/USDT a wallet configurada
   - Retiro a Airtm o mantener en wallet

⏱️ Tiempo estimado: 10-15 minutos
CFAEOF

# 4g: DATAANNOTATION.tech
echo "   📡 4g. DATAANNOTATION.tech..."
cat > ~/platform-setup/dataannotation-register.md << 'DAEOF'
# DATAANNOTATION.tech Registration

1. Ir a: https://dataannotation.tech/join

2. Durante registro:
   - País: Argentina (supportado nativamente)
   - Payment method: USDC/USDT crypto payment
   - Skills tags: Seleccionar TODO lo que sepas:
     * NLP / procesamiento de lenguaje natural
     * Text annotation / etiquetado de texto
     * Image tagging / etiquetado de imágenes
     * Code review / revisión de código
     * Data classification / clasificación de datos
     * Sentiment analysis / análisis de sentimiento
     * Audio transcription (si aplica)

3. Realizar pruebas de verificación:
   - La plataforma tiene exámenes en pantalla para validar tu skill level
   - Estos determinan qué tareas de mayor calidad/pago te asignan
   - No hay entrevistas humanas - sistema algorítmico

4. Acceder al dashboard:
   - Tareas disponibles por categoría y pago estimado
   - Progress tracker de tareas completadas
   - Earnings USDC acumulados
   - Rating/performance score algorítmico

5. Flujo por tarea:
   - Seleccionar tarea disponible
   - Completar trabajo en la interfaz de la plataforma
   - Submitir para validación
   - Sistema IA valida tus respuestas automáticamente
   - Si aprobado: USDC añadido a tu balance
   - Retiro cuando reaches mínimo $25-50

⏱️ Tiempo estimado: 10-15 minutos
   - Registro: 5 min
   - Configuración skills tags: 5 min
   - Primera prueba de validación: Variable (determina level de tareas)

💡 Consejo: Cuantas más skills tags active, más y mejores tareas recibirás.
DAEOF

echo ""
echo "   ✅ Todos los scripts de plataforma creados en ~/platform-setup/"
echo ""

# ============================================
# PASO 5: Earnings Dashboard
# ============================================
echo "5️⃣ PASO 5: Configurando Earnings Dashboard Python..."
mkdir -p ~/earnings-dashboard

cat > ~/earnings-dashboard/tracker.py << 'PYEOF'
#!/usr/bin/env python3
"""
OWNEX 9.0.0 - Earnings Tracker Crypto AI Platforms
Tracking income from all 7 platforms + Airtm retiros
"""

import json
import os
from datetime import datetime, timezone

class OwnexEarningsTracker:
    def __init__(self, data_file="~/earnings-dashboard/data.json"):
        self.data_file = os.path.expanduser(data_file)
        self.platforms = {
            "sahara_ai": {"earnings": 0.0, "tasks": 0, "status": "pending"},
            "outlier_ai": {"earnings": 0.0, "tasks": 0, "status": "pending"},
            "gitcoin": {"earnings": 0.0, "tasks": 0, "status": "pending"},
            "immunefi": {"earnings": 0.0, "tasks": 0, "status": "pending"},
            "publicai": {"earnings": 0.0, "tasks": 0, "status": "pending"},
            "codeforai": {"earnings": 0.0, "tasks": 0, "status": "pending"},
            "dataannotation": {"earnings": 0.0, "tasks": 0, "status": "pending"},
            "airtm_retiros": {"total_usd": 0.0, "count": 0, "last_retiro": None}
        }
        self._load_data()
    
    def _load_data(self):
        """Cargar datos existentes o crear estructura"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                # Migrar estructura si es necesario
                for k, v in self.platforms.items():
                    if k in data:
                        for pk, pv in v.items():
                            self.platforms[k][pk] = data[k].get(pk, pv)
            except:
                pass
    
    def _save_data(self):
        """Guardar datos a archivo"""
        with open(self.data_file, 'w') as f:
            json.dump(self.platforms, f, indent=2)
    
    def report_task(self, platform, earnings_usd=0.0, task_success=True):
        """Reportar tarea completada en una plataforma"""
        if platform in self.platforms:
            self.platforms[platform]["tasks"] += 1
            if task_success and earnings_usd > 0:
                self.platforms[platform]["earnings"] += earnings_usd
            print(f"📊 {platform:20s} | +${earnings_usd:6.2f} | Total: {self.platforms[platform]['tasks']:3d} tasks | Earned: ${self.platforms[platform]['earnings']:.2f}")
            self._save_data()
    
    def report_retiro(self, amount_usd, transaction_id=None):
        """Reportar retiro a Airtm"""
        self.platforms["airtm_retiros"]["total_usd"] += amount_usd
        self.platforms["airtm_retiros"]["count"] += 1
        self.platforms["airtm_retiros"]["last_retiro"] = {
            "amount": amount_usd,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transaction_id": transaction_id
        }
        print(f"💸 Retiro Airtm: ${amount_usd:.2f} | Total retiros: {self.platforms['airtm_retiros']['count']} | Total USD: ${self.platforms['airtm_retiros']['total_usd']:.2f}")
        self._save_data()
    
    def show_status(self):
        """Mostrar resumen completo"""
        os.system('clear' or 'cls')
        print("="*70)
        print("📊 OWNEX 9.0.0 - EARNINGS DASHBOARD")
        print("="*70)
        
        # Header
        print(f"\n{'PLATFORM':25s} | {'EARNINGS':>10s} | {'TASKS':>6s} | {'STATUS'}")
        print("-"*70)
        
        for platform, data in self.platforms.items():
            if platform == "airtm_retiros":
                print(f"{'AIRTM RETROS':25s} | ${data['total_usd']:9.2f} | {data['count']:6d} | {data['last_retiro']['timestamp'][:10] if data['last_retiro'] else 'N/A':10s}")
            else:
                print(f"{platform:25s} | ${data['earnings']:9.2f} | {data['tasks']:6d} | {data['status']}")
        
        # Total
        total_earnings = sum(p['earnings'] for p in self.platforms if p != 'airtm_retiros')
        total_tasks = sum(p['tasks'] for p in self.platforms if p != 'airtm_retiros')
        
        print("-"*70)
        print(f"{'TOTAL':25s} | ${total_earnings:9.2f} | {total_tasks:6d} | {'')}")
        print("="*70)
        print(f"\n💡 Instrucciones:")
        print(f"  - Reportar tareas: tracker.report_task('outlier_ai', 5.50, True)")
        print(f"  - Reportar retiro: tracker.report_retiro(25.00, 'airtm-tx-001')")
        print(f"  - Ver status: tracker.show_status()")
        print("="*70 + "\n")
    
    def get_best_platforms(self, n=3):
        """Obtener las N plataformas con más earnings"""
        platforms_earnings = [
            (name, data['earnings'], data['tasks'])
            for name, data in self.platforms.items()
            if name != 'airtm_retiros' and data['tasks'] > 0
        ]
        platforms_earnings.sort(key=lambda x: x[1], reverse=True)
        return platforms_earnings[:n]

# Ejemplo de uso si se ejecuta directamente
if __name__ == "__main__":
    import sys
    tracker = OwnexEarningsTracker()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            tracker.show_status()
        elif cmd == "best":
            best = tracker.get_best_platforms()
            print(f"\n🏆 Top plataformas por earnings:\n")
            for i, (name, earnings, tasks) in enumerate(best, 1):
                print(f"  [{i}] {name:20s} | ${earnings:.2f} | {tasks} tasks")
    else:
        tracker.show_status()

PYEOF

echo "   ✅ Earnings dashboard creado en ~/earnings-dashboard/tracker.py"
echo ""

# ============================================
# PASO 6: Resumen Final
# ============================================
echo "6️⃣ PASO 6: Resumen Completo y Próximos Pasos..."
echo ""
echo "============================================"
echo "📋 RESUMEN CONFIGURACIÓN OWNEX 9.0.0"
echo "============================================"
echo ""
echo "📁 ARCHIVOS CREADOS EN TU HOME DIRECTORY:"
echo ""
echo "  ~/github-setup/README.md       - GitHub Profile Optimization"
echo "  ~/wallet-setup/metamask-guide.md - MetaMask Universal Setup"
echo "  ~/airtm-setup/kyc-guide.md     - Airtm Argentina KYC Guide"
echo "  ~/platform-setup/ - Todos los scripts de registro (7 plataformas)"
echo "     ├── sahara-register.md"
echo "     ├── outlier-register.md"
echo "     ├── gitcoin-setup.md"
echo "     ├── immunefi-register.md"
echo "     ├── publicai-sapien.md"
echo "     ├── codeforai-register.md"
echo "     └── dataannotation-register.md"
echo "  ~/earnings-dashboard/tracker.py - Earnings Tracking Dashboard"
echo ""
echo "============================================"
echo "📅 PLAN DE EJECUTORIO RECOMENDADO:"
echo ""
echo "  SEMANA 1 (Días 1-3):"
echo "    ✅ Leer ~/airtm-setup/kyc-guide.md completamente"
echo "    ✅ Crear cuenta Airtm y completar KYC/KYL"
echo "    ✅ Hacer primer retiro teste $10 USDT → Airtm → PagoFácil"
echo "    ✅ Verificar que el flujo funciona correctamente"
echo ""
echo "  SEMANA 1 (Días 4-7):"
echo "    ✅ Registrarse en Outlier AI (Argentina payment: Airtm)"
echo "    ✅ Registrarse en Sahara AI (wallet connect)"
echo "    ✅ Registrarse en Gitcoin (usar GitHub optimizado)"
echo ""
echo "  SEMANA 2 (Días 8-14):"
echo "    ✅ Registrarse en CODEFORAI.tech"
echo "    ✅ Registrarse en DATAANNOTATION.tech"
echo "    ✅ Registrarse en Immunefi (preparar portfolio 2-3 repos)"
echo "    ✅ Registrarse en PublicAI y Sapien"
echo ""
echo "  SEMANA 3 (Días 15-21):"
echo "    ✅ Completar primera tarea en Outlier AI o Sahara AI"
echo "    ✅ Retirar earnings a Airtm (primer retiro real)"
echo "    ✅ Retirar a pesos argentinos y verificar llegada"
echo "    ✅ Reportar en earnings dashboard tracker.py"
echo ""
echo "  SEMANA 4 (Días 22-30):"
echo "    ✅ Evaluar cuál plataforma genera mejor $/hora"
echo "    ✅ Enfocarse en top 2-3 plataformas ganadoras"
echo "    ✅ Optimizar skills tags en cada una"
echo "    ✅ Continuar flujo continuo de tareas y retiros"
echo ""
echo "============================================"
echo "💰 OBJETIVO INICIAL: Primeros $100-200 en 30 días"
echo "   - Outlier AI + Sahara AI: Tareas rápidas, pago semanal"
echo "   - Gitcoin: Un bounty pequeño en primera semana"
echo "   - DATAANNOTATION: Múltiples tareas pequeñas"
echo ""
echo "============================================"
echo "🎯 COMPONENTES TECNICOS LISTOS:"
echo "  ✅ Sistema priorización 300+ adapters (Rastro DB)"
echo "  ✅ Tabla adapter_performance_metrics operativa"
echo "  ✅ Formula priority_score = recency(40%) + success_rate(40%) + volume(20%)"
echo "  ✅ Earnings tracker con integración planned"
echo "  ✅ Todo configurado para Argentina, sin entrevistas human"
echo "  ✅ Pago en USDC/USDT en todas plataformas"
echo "============================================"
echo ""
echo "🚀 ¡CONFIGURACIÓN OWNEX 9.0.0 COMPLETA! "
echo "   Seguí el plan de 4 semanas y empezá a generar ingresos"
echo "   cripto sin entrevistas humanas. ¡Suerte! 🍀"
echo ""