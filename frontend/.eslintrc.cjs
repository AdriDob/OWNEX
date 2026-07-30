module.exports = {
  root: true,
  env: { browser: true, node: true },
  plugins: ["vue"],
  extends: [
    "eslint:recommended",
    "plugin:vue/vue3-recommended"
  ],
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module"
  },
  rules: {
    "vue/multi-word-component-names": "off",
    "vue/no-multiple-slot-args": "off",
    "vue/valid-define-emits": "off",
    "no-unused-vars": "warn",
    "prefer-const": "warn"
  }
}