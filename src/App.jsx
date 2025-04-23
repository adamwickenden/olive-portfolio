import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { onAuthStateChanged, signInWithPopup } from 'firebase/auth';
import { auth, provider } from './firebase';

import AdminPage from './pages/AdminPage';
import HomePage from './pages/HomePage';

const allowedEmails = ['adamwickenden94@gmail.com', 'olivepometsey@gmail.com'];

function App() {
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

  // Handle login for /admin route
  useEffect(() => {
    if (authChecked && !user) {
      signInWithPopup(auth, provider)
        .then((result) => {
          console.log('Signed in with popup:', result.user);
          setUser(result.user);
        })
        .catch((error) => {
          console.error('Popup sign-in error:', error);
        });
    }
  }, [authChecked, user]);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        
        {/* Protected Admin Route */}
        <Route
          path="/admin"
          element={
            !authChecked ? (
              <div>Loading...</div>
            ) : user && allowedEmails.includes(user.email) ? (
              <AdminPage />
            ) : (
              <Navigate to="/" replace />
            )
          }
        />
      </Routes>
    </Router>
  );
}

export default App;