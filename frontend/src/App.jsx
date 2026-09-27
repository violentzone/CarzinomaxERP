import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/layout/AppLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import FinancePage from './pages/finance/FinancePage'
import ScmPage from './pages/scm/ScmPage'
import HrPage from './pages/hr/HrPage'
import DevTrackingPage from './pages/devTracking/DevTrackingPage'
import UsersPage from './pages/admin/Users'
import NotFound from './pages/NotFound'

const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Dashboard />, handle: { title: 'Dashboard' } },
      { path: 'dev-tracking', element: <DevTrackingPage />, handle: { title: 'Dev Tracking' } },
      { path: 'hr', element: <HrPage />, handle: { title: 'People & Payroll' } },
      { path: 'finance', element: <FinancePage />, handle: { title: 'Finance' } },
      { path: 'scm', element: <ScmPage />, handle: { title: 'Purchases' } },
      { path: 'admin/users', element: <UsersPage />, handle: { title: 'Users & Access' } },
      { path: '*', element: <NotFound />, handle: { title: 'Not Found' } },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
