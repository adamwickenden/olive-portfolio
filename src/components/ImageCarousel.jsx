import React, { useEffect, useState } from 'react';
import Papa from 'papaparse';

import Marquee from "react-fast-marquee";

const articlesRoot = 'src/assets/articles';

const ImageCarousel = ({articleDir}) => {
    const [articles, setArticles] = useState([]);

    useEffect(() => {
        const fetchData = async () => {
            const response = await fetch(`${articlesRoot}/articles.csv`);
            const reader = response.body.getReader();
            const result = await reader.read();
            const decoder = new TextDecoder('utf-8');
            const csv = decoder.decode(result.value);
            const { data } = Papa.parse(csv, { header: true });
            setArticles(data);
        };

        fetchData();
    }, []);

    return (
        <div>
            <Marquee autoFill={true} style={{width:'2000px'}} direction={articleDir} speed={25}>
            {articles.length > 0 ? (
                articles.map((article, index) => (
                    <div key={index}>
                        <a href={article.LINK} style={{ color: 'blue', textDecoration: 'underline' }}>
                            <img 
                                src={`${articlesRoot}/${article.IMAGE}`} 
                                alt={article.TITLE} 
                                style={{ width: '150px', height: '200px', objectFit: 'cover' }} 
                            />
                        </a>
                    </div>
                ))
            ) : (
                <p>No articles available</p>
            )}
            </Marquee>
        </div>
    );
};

export default ImageCarousel;