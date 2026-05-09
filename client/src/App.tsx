import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import Auth from "./Pages/Auth"
import Dashboard from "./Pages/Dashboard"
import Layout from "./Pages/Layout"
import NotFound from "./Pages/notfound"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Route>

        <Route path="/auth" element={<Auth />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
