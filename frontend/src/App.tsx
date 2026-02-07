import { Routes, Route } from 'react-router-dom'

// Placeholder pages - to be implemented
const Dashboard = () => <div className="p-8">Dashboard - Coming Soon</div>
const Tickets = () => <div className="p-8">Tickets - Coming Soon</div>
const Inventory = () => <div className="p-8">Inventory - Coming Soon</div>
const Accessories = () => <div className="p-8">Accessories - Coming Soon</div>
const Customers = () => <div className="p-8">Customers - Coming Soon</div>
const Admin = () => <div className="p-8">Admin - Coming Soon</div>
const Login = () => <div className="p-8">Login - Coming Soon</div>
const NotFound = () => <div className="p-8">404 - Page Not Found</div>

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        {/* Auth Routes */}
        <Route path="/login" element={<Login />} />

        {/* Main Application Routes */}
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tickets/*" element={<Tickets />} />
        <Route path="/inventory/*" element={<Inventory />} />
        <Route path="/accessories/*" element={<Accessories />} />
        <Route path="/customers/*" element={<Customers />} />
        <Route path="/admin/*" element={<Admin />} />

        {/* 404 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </div>
  )
}

export default App
