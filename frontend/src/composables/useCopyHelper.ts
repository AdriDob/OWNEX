import { type Ref, ref } from 'vue'
import { useToast } from '@/composables/useToast'

const lastCopied = ref<string | null>(null)

async function copyToClipboard(text: string, label?: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    lastCopied.value = label || text
    return true
  } catch {
    return false
  }
}

export function useCopyHelper() {
  const { toast } = useToast()

  async function copyText(text: string, label?: string): Promise<boolean> {
    const ok = await copyToClipboard(text, label)
    if (ok) toast.success(label ? `${label} copiado` : 'Texto copiado')
    else toast.error('Error al copiar')
    return ok
  }

  async function copyJSON(obj: any): Promise<boolean> {
    const text = JSON.stringify(obj, null, 2)
    const ok = await copyToClipboard(text)
    if (ok) toast.success('JSON copiado')
    else toast.error('Error al copiar JSON')
    return ok
  }

  async function copyId(id: string): Promise<boolean> {
    const ok = await copyToClipboard(id)
    if (ok) toast.success('ID copiado')
    else toast.error('Error al copiar ID')
    return ok
  }

  async function copyHash(hash: string): Promise<boolean> {
    const ok = await copyToClipboard(hash)
    if (ok) toast.success('Hash copiado')
    else toast.error('Error al copiar hash')
    return ok
  }

  async function copyWalletAddress(address: string): Promise<boolean> {
    const ok = await copyToClipboard(address)
    if (ok) toast.success('Dirección de wallet copiada')
    else toast.error('Error al copiar dirección')
    return ok
  }

  async function copyApiKeyName(keyName: string): Promise<boolean> {
    const ok = await copyToClipboard(keyName)
    if (ok) toast.success('API Key copiada')
    else toast.error('Error al copiar API Key')
    return ok
  }

  async function copyError(error: string): Promise<boolean> {
    const ok = await copyToClipboard(error)
    if (ok) toast.success('Error copiado')
    else toast.error('Error al copiar')
    return ok
  }

  return {
    copyText,
    copyJSON,
    copyId,
    copyHash,
    copyWalletAddress,
    copyApiKeyName,
    copyError,
    lastCopied,
  }
}
