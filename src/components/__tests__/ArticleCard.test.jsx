import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import ArticleCard from '../ArticleCard'

describe('ArticleCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders error state when fetch fails', async () => {
    global.fetch.mockRejectedValueOnce(new Error('Network error'))
    
    render(<ArticleCard url="https://example.com" />)
    
    await waitFor(() => {
      expect(screen.getByText('Error loading article')).toBeInTheDocument()
      expect(screen.getByText('Failed to load article preview')).toBeInTheDocument()
    })
  })

  it('renders article data when fetch succeeds', async () => {
    const mockResponse = {
      contents: `
        <html>
          <head>
            <title>Test Article</title>
            <meta property="og:title" content="Test Article Title" />
            <meta property="og:description" content="Test description" />
            <meta property="og:image" content="https://example.com/image.jpg" />
            <meta property="og:site_name" content="Test Site" />
          </head>
        </html>
      `
    }

    global.fetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockResponse)
    })

    // Mock DOMParser
    const mockQuerySelector = vi.fn()
    mockQuerySelector.mockReturnValueOnce({ content: 'Test Article Title' })
    mockQuerySelector.mockReturnValueOnce({ content: 'Test description' })
    mockQuerySelector.mockReturnValueOnce({ content: 'https://example.com/image.jpg' })
    mockQuerySelector.mockReturnValueOnce({ content: 'Test Site' })

    const mockParser = {
      parseFromString: vi.fn().mockReturnValue({
        querySelector: mockQuerySelector
      })
    }
    global.DOMParser = vi.fn().mockImplementation(() => mockParser)

    render(<ArticleCard url="https://example.com" />)
    
    await waitFor(() => {
      expect(screen.getByText('Test Article Title')).toBeInTheDocument()
      expect(screen.getByText('Test description')).toBeInTheDocument()
      expect(screen.getByText('Test Site')).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /read article/i })).toBeInTheDocument()
    })
  })

  it('renders image when available', async () => {
    const mockResponse = {
      contents: `
        <html>
          <head>
            <meta property="og:image" content="https://example.com/image.jpg" />
          </head>
        </html>
      `
    }

    global.fetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockResponse)
    })

    const mockQuerySelector = vi.fn()
    mockQuerySelector.mockReturnValueOnce({ content: 'Test Title' })
    mockQuerySelector.mockReturnValueOnce({ content: 'Test description' })
    mockQuerySelector.mockReturnValueOnce({ content: 'https://example.com/image.jpg' })
    mockQuerySelector.mockReturnValueOnce({ content: 'Test Site' })

    const mockParser = {
      parseFromString: vi.fn().mockReturnValue({
        querySelector: mockQuerySelector
      })
    }
    global.DOMParser = vi.fn().mockImplementation(() => mockParser)

    render(<ArticleCard url="https://example.com" />)
    
    await waitFor(() => {
      const image = screen.getByRole('img')
      expect(image).toBeInTheDocument()
      expect(image).toHaveAttribute('src', 'https://example.com/image.jpg')
    })
  })

  it('does not render image when not available', async () => {
    const mockResponse = {
      contents: `
        <html>
          <head>
            <title>Test Article</title>
          </head>
        </html>
      `
    }

    global.fetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockResponse)
    })

    const mockQuerySelector = vi.fn()
    mockQuerySelector.mockReturnValueOnce({ content: 'Test Title' })
    mockQuerySelector.mockReturnValueOnce({ content: 'Test description' })
    mockQuerySelector.mockReturnValueOnce(null) // No image
    mockQuerySelector.mockReturnValueOnce({ content: 'Test Site' })

    const mockParser = {
      parseFromString: vi.fn().mockReturnValue({
        querySelector: mockQuerySelector
      })
    }
    global.DOMParser = vi.fn().mockImplementation(() => mockParser)

    render(<ArticleCard url="https://example.com" />)
    
    await waitFor(() => {
      expect(screen.queryByRole('img')).not.toBeInTheDocument()
    })
  })

  it('has correct link attributes', async () => {
    const mockResponse = {
      contents: `
        <html>
          <head>
            <title>Test Article</title>
          </head>
        </html>
      `
    }

    global.fetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockResponse)
    })

    const mockQuerySelector = vi.fn()
    mockQuerySelector.mockReturnValueOnce({ content: 'Test Title' })
    mockQuerySelector.mockReturnValueOnce({ content: 'Test description' })
    mockQuerySelector.mockReturnValueOnce(null)
    mockQuerySelector.mockReturnValueOnce({ content: 'Test Site' })

    const mockParser = {
      parseFromString: vi.fn().mockReturnValue({
        querySelector: mockQuerySelector
      })
    }
    global.DOMParser = vi.fn().mockImplementation(() => mockParser)

    render(<ArticleCard url="https://example.com" />)
    
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /read article/i })
      expect(link).toHaveAttribute('href', 'https://example.com')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    })
  })
}) 