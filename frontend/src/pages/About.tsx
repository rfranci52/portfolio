import { Navigate } from 'react-router-dom'

// The /about address stays valid for old links and lands on the home page.
export default function About() {
  return <Navigate to="/" replace />
}
