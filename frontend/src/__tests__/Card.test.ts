import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardFooter from '@/components/ui/CardFooter.vue'

describe('Card', () => {
  it('renders Card with default slot content', () => {
    const wrapper = mount(Card, {
      slots: { default: 'Card body' },
    })
    expect(wrapper.text()).toContain('Card body')
  })

  it('renders CardHeader', () => {
    const wrapper = mount(CardHeader, {
      slots: { default: 'Header' },
    })
    expect(wrapper.text()).toContain('Header')
    expect(wrapper.find('div').exists()).toBe(true)
  })

  it('renders CardTitle', () => {
    const wrapper = mount(CardTitle, {
      slots: { default: 'Title' },
    })
    expect(wrapper.text()).toContain('Title')
    expect(wrapper.find('h3').exists()).toBe(true)
  })

  it('renders CardDescription', () => {
    const wrapper = mount(CardDescription, {
      slots: { default: 'Description text' },
    })
    expect(wrapper.text()).toContain('Description text')
    expect(wrapper.find('p').exists()).toBe(true)
  })

  it('renders CardContent', () => {
    const wrapper = mount(CardContent, {
      slots: { default: 'Content area' },
    })
    expect(wrapper.text()).toContain('Content area')
  })

  it('renders CardFooter', () => {
    const wrapper = mount(CardFooter, {
      slots: { default: 'Footer' },
    })
    expect(wrapper.text()).toContain('Footer')
  })

  it('composes Card with all sub-components', () => {
    const wrapper = mount(Card, {
      slots: {
        default: `
          <CardHeader>
            <CardTitle>Test Title</CardTitle>
            <CardDescription>Test Description</CardDescription>
          </CardHeader>
          <CardContent>Test Content</CardContent>
          <CardFooter>Test Footer</CardFooter>
        `,
      },
      global: {
        components: { CardHeader, CardTitle, CardDescription, CardContent, CardFooter },
      },
    })
    expect(wrapper.text()).toContain('Test Title')
    expect(wrapper.text()).toContain('Test Description')
    expect(wrapper.text()).toContain('Test Content')
    expect(wrapper.text()).toContain('Test Footer')
  })
})
