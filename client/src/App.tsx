import { BrowserRouter, Route, Routes } from "react-router"
import Auth from "./Pages/Auth"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/auth" element={<Auth />} />
        <Route path="*" element={<Auth />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
