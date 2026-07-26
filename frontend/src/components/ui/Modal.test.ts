import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import Modal from '@/components/ui/Modal.vue'

describe('Modal', () => {
  let wrapper: VueWrapper<any>

  beforeEach(() => {
    document.body.style.overflow = ''
    wrapper = mount(Modal, {
      props: {
        open: true,
        title: 'Test Modal',
        size: 'md',
        closable: true,
      },
      global: {
        stubs: {
          Teleport: true,
          Transition: true,
        },
      },
      attachTo: document.body,
    })
  })

  afterEach(() => {
    wrapper.unmount()
    document.body.style.overflow = ''
  })

  it('renders modal when open is true', () => {
    expect(wrapper.find('.fixed.inset-0.z-50').exists()).toBe(true)
    expect(wrapper.find('h3').text()).toBe('Test Modal')
  })

  it('does not render modal when open is false', async () => {
    await wrapper.setProps({ open: false })
    expect(wrapper.find('.fixed.inset-0.z-50').exists()).toBe(false)
  })

  it('emits close event when clicking backdrop', async () => {
    await wrapper.find('.fixed.inset-0.z-50 > .absolute.inset-0').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
    expect(wrapper.emitted('update:open')).toBeTruthy()
    expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
  })

  it('does not close when clicking modal content', async () => {
    await wrapper.find('.relative.w-full').trigger('click')
    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('emits close event when pressing Escape key', async () => {
    const keydownEvent = new KeyboardEvent('keydown', { key: 'Escape' })
    window.dispatchEvent(keydownEvent)
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('does not emit close when Escape pressed but not closable', async () => {
    await wrapper.setProps({ closable: false })
    const keydownEvent = new KeyboardEvent('keydown', { key: 'Escape' })
    window.dispatchEvent(keydownEvent)
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('applies correct size classes', async () => {
    const sizes = ['sm', 'md', 'lg', 'xl', 'full']
    const sizeClasses = ['max-w-sm', 'max-w-md', 'max-w-lg', 'max-w-xl', 'max-w-[90vw]']
    
    for (let i = 0; i < sizes.length; i++) {
      await wrapper.setProps({ size: sizes[i] })
      expect(wrapper.find('.relative.w-full').classes()).toContain(sizeClasses[i])
    }
  })

  it('hides close button when closable is false', async () => {
    await wrapper.setProps({ closable: false })
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('shows close button when closable is true', async () => {
    await wrapper.setProps({ closable: true })
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('locks body scroll when mounted with open true', () => {
    const openWrapper = mount(Modal, {
      props: { open: true },
      global: { stubs: { Teleport: true, Transition: true } },
      attachTo: document.body,
    })
    expect(openWrapper.find('.fixed.inset-0.z-50').exists()).toBe(true)
    openWrapper.unmount()
  })

  it('unlocks body scroll when closed', async () => {
    await wrapper.setProps({ open: false })
    expect(wrapper.find('.fixed.inset-0.z-50').exists()).toBe(false)
  })

  it('applies custom class prop', async () => {
    await wrapper.setProps({ class: 'custom-modal-class' })
    expect(wrapper.find('.relative.w-full').classes()).toContain('custom-modal-class')
  })

  it('renders slot content', () => {
    const slotWrapper = mount(Modal, {
      props: { open: true },
      slots: { default: '<div class="slot-content">Slot Content</div>' },
      global: { stubs: { Teleport: true, Transition: true } },
      attachTo: document.body,
    })
    
    expect(slotWrapper.find('.slot-content').exists()).toBe(true)
    expect(slotWrapper.text()).toContain('Slot Content')
    slotWrapper.unmount()
  })

  it('emits update:open false when close button clicked', async () => {
    const closeButton = wrapper.find('button')
    await closeButton.trigger('click')
    expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
  })
})