import React, { useEffect, useState } from 'react';
import { collection, getDocs } from 'firebase/firestore';
import { db } from '../firebase';  // Make sure to import Firestore from firebase.js
import Marquee from "react-fast-marquee";

const ImageCarousel = ({ articleDir }) => {
    const [articles, setArticles] = useState([]);
  
    useEffect(() => {
      const fetchData = async () => {
        // Fetching articles from Firestore
        const querySnapshot = await getDocs(collection(db, 'covers'));
        const data = querySnapshot.docs.map(doc => doc.data());  // Extracting data from documents
        setArticles(data);
      };
  
      fetchData();
    }, []);
  
    return (
      <div style={{ margin: 0, padding: 0 }}>
        <Marquee autoFill={true} style={{ width: '100%' }} direction={articleDir} speed={25}>
          {articles.length > 0 ? (
            articles.map((article, index) => (
              <div key={index}>
                <a href={article.LINK} style={{ color: 'blue', textDecoration: 'underline' }}>
                  <img 
                    // Generate the correct URL for images in Firebase Storage
                    src={`https://firebasestorage.googleapis.com/v0/b/olive-portfolio.firebasestorage.app/o/${encodeURIComponent(article.IMAGE)}?alt=media`} 
                    alt={article.TITLE} 
                    style={{ width: '150px', height: '200px', objectFit: 'cover' }} 
                  />
                </a>
              </div>
            ))
          ) : (
            <p style={{ margin: 0 }}>&#128557;</p>
          )}
        </Marquee>
      </div>
    );
  };
  
  export default ImageCarousel;