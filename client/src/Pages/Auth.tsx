import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { supabase } from "../lib/supabase"

const Auth = () => {
  const navigate = useNavigate()

  useEffect(() => {
    const checkSession = async () => {
      const { data } = await supabase.auth.getSession()

      if (data.session) {
        navigate("/dashboard", { replace: true })
      }
    }

    checkSession()

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (session) {
        navigate("/dashboard", { replace: true })
      }
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [navigate])

  const login = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: `${window.location.origin}/auth`,
      },
    })
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1>Sign in</h1>
        <p>Continue with GitHub to access the search assistant.</p>
        <button className="ask-button ask-button--auth" onClick={login}>
          Sign in with GitHub
        </button>
      </div>
    </div>
  )
}

export default Auth