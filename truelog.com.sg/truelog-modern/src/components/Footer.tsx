import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

// TrueLog Brand Colors
const TRUELOG_BLUE = '#385CF2';
const TRUELOG_CYAN = '#0E9ED5';

const Footer: React.FC = () => {
  const footerLinks = {
    Services: [
      { name: 'Freight Forwarding', href: '/services/freight-forwarding' },
      { name: 'Global Fulfillment', href: '/services/global-fulfillment' },
      { name: 'IT Logistics', href: '/services/ict-logistics' },
      { name: 'IOR/EOR Solutions', href: '/services/ior-eor-solutions' },
      { name: 'Compliance', href: '/services/compliance' },
    ],
    Company: [
      { name: 'About Us', href: '/about-us' },
      { name: 'Global Coverage', href: '/global-coverage' },
      { name: 'Careers', href: '/careers' },
      { name: 'Contact Us', href: '/contact-us' },
    ],
    Resources: [
      { name: 'FAQ', href: '/faq' },
      { name: 'Blog', href: '/resources' },
      { name: 'Case Studies', href: '/resources' },
      { name: 'Support', href: '/contact-us' },
    ],
    Legal: [
      { name: 'Privacy Policy', href: '/privacy-policy' },
      { name: 'Terms of Service', href: '/terms-of-service' },
      { name: 'Cookie Policy', href: '/cookie-policy' },
    ]
  };

  const socialLinks = [
    { name: 'LinkedIn', icon: 'L', href: 'https://linkedin.com' },
    { name: 'Twitter', icon: 'X', href: 'https://twitter.com' },
    { name: 'Facebook', icon: 'F', href: 'https://facebook.com' },
    { name: 'Instagram', icon: 'I', href: 'https://instagram.com' },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <footer className="bg-slate-950 relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0">
        <motion.div 
          className="absolute top-0 left-1/4 w-96 h-96 rounded-full blur-3xl"
          style={{ background: `${TRUELOG_BLUE}08` }}
          animate={{ scale: [1, 1.1, 1], opacity: [0.5, 0.8, 0.5] }}
          transition={{ duration: 10, repeat: Infinity }}
        />
        <motion.div 
          className="absolute bottom-0 right-1/4 w-80 h-80 rounded-full blur-3xl"
          style={{ background: `${TRUELOG_CYAN}08` }}
          animate={{ scale: [1.1, 1, 1.1], opacity: [0.8, 0.5, 0.8] }}
          transition={{ duration: 10, repeat: Infinity, delay: 2 }}
        />
      </div>

      {/* Grid Pattern */}
      <div 
        className="absolute inset-0" 
        style={{ 
          background: 'linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)',
          backgroundSize: '40px 40px'
        }} 
      />

      {/* Main Footer Content */}
      <div className="relative container-custom pt-20 pb-12">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-12 mb-16"
        >
          {/* Brand Section */}
          <motion.div variants={itemVariants} className="lg:col-span-2">
            <Link to="/" className="inline-block mb-6">
              <motion.div
                whileHover={{ scale: 1.05 }}
                className="flex items-center"
              >
                <img
                  src={`${process.env.PUBLIC_URL}/assets/images/truelog-logo.png`}
                  alt="Truelog Logo"
                  className="h-10 w-auto"
                />
              </motion.div>
            </Link>

            <p className="text-slate-400 leading-relaxed mb-6 max-w-sm text-[14px]">
              TrueLog offers comprehensive logistics solutions, from freight forwarding
              to IT logistics, ensuring efficiency and reliability across Singapore and beyond.
            </p>

            {/* Contact Info */}
            <div className="space-y-3 text-slate-400">
              <motion.a
                href="mailto:sales@truelog.com.sg"
                className="flex items-center gap-3 hover:text-white transition-colors group"
                whileHover={{ x: 5 }}
              >
                <div 
                  className="w-8 h-8 bg-slate-800 rounded-lg flex items-center justify-center transition-colors"
                  style={{ '--hover-bg': TRUELOG_CYAN } as React.CSSProperties}
                  onMouseEnter={(e) => e.currentTarget.style.background = TRUELOG_CYAN}
                  onMouseLeave={(e) => e.currentTarget.style.background = '#1e293b'}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                sales@truelog.com.sg
              </motion.a>
              <motion.a
                href="tel:+6569093756"
                className="flex items-center gap-3 hover:text-white transition-colors group"
                whileHover={{ x: 5 }}
              >
                <div 
                  className="w-8 h-8 bg-slate-800 rounded-lg flex items-center justify-center"
                  onMouseEnter={(e) => e.currentTarget.style.background = TRUELOG_CYAN}
                  onMouseLeave={(e) => e.currentTarget.style.background = '#1e293b'}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                </div>
                +65 6909 3756
              </motion.a>
              <motion.div
                className="flex items-center gap-3"
                whileHover={{ x: 5 }}
              >
                <div className="w-8 h-8 bg-slate-800 rounded-lg flex items-center justify-center">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  </svg>
                </div>
                Singapore
              </motion.div>
            </div>
          </motion.div>

          {/* Links Sections */}
          {Object.entries(footerLinks).map(([category, links], categoryIndex) => (
            <motion.div
              key={category}
              variants={itemVariants}
              className="lg:col-span-1"
            >
              <h3 className="text-white font-semibold text-sm uppercase tracking-wider mb-6">
                {category}
              </h3>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.name}>
                    <Link
                      to={link.href}
                      className="text-slate-400 hover:text-white transition-colors duration-200 text-sm inline-block group"
                    >
                      <span className="relative">
                        {link.name}
                        <span 
                          className="absolute -bottom-0.5 left-0 w-0 h-px transition-all duration-300 group-hover:w-full"
                          style={{ background: `linear-gradient(90deg, ${TRUELOG_BLUE}, ${TRUELOG_CYAN})` }}
                        />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </motion.div>

        {/* Newsletter Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="border-t border-slate-800 pt-12 mb-12"
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
            <div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Stay Updated with Industry Insights
              </h3>
              <p className="text-slate-400 text-[14px]">
                Get the latest logistics trends, tips, and company updates delivered to your inbox.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-5 py-3.5 bg-slate-800/50 text-white rounded-xl border border-slate-700 focus:outline-none focus:ring-2 focus:border-transparent placeholder-slate-500 transition-all"
                style={{ '--tw-ring-color': TRUELOG_CYAN } as React.CSSProperties}
                onFocus={(e) => e.currentTarget.style.borderColor = TRUELOG_CYAN}
                onBlur={(e) => e.currentTarget.style.borderColor = '#334155'}
              />
              {/* CTA Button - Inter Bold, ALL CAPS, White on #0E9ED5 */}
              <motion.button
                className="px-6 py-3.5 rounded-xl font-bold uppercase tracking-wider text-white text-[14px] transition-all duration-300"
                style={{ backgroundColor: TRUELOG_CYAN }}
                whileHover={{ 
                  scale: 1.02, 
                  boxShadow: `0 10px 30px -10px ${TRUELOG_CYAN}80`,
                  backgroundColor: '#0b7aa6'
                }}
                whileTap={{ scale: 0.98 }}
              >
                SUBSCRIBE
              </motion.button>
            </div>
          </div>
        </motion.div>

        {/* Social Media & Certifications */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="border-t border-slate-800 pt-8"
        >
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            {/* Social Icons */}
            <div className="flex gap-3">
              {socialLinks.map((social) => (
                <motion.a
                  key={social.name}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  whileHover={{ y: -3, scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  className="w-10 h-10 bg-slate-800 rounded-xl flex items-center justify-center text-slate-400 hover:text-white transition-all duration-300"
                  style={{ '--hover-bg': `linear-gradient(135deg, ${TRUELOG_BLUE}, ${TRUELOG_CYAN})` } as React.CSSProperties}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = `linear-gradient(135deg, ${TRUELOG_BLUE}, ${TRUELOG_CYAN})`;
                    e.currentTarget.style.color = 'white';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#1e293b';
                    e.currentTarget.style.color = '#94a3b8';
                  }}
                >
                  <span className="text-sm font-medium">{social.icon}</span>
                </motion.a>
              ))}
            </div>

            {/* Certifications */}
            <div className="flex items-center gap-6 text-slate-500 text-sm">
              {['IATA Certified', 'FIATA Member', 'ISO 9001'].map((cert, index) => (
                <motion.span
                  key={cert}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.2 + index * 0.1 }}
                  className="flex items-center gap-2"
                >
                  <span 
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ backgroundColor: TRUELOG_CYAN }}
                  />
                  {cert}
                </motion.span>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Bottom Bar */}
      <div className="relative border-t border-slate-800">
        <div className="container-custom py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="text-slate-500 text-sm"
            >
              © {new Date().getFullYear()} Truelog. All rights reserved.
            </motion.div>
            <div className="flex gap-6 text-slate-500 text-sm">
              {['Privacy Policy', 'Terms of Service', 'Cookie Settings'].map((item) => (
                <Link
                  key={item}
                  to={`/${item.toLowerCase().replace(/\s+/g, '-')}`}
                  className="hover:text-white transition-colors duration-200 relative group"
                >
                  {item}
                  <span 
                    className="absolute -bottom-0.5 left-0 w-0 h-px transition-all duration-300 group-hover:w-full"
                    style={{ backgroundColor: TRUELOG_CYAN }}
                  />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
