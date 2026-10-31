# Wallet and Payout Security (OWNEX v8.0)
*Generated: 2026-10-31 | Per Integration Bundle §11*

## Critical Warnings

**Do not infer that a wallet-compatible token can be cashed out legally, cheaply, or reliably in Argentina.**
Do not connect to, store credentials for, or initiate activity on any payout provider until its current status and security are verified.

**Never store seed phrases or private keys** in application configuration, logs, source code, database backups, or GitHub.
Prefer user-controlled wallets and explicit transaction signing.
Human approval is required for: transfers, swaps, bridges, staking, deposits, paid onboarding, paid assessments, grant submissions with legal commitments.
Include chain ID, token contract, destination, amount, fees, and simulation/quote evidence before every approval.

## Argentina Off-Ramp Analysis by Source

### taskbounty: TaskBounty (task-bounty.ai)

- **Argentina Availability**: conditional
- **Payout Currency**: USDC/ETH
- **Verified Routes**:
  - Route requires end-to-end verification before use
  - USDC -> AirTM/Mercuryo (0%, minutos)
  - USDC -> LBank/OKX (0% fees)
- **Warnings**:
  - ⚠️ AirTM 2.2% fee for MP/Santander conversion
  - ⚠️ Verify LBank/OKX Argentina withdrawal support

---

### github_bounties: GitHub bounties

- **Argentina Availability**: denied
- **Payout Currency**: unknown
- **Verified Routes**:
  - Argentina explicitly blocked - do NOT attempt payout route
- **Warnings**:
  - ⚠️ Source explicitly denies Argentina payout access
- **Argentina-related blockers**: no primary evidence

---

### agenthansa: AgentHansa

- **Argentina Availability**: denied
- **Payout Currency**: unknown
- **Verified Routes**:
  - Argentina explicitly blocked - do NOT attempt payout route
- **Warnings**:
  - ⚠️ Source explicitly denies Argentina payout access
- **Argentina-related blockers**: no primary evidence

---

### opire: Opire

- **Argentina Availability**: conditional
- **Payout Currency**: USDC/SOL
- **Verified Routes**:
  - Route requires end-to-end verification before use
  - USDC -> AirTM/Mercuryo (0%, minutos)
  - USDC -> LBank/OKX (0% fees)
- **Warnings**:
  - ⚠️ AirTM 2.2% fee for MP/Santander conversion
  - ⚠️ Verify LBank/OKX Argentina withdrawal support
- **Argentina-related blockers**: no primary evidence, research mixed on receipts

---

### bugbounty: Bug Bounties (security)

- **Argentina Availability**: conditional
- **Payout Currency**: USD/USDC-ETH
- **Verified Routes**:
  - Route requires end-to-end verification before use
  - USDC -> AirTM/Mercuryo (0%, minutos)
  - USDC -> LBank/OKX (0% fees)
- **Warnings**:
  - ⚠️ AirTM 2.2% fee for MP/Santander conversion
  - ⚠️ Verify LBank/OKX Argentina withdrawal support

---

## Supported Blockchain Networks

| Network | Description | Primary Use in OWNEX |
|---------|-------------|---------------------|
| **USDC_Base** | USDC on Base network (Ethereum L2, low fees) | x402 per-call payments, API marketplace |
| **USDC_Solana** | USDC on Solana network | High-speed transfers, Solana bounties |
| **USDC_Polygon** | USDC on Polygon network | Moderate-fee transfers, broader compatibility |
| **SOL_Solana** | SOLana native token | Transaction fees, Phantom wallet interactions |
| **$SX** | Solana-based $SX token | Proxies.sx bounty payouts |
| **OP_Optimism** | OP token on Optimism | Optimism RetroPGF, grants |
| **ETH_Ethereum** | ETH on Ethereum mainnet | Highest security, highest gas fees |
| **BTRST_Braintrust** | BTRST token | Braintrust platform, 0% fee to workers |

**⚠️ Do not connect to, store credentials for, or initiate activity on any payout provider** until its current status and security are verified.
As of 2026-10-31, **⚠️ Binance P2P must NOT be used** (hack 29-30 oct 2026, retiros pausados).

## Argentina Payout Route Summary

| Source | Availability | Route Status |
|--------|-------------|-------------|
| taskbounty      | conditional | USDC route available      | 🟡 Route requires verification before use |
| github_bounties | denied   | USD/other route needed    | 🚫 Explicitly blocked |
| agenthansa      | denied   | USD/other route needed    | 🚫 Explicitly blocked |
| opire           | conditional | USDC route available      | 🟡 Route requires verification before use |
| bugbounty       | conditional | USDC route available      | 🟡 Route requires verification before use |

## Key Principles (§11)
- Do not infer that a wallet-compatible token can be cashed out legally, cheaply, or reliably in Argentina
- Do not connect to, store credentials for, or initiate activity on any payout provider until its current status and security are verified
- Never store seed phrases or private keys in application configuration, logs, source code, database backups, or GitHub
- Prefer user-controlled wallets and explicit transaction signing
- Human approval required for transfers, swaps, bridges, staking, deposits, paid onboarding, paid assessments, grant submissions with legal commitments
- Include chain ID, token contract, destination, amount, fees, and simulation/quote evidence before approval