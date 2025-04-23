// src/App.jsx
import { useEffect, useState } from 'react';
import {
  onAuthStateChanged,
  signInWithPopup,
} from 'firebase/auth';
import { auth, provider } from './firebase';

import AdminPage from './pages/AdminPage';
import HomePage from './pages/HomePage';

// Use emails, not UIDs
const allowedEmails = ['adamwickenden94@gmail.com'];

function App() {
  const path = window.location.pathname;
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  // Listen for auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      console.log('Auth state changed:', currentUser);
      setUser(currentUser);
      setAuthChecked(true);
    });

    return () => unsubscribe();
  }, []);

  // Handle login for /admin
  useEffect(() => {
    if (path === '/admin' && authChecked && !user) {
      signInWithPopup(auth, provider)
        .then((result) => {
          console.log('Signed in with popup:', result.user);
          setUser(result.user);
        })
        .catch((error) => {
          console.error('Popup sign-in error:', error);
        });
    }
  }, [path, authChecked, user]);

  if (path === '/admin') {
    if (!authChecked) return null;
    if (!user) return null;

    if (!allowedEmails.includes(user.email)) {
      window.location.href = '/';
      return null;
    }

    return <AdminPage />;
  }

  return <HomePage />;
}

export default App;