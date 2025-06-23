// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
import { getStorage } from 'firebase/storage';

// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v9-compat and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyClXKjwpGEGJjjV_9O7VqOqWmZ6m4uqRFE",
  authDomain: "olive-portfolio.firebaseapp.com",
  projectId: "olive-portfolio",
  storageBucket: "olive-portfolio.firebasestorage.app",
  messagingSenderId: "1057325844754",
  appId: "1:1057325844754:web:fce9c1e47f1c0efc7a0c4c",
  measurementId: "G-CXJR3QLMQP"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
// Initialize Analytics (but don't assign to variable since it's not used)
getAnalytics(app);

const auth = getAuth(app);
const provider = new GoogleAuthProvider();
// Initialize Firestore
export const db = getFirestore(app);
// Initialize Storage
export const storage = getStorage(app);

export { auth, provider };