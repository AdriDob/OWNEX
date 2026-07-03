import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Badge from '@/components/ui/Badge.vue'

describe('Badge', () => {
  it('renders default slot content', () => {
    const wrapper = mount(Badge, {
      slots: { default: 'Active' },
    })
    expect(wrapper.text()).toContain('Active')
  })

  it('applies default variant classes', () => {
    const wrapper = mount(Badge, {
      slots: { default: 'Default' },
    })
    const span = wrapper.find('span')
    expect(span.classes()).toContain('bg-surface')
  })

  it('applies warning variant classes', () => {
    const wrapper = mount(Badge, {
      props: { variant: 'warning' },
      slots: { default: 'Warning' },
    })
    const span = wrapper.find('span')
    expect(span.classes()).toContain('bg-warning/15')
  })

  it('applies destructive variant classes', () => {
    const wrapper = mount(Badge, {
      props: { variant: 'destructive' },
      slots: { default: 'Destructive' },
    })
    const span = wrapper.find('span')
    expect(span.classes()).toContain('bg-destructive/15')
  })

  it('applies outline variant classes', () => {
    const wrapper = mount(Badge, {
      props: { variant: 'outline' },
      slots: { default: 'Outline' },
    })
    const span = wrapper.find('span')
    expect(span.classes()).toContain('border-border')
  })
})
