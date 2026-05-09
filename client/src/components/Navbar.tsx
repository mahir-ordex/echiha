import axios from "axios";
import { BsPerplexity, BsStars } from "react-icons/bs";
import { FiPlus } from "react-icons/fi";
import { MdOutlineExpandMore } from "react-icons/md";
import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

const Navbar = () => {
    const [showHistory, setShowHistory] = useState(false)

    const [token, setToken] = useState<unknown | string>(null)
    const [history, setHistory] = useState<string[]>([])

    const handleFetchData = async() => {
        try {
            if (!token) return
            const res: any = await axios.get("/api/conversations", {
                headers:{
                    "Authorization":`Bearer ${token}`
                }
            })
            setHistory(res.data?.conversation ?? [])
        } catch (error) {
            console.error(error)
            
        }
    }
    useEffect(() => {
        handleFetchData()
    },[])

    return (
        <>
        <header className="topbar">
            <div className="topbar__left">
                <span className="topbar__brand">
                    <BsStars />
                    Perplexity-ish
                </span>
                <span className="topbar__badge">Search + sources</span>
            </div>

            <div className="topbar__right">
                <NavLink to="/dashboard" className="topbar__button">
                    <FiPlus />
                    New
                </NavLink>
            </div>
        </header>

        <span><BsPerplexity/> Perplexity </span>

        <span onClick={() => setShowHistory(false)}><MdOutlineExpandMore/> History</span>
        <div>
            {showHistory && history.length > 0 && history.map((title: string, idx: number) => (
                <li key={idx}>{title}</li>
            ))}
        </div>
        </>
    )
}

export default Navbar;