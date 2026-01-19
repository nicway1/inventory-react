import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { MapPinIcon, PhoneIcon, EnvelopeIcon, ClockIcon, XMarkIcon } from '@heroicons/react/24/outline';

const ContactUs: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    phone: '',
    service: '',
    message: ''
  });
  
  const [selectedMap, setSelectedMap] = useState<{office: string, mapUrl: string} | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle form submission
    console.log('Form submitted:', formData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="pt-16">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 py-20 relative overflow-hidden">
        {/* Animated Background Elements */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-primary-400/20 to-blue-500/20 rounded-full blur-3xl animate-spin" style={{animationDuration: '20s'}}></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-br from-blue-400/20 to-purple-500/20 rounded-full blur-3xl animate-spin" style={{animationDuration: '25s', animationDirection: 'reverse'}}></div>
          <div className="absolute top-1/4 left-1/4 w-60 h-60 bg-gradient-to-br from-purple-400/10 to-pink-500/10 rounded-full blur-2xl animate-pulse"></div>
          
          {/* Floating particles */}
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className="absolute w-2 h-2 bg-white/20 rounded-full animate-ping"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                animationDelay: `${Math.random() * 2}s`,
                animationDuration: `${2 + Math.random() * 3}s`
              }}
            />
          ))}
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 1, delay: 0.2 }}
              className="mb-8"
            >
              <div className="relative inline-block">
                <h1 className="text-5xl lg:text-6xl font-heading font-bold text-white mb-6 relative z-10">
                  Contact Us
                </h1>
                {/* Glowing text effect */}
                <div className="absolute inset-0 text-5xl lg:text-6xl font-heading font-bold text-primary-400 blur-sm opacity-50 animate-pulse">
                  Contact Us
                </div>
              </div>
            </motion.div>
            
            <motion.p 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="text-xl text-gray-200 max-w-3xl mx-auto leading-relaxed"
            >
              If you'd like to find out more about our services, or you have any other questions, please complete the contact form below and we'll get back to you as quickly as possible.
            </motion.p>

            {/* Call-to-action indicators */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.8 }}
              className="flex justify-center items-center space-x-8 mt-12"
            >
              {[
                { icon: '📞', text: '24/7 Support' },
                { icon: '🌍', text: 'Global Coverage' },
                { icon: '⚡', text: 'Quick Response' }
              ].map((item, index) => (
                <div key={index} className="text-center">
                  <div className="text-2xl mb-2 animate-bounce" style={{animationDelay: `${index * 0.2}s`}}>
                    {item.icon}
                  </div>
                  <p className="text-gray-300 text-sm font-medium">{item.text}</p>
                </div>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Contact Form & Info */}
      <section className="py-20 bg-gradient-to-br from-gray-50 to-blue-50 relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-5">
          <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <pattern id="contact-pattern" width="20" height="20" patternUnits="userSpaceOnUse">
                <circle cx="10" cy="10" r="1" fill="currentColor" className="text-primary-600"/>
                <path d="M0 10h20M10 0v20" stroke="currentColor" strokeWidth="0.5" className="text-primary-600" opacity="0.3"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#contact-pattern)"/>
          </svg>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            {/* Contact Form */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="bg-white rounded-3xl p-8 lg:p-10 shadow-xl border border-gray-100 relative overflow-hidden hover:shadow-2xl transition-all duration-300"
            >
              {/* Animated form background */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary-50/50 to-blue-50/50 opacity-0 hover:opacity-100 transition-opacity duration-500"></div>
              <div className="relative z-10">
              <div className="text-center mb-8">
                <h2 className="text-3xl font-heading font-bold text-gray-900 mb-4">
                  Get a Quote
                </h2>
                <p className="text-gray-600">
                  Tell us about your logistics needs and we'll get back to you as quickly as possible
                </p>
              </div>
              
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      name="name"
                      required
                      value={formData.name}
                      onChange={handleChange}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email Address *
                    </label>
                    <input
                      type="email"
                      name="email"
                      required
                      value={formData.email}
                      onChange={handleChange}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Company
                    </label>
                    <input
                      type="text"
                      name="company"
                      value={formData.company}
                      onChange={handleChange}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Enquiry Type
                  </label>
                  <select
                    name="service"
                    value={formData.service}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    <option value="">Please Select</option>
                    <option value="General Enquiry">General Enquiry</option>
                    <option value="Service Enquiry">Service Enquiry</option>
                    <option value="Career Opportunity">Career Opportunity</option>
                    <option value="Feedback & Suggestions">Feedback & Suggestions</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Message *
                  </label>
                  <textarea
                    name="message"
                    required
                    rows={6}
                    value={formData.message}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="Tell us about your logistics needs..."
                  ></textarea>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  className="w-full bg-gradient-to-r from-primary-600 to-primary-700 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:from-primary-700 hover:to-primary-800 transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                  Send Message
                  <svg className="ml-2 h-5 w-5 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </motion.button>
              </form>
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
              <div className="text-center lg:text-left">
                <h2 className="text-3xl font-heading font-bold text-gray-900 mb-4">
                  Contact Information
                </h2>
                <p className="text-gray-600 mb-8">
                  Connect with our global offices or reach out through any of these channels. We're here to help with your logistics needs.
                </p>
              </div>

              <div className="space-y-6">
                {[
                  {
                    icon: EnvelopeIcon,
                    title: 'Email us on',
                    content: 'sales@truelog.com.sg',
                    color: 'bg-purple-100 text-purple-600',
                    href: 'mailto:sales@truelog.com.sg'
                  },
                  {
                    icon: PhoneIcon,
                    title: 'Main Office Singapore',
                    content: '+65 6909 3756',
                    color: 'bg-green-100 text-green-600',
                    href: 'tel:+6569093756'
                  },
                  {
                    icon: ClockIcon,
                    title: 'Business Hours',
                    content: 'Monday - Friday: 9:00 AM - 6:00 PM\nSaturday: 9:00 AM - 1:00 PM\nSunday: Closed',
                    color: 'bg-orange-100 text-orange-600'
                  }
                ].map((item, index) => (
                  <motion.div
                    key={item.title}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: index * 0.1 }}
                    className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100 hover:shadow-xl transition-all duration-300"
                  >
                    <div className="flex items-start space-x-4">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${item.color}`}>
                        <item.icon className="h-6 w-6" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                        {item.href ? (
                          <a href={item.href} className="text-primary-600 hover:text-primary-700 font-medium transition-colors duration-200 whitespace-pre-line">
                            {item.content}
                          </a>
                        ) : (
                          <p className="text-gray-600 whitespace-pre-line">{item.content}</p>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Interactive Map */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: 0.4 }}
                className="bg-white rounded-2xl shadow-lg overflow-hidden border border-gray-100"
              >
                <div className="p-4 bg-gradient-to-r from-primary-600 to-primary-700">
                  <h3 className="text-white font-semibold flex items-center">
                    <MapPinIcon className="h-5 w-5 mr-2" />
                    Singapore Headquarters Location
                  </h3>
                </div>
                <div className="h-64">
                  <iframe
                    src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3988.8177207977877!2d103.84798331475427!3d1.2793693990651432!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x31da1911c074a6a3%3A0x2b662908b80b4e5e!2s101%20Cecil%20St%2C%20Singapore!5e0!3m2!1sen!2ssg!4v1640995200000!5m2!1sen!2ssg"
                    width="100%"
                    height="100%"
                    style={{ border: 0 }}
                    allowFullScreen
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                    title="TrueLog Singapore Headquarters"
                  ></iframe>
                </div>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Global Offices Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <span className="inline-block px-4 py-2 bg-primary-100 text-primary-700 rounded-full text-sm font-medium mb-4">
              Global Presence
            </span>
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
              Our Global Offices
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              With offices across four continents, we're always close to you and your business
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                country: 'Singapore',
                office: 'Headquarters',
                address: '101 Cecil Street #11-05\nSingapore 069533',
                phone: '+65 6909 3756',
                phoneAlt: '+65 6909 3757',
                flag: '🇸🇬',
                mapUrl: 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3988.8177207977877!2d103.84798331475427!3d1.2793693990651432!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x31da1911c074a6a3%3A0x2b662908b80b4e5e!2s101%20Cecil%20St%2C%20Singapore!5e0!3m2!1sen!2ssg!4v1640995200000!5m2!1sen!2ssg'
              },
              {
                country: 'Singapore',
                office: 'Cargo Operations',
                address: '115 Airport Cargo Road #01-24/25\nCAB C Singapore 819466',
                phone: '+65 6214 4091',
                phoneAlt: '+65 6214 4092',
                flag: '🇸🇬',
                mapUrl: 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3988.7841984579656!2d103.96462831475434!3d1.3294994990589745!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x31da3d4df7b6831f%3A0x50b85b692d4b7c0a!2s115%20Airport%20Cargo%20Rd%2C%20Singapore!5e0!3m2!1sen!2ssg!4v1640995300000!5m2!1sen!2ssg'
              },
              {
                country: 'Vietnam',
                office: 'Truelog Vietnam',
                address: 'CT Building, 56 Yen The Ward 2\nTan Binh District\nHo Chi Minh City 700000',
                phone: '+84 397 337 372',
                flag: '🇻🇳',
                mapUrl: 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3919.0578556834544!2d106.64831431480028!3d10.80217816155513!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3175291ccc6a7e85%3A0x9c61aa5c5c5c5c5c!2s56%20Y%C3%AAn%20Th%E1%BA%BF%2C%20Ward%202%2C%20Tan%20Binh%2C%20Ho%20Chi%20Minh%20City%2C%20Vietnam!5e0!3m2!1sen!2ssg!4v1640995400000!5m2!1sen!2ssg'
              },
              {
                country: 'India',
                office: 'TrueLog India Private Limited',
                address: 'New Delhi',
                phone: '+91 979 091 6352',
                flag: '🇮🇳',
                mapUrl: 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d448196.52631719535!2d76.76357715!3d28.643684650000003!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390cfd5b347eb62d%3A0x52c2b7494e204dce!2sNew%20Delhi%2C%20Delhi%2C%20India!5e0!3m2!1sen!2ssg!4v1640995500000!5m2!1sen!2ssg'
              },
              {
                country: 'Belgium',
                office: 'Truelog Europe',
                address: 'Kerkstraat 61-63 bus 403\n8370 Blankenberge',
                phone: '+32 456 390 341',
                phoneAlt: '+32 456 390 342',
                flag: '🇧🇪',
                mapUrl: 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2519.3456789012345!2d3.1319246147851357!3d51.31234563123456!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x47c350123456789a%3A0x123456789abcdef0!2sKerkstraat%2061-63%2C%208370%20Blankenberge%2C%20Belgium!5e0!3m2!1sen!2ssg!4v1640995600000!5m2!1sen!2ssg'
              }
            ].map((office, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-lg hover:border-gray-200 transition-all duration-300 group"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-5">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-2xl">{office.flag}</span>
                      <h3 className="text-lg font-bold text-gray-900">{office.country}</h3>
                    </div>
                    <p className="text-primary-600 text-sm font-medium">{office.office}</p>
                  </div>
                </div>

                {/* Address */}
                <div className="mb-4">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 group-hover:bg-primary-50 transition-colors">
                      <MapPinIcon className="h-4 w-4 text-gray-500 group-hover:text-primary-600 transition-colors" />
                    </div>
                    <p className="text-gray-600 text-sm whitespace-pre-line leading-relaxed">{office.address}</p>
                  </div>
                </div>

                {/* Phone */}
                <div className="mb-5">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 group-hover:bg-primary-50 transition-colors">
                      <PhoneIcon className="h-4 w-4 text-gray-500 group-hover:text-primary-600 transition-colors" />
                    </div>
                    <div className="space-y-1">
                      <a href={`tel:${office.phone.replace(/\s/g, '')}`} className="block text-gray-700 hover:text-primary-600 text-sm font-medium transition-colors duration-200">
                        {office.phone}
                      </a>
                      {office.phoneAlt && (
                        <a href={`tel:${office.phoneAlt.replace(/\s/g, '')}`} className="block text-gray-700 hover:text-primary-600 text-sm font-medium transition-colors duration-200">
                          {office.phoneAlt}
                        </a>
                      )}
                    </div>
                  </div>
                </div>

                {/* View Map Button */}
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setSelectedMap({office: `${office.country} - ${office.office}`, mapUrl: office.mapUrl})}
                  className="w-full bg-gray-50 hover:bg-primary-50 text-gray-700 hover:text-primary-600 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 border border-gray-200 hover:border-primary-200"
                >
                  <MapPinIcon className="h-4 w-4" />
                  <span>View on Map</span>
                </motion.button>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="text-center mt-16"
          >
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 max-w-2xl mx-auto">
              <h3 className="text-xl font-bold text-gray-900 mb-3">Need Local Support?</h3>
              <p className="text-gray-600 mb-6">
                Our local teams understand regional requirements and can provide personalized assistance in your timezone.
              </p>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="bg-primary-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-primary-700 transition-all duration-200"
              >
                Contact Your Local Office
              </motion.button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-xl text-gray-600">
              Quick answers to common questions about our logistics services
            </p>
          </motion.div>

          <div className="space-y-6">
            {[
              {
                question: 'What logistics services do you offer?',
                answer: 'We provide comprehensive logistics solutions including freight forwarding, global fulfillment, ICT logistics, IOR/EOR services, and compliance management across 50+ countries.'
              },
              {
                question: 'How do you ensure cargo security?',
                answer: 'We implement multi-layered security protocols including GPS tracking, tamper-evident seals, background-checked staff, secure facilities, and comprehensive insurance coverage for all shipments.'
              },
              {
                question: 'What are your delivery timeframes?',
                answer: 'Delivery times vary by service and destination. Express air freight: 1-3 days, standard air freight: 3-7 days, sea freight: 15-45 days. We provide real-time tracking for all shipments.'
              },
              {
                question: 'Do you handle customs clearance?',
                answer: 'Yes, we provide complete customs clearance services including documentation, duty calculation, permit applications, and compliance with local regulations in all countries we serve.'
              },
              {
                question: 'How can I track my shipment?',
                answer: 'You can track your shipment 24/7 through our online portal, mobile app, or by contacting our customer service team. We provide real-time updates and notifications throughout the journey.'
              },
              {
                question: 'What industries do you specialize in?',
                answer: 'We specialize in technology, healthcare, automotive, manufacturing, e-commerce, and fashion industries, with particular expertise in IT equipment and sensitive electronics logistics.'
              }
            ].map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                className="bg-gray-50 rounded-2xl p-6 hover:bg-gray-100 transition-colors duration-300"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  {faq.question}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {faq.answer}
                </p>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="text-center mt-12"
          >
            <p className="text-gray-600 mb-6">
              Still have questions? We're here to help!
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-primary-600 text-white px-8 py-3 rounded-xl font-semibold hover:bg-primary-700 transition-colors duration-200"
            >
              Contact Support
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* Map Modal */}
      {selectedMap && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedMap(null)}
        >
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.5, opacity: 0 }}
            transition={{ type: "spring", duration: 0.5 }}
            className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 bg-gradient-to-r from-primary-600 to-primary-700 text-white flex items-center justify-between">
              <h3 className="text-xl font-bold flex items-center">
                <MapPinIcon className="h-6 w-6 mr-2" />
                {selectedMap.office}
              </h3>
              <motion.button
                whileHover={{ scale: 1.1, rotate: 90 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setSelectedMap(null)}
                className="p-2 hover:bg-white/20 rounded-full transition-colors duration-200"
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
                referrerPolicy="no-referrer-when-downgrade"
                title={`Map of ${selectedMap.office}`}
              ></iframe>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
};

export default ContactUs;