// src/components/AdminPage.jsx
import React, { useState } from 'react';
import { db, storage } from '../firebase';  // Import your Firebase setup
import { collection, addDoc } from 'firebase/firestore';
import { ref, uploadBytes } from 'firebase/storage';

import { useNavigate } from 'react-router-dom';
import './AdminPage.css';

const AdminPage = () => {
  const [selectedCollection, setSelectedCollection] = useState('covers');
  const [title, setTitle] = useState('');
  const [link, setLink] = useState('https://');
  const [publication, setPublication] = useState('');
  const [date, setDate] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imageUrl, setImageUrl] = useState('');

  // Navigation
  const navigate = useNavigate();
  const handleHomeClick = () => {
    navigate('/');
  };

  // Handle the form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!imageFile) {
      alert('Please select an image.');
      return;
    }

    // 1. Upload the image to Firebase Storage
    const writeLocation = `${selectedCollection}/${imageFile.name}`
    const imageRef = ref(storage, writeLocation);

    try {
      // Upload the file
      const uploadResult = await uploadBytes(imageRef, imageFile);

      // 3. Create the new document in the selected Firestore collection
      const docRef = await addDoc(collection(db, selectedCollection), {
        DATE: date,
        PUBLICATION: publication,
        TITLE: title,
        LINK: link,
        IMAGE: writeLocation,
      });

      alert('Document added successfully!');
      // Reset form fields
      setTitle('');
      setLink('https://');
      setPublication('');
      setDate('');
      setImageFile(null);
      setImageUrl('');
      document.getElementById('image').value = ''; // Reset the file input by its id
    } catch (error) {
      console.error('Error uploading document:', error);
      alert('Error adding document.');
    }
  };

  // Handle file change
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setImageFile(file);
    setImageUrl(URL.createObjectURL(file)); // Preview image locally
  };

  return (
    <div className="admin-page-container">
      <h2>Admin Page</h2>
      <button onClick={handleHomeClick}>Go to Home</button>

      <form onSubmit={handleSubmit} className="admin-page-form">
        <div className="form-group">
          <label htmlFor="collection">Select Collection</label>
          <select
            id="collection"
            value={selectedCollection}
            onChange={(e) => setSelectedCollection(e.target.value)}
          >
            <option value="covers">covers</option>
            <option value="features">features</option>
            <option value="profiles">profiles</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="title">Title</label>
          <input
            type="text"
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="publication">Publication</label>
          <input
            type="text"
            id="publication"
            value={publication}
            onChange={(e) => setPublication(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="link">Link</label>
          <input
            type="url"
            id="link"
            value={link}
            onChange={(e) => setLink(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="date">Date</label>
          <input
            type="date"
            id="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="image">Image</label>
          <input
            type="file"
            id="image"
            onChange={handleFileChange}
            required
          />
          {imageUrl && <img src={imageUrl} alt="Preview" className="image-preview" />}
        </div>

        <button type="submit">Add Document</button>
      </form>
    </div>
  );
};

export default AdminPage;