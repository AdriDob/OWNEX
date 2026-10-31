<template>
  <div class="panel">
    <div class="card-base">
      <h3 class="text-primary">Live Trading Panel</h3>
      <p>Connect your trading account to enable live trading.</p>
      <div class="glass">
        <p>Status: Waiting for connection...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
// No script needed for minimal panel
</script>

<style scoped>
.card-base {
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.85), rgba(5, 5, 5, 0.65));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 20px;
}
</style>