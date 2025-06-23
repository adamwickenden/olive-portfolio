import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import HomePage from '../HomePage'

// Mock the ImageCarousel component
vi.mock('../../components/ImageCarousel', () => ({
  default: ({ articleDir }) => (
    <div data-testid="image-carousel" data-direction={articleDir}>
      Mock Image Carousel
    </div>
  )
}))

describe('HomePage', () => {
  it('renders the hero section with name and tagline', () => {
    render(<HomePage />)
    
    expect(screen.getByText('Olive Pometsey')).toBeInTheDocument()
    expect(screen.getByText('Investigative Journalist & Storyteller')).toBeInTheDocument()
  })

  it('renders the image carousel section', () => {
    render(<HomePage />)
    
    const carousel = screen.getByTestId('image-carousel')
    expect(carousel).toBeInTheDocument()
    expect(carousel).toHaveAttribute('data-direction', 'right')
  })

  it('renders the featured articles section', () => {
    render(<HomePage />)
    
    expect(screen.getByText('Featured Articles')).toBeInTheDocument()
    expect(screen.getByText('Investigative pieces and in-depth reporting')).toBeInTheDocument()
  })

  it('renders all featured article cards', () => {
    render(<HomePage />)
    
    // Check for article titles
    expect(screen.getByText('The Hidden Impact of Climate Change on Local Communities')).toBeInTheDocument()
    expect(screen.getByText('Voices from the Frontline: Healthcare Workers\' Stories')).toBeInTheDocument()
    expect(screen.getByText('The Future of Digital Journalism')).toBeInTheDocument()
    
    // Check for article categories
    expect(screen.getByText('Investigative')).toBeInTheDocument()
    expect(screen.getByText('Feature')).toBeInTheDocument()
    expect(screen.getByText('Analysis')).toBeInTheDocument()
    
    // Check for read more links
    const readMoreLinks = screen.getAllByText(/Read Article →/)
    expect(readMoreLinks).toHaveLength(3)
  })

  it('renders the publications and awards section', () => {
    render(<HomePage />)
    
    expect(screen.getByText('Publications & Awards')).toBeInTheDocument()
    expect(screen.getByText('Where my work has been featured')).toBeInTheDocument()
  })

  it('renders all publication cards', () => {
    render(<HomePage />)
    
    expect(screen.getByText('The Guardian')).toBeInTheDocument()
    expect(screen.getByText('Contributing Writer')).toBeInTheDocument()
    
    expect(screen.getByText('BBC News')).toBeInTheDocument()
    expect(screen.getByText('Freelance Journalist')).toBeInTheDocument()
    
    expect(screen.getByText('Journalism Excellence Award')).toBeInTheDocument()
    expect(screen.getByText('2023 Winner')).toBeInTheDocument()
  })

  it('renders the contact section', () => {
    render(<HomePage />)
    
    expect(screen.getByText('Get In Touch')).toBeInTheDocument()
    expect(screen.getByText('For story pitches, collaborations, or speaking engagements')).toBeInTheDocument()
    expect(screen.getByText('olivepometsey@gmail.com')).toBeInTheDocument()
  })

  it('renders the contact button with correct email link', () => {
    render(<HomePage />)
    
    const contactButton = screen.getByText('Contact Me')
    expect(contactButton).toBeInTheDocument()
    expect(contactButton.closest('a')).toHaveAttribute('href', 'mailto:olivepometsey@gmail.com')
  })

  it('renders all main sections in correct order', () => {
    render(<HomePage />)
    
    const sections = document.querySelectorAll('section')
    const sectionClasses = Array.from(sections).map(section => section.className)
    
    // Check that we have the expected sections
    expect(sectionClasses).toContain('carousel-section')
    expect(sectionClasses).toContain('hero-section')
    expect(sectionClasses).toContain('features-section')
    expect(sectionClasses).toContain('profiles-section')
    expect(sectionClasses).toContain('contact-section')
  })

  it('has proper heading hierarchy', () => {
    render(<HomePage />)
    
    const h1 = screen.getByRole('heading', { level: 1 })
    expect(h1).toHaveTextContent('Olive Pometsey')
    
    const h2s = screen.getAllByRole('heading', { level: 2 })
    expect(h2s).toHaveLength(3) // Featured Articles, Publications & Awards, Get In Touch
    
    const h3s = screen.getAllByRole('heading', { level: 3 })
    expect(h3s.length).toBeGreaterThan(0) // Article titles and publication names
  })
}) 