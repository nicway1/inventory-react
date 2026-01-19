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
    console.log('Form submitted:', formData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="pt-16 bg-slate-900">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 py-20 relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-primary-400/20 to-blue-500/20 rounded-full blur-3xl animate-spin" style={{animationDuration: '20s'}}></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-br from-blue-400/20 to-purple-500/20 rounded-full blur-3xl animate-spin" style={{animationDuration: '25s', animationDirection: 'reverse'}}></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-5xl lg:text-6xl font-heading font-bold text-white mb-6">
              Contact Us
            </h1>
            <p className="text-xl text-gray-200 max-w-3xl mx-auto leading-relaxed">
              If you'd like to find out more about our services, please complete the contact form below.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Contact Form & Info */}
      <section className="py-20 bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            {/* Contact Form */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="bg-slate-800/50 backdrop-blur-sm rounded-3xl p-8 lg:p-10 border border-slate-700/50"
            >
              <div className="text-center mb-8">
                <h2 className="text-3xl font-heading font-bold text-white mb-4">
                  Get a Quote
                </h2>
                <p className="text-gray-300">
                  Tell us about your logistics needs
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Full Name *</label>
                    <input
                      type="text"
                      name="name"
                      required
                      value={formData.name}
                      onChange={handleChange}
                      className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Email Address *</label>
                    <input
                      type="email"
                      name="email"
                      required
                      value={formData.email}
                      onChange={handleChange}
                      className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Company</label>
                    <input
                      type="text"
                      name="company"
                      value={formData.company}
                      onChange={handleChange}
                      className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Phone Number</label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Enquiry Type</label>
                  <select
                    name="service"
                    value={formData.service}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    <option value="">Please Select</option>
                    <option value="General Enquiry">General Enquiry</option>
                    <option value="Service Enquiry">Service Enquiry</option>
                    <option value="Career Opportunity">Career Opportunity</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Message *</label>
                  <textarea
                    name="message"
                    required
                    rows={6}
                    value={formData.message}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="Tell us about your logistics needs..."
                  ></textarea>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  className="w-full bg-gradient-to-r from-primary-600 to-primary-700 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:from-primary-700 hover:to-primary-800 transition-all duration-200"
                >
                  Send Message
                </motion.button>
              </form>
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
                <h2 className="text-3xl font-heading font-bold text-white mb-4">
                  Contact Information
                </h2>
                <p className="text-gray-300 mb-8">
                  Connect with our global offices or reach out through any of these channels.
                </p>
              </div>

              <div className="space-y-6">
                {[
                  { icon: EnvelopeIcon, title: 'Email us on', content: 'sales@truelog.com.sg', color: 'bg-purple-500/20 text-purple-400', href: 'mailto:sales@truelog.com.sg' },
                  { icon: PhoneIcon, title: 'Main Office Singapore', content: '+65 6909 3756', color: 'bg-green-500/20 text-green-400', href: 'tel:+6569093756' },
                  { icon: ClockIcon, title: 'Business Hours', content: 'Monday - Friday: 9:00 AM - 6:00 PM', color: 'bg-orange-500/20 text-orange-400' }
                ].map((item, index) => (
                  <motion.div
                    key={item.title}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: index * 0.1 }}
                    className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50"
                  >
                    <div className="flex items-start space-x-4">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${item.color}`}>
                        <item.icon className="h-6 w-6" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-white mb-2">{item.title}</h3>
                        {item.href ? (
                          <a href={item.href} className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
                            {item.content}
                          </a>
                        ) : (
                          <p className="text-gray-300">{item.content}</p>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Global Offices Section */}
      <section className="py-20 bg-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <span className="inline-block px-4 py-2 bg-primary-500/20 text-primary-400 rounded-full text-sm font-medium mb-4">
              Global Presence
            </span>
            <h2 className="text-4xl font-heading font-bold text-white mb-4">
              Our Global Offices
            </h2>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              With offices across four continents, we're always close to you
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { country: 'Singapore', office: 'Headquarters', address: '101 Cecil Street #11-05\nSingapore 069533', phone: '+65 6909 3756', flag: '🇸🇬', mapUrl: 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3988.8177207977877!2d103.84798331475427!3d1.2793693990651432!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x31da1911c074a6a3%3A0x2b662908b80b4e5e!2s101%20Cecil%20St%2C%20Singapore!5e0!3m2!1sen!2ssg!4v1640995200000!5m2!1sen!2ssg' },
              { country: 'Vietnam', office: 'Truelog Vietnam', address: 'CT Building, 56 Yen The\nHo Chi Minh City', phone: '+84 397 337 372', flag: '🇻🇳', mapUrl: '' },
              { country: 'India', office: 'TrueLog India', address: 'New Delhi', phone: '+91 979 091 6352', flag: '🇮🇳', mapUrl: '' },
              { country: 'Belgium', office: 'Truelog Europe', address: 'Kerkstraat 61-63\n8370 Blankenberge', phone: '+32 456 390 341', flag: '🇧🇪', mapUrl: '' }
            ].map((office, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="bg-slate-700/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-600/50 hover:border-primary-500/50 transition-all duration-300"
              >
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-2xl">{office.flag}</span>
                  <h3 className="text-lg font-bold text-white">{office.country}</h3>
                </div>
                <p className="text-primary-400 text-sm font-medium mb-3">{office.office}</p>
                <div className="flex items-start gap-3 mb-3">
                  <MapPinIcon className="h-4 w-4 text-gray-400 mt-1" />
                  <p className="text-gray-300 text-sm whitespace-pre-line">{office.address}</p>
                </div>
                <div className="flex items-center gap-3">
                  <PhoneIcon className="h-4 w-4 text-gray-400" />
                  <a href={`tel:${office.phone.replace(/\s/g, '')}`} className="text-gray-300 hover:text-primary-400 text-sm transition-colors">
                    {office.phone}
                  </a>
                </div>
                {office.mapUrl && (
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setSelectedMap({office: `${office.country} - ${office.office}`, mapUrl: office.mapUrl})}
                    className="w-full mt-4 bg-slate-600/50 hover:bg-primary-500/20 text-gray-300 hover:text-primary-400 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2"
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
      <section className="py-20 bg-slate-900">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-white mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-xl text-gray-300">
              Quick answers to common questions
            </p>
          </motion.div>

          <div className="space-y-6">
            {[
              { question: 'What logistics services do you offer?', answer: 'We provide comprehensive logistics solutions including freight forwarding, global fulfillment, ICT logistics, IOR/EOR services, and compliance management across 50+ countries.' },
              { question: 'How do you ensure cargo security?', answer: 'We implement multi-layered security protocols including GPS tracking, tamper-evident seals, and comprehensive insurance coverage for all shipments.' },
              { question: 'What are your delivery timeframes?', answer: 'Express air freight: 1-3 days, standard air freight: 3-7 days, sea freight: 15-45 days. We provide real-time tracking for all shipments.' },
              { question: 'Do you handle customs clearance?', answer: 'Yes, we provide complete customs clearance services including documentation, duty calculation, permit applications, and compliance with local regulations.' }
            ].map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50"
              >
                <h3 className="text-lg font-semibold text-white mb-3">{faq.question}</h3>
                <p className="text-gray-300 leading-relaxed">{faq.answer}</p>
              </motion.div>
            ))}
          </div>
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
            className="bg-slate-800 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden"
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
              ></iframe>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
};

export default ContactUs;
