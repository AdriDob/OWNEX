import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import DataTable from '@/components/ui/DataTable.vue'

interface TestItem {
  id: number
  name: string
  email: string
  status: string
  score: number
}

const testItems: TestItem[] = [
  { id: 1, name: 'Alice', email: 'alice@example.com', status: 'active', score: 95 },
  { id: 2, name: 'Bob', email: 'bob@example.com', status: 'inactive', score: 87 },
  { id: 3, name: 'Charlie', email: 'charlie@example.com', status: 'active', score: 92 },
  { id: 4, name: 'Diana', email: 'diana@example.com', status: 'pending', score: 78 },
]

const testColumns = [
  { key: 'id', label: 'ID', sortable: true, align: 'center' as const },
  { key: 'name', label: 'Name', sortable: true },
  { key: 'email', label: 'Email', sortable: true },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'score', label: 'Score', sortable: true, align: 'right' as const },
]

function mountTable(props: any = {}) {
  return mount(DataTable, {
    props: {
      columns: testColumns,
      items: testItems,
      ...props,
    },
    global: {
      stubs: {
        ChevronUp: true,
        ChevronDown: true,
        Search: true,
        X: true,
      },
    },
  })
}

describe('DataTable', () => {
  let wrapper: VueWrapper<any>

  beforeEach(() => {
    wrapper = mountTable({ searchable: true, pageSize: 2 })
  })

  it('renders table with correct headers', () => {
    const headers = wrapper.findAll('th')
    expect(headers.length).toBe(5)
    expect(headers[0].text()).toContain('ID')
    expect(headers[1].text()).toContain('Name')
    expect(headers[2].text()).toContain('Email')
    expect(headers[3].text()).toContain('Status')
    expect(headers[4].text()).toContain('Score')
  })

  it('renders correct number of data rows per page', () => {
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(2) // 2 data rows with pageSize=2
  })

  it('shows search input when searchable is true', () => {
    const searchInput = wrapper.find('input[type="search"]')
    expect(searchInput.exists()).toBe(true)
  })

  it('filters items by search query', async () => {
    const searchInput = wrapper.find('input[type="search"]')
    await searchInput.setValue('alice')
    
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(1) // 1 data row
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).not.toContain('Bob')
  })

  it('clears search when clicking X button', async () => {
    const searchInput = wrapper.find('input[type="search"]')
    await searchInput.setValue('alice')
    
    const clearButton = wrapper.find('button[type="button"]')
    await clearButton.trigger('click')
    
    expect(searchInput.element.value).toBe('')
  })

  it('sorts by column when clicking sortable header', async () => {
    const nameHeader = wrapper.findAll('th')[1] // Name column
    await nameHeader.trigger('click')
    
    // Should sort ascending by name
    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('Alice')
    expect(rows[1].text()).toContain('Bob')
    
    // Click again to sort descending
    await nameHeader.trigger('click')
    
    const rowsDesc = wrapper.findAll('tbody tr')
    expect(rowsDesc[0].text()).toContain('Diana')
  })

  it('paginates correctly', async () => {
    // First page has 2 items
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('Bob')
    expect(wrapper.text()).not.toContain('Charlie')
    
    // Go to next page
    const buttons = wrapper.findAll('button')
    const nextButton = buttons.find(b => b.text() === 'Siguiente')
    expect(nextButton).toBeDefined()
    await nextButton!.trigger('click')
    
    expect(wrapper.text()).toContain('Charlie')
    expect(wrapper.text()).toContain('Diana')
  })

  it('shows loading skeleton when loading prop is true', () => {
    const loadingWrapper = mount(DataTable, {
      props: {
        columns: testColumns,
        items: testItems,
        loading: true,
        pageSize: 2,
      },
      global: {
        stubs: { ChevronUp: true, ChevronDown: true, Search: true, X: true },
      },
    })
    
    expect(loadingWrapper.find('.ownex-skeleton').exists()).toBe(true)
  })

  it('shows empty state when no items', () => {
    const emptyWrapper = mount(DataTable, {
      props: {
        columns: testColumns,
        items: [],
        emptyTitle: 'No data',
        emptyDescription: 'No items found',
      },
      global: {
        stubs: { ChevronUp: true, ChevronDown: true, Search: true, X: true },
      },
    })
    
    expect(emptyWrapper.text()).toContain('No data')
    expect(emptyWrapper.text()).toContain('No items found')
  })

  it('renders custom cell content via slot', () => {
    const slotWrapper = mount(DataTable, {
      props: {
        columns: testColumns,
        items: testItems,
        pageSize: 2,
      },
      slots: {
        'cell-status': '<span class="custom-badge">{{ value }}</span>',
      },
      global: {
        stubs: { ChevronUp: true, ChevronDown: true, Search: true, X: true },
      },
    })
    
    expect(slotWrapper.find('.custom-badge').exists()).toBe(true)
  })

  it('renders custom render function for column', () => {
    const customColumns = [
      { key: 'score', label: 'Score', sortable: true, render: (item: TestItem) => `${item.score}%` },
    ]
    
    const renderWrapper = mount(DataTable, {
      props: {
        columns: customColumns,
        items: testItems,
        pageSize: 2,
      },
      global: {
        stubs: { ChevronUp: true, ChevronDown: true, Search: true, X: true },
      },
    })
    
    expect(renderWrapper.text()).toContain('95%')
    expect(renderWrapper.text()).toContain('87%')
  })

  it('handles row click event', async () => {
    const clickHandler = vi.fn()
    const clickWrapper = mountTable({ 
      pageSize: 2,
      rowClick: clickHandler,
    })
    
    const firstRow = clickWrapper.findAll('tbody tr')[0] // First data row
    await firstRow.trigger('click')
    
    expect(clickHandler).toHaveBeenCalledWith(testItems[0])
  })

  it('shows correct pagination info', () => {
    expect(wrapper.text()).toContain('4 resultados')
    expect(wrapper.text()).toContain('Pág 1/2')
  })

  it('applies custom class when provided', () => {
    const classWrapper = mountTable({ class: 'custom-table-class' })
    expect(classWrapper.classes()).toContain('custom-table-class')
  })

  it('applies custom render function for column', () => {
    const customColumns = [
      { key: 'score', label: 'Score', sortable: true, render: (item: TestItem) => `${item.score}%` },
    ]
    
    const renderWrapper = mount(DataTable, {
      props: {
        columns: customColumns,
        items: testItems,
        pageSize: 2,
      },
      global: {
        stubs: { ChevronUp: true, ChevronDown: true, Search: true, X: true },
      },
    })
    
    expect(renderWrapper.text()).toContain('95%')
    expect(renderWrapper.text()).toContain('87%')
  })

  it('applies custom alignment classes', () => {
    // Check right-aligned column
    const scoreHeader = wrapper.findAll('th')[4]
    expect(scoreHeader.classes()).toContain('text-right')
    
    const firstScoreCell = wrapper.findAll('tbody tr')[0].findAll('td')[4]
    expect(firstScoreCell.classes()).toContain('text-right')
  })

  it('applies custom class prop', () => {
    const classWrapper = mountTable({ class: 'custom-table-class' })
    expect(classWrapper.classes()).toContain('custom-table-class')
  })

  it('displays sort indicator on sorted column', async () => {
    const nameHeader = wrapper.findAll('th')[1] // Name column
    await nameHeader.trigger('click')
    
    // Should show chevron for ascending
    const sortedHeader = wrapper.findAll('th')[1]
    const hasChevron = sortedHeader.find('svg').exists()
    expect(hasChevron).toBe(true)
  })

  it('toggles sort direction on second click', async () => {
    const nameHeader = wrapper.findAll('th')[1]
    await nameHeader.trigger('click')
    await nameHeader.trigger('click')
    
    // Should sort descending (Diana first)
    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('Diana')
  })
})