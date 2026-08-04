import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Button from '@/components/ui/Button.vue'

describe('Button', () => {
  it('renders default slot content', () => {
    const wrapper = mount(Button, {
      slots: { default: 'Click me' },
    })
    expect(wrapper.text()).toContain('Click me')
  })

  it('applies default variant classes', () => {
    const wrapper = mount(Button, {
      slots: { default: 'Hello' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('bg-primary')
  })

  it('applies destructive variant classes', () => {
    const wrapper = mount(Button, {
      props: { variant: 'destructive' },
      slots: { default: 'Delete' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('bg-destructive')
  })

  it('applies outline variant classes', () => {
    const wrapper = mount(Button, {
      props: { variant: 'outline' },
      slots: { default: 'Outline' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('border-border')
  })

  it('applies secondary variant classes', () => {
    const wrapper = mount(Button, {
      props: { variant: 'secondary' },
      slots: { default: 'Secondary' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('bg-surface')
  })

  it('applies ghost variant classes', () => {
    const wrapper = mount(Button, {
      props: { variant: 'ghost' },
      slots: { default: 'Ghost' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('text-muted-foreground')
  })

  it('applies link variant classes', () => {
    const wrapper = mount(Button, {
      props: { variant: 'link' },
      slots: { default: 'Link' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('underline-offset-4')
  })

  it('applies default size classes', () => {
    const wrapper = mount(Button, {
      slots: { default: 'Hello' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('h-9')
  })

  it('applies sm size classes', () => {
    const wrapper = mount(Button, {
      props: { size: 'sm' },
      slots: { default: 'Small' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('h-8')
  })

  it('applies lg size classes', () => {
    const wrapper = mount(Button, {
      props: { size: 'lg' },
      slots: { default: 'Large' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('h-10')
  })

  it('applies icon size classes', () => {
    const wrapper = mount(Button, {
      props: { size: 'icon' },
      slots: { default: '+' },
    })
    const button = wrapper.find('button')
    expect(button.classes()).toContain('w-9')
  })

  it('renders as child when asChild prop is true', () => {
    const wrapper = mount(Button, {
      props: { asChild: true },
      slots: { default: '<span class="inner">content</span>' },
    })
    expect(wrapper.find('button').exists()).toBe(false)
    expect(wrapper.html()).toContain('inner')
  })

  it('handles click events', async () => {
    const wrapper = mount(Button, {
      slots: { default: 'Click' },
    })
    await wrapper.find('button').trigger('click')
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('is disabled when disabled prop is set', () => {
    const wrapper = mount(Button, {
      props: { disabled: true },
      slots: { default: 'Disabled' },
    })
    const button = wrapper.find('button')
    expect(button.attributes('disabled')).toBeDefined()
  })
})
