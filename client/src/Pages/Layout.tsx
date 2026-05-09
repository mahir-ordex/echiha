import { NavLink, Outlet } from "react-router-dom";
import Navbar from "../components/Navbar";

const readRecentChats = (): string[] => {
  try {
    return JSON.parse(localStorage.getItem("pp_recent_chats") ?? "[]") as string[];
  } catch {
    return [];
  }
};

const Layout = () => {
  const recentChats = readRecentChats();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand__logo">P</div>
          <div>
            <div className="brand__kicker">Perplexity style</div>
            <div className="brand__title">Search assistant</div>
          </div>
        </div>

        <NavLink to="/dashboard" className="sidebar__newchat">
          New chat
        </NavLink>

        <div className="sidebar__block">
          <div className="sidebar__label">Recent searches</div>
          <div className="sidebar__list">
            {recentChats.length > 0 ? (
              recentChats.map((item) => (
                <div className="sidebar__item" key={item}>
                  {item}
                </div>
              ))
            ) : (
              <p className="sidebar__empty">No history yet.</p>
            )}
          </div>
        </div>

        <div className="sidebar__footer">Answers with sources, search first.</div>
      </aside>

      <main className="main">
        <Navbar />
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;