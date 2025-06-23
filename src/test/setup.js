import '@testing-library/jest-dom'
import React from 'react'

// Mock Firebase
vi.mock('../firebase', () => ({
  db: {},
  auth: {},
  storage: {}
}))

// Mock react-fast-marquee
vi.mock('react-fast-marquee', () => ({
  default: ({ children }) => React.createElement('div', { 'data-testid': 'marquee' }, children)
}))

// Mock fetch globally
global.fetch = vi.fn()

// Mock DOMParser
global.DOMParser = class DOMParser {
  parseFromString(string, contentType) {
    return {
      querySelector: vi.fn(),
      querySelectorAll: vi.fn()
    }
  }
} 