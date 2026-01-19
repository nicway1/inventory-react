import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MagneticButton } from './ui';

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
    <footer className="bg-secondary-950 relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl" />
      </div>

      {/* Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px]" />

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
                  src="/assets/images/truelog-logo.png"
                  alt="Truelog Logo"
                  className="h-10 w-auto"
                />
              </motion.div>
            </Link>

            <p className="text-secondary-400 leading-relaxed mb-6 max-w-sm">
              TrueLog offers comprehensive logistics solutions, from freight forwarding
              to IT logistics, ensuring efficiency and reliability across Singapore and beyond.
            </p>

            {/* Contact Info */}
            <div className="space-y-3 text-secondary-400">
              <motion.a
                href="mailto:contact@truelog.com.sg"
                className="flex items-center gap-3 hover:text-white transition-colors group"
                whileHover={{ x: 5 }}
              >
                <div className="w-8 h-8 bg-secondary-800 rounded-lg flex items-center justify-center group-hover:bg-primary-600 transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                contact@truelog.com.sg
              </motion.a>
              <motion.div
                className="flex items-center gap-3"
                whileHover={{ x: 5 }}
              >
                <div className="w-8 h-8 bg-secondary-800 rounded-lg flex items-center justify-center">
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
                      className="text-secondary-400 hover:text-white transition-colors duration-200 text-sm inline-block group"
                    >
                      <span className="relative">
                        {link.name}
                        <span className="absolute -bottom-0.5 left-0 w-0 h-px bg-gradient-to-r from-primary-500 to-accent-cyan transition-all duration-300 group-hover:w-full" />
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
          className="border-t border-secondary-800 pt-12 mb-12"
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
            <div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Stay Updated with Industry Insights
              </h3>
              <p className="text-secondary-400">
                Get the latest logistics trends, tips, and company updates delivered to your inbox.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-5 py-3.5 bg-secondary-800/50 text-white rounded-xl border border-secondary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent placeholder-secondary-500 transition-all"
              />
              <MagneticButton variant="primary" size="md">
                Subscribe
              </MagneticButton>
            </div>
          </div>
        </motion.div>

        {/* Social Media & Certifications */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="border-t border-secondary-800 pt-8"
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
                  className="w-10 h-10 bg-secondary-800 rounded-xl flex items-center justify-center text-secondary-400 hover:bg-gradient-to-br hover:from-primary-600 hover:to-purple-600 hover:text-white transition-all duration-300"
                >
                  <span className="text-sm font-medium">{social.icon}</span>
                </motion.a>
              ))}
            </div>

            {/* Certifications */}
            <div className="flex items-center gap-6 text-secondary-500 text-sm">
              {['IATA Certified', 'FIATA Member', 'ISO 9001'].map((cert, index) => (
                <motion.span
                  key={cert}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.2 + index * 0.1 }}
                  className="flex items-center gap-2"
                >
                  <span className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                  {cert}
                </motion.span>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Bottom Bar */}
      <div className="relative border-t border-secondary-800">
        <div className="container-custom py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="text-secondary-500 text-sm"
            >
              © {new Date().getFullYear()} Truelog. All rights reserved.
            </motion.div>
            <div className="flex gap-6 text-secondary-500 text-sm">
              {['Privacy Policy', 'Terms of Service', 'Cookie Settings'].map((item) => (
                <Link
                  key={item}
                  to={`/${item.toLowerCase().replace(/\s+/g, '-')}`}
                  className="hover:text-white transition-colors duration-200 relative group"
                >
                  {item}
                  <span className="absolute -bottom-0.5 left-0 w-0 h-px bg-primary-500 transition-all duration-300 group-hover:w-full" />
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
