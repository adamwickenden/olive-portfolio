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
      <div>
        <Marquee autoFill={true} style={{ width: '2000px' }} direction={articleDir} speed={25}>
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
            <p>     &#128557;   </p>
          )}
        </Marquee>
      </div>
    );
  };
  
  export default ImageCarousel;