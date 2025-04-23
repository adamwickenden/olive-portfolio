// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
import { getStorage } from 'firebase/storage';

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyATAdXF3tyB-p1HKjQg-P5mi0X0KhUthTo",
  authDomain: "olive-portfolio.firebaseapp.com",
  projectId: "olive-portfolio",
  storageBucket: "olive-portfolio.firebasestorage.app",
  messagingSenderId: "876030851212",
  appId: "1:876030851212:web:fe4d57f91cfbc9214be3a9",
  measurementId: "G-4NQZS6ZN36"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

const auth = getAuth(app);
const provider = new GoogleAuthProvider();
const db = getFirestore(app);
const storage = getStorage(app);

export { auth, provider, db, storage};