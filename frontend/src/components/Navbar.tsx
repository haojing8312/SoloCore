/**
 * Navigation bar component
 */

import { Link, useLocation } from 'react-router-dom';
import { Film } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';

export function Navbar() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: '首页' },
    { path: '/tasks', label: '任务列表' },
    { path: '/stats', label: '统计' },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="fixed top-0 w-full z-50 glass-nav h-16 flex items-center justify-between px-6 lg:px-12">
      {/* Logo */}
      <Link to="/" className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity">
        <div className="bg-black dark:bg-white text-white dark:text-black w-8 h-8 rounded-lg flex items-center justify-center transition-colors">
          <Film className="w-4 h-4" />
        </div>
        <span className="font-semibold text-lg tracking-tight text-gray-900 dark:text-gray-100">
          TextLoom
        </span>
      </Link>

      {/* Navigation */}
      <div className="hidden md:flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-full transition-colors">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`
              px-6 py-1.5 rounded-full text-sm font-medium transition-all
              ${
                isActive(item.path)
                  ? 'bg-white dark:bg-gray-700 shadow-sm text-black dark:text-white'
                  : 'text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white'
              }
            `}
          >
            {item.label}
          </Link>
        ))}
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-4">
        <ThemeToggle />
      </div>
    </nav>
  );
}
