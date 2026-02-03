import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MapPinIcon, PhoneIcon, EnvelopeIcon, ClockIcon, XMarkIcon, PaperAirplaneIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

// TrueLog Brand Colors
const TRUELOG_BLUE = '#385CF2';
const TRUELOG_CYAN = '#0E9ED5';

// Particle Background Component
const ParticleBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const particles: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      size: number;
      opacity: number;
    }> = [];

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    resize();
    window.addEventListener('resize', resize);

    // Create particles
    for (let i = 0; i < 50; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 1,
        opacity: Math.random() * 0.5 + 0.2,
      });
    }

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(56, 92, 242, ${p.opacity})`;
        ctx.fill();
      });

      // Draw connections
      particles.forEach((p1, i) => {
        particles.slice(i + 1).forEach((p2) => {
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(14, 158, 213, ${0.1 * (1 - dist / 150)})`;
            ctx.stroke();
          }
        });
      });

      requestAnimationFrame(animate);
    };

    animate();

    return () => window.removeEventListener('resize', resize);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
      style={{ opacity: 0.6 }}
    />
  );
};

const ContactUs: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    phone: '',
    service: '',
    message: ''
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [selectedMap, setSelectedMap] = useState<{office: string, mapUrl: string} | null>(null);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    setIsSubmitting(false);
    setIsSubmitted(true);
    
    // Reset after showing success
    setTimeout(() => {
      setIsSubmitted(false);
      setFormData({
        name: '',
        email: '',
        company: '',
        phone: '',
        service: '',
        message: ''
      });
    }, 3000);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const contactInfo = [
    { 
      icon: EnvelopeIcon, 
      title: 'Email us on', 
      content: 'sales@truelog.com.sg', 
      href: 'mailto:sales@truelog.com.sg',
      gradient: `linear-gradient(135deg, ${TRUELOG_BLUE}20, ${TRUELOG_CYAN}20)`
    },
    { 
      icon: PhoneIcon, 
      title: 'Main Office Singapore', 
      content: '+65 6909 3756', 
      href: 'tel:+6569093756',
      gradient: `linear-gradient(135deg, ${TRUELOG_CYAN}20, ${TRUELOG_BLUE}20)`
    },
    { 
      icon: ClockIcon, 
      title: 'Business Hours', 
      content: 'Monday - Friday: 9:00 AM - 6:00 PM',
      gradient: `linear-gradient(135deg, ${TRUELOG_BLUE}15, ${TRUELOG_CYAN}15)`
    }
  ];

  const offices = [
    { 
      country: 'Singapore', 
      office: 'Headquarters', 
      address: '101 Cecil Street #11-05\nSingapore 069533', 
      phone: '+65 6909 3756', 
      flag: '🇸🇬', 
      mapUrl: 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3988.8177207977877!2d103.84798331475427!3d1.2793693990651432!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x31da1911c074a6a3%3A0x2b662908b80b4e5e!2s101%20Cecil%20St%2C%20Singapore!5e0!3m2!1sen!2ssg!4v1640995200000!5m2!1sen!2ssg' 
    },
    { country: 'Vietnam', office: 'Truelog Vietnam', address: 'CT Building, 56 Yen The\nHo Chi Minh City', phone: '+84 397 337 372', flag: '🇻🇳', mapUrl: '' },
    { country: 'India', office: 'TrueLog India', address: 'New Delhi', phone: '+91 979 091 6352', flag: '🇮🇳', mapUrl: '' },
    { country: 'Belgium', office: 'Truelog Europe', address: 'Kerkstraat 61-63\n8370 Blankenberge', phone: '+32 456 390 341', flag: '🇧🇪', mapUrl: '' }
  ];

  const faqs = [
    { question: 'What logistics services do you offer?', answer: 'We provide comprehensive logistics solutions including freight forwarding, global fulfillment, ICT logistics, IOR/EOR services, and compliance management across 50+ countries.' },
    { question: 'How do you ensure cargo security?', answer: 'We implement multi-layered security protocols including GPS tracking, tamper-evident seals, and comprehensive insurance coverage for all shipments.' },
    { question: 'What are your delivery timeframes?', answer: 'Express air freight: 1-3 days, standard air freight: 3-7 days, sea freight: 15-45 days. We provide real-time tracking for all shipments.' },
    { question: 'Do you handle customs clearance?', answer: 'Yes, we provide complete customs clearance services including documentation, duty calculation, permit applications, and compliance with local regulations.' }
  ];

  return (
    <div className="pt-16 bg-white dark:bg-slate-900">
      {/* Hero Section */}
      <section className="relative py-24 overflow-hidden" style={{ background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)` }}>
        <ParticleBackground />
        
        {/* Gradient Orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <motion.div 
            className="absolute -top-40 -right-40 w-96 h-96 rounded-full blur-3xl"
            style={{ background: 'rgba(255,255,255,0.1)' }}
            animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
            transition={{ duration: 8, repeat: Infinity }}
          />
          <motion.div 
            className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full blur-3xl"
            style={{ background: 'rgba(255,255,255,0.1)' }}
            animate={{ scale: [1.2, 1, 1.2], opacity: [0.5, 0.3, 0.5] }}
            transition={{ duration: 10, repeat: Infinity }}
          />
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-block px-4 py-2 rounded-full text-sm font-medium mb-6 bg-white/20 text-white backdrop-blur-sm"
            >
              Get in Touch
            </motion.span>
            {/* H1 - Inter Bold, 40-48px */}
            <h1 className="text-[40px] lg:text-[48px] font-bold text-white mb-6 leading-tight">
              Contact Us
            </h1>
            {/* Body Text */}
            <p className="text-[16px] lg:text-[18px] text-white/90 max-w-3xl mx-auto leading-relaxed">
              If you'd like to find out more about our services, please complete the contact form below.
            </p>
          </motion.div>
        </div>

        {/* Wave Divider */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg viewBox="0 0 1440 120" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full">
            <path d="M0 120L60 105C120 90 240 60 360 45C480 30 600 30 720 37.5C840 45 960 60 1080 67.5C1200 75 1320 75 1380 75L1440 75V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z" fill="white" className="dark:fill-slate-900"/>
          </svg>
        </div>
      </section>

      {/* Contact Form & Info */}
      <section className="py-20 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            {/* Contact Form */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="relative"
            >
              <div 
                className="absolute inset-0 rounded-3xl blur-xl opacity-30"
                style={{ background: `linear-gradient(135deg, ${TRUELOG_BLUE}30, ${TRUELOG_CYAN}30)` }}
              />
              <div className="relative bg-white dark:bg-slate-800 rounded-3xl p-8 lg:p-10 shadow-xl border border-slate-100 dark:border-slate-700">
                <div className="text-center mb-8">
                  {/* H2 - Inter Bold, 28-32px, #000000 */}
                  <h2 className="text-[28px] lg:text-[32px] font-bold text-black dark:text-white mb-4">
                    Get a Quote
                  </h2>
                  <p className="text-[16px] text-black dark:text-slate-300">
                    Tell us about your logistics needs
                  </p>
                </div>

                <AnimatePresence mode="wait">
                  {isSubmitted ? (
                    <motion.div
                      key="success"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      className="flex flex-col items-center justify-center py-16"
                    >
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', delay: 0.2 }}
                        className="w-20 h-20 rounded-full flex items-center justify-center mb-6"
                        style={{ background: `linear-gradient(135deg, ${TRUELOG_BLUE}, ${TRUELOG_CYAN})` }}
                      >
                        <CheckCircleIcon className="h-10 w-10 text-white" />
                      </motion.div>
                      <h3 className="text-2xl font-bold text-black dark:text-white mb-2">Message Sent!</h3>
                      <p className="text-slate-600 dark:text-slate-400">We'll get back to you shortly.</p>
                    </motion.div>
                  ) : (
                    <motion.form
                      key="form"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      onSubmit={handleSubmit}
                      className="space-y-6"
                    >
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {[
                          { name: 'name', label: 'Full Name', type: 'text', required: true },
                          { name: 'email', label: 'Email Address', type: 'email', required: true },
                          { name: 'company', label: 'Company', type: 'text', required: false },
                          { name: 'phone', label: 'Phone Number', type: 'tel', required: false },
                        ].map((field) => (
                          <div key={field.name} className="relative">
                            <label className="block text-sm font-medium text-black dark:text-slate-300 mb-2">
                              {field.label} {field.required && '*'}
                            </label>
                            <motion.input
                              type={field.type}
                              name={field.name}
                              required={field.required}
                              value={formData[field.name as keyof typeof formData]}
                              onChange={handleChange}
                              onFocus={() => setFocusedField(field.name)}
                              onBlur={() => setFocusedField(null)}
                              className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-700/50 border-2 rounded-xl text-black dark:text-white placeholder-slate-400 transition-all duration-300"
                              style={{
                                borderColor: focusedField === field.name ? TRUELOG_CYAN : 'transparent',
                                boxShadow: focusedField === field.name ? `0 0 0 3px ${TRUELOG_CYAN}20` : 'none'
                              }}
                              whileFocus={{ scale: 1.01 }}
                            />
                          </div>
                        ))}
                      </div>

                      <div className="relative">
                        <label className="block text-sm font-medium text-black dark:text-slate-300 mb-2">Enquiry Type</label>
                        <select
                          name="service"
                          value={formData.service}
                          onChange={handleChange}
                          onFocus={() => setFocusedField('service')}
                          onBlur={() => setFocusedField(null)}
                          className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-700/50 border-2 rounded-xl text-black dark:text-white transition-all duration-300"
                          style={{
                            borderColor: focusedField === 'service' ? TRUELOG_CYAN : 'transparent',
                            boxShadow: focusedField === 'service' ? `0 0 0 3px ${TRUELOG_CYAN}20` : 'none'
                          }}
                        >
                          <option value="">Please Select</option>
                          <option value="General Enquiry">General Enquiry</option>
                          <option value="Service Enquiry">Service Enquiry</option>
                          <option value="Career Opportunity">Career Opportunity</option>
                        </select>
                      </div>

                      <div className="relative">
                        <label className="block text-sm font-medium text-black dark:text-slate-300 mb-2">Message *</label>
                        <textarea
                          name="message"
                          required
                          rows={5}
                          value={formData.message}
                          onChange={handleChange}
                          onFocus={() => setFocusedField('message')}
                          onBlur={() => setFocusedField(null)}
                          className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-700/50 border-2 rounded-xl text-black dark:text-white placeholder-slate-400 transition-all duration-300 resize-none"
                          style={{
                            borderColor: focusedField === 'message' ? TRUELOG_CYAN : 'transparent',
                            boxShadow: focusedField === 'message' ? `0 0 0 3px ${TRUELOG_CYAN}20` : 'none'
                          }}
                          placeholder="Tell us about your logistics needs..."
                        />
                      </div>

                      {/* CTA Button - Inter Bold, ALL CAPS, White on #0E9ED5 */}
                      <motion.button
                        whileHover={{ scale: 1.02, boxShadow: `0 10px 40px -10px ${TRUELOG_CYAN}80` }}
                        whileTap={{ scale: 0.98 }}
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full py-4 rounded-xl font-bold uppercase tracking-wider text-[14px] text-white transition-all duration-300 flex items-center justify-center gap-2"
                        style={{ 
                          backgroundColor: TRUELOG_CYAN,
                          boxShadow: `0 4px 20px -5px ${TRUELOG_CYAN}60`
                        }}
                      >
                        {isSubmitting ? (
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                            className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                          />
                        ) : (
                          <>
                            <PaperAirplaneIcon className="h-5 w-5" />
                            SEND MESSAGE
                          </>
                        )}
                      </motion.button>
                    </motion.form>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>

            {/* Contact Information */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="space-y-8"
            >
              <div>
                {/* H2 style */}
                <h2 className="text-[28px] lg:text-[32px] font-bold text-black dark:text-white mb-4">
                  Contact Information
                </h2>
                <p className="text-[16px] text-black dark:text-slate-300 mb-8">
                  Connect with our global offices or reach out through any of these channels.
                </p>
              </div>

              <div className="space-y-4">
                {contactInfo.map((item, index) => (
                  <motion.div
                    key={item.title}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: index * 0.1 }}
                    whileHover={{ scale: 1.02, y: -2 }}
                    className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-lg border border-slate-100 dark:border-slate-700 transition-all duration-300"
                    style={{ background: item.gradient }}
                  >
                    <div className="flex items-start space-x-4">
                      <motion.div
                        whileHover={{ rotate: 10 }}
                        className="w-14 h-14 rounded-xl flex items-center justify-center text-white"
                        style={{ background: `linear-gradient(135deg, ${TRUELOG_BLUE}, ${TRUELOG_CYAN})` }}
                      >
                        <item.icon className="h-7 w-7" />
                      </motion.div>
                      <div className="flex-1">
                        {/* H3 style - Inter Medium, 20-24px, #0E9ED5 */}
                        <h3 className="font-medium text-[18px] mb-2" style={{ color: TRUELOG_CYAN }}>
                          {item.title}
                        </h3>
                        {item.href ? (
                          <a 
                            href={item.href} 
                            className="text-[16px] font-medium transition-colors hover:underline"
                            style={{ color: TRUELOG_BLUE }}
                          >
                            {item.content}
                          </a>
                        ) : (
                          <p className="text-[16px] text-black dark:text-slate-300">{item.content}</p>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Quick Stats */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="grid grid-cols-3 gap-4 mt-8"
              >
                {[
                  { value: '24/7', label: 'Support' },
                  { value: '50+', label: 'Countries' },
                  { value: '15+', label: 'Years' },
                ].map((stat, index) => (
                  <motion.div
                    key={stat.label}
                    whileHover={{ y: -5 }}
                    className="text-center p-4 rounded-xl bg-slate-50 dark:bg-slate-800"
                  >
                    <div 
                      className="text-2xl font-bold mb-1"
                      style={{ 
                        background: `linear-gradient(135deg, ${TRUELOG_BLUE}, ${TRUELOG_CYAN})`,
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text'
                      }}
                    >
                      {stat.value}
                    </div>
                    <div className="text-sm text-slate-600 dark:text-slate-400">{stat.label}</div>
                  </motion.div>
                ))}
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Global Offices Section */}
      <section className="py-20 bg-slate-50 dark:bg-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="inline-block px-4 py-2 rounded-full text-sm font-medium mb-4"
              style={{ 
                background: `${TRUELOG_BLUE}15`,
                border: `1px solid ${TRUELOG_BLUE}30`,
                color: TRUELOG_BLUE
              }}
            >
              Global Presence
            </motion.span>
            {/* H2 style */}
            <h2 className="text-[28px] lg:text-[32px] font-bold text-black dark:text-white mb-4">
              Our Global Offices
            </h2>
            <p className="text-[16px] text-black dark:text-slate-300 max-w-3xl mx-auto">
              With offices across four continents, we're always close to you
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {offices.map((office, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={{ y: -8, scale: 1.02 }}
                className="bg-white dark:bg-slate-700 rounded-2xl p-6 shadow-lg border border-slate-100 dark:border-slate-600 transition-all duration-300 group"
              >
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl">{office.flag}</span>
                  <h3 className="text-lg font-bold text-black dark:text-white">{office.country}</h3>
                </div>
                {/* H3 style */}
                <p className="text-sm font-medium mb-3" style={{ color: TRUELOG_CYAN }}>{office.office}</p>
                <div className="flex items-start gap-3 mb-3">
                  <MapPinIcon className="h-4 w-4 mt-1" style={{ color: TRUELOG_BLUE }} />
                  <p className="text-sm text-slate-600 dark:text-slate-300 whitespace-pre-line">{office.address}</p>
                </div>
                <div className="flex items-center gap-3">
                  <PhoneIcon className="h-4 w-4" style={{ color: TRUELOG_BLUE }} />
                  <a 
                    href={`tel:${office.phone.replace(/\s/g, '')}`} 
                    className="text-sm transition-colors"
                    style={{ color: TRUELOG_BLUE }}
                  >
                    {office.phone}
                  </a>
                </div>
                {office.mapUrl && (
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setSelectedMap({office: `${office.country} - ${office.office}`, mapUrl: office.mapUrl})}
                    className="w-full mt-4 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 text-white"
                    style={{ 
                      background: `linear-gradient(135deg, ${TRUELOG_BLUE}, ${TRUELOG_CYAN})`,
                      boxShadow: `0 4px 15px -5px ${TRUELOG_BLUE}40`
                    }}
                  >
                    <MapPinIcon className="h-4 w-4" />
                    View on Map
                  </motion.button>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 bg-white dark:bg-slate-900">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            {/* H2 style */}
            <h2 className="text-[28px] lg:text-[32px] font-bold text-black dark:text-white mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-[16px] text-black dark:text-slate-300">
              Quick answers to common questions
            </p>
          </motion.div>

          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ scale: 1.01 }}
                className="bg-slate-50 dark:bg-slate-800 rounded-2xl p-6 border border-slate-100 dark:border-slate-700 transition-all duration-300"
              >
                {/* H3 style */}
                <h3 className="text-[18px] font-medium mb-3" style={{ color: TRUELOG_CYAN }}>
                  {faq.question}
                </h3>
                <p className="text-[16px] text-black dark:text-slate-300 leading-relaxed">{faq.answer}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Map Modal */}
      <AnimatePresence>
        {selectedMap && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedMap(null)}
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0, y: 50 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.8, opacity: 0, y: 50 }}
              transition={{ type: "spring", duration: 0.5 }}
              className="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div 
                className="p-6 text-white flex items-center justify-between"
                style={{ background: `linear-gradient(135deg, ${TRUELOG_BLUE}, ${TRUELOG_CYAN})` }}
              >
                <h3 className="text-xl font-bold flex items-center">
                  <MapPinIcon className="h-6 w-6 mr-2" />
                  {selectedMap.office}
                </h3>
                <motion.button
                  whileHover={{ scale: 1.1, rotate: 90 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => setSelectedMap(null)}
                  className="p-2 hover:bg-white/20 rounded-full transition-colors"
                >
                  <XMarkIcon className="h-6 w-6" />
                </motion.button>
              </div>
              <div className="h-96">
                <iframe
                  src={selectedMap.mapUrl}
                  width="100%"
                  height="100%"
                  style={{ border: 0 }}
                  allowFullScreen
                  loading="lazy"
                  title={`Map of ${selectedMap.office}`}
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ContactUs;
