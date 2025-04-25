import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { onAuthStateChanged, signInWithPopup } from 'firebase/auth';
import { auth, provider } from './firebase';

import AdminPage from './pages/AdminPage';
import HomePage from './pages/HomePage';

const allowedEmails = import.meta.env.VITE_ALLOWED_USERS.split(", ");

function AdminRoute() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

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

    if (!authChecked){
        return <div>Loading...</div>
    }

    return user && allowedEmails.includes(user.email) ? <Outlet/> : <Navigate to="/" replace />
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        {/* Protected Admin Route */}
        <Route element={<AdminRoute/>}>
        <Route
          path="/admin"
          element={<AdminPage />}
        />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;