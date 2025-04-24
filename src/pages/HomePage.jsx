import React from 'react';
import ImageCarousel from '../components/ImageCarousel';
import '../pages/HomePage.css';

const HomePage = () => {
  return (
    <div className="home-page">

      <div className="carousel-container">
        <ImageCarousel articleDir="right" />
      </div>

      <div className="name-container">
        <h1>Olive Pometsey</h1>
      </div>

      <div className="sections-container">
        <div className="section">
          <h2>Features</h2>
          {/* Add content for features here */}
        </div>
        <div className="section">
          <h2>Profiles</h2>
          {/* Add content for profiles here */}
        </div>
      </div>

      <div className="contact-section">
        <h2>Contact</h2>
        {/* Add content for contact here */}
      </div>
    
    </div>
  );
};

export default HomePage;
