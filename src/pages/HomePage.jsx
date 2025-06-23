import React from 'react';
import ImageCarousel from '../components/ImageCarousel';
import '../pages/HomePage.css';

const HomePage = () => {
  return (
    <div className="home-page">
      <section className="carousel-section">
        <div className="carousel-container">
          <ImageCarousel articleDir="right" />
        </div>
      </section>

      <section className="hero-section">
        <div className="hero-content">
          <h1 className="name">Olive Pometsey - ACTIONS CHECK</h1>
          <p className="tagline">Investigative Journalist & Storyteller</p>
        </div>
      </section>

      <section className="features-section">
        <div className="section-header">
          <h2>Featured Articles</h2>
          <p>Investigative pieces and in-depth reporting</p>
        </div>
        <div className="features-grid">
          <div className="feature-card">
            <span className="article-category">Investigative</span>
            <h3>The Hidden Impact of Climate Change on Local Communities</h3>
            <p>A year-long investigation into how climate change is affecting small coastal towns</p>
            <a href="#" className="read-more">Read Article →</a>
          </div>
          <div className="feature-card">
            <span className="article-category">Feature</span>
            <h3>Voices from the Frontline: Healthcare Workers' Stories</h3>
            <p>Personal accounts from healthcare professionals during the pandemic</p>
            <a href="#" className="read-more">Read Article →</a>
          </div>
          <div className="feature-card">
            <span className="article-category">Analysis</span>
            <h3>The Future of Digital Journalism</h3>
            <p>An in-depth look at how technology is reshaping modern journalism</p>
            <a href="#" className="read-more">Read Article →</a>
          </div>
        </div>
      </section>

      <section className="profiles-section">
        <div className="section-header">
          <h2>Publications & Awards</h2>
          <p>Where my work has been featured</p>
        </div>
        <div className="profiles-grid">
          <div className="publication-card">
            <h3>The Guardian</h3>
            <p>Contributing Writer</p>
          </div>
          <div className="publication-card">
            <h3>BBC News</h3>
            <p>Freelance Journalist</p>
          </div>
          <div className="publication-card">
            <h3>Journalism Excellence Award</h3>
            <p>2023 Winner</p>
          </div>
        </div>
      </section>

      <section className="contact-section">
        <div className="section-header">
          <h2>Get In Touch</h2>
          <p>For story pitches, collaborations, or speaking engagements</p>
          <br></br>
          <p>olivepometsey@gmail.com</p>
        </div>
        <div className="contact-content">
          <a href="mailto:olivepometsey@gmail.com" className="contact-button">
            Contact Me
          </a>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
