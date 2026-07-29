export interface AssistantCharacter {
  id: string
  name: string
  title: string
  color: string
  bgGradient: string
  borderColor: string
  messages: string[]
  context: string[]
}

export const assistants: AssistantCharacter[] = [
  {
    id: 'merlin',
    name: 'Merlin',
    title: 'OWNEX Architect',
    color: 'text-purple-400',
    bgGradient: 'from-purple-900/30 to-transparent',
    borderColor: 'border-purple-500/30',
    messages: [
      'El sistema está estable. Los pipelines DISCOVER→RECON→HYPOTHESIS fluyen sin interrupciones.',
      'He observado un patrón en tus hallazgos recientes. Los endpoints con IDOR son 3x más probables de ser aceptados.',
      'La matriz de conocimiento se expande. Sugiero priorizar targets con puntuación EVH > 70.',
    ],
    context: ['mission-control', 'health-center', 'orion'],
  },
  {
    id: 'clippy',
    name: 'Clippy',
    title: 'Help Assistant',
    color: 'text-blue-400',
    bgGradient: 'from-blue-900/30 to-transparent',
    borderColor: 'border-blue-500/30',
    messages: [
      'Veo que tienes findings pendientes de reporte. ¿Quieres que genere un draft?',
      'Tip: Usá Ctrl+K para abrir la paleta de comandos. ¡Hay más de 100 comandos!',
      'Parece que hace 48h que no revisás tus hypotheses. Hay 3 nuevas esperando validación.',
    ],
    context: ['findings', 'reports', 'settings'],
  },
  {
    id: 'rover',
    name: 'Rover',
    title: 'Security Guard Dog',
    color: 'text-amber-400',
    bgGradient: 'from-amber-900/30 to-transparent',
    borderColor: 'border-amber-500/30',
    messages: [
      '🐾 ¡Woof! Sistema seguro. No se detectaron anomalías en los últimos 60 minutos.',
      'OWNEX está protegiendo tu identidad. Todos los secrets están en la bóveda cifrada.',
      'Revisé los logs de acceso. Todo en orden, jefe. 🐕',
    ],
    context: ['security', 'health-center', 'settings'],
  },
  {
    id: 'links',
    name: 'Links',
    title: 'Data Connector',
    color: 'text-cyan-400',
    bgGradient: 'from-cyan-900/30 to-transparent',
    borderColor: 'border-cyan-500/30',
    messages: [
      '📡 Conexiones activas: 3 plataformas, 2 exchanges, blockchain sincronizado.',
      'El Knowledge Graph tiene 142 nodos y 389 edges. La densidad de conexiones aumentó 12% esta semana.',
      'Detecté una correlación entre tus findings de SSRF y los programas de HackerOne. ¿Investigo?',
    ],
    context: ['knowledge-graph', 'connections', 'sync-center'],
  },
  {
    id: 'dot',
    name: 'The Dot',
    title: 'Minimalist Observer',
    color: 'text-foreground',
    bgGradient: 'from-gray-800/30 to-transparent',
    borderColor: 'border-gray-600/30',
    messages: [
      '• Simplicity is the ultimate sophistication. Tu health score está en 92. Excelente.',
      '• Menos ruido, más señal. Los bottlenecks están reduciéndose un 5% semanal.',
      '• 42 oportunidades evaluadas. 8 con score > 80. La paciencia paga.',
    ],
    context: ['mission-control', 'insights'],
  },
  {
    id: 'f1',
    name: 'F1',
    title: 'Revenue Analyst',
    color: 'text-gold',
    bgGradient: 'from-yellow-900/30 to-transparent',
    borderColor: 'border-yellow-600/30',
    messages: [
      '💰 Total revenue este mes: $2,450. Tendencia: +18% vs mes anterior. ¡Vamos bien!',
      'He calculado el Expected Value de tus targets activos. Priorizá los de tipo IDOR en programas sin competencia.',
      'Tu mejor programa es HackerOne con 62% de acceptance rate. Sugiero enfocar esfuerzos allí.',
    ],
    context: ['revenue', 'financial-truth', 'money-radar'],
  },
  {
    id: 'pepe',
    name: 'Pepe',
    title: 'Memecoin & Trading Advisor',
    color: 'text-green-400',
    bgGradient: 'from-green-900/30 to-transparent',
    borderColor: 'border-green-500/30',
    messages: [
      '¡This is fine! 🔥 But seriously, set a stop loss. Always. No exceptions.',
      'Bro, I found a memecoin with 420x potential. DYOR, but the chart looks... interesting. 🐸',
      '50% chance moon, 50% chance -99%. That\'s the Pepe way. You in?',
      'Stonks only go up! ... Wait, no, that\'s not true. Stonks go up, down, left, right, and sometimes diagonal.',
      'Pepe says: degen a little, but never more than you can afford to lose. 🐸💚',
      'I\'ve seen things. Rug pulls that would make you cry. Always check the liquidity pool.',
      'Today\'s play: 0.1 ETH into that new frog coin. If it hits, lambo. If not, ramen. LFG!',
    ],
    context: ['memecoins', 'trading', 'money-radar', 'high-risk'],
  },
]

export function getAssistantForContext(context: string): AssistantCharacter[] {
  return assistants.filter(a => a.context.includes(context))
}

export function getRandomMessage(assistant: AssistantCharacter): string {
  return assistant.messages[Math.floor(Math.random() * assistant.messages.length)]
}

export function getById(id: string): AssistantCharacter | undefined {
  return assistants.find(a => a.id === id)
}
