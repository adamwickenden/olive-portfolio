import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';

const ArticleCard = ({ url }) => {
  const [metadata, setMetadata] = useState({
    title: '',
    description: '',
    image: '',
    siteName: '',
    loading: true,
    error: null
  });

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        // Using a proxy service to avoid CORS issues
        const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(url)}`;
        const response = await fetch(proxyUrl);
        const data = await response.json();
        
        // Create a temporary DOM element to parse the HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(data.contents, 'text/html');

        // Extract metadata
        const title = doc.querySelector('meta[property="og:title"]')?.content || 
                     doc.querySelector('title')?.textContent || '';
        
        const description = doc.querySelector('meta[property="og:description"]')?.content || 
                          doc.querySelector('meta[name="description"]')?.content || '';
        
        const image = doc.querySelector('meta[property="og:image"]')?.content || '';
        
        const siteName = doc.querySelector('meta[property="og:site_name"]')?.content || 
                        new URL(url).hostname;

        setMetadata({
          title,
          description,
          image,
          siteName,
          loading: false
        });
      } catch (error) {
        console.error('Error fetching metadata:', error);
        setMetadata(prev => ({
          ...prev,
          loading: false,
          error: 'Failed to load article preview'
        }));
      }
    };

    fetchMetadata();
  }, [url]);

  if (metadata.loading) {
    return (
      <div className="feature-card loading">
        <div className="loading-placeholder"></div>
      </div>
    );
  }

  if (metadata.error) {
    return (
      <div className="feature-card error">
        <h3>Error loading article</h3>
        <p>{metadata.error}</p>
      </div>
    );
  }

  return (
    <div className="feature-card">
      <span className="article-category">{metadata.siteName}</span>
      {metadata.image && (
        <div className="article-image">
          <img src={metadata.image} alt={metadata.title} />
        </div>
      )}
      <h3>{metadata.title}</h3>
      <p>{metadata.description}</p>
      <a href={url} className="read-more" target="_blank" rel="noopener noreferrer">
        Read Article
      </a>
    </div>
  );
};

ArticleCard.propTypes = {
  url: PropTypes.string.isRequired
};

export default ArticleCard; 