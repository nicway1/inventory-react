import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Bars3Icon, XMarkIcon, ChevronDownIcon, SunIcon, MoonIcon } from '@heroicons/react/24/outline';
import { MagneticButton } from './ui';
import { useTheme } from '../contexts/ThemeContext';

// TrueLog Brand Colors
const TRUELOG_BLUE = '#385CF2';
const TRUELOG_CYAN = '#0E9ED5';

const Header: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const location = useLocation();
  const { toggleTheme, isDark } = useTheme();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navigation = [
    {
      name: 'Services',
      href: '/services',
      dropdown: [
        { name: 'Freight Forwarding', href: '/services/freight-forwarding', description: 'Air & sea freight solutions' },
        { name: 'Global Fulfillment', href: '/services/global-fulfillment', description: 'End-to-end warehousing' },
        { name: 'ICT Logistics', href: '/services/ict-logistics', description: 'Technology equipment shipping' },
        { name: 'IOR/EOR Solutions', href: '/services/ior-eor-solutions', description: 'Import/export compliance' },
        { name: 'Compliance', href: '/services/compliance', description: 'Regulatory support' },
      ]
    },
    { name: 'About Us', href: '/about-us' },
    { name: 'Global Coverage', href: '/global-coverage' },
    { name: 'Blog', href: '/blog' },
    { name: 'Resources', href: '/resources' },
    { name: 'FAQ', href: '/faq' },
    { name: 'Contact', href: '/contact-us' },
  ];

  const isActive = (href: string) => location.pathname === href;

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-white/95 dark:bg-slate-900/95 backdrop-blur-lg shadow-lg border-b border-secondary-100 dark:border-slate-700'
          : 'bg-white/95 dark:bg-secondary-900/80 backdrop-blur-md shadow-lg border-b border-secondary-100 dark:border-transparent'
      }`}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
          {/* Logo */}
          <Link to="/" className="flex-shrink-0">
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center cursor-pointer"
            >
              <img
                src={`${process.env.PUBLIC_URL}/assets/images/truelog-logo.png`}
                alt="Truelog Logo"
                className="h-10 w-auto"
              />
            </motion.div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center space-x-1">
            {navigation.map((item) => (
              <div
                key={item.name}
                className="relative"
                onMouseEnter={() => item.dropdown && setActiveDropdown(item.name)}
                onMouseLeave={() => setActiveDropdown(null)}
              >
                <Link
                  to={item.href}
                  className={`relative px-4 py-2 text-sm font-medium transition-colors duration-200 flex items-center gap-1 ${
                    isActive(item.href)
                      ? 'dark:text-white'
                      : 'text-secondary-700 dark:text-white/90 dark:hover:text-white'
                  }`}
                  style={isActive(item.href) ? { color: TRUELOG_BLUE } : undefined}
                  onMouseEnter={(e) => !isActive(item.href) && (e.currentTarget.style.color = TRUELOG_BLUE)}
                  onMouseLeave={(e) => !isActive(item.href) && (e.currentTarget.style.color = '')}
                >
                  <span className="relative">
                    {item.name}
                    {/* Animated underline */}
                    <motion.span
                      className="absolute -bottom-1 left-0 h-0.5 rounded-full"
                      style={{ background: `linear-gradient(90deg, ${TRUELOG_BLUE}, ${TRUELOG_CYAN})` }}
                      initial={{ width: 0 }}
                      animate={{ width: isActive(item.href) ? '100%' : 0 }}
                      whileHover={{ width: '100%' }}
                      transition={{ duration: 0.2 }}
                    />
                  </span>
                  {item.dropdown && (
                    <motion.span
                      animate={{ rotate: activeDropdown === item.name ? 180 : 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <ChevronDownIcon className="h-4 w-4" />
                    </motion.span>
                  )}
                </Link>

                {/* Dropdown Menu */}
                <AnimatePresence>
                  {item.dropdown && activeDropdown === item.name && (
                    <motion.div
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                      className="absolute top-full left-0 mt-2 w-72 bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-secondary-100 dark:border-slate-700 overflow-hidden"
                    >
                      <div className="p-2">
                        {item.dropdown.map((subItem, index) => (
                          <motion.div
                            key={subItem.name}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                          >
                            <Link
                              to={subItem.href}
                              className="flex flex-col px-4 py-3 rounded-xl text-secondary-700 dark:text-slate-300 transition-all duration-200 group"
                              style={{ '--hover-bg': `${TRUELOG_BLUE}10` } as React.CSSProperties}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor = `${TRUELOG_BLUE}10`;
                                e.currentTarget.style.color = TRUELOG_BLUE;
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor = '';
                                e.currentTarget.style.color = '';
                              }}
                            >
                              <span className="font-medium text-sm group-hover:translate-x-1 transition-transform duration-200">
                                {subItem.name}
                              </span>
                              <span 
                                className="text-xs text-secondary-500 dark:text-slate-400 transition-colors"
                                style={{ '--hover-color': TRUELOG_CYAN } as React.CSSProperties}
                              >
                                {subItem.description}
                              </span>
                            </Link>
                          </motion.div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>

          {/* CTA Buttons */}
          <div className="hidden lg:flex items-center gap-3">
            {/* Theme Toggle */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={toggleTheme}
              className={`p-2 rounded-xl transition-all duration-200 text-secondary-700 hover:bg-secondary-100 dark:text-gray-300 dark:hover:bg-slate-700`}
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? (
                <SunIcon className="h-5 w-5" />
              ) : (
                <MoonIcon className="h-5 w-5" />
              )}
            </motion.button>
            <motion.a
              href="https://www.truelog.site/auth/login"
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 text-sm font-medium rounded-xl transition-all duration-200"
              style={{ 
                border: `1px solid ${TRUELOG_BLUE}`,
                color: TRUELOG_BLUE
              }}
              whileHover={{ 
                backgroundColor: `${TRUELOG_BLUE}10`,
                scale: 1.02
              }}
              whileTap={{ scale: 0.98 }}
            >
              Client Login
            </motion.a>
            {/* CTA Button - Inter Bold, ALL CAPS, White on #0E9ED5 */}
            <motion.button
              className="px-5 py-2.5 text-[14px] font-bold uppercase tracking-wider rounded-xl text-white transition-all duration-300"
              style={{ 
                backgroundColor: TRUELOG_CYAN,
                boxShadow: `0 4px 20px -5px ${TRUELOG_CYAN}60`
              }}
              whileHover={{ 
                scale: 1.02,
                boxShadow: `0 8px 30px -5px ${TRUELOG_CYAN}80`,
                backgroundColor: '#0b7aa6'
              }}
              whileTap={{ scale: 0.98 }}
            >
              GET QUOTE
            </motion.button>
          </div>

          {/* Mobile menu button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className={`lg:hidden p-2 rounded-xl transition-colors duration-200 text-secondary-700 hover:bg-secondary-100 dark:text-white dark:hover:bg-white/20`}
          >
            <AnimatePresence mode="wait">
              {isMenuOpen ? (
                <motion.div
                  key="close"
                  initial={{ rotate: -90, opacity: 0 }}
                  animate={{ rotate: 0, opacity: 1 }}
                  exit={{ rotate: 90, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <XMarkIcon className="h-6 w-6" />
                </motion.div>
              ) : (
                <motion.div
                  key="menu"
                  initial={{ rotate: 90, opacity: 0 }}
                  animate={{ rotate: 0, opacity: 1 }}
                  exit={{ rotate: -90, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <Bars3Icon className="h-6 w-6" />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.button>
        </div>

        {/* Mobile Navigation Menu */}
        <AnimatePresence>
          {isMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className="lg:hidden overflow-hidden"
            >
              <motion.div
                initial={{ y: -20 }}
                animate={{ y: 0 }}
                className="px-2 pt-2 pb-6 space-y-1 bg-white/95 dark:bg-slate-800/95 backdrop-blur-lg rounded-2xl mt-2 border border-secondary-100 dark:border-slate-700 shadow-xl"
              >
                {navigation.map((item, index) => (
                  <motion.div
                    key={item.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Link
                      to={item.href}
                      className={`block px-4 py-3 text-base font-medium rounded-xl transition-all duration-200 ${
                        isActive(item.href)
                          ? 'text-white'
                          : 'text-secondary-700 dark:text-slate-300 hover:text-white'
                      }`}
                      style={isActive(item.href) ? { 
                        backgroundColor: `${TRUELOG_BLUE}15`,
                        color: TRUELOG_BLUE
                      } : undefined}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      {item.name}
                    </Link>
                    {/* Mobile dropdown items */}
                    {item.dropdown && (
                      <div className="ml-4 mt-1 space-y-1">
                        {item.dropdown.map((subItem) => (
                          <Link
                            key={subItem.name}
                            to={subItem.href}
                            className="block px-4 py-2 text-sm text-secondary-600 dark:text-slate-400 transition-colors duration-200"
                            style={{ '--hover-color': TRUELOG_BLUE } as React.CSSProperties}
                            onMouseEnter={(e) => e.currentTarget.style.color = TRUELOG_BLUE}
                            onMouseLeave={(e) => e.currentTarget.style.color = ''}
                            onClick={() => setIsMenuOpen(false)}
                          >
                            {subItem.name}
                          </Link>
                        ))}
                      </div>
                    )}
                  </motion.div>
                ))}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="pt-4 px-2 space-y-2"
                >
                  <a
                    href="https://www.truelog.site/auth/login"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full px-4 py-3 text-center font-medium rounded-xl transition-all duration-200"
                    style={{ 
                      border: `1px solid ${TRUELOG_BLUE}`,
                      color: TRUELOG_BLUE
                    }}
                  >
                    Client Login
                  </a>
                  {/* Mobile CTA Button */}
                  <motion.button
                    className="w-full px-4 py-3 text-[14px] font-bold uppercase tracking-wider rounded-xl text-white transition-all duration-300"
                    style={{ 
                      backgroundColor: TRUELOG_CYAN,
                      boxShadow: `0 4px 20px -5px ${TRUELOG_CYAN}60`
                    }}
                    whileTap={{ scale: 0.98 }}
                  >
                    GET QUOTE
                  </motion.button>
                </motion.div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>
    </motion.header>
  );
};

export default Header;
