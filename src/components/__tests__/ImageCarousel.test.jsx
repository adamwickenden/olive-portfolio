import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import ImageCarousel from '../ImageCarousel'

// Mock Firebase Firestore
vi.mock('firebase/firestore', () => ({
  collection: vi.fn(),
  getDocs: vi.fn()
}))

describe('ImageCarousel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', async () => {
    const { getDocs } = await import('firebase/firestore')
    getDocs.mockResolvedValueOnce({
      docs: []
    })

    render(<ImageCarousel articleDir="left" />)
    expect(screen.getByTestId('marquee')).toBeInTheDocument()
  })

  it('renders articles when data is fetched successfully', async () => {
    const { collection, getDocs } = await import('firebase/firestore')
    const mockArticles = [
      {
        TITLE: 'Test Article 1',
        LINK: 'https://example1.com',
        IMAGE: 'test-image-1.jpg'
      },
      {
        TITLE: 'Test Article 2',
        LINK: 'https://example2.com',
        IMAGE: 'test-image-2.jpg'
      }
    ]

    collection.mockReturnValue('mock-collection')
    getDocs.mockResolvedValueOnce({
      docs: mockArticles.map(article => ({
        data: () => article
      }))
    })

    render(<ImageCarousel articleDir="left" />)

    await waitFor(() => {
      const images = screen.getAllByRole('img')
      expect(images).toHaveLength(2)
      expect(images[0]).toHaveAttribute('alt', 'Test Article 1')
      expect(images[1]).toHaveAttribute('alt', 'Test Article 2')
    })
  })

  it('renders correct image URLs', async () => {
    const { collection, getDocs } = await import('firebase/firestore')
    const mockArticles = [
      {
        TITLE: 'Test Article',
        LINK: 'https://example.com',
        IMAGE: 'test-image.jpg'
      }
    ]

    collection.mockReturnValue('mock-collection')
    getDocs.mockResolvedValueOnce({
      docs: mockArticles.map(article => ({
        data: () => article
      }))
    })

    render(<ImageCarousel articleDir="left" />)

    await waitFor(() => {
      const image = screen.getByRole('img')
      const expectedUrl = `https://firebasestorage.googleapis.com/v0/b/olive-portfolio.firebasestorage.app/o/${encodeURIComponent('test-image.jpg')}?alt=media`
      expect(image).toHaveAttribute('src', expectedUrl)
    })
  })

  it('renders correct link URLs', async () => {
    const { collection, getDocs } = await import('firebase/firestore')
    const mockArticles = [
      {
        TITLE: 'Test Article',
        LINK: 'https://example.com',
        IMAGE: 'test-image.jpg'
      }
    ]

    collection.mockReturnValue('mock-collection')
    getDocs.mockResolvedValueOnce({
      docs: mockArticles.map(article => ({
        data: () => article
      }))
    })

    render(<ImageCarousel articleDir="left" />)

    await waitFor(() => {
      const link = screen.getByRole('link')
      expect(link).toHaveAttribute('href', 'https://example.com')
    })
  })

  it('renders sad face when no articles are available', async () => {
    const { collection, getDocs } = await import('firebase/firestore')

    collection.mockReturnValue('mock-collection')
    getDocs.mockResolvedValueOnce({
      docs: []
    })

    render(<ImageCarousel articleDir="left" />)

    await waitFor(() => {
      expect(screen.getByText('😭')).toBeInTheDocument()
    })
  })

  it('handles Firebase fetch error gracefully', async () => {
    const { collection, getDocs } = await import('firebase/firestore')

    collection.mockReturnValue('mock-collection')
    getDocs.mockRejectedValueOnce(new Error('Firebase error'))

    // Mock console.error to prevent unhandled error
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(<ImageCarousel articleDir="left" />)

    await waitFor(() => {
      expect(screen.getByText('😭')).toBeInTheDocument()
    })

    consoleSpy.mockRestore()
  })

  it('applies correct styling to images', async () => {
    const { collection, getDocs } = await import('firebase/firestore')
    const mockArticles = [
      {
        TITLE: 'Test Article',
        LINK: 'https://example.com',
        IMAGE: 'test-image.jpg'
      }
    ]

    collection.mockReturnValue('mock-collection')
    getDocs.mockResolvedValueOnce({
      docs: mockArticles.map(article => ({
        data: () => article
      }))
    })

    render(<ImageCarousel articleDir="left" />)

    await waitFor(() => {
      const image = screen.getByRole('img')
      expect(image).toHaveStyle({
        width: '150px',
        height: '200px',
        objectFit: 'cover',
        display: 'block',
        margin: '0',
        padding: '0',
        lineHeight: '0'
      })
    })
  })

  it('renders with different article directions', async () => {
    const { collection, getDocs } = await import('firebase/firestore')
    const mockArticles = [
      {
        TITLE: 'Test Article',
        LINK: 'https://example.com',
        IMAGE: 'test-image.jpg'
      }
    ]

    collection.mockReturnValue('mock-collection')
    getDocs.mockResolvedValueOnce({
      docs: mockArticles.map(article => ({
        data: () => article
      }))
    })

    const { rerender } = render(<ImageCarousel articleDir="left" />)
    
    await waitFor(() => {
      expect(screen.getByTestId('marquee')).toBeInTheDocument()
    })

    // Test with right direction
    getDocs.mockResolvedValueOnce({
      docs: mockArticles.map(article => ({
        data: () => article
      }))
    })

    rerender(<ImageCarousel articleDir="right" />)
    
    await waitFor(() => {
      expect(screen.getByTestId('marquee')).toBeInTheDocument()
    })
  })

  it('fetches data from correct Firestore collection', async () => {
    const { collection, getDocs } = await import('firebase/firestore')
    const mockArticles = [
      {
        TITLE: 'Test Article',
        LINK: 'https://example.com',
        IMAGE: 'test-image.jpg'
      }
    ]

    collection.mockReturnValue('mock-collection')
    getDocs.mockResolvedValueOnce({
      docs: mockArticles.map(article => ({
        data: () => article
      }))
    })

    render(<ImageCarousel articleDir="left" />)

    await waitFor(() => {
      expect(collection).toHaveBeenCalledWith({}, 'covers')
    })
  })
}) 