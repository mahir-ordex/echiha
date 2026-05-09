// ProtectedRoute.tsx

import { useEffect, useState } from "react"
import { Navigate } from "react-router-dom"
import { supabase } from "../lib/supabase"

const ProtectedRoute = ({ children }: any) => {
  const [loading, setLoading] = useState(true)
  const [authenticated, setAuthenticated] = useState(false)

  useEffect(() => {
    const check = async () => {
      const { data } = await supabase.auth.getSession()
      setAuthenticated(!!data.session)
      setLoading(false)
    }

    check()

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      setAuthenticated(!!session)
    })

    return () => subscription.unsubscribe()
  }, [])

  if (loading) return null
  if (!authenticated) return <Navigate to="/auth" replace />

  return children
}

export default ProtectedRoute