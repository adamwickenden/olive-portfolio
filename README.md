# Olive Pometsey Portfolio Website

A modern, responsive portfolio website for investigative journalist Olive Pometsey, built with React and deployed on Firebase Hosting.

## 🌐 Live Website

The website showcases Olive's work as a freelance investigative journalist based in London, featuring her articles, publications, and contact information.

## 🏗️ Architecture

- **Frontend**: React 18 with Vite for fast development and building
- **Routing**: React Router DOM for client-side navigation
- **Authentication**: Firebase Auth with Google OAuth for admin access
- **Database**: Cloud Firestore for article storage and management
- **Storage**: Firebase Storage for images and media files
- **Hosting**: Firebase Hosting with automatic deployments
- **CI/CD**: GitHub Actions for automated testing, linting, and deployment

## 📁 Project Structure

```
olive-portfolio/
├── src/
│   ├── components/          # Reusable React components
│   │   ├── ArticleCard.jsx  # Individual article display
│   │   ├── ImageCarousel.jsx # Article carousel component
│   │   └── __tests__/       # Component tests
│   ├── pages/               # Main page components
│   │   ├── HomePage.jsx     # Public portfolio page
│   │   ├── AdminPage.jsx    # Protected admin interface
│   │   └── __tests__/       # Page tests
│   ├── assets/              # Static assets (images, etc.)
│   ├── firebase.js          # Firebase configuration
│   ├── App.jsx              # Main app component with routing
│   └── main.jsx             # React app entry point
├── functions/               # Firebase Cloud Functions (Python)
├── .github/workflows/       # GitHub Actions CI/CD pipeline
├── coverage/                # Test coverage reports
└── dist/                    # Built application (generated)
```

## 🚀 Getting Started

### Prerequisites

- Node.js 20.x or higher
- npm or yarn package manager
- Firebase CLI (for deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd olive-portfolio
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   VITE_FIREBASE_API_KEY=your_firebase_api_key
   VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=your_project_id
   VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
   VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
   VITE_FIREBASE_APP_ID=your_app_id
   VITE_ALLOWED_USERS=admin@example.com,user@example.com
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

The application will be available at `http://localhost:5173`

## 🧪 Testing

The project uses Vitest and React Testing Library for comprehensive testing.

### Available Test Commands

```bash
# Run all tests
npm run test

# Run tests with UI interface
npm run test:ui

# Run tests with coverage report
npm run test:coverage
```

### Test Coverage

Current test suite covers:
- **HomePage**: 10 tests covering all sections, headings, and content rendering
- **ImageCarousel**: 9 tests covering loading states, article rendering, and error handling
- **ArticleCard**: 5 tests covering loading states, data rendering, and fallback values
- **AdminPage**: 7 tests covering form rendering, field updates, and basic interactions

### Test Configuration

- **Framework**: Vitest with jsdom environment
- **Testing Library**: React Testing Library for component testing
- **Mocking**: Firebase services, external libraries, and DOM APIs
- **Coverage**: Istanbul/c8 for code coverage reporting

## 🔍 Linting

The project uses ESLint for code quality and consistency.

```bash
# Run linter
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix
```

### Linting Configuration

- **ESLint**: Modern JavaScript/React rules
- **Plugins**: React, React Hooks, React Refresh
- **Standards**: ES2022+ features, React best practices

## 🚀 Building and Deployment

### Local Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Firebase Deployment

The project uses Firebase Hosting with automatic deployments via GitHub Actions.

**Manual Deployment:**
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Deploy to Firebase
firebase deploy
```

## 🔄 CI/CD Pipeline

The project uses GitHub Actions for automated testing and deployment.

### Workflow Overview

1. **Test Stage** (runs on all pushes and PRs):
   - Checkout code
   - Setup Node.js 20
   - Install dependencies
   - Run ESLint
   - Run test suite with coverage
   - Upload coverage to Codecov

2. **Deploy Stage** (runs only on main branch pushes):
   - Runs after successful tests
   - Build production bundle
   - Deploy to Firebase Hosting

### Workflow Configuration

- **Triggers**: All branch pushes and pull requests
- **Node Version**: 20.x
- **Dependencies**: Cached for faster builds
- **Coverage**: Integrated with Codecov
- **Deployment**: Automatic on main branch merges

### Branch Protection

- `main` branch requires PR reviews
- All status checks must pass before merging
- Tests and linting must pass in CI

## 🔐 Authentication & Admin Access

The admin panel (`/admin`) is protected by Firebase Authentication:

- **Provider**: Google OAuth
- **Access Control**: Email-based allowlist via environment variables
- **Protected Routes**: React Router with authentication guards
- **Session Management**: Firebase Auth state persistence

## 📊 Features

### Public Features
- **Responsive Design**: Mobile-first, modern UI
- **Article Carousel**: Dynamic display of featured articles
- **Publication Showcase**: Professional background and achievements
- **Contact Information**: Direct communication channels

### Admin Features
- **Article Management**: Upload and manage article content
- **Image Upload**: Firebase Storage integration
- **CSV Import**: Bulk article data import
- **Real-time Updates**: Firestore integration for live content updates

## 🛠️ Technologies Used

### Frontend
- React 18.3.1
- React Router DOM 7.5.1
- Vite 5.4.18
- CSS3 with modern features

### Backend & Services
- Firebase Auth
- Cloud Firestore
- Firebase Storage
- Firebase Hosting
- Firebase Functions (Python)

### Development Tools
- Vitest & React Testing Library
- ESLint with React plugins
- GitHub Actions
- Codecov for coverage reporting

### Dependencies
- `react-fast-marquee`: Smooth scrolling text effects
- `react-responsive-carousel`: Image carousel functionality
- `@dhaiwat10/react-link-preview`: Link preview cards
- `papaparse`: CSV parsing for data import

## 📈 Performance & Monitoring

- **Build Optimization**: Vite's fast bundling and tree-shaking
- **Code Splitting**: React Router lazy loading
- **Asset Optimization**: Automatic image and bundle optimization
- **Monitoring**: Firebase Analytics and Performance Monitoring

## 📝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`npm run test && npm run lint`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Write tests for new components and features
- Follow the existing code style and ESLint rules
- Ensure all CI checks pass before requesting review
- Update documentation for significant changes

## 📄 License

This project is private and proprietary. All rights reserved.