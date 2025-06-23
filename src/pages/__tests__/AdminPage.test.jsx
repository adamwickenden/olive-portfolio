import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import AdminPage from '../AdminPage'

// Mock Firebase
vi.mock('../../firebase', () => ({
  db: {},
  storage: {}
}))

// Mock Firebase Firestore
vi.mock('firebase/firestore', () => ({
  collection: vi.fn(),
  addDoc: vi.fn()
}))

// Mock Firebase Storage
vi.mock('firebase/storage', () => ({
  ref: vi.fn(),
  uploadBytes: vi.fn()
}))

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate
  }
})

// Mock URL.createObjectURL
global.URL.createObjectURL = vi.fn(() => 'mock-url')

describe('AdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders admin page title and navigation button', () => {
    render(
      <BrowserRouter>
        <AdminPage />
      </BrowserRouter>
    )
    
    expect(screen.getByText('Admin Page')).toBeInTheDocument()
    expect(screen.getByText('Go to Home')).toBeInTheDocument()
  })

  it('renders all form fields', () => {
    render(
      <BrowserRouter>
        <AdminPage />
      </BrowserRouter>
    )
    
    expect(screen.getByLabelText('Select Collection')).toBeInTheDocument()
    expect(screen.getByLabelText('Title')).toBeInTheDocument()
    expect(screen.getByLabelText('Publication')).toBeInTheDocument()
    expect(screen.getByLabelText('Link')).toBeInTheDocument()
    expect(screen.getByLabelText('Date')).toBeInTheDocument()
    expect(screen.getByLabelText('Image')).toBeInTheDocument()
    expect(screen.getByText('Add Document')).toBeInTheDocument()
  })

  it('has correct default values', () => {
    render(
      <BrowserRouter>
        <AdminPage />
      </BrowserRouter>
    )
    
    expect(screen.getByDisplayValue('covers')).toBeInTheDocument()
    expect(screen.getByDisplayValue('https://')).toBeInTheDocument()
  })

  it('allows changing collection selection', () => {
    render(
      <BrowserRouter>
        <AdminPage />
      </BrowserRouter>
    )
    
    const select = screen.getByLabelText('Select Collection')
    fireEvent.change(select, { target: { value: 'features' } })
    
    expect(select.value).toBe('features')
  })

  it('allows updating form fields', () => {
    render(
      <BrowserRouter>
        <AdminPage />
      </BrowserRouter>
    )
    
    const titleInput = screen.getByLabelText('Title')
    const publicationInput = screen.getByLabelText('Publication')
    const linkInput = screen.getByLabelText('Link')
    const dateInput = screen.getByLabelText('Date')
    
    fireEvent.change(titleInput, { target: { value: 'Test Title' } })
    fireEvent.change(publicationInput, { target: { value: 'Test Publication' } })
    fireEvent.change(linkInput, { target: { value: 'https://test.com' } })
    fireEvent.change(dateInput, { target: { value: '2024-01-01' } })
    
    expect(titleInput.value).toBe('Test Title')
    expect(publicationInput.value).toBe('Test Publication')
    expect(linkInput.value).toBe('https://test.com')
    expect(dateInput.value).toBe('2024-01-01')
  })

  it('handles file selection and shows preview', () => {
    render(
      <BrowserRouter>
        <AdminPage />
      </BrowserRouter>
    )
    
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
    const fileInput = screen.getByLabelText('Image')
    
    fireEvent.change(fileInput, { target: { files: [file] } })
    
    expect(screen.getByAltText('Preview')).toBeInTheDocument()
    expect(screen.getByAltText('Preview')).toHaveAttribute('src', 'mock-url')
  })

  it('navigates to home when home button is clicked', () => {
    render(
      <BrowserRouter>
        <AdminPage />
      </BrowserRouter>
    )
    
    const homeButton = screen.getByText('Go to Home')
    fireEvent.click(homeButton)
    
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })
}) 