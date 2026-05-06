import { createClient } from "@supabase/supabase-js/dist/index.cjs"





const Auth = () => {
    const supabase = createClient(import.meta.env.VITE_SUPABASE_URL,import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY)

    const login = async() => {
        const {data,error} =await supabase.auth.signInWithOAuth({
            provider:"github"
        })

        if(error){
            alert("Error while signin")
        }
        console.log(data)
    }

    
    return (
        <>
        <button onClick={() => login()}>Login With GitHub</button>
        </>
    )
}

export default Auth