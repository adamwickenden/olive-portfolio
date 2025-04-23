import React from 'react';
import ImageCarousel from '../components/ImageCarousel'
import headshot from '../assets/headshot.jfif'
import '../pages/HomePage.css'

const HomePage = () => {
  
  return (
    <div className="app">
      <div className="author-col" style={{ maxWidth: '200px' }}>
        <header>
          <div className="header-content">
            <h1 style={{ fontSize: '1.5rem' }}>Olive Pometsey</h1>
            <img src={headshot} className="headshot" alt="Headshot" style={{ maxWidth: '100%' }} />
          </div>
        </header>
        <h2 style={{ fontSize: '1.2rem' }}>About Me</h2>
        <p style={{ fontSize: '0.9rem' }}>
          Welcome to my portfolio! I am a freelance journalist with a passion for storytelling. 
          I specialize in covering a wide range of topics including politics, culture, and human interest stories.
        </p>
      </div>
      <div className="covers">
        <ImageCarousel articleDir="right"/>
        {/* <ImageCarousel articleDir="right"/> */}
      </div>
    </div>
  );
};

export default HomePage;