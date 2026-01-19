import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDownIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ClockIcon,
  GlobeAltIcon,
  CurrencyDollarIcon,
  TruckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

interface FAQItem {
  question: string;
  answer: string;
  category: string;
  icon: any;
}

const FAQ: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const faqData: FAQItem[] = [
    {
      question: "What is trade compliance?",
      answer: "Trade compliance involves following international laws and regulations governing the import and export of goods. It's crucial for ensuring smooth and legal global trade operations.",
      category: "Compliance",
      icon: ShieldCheckIcon
    },
    {
      question: "How can TrueLog help with trade compliance?",
      answer: "TrueLog simplifies trade processes by ensuring compliance with all necessary regulations, minimizing delays, and preventing legal issues.",
      category: "Services",
      icon: ShieldCheckIcon
    },
    {
      question: "What is an Importer of Record (IOR)?",
      answer: "The IOR is responsible for ensuring imported goods comply with local laws and regulations, paying duties and taxes, and maintaining records of the import.",
      category: "Compliance",
      icon: DocumentTextIcon
    },
    {
      question: "What is a consignee?",
      answer: "A consignee is the person or entity to whom the shipment is delivered. They are responsible for receiving and taking ownership of the goods.",
      category: "Shipping",
      icon: TruckIcon
    },
    {
      question: "When do I receive my order?",
      answer: "Delivery times vary depending on the shipping method, origin, and destination. For express services, delivery typically takes 2-5 business days. Standard shipping may take 5-15 business days. Contact our team for specific delivery estimates for your shipment.",
      category: "Delivery",
      icon: ClockIcon
    },
    {
      question: "How are customs duties calculated?",
      answer: "Customs duties are based on the value of the goods, their classification under the Harmonized System (HS) code, and the regulations of the destination country.",
      category: "Customs",
      icon: CurrencyDollarIcon
    },
    {
      question: "What does Delivered Duty Paid (DDP) mean?",
      answer: "DDP means the seller is responsible for all costs, including shipping, duties, and taxes, until the goods are delivered to the buyer.",
      category: "Customs",
      icon: CurrencyDollarIcon
    },
    {
      question: "What is customs clearance?",
      answer: "Customs clearance involves the preparation and submission of documents required to import or export goods, ensuring they meet all legal requirements.",
      category: "Customs",
      icon: DocumentTextIcon
    },
    {
      question: "How long does customs clearance take?",
      answer: "The time for customs clearance varies by country and can range from a few days to several weeks, depending on the complexity of the shipment.",
      category: "Customs",
      icon: ClockIcon
    },
    {
      question: "What are the benefits of centralized procurement?",
      answer: "Centralized procurement can reduce costs, streamline operations, and improve compliance by centralizing control and visibility over the procurement process.",
      category: "Services",
      icon: GlobeAltIcon
    }
  ];

  // Filter FAQs based on search query
  const filteredFAQs = useMemo(() => {
    if (!searchQuery.trim()) return faqData;

    const query = searchQuery.toLowerCase();
    return faqData.filter(
      faq =>
        faq.question.toLowerCase().includes(query) ||
        faq.answer.toLowerCase().includes(query) ||
        faq.category.toLowerCase().includes(query)
    );
  }, [searchQuery]);

  const toggleFAQ = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Hero Section with Enhanced Design */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="relative bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-800 text-white py-24 overflow-hidden"
      >
        {/* Animated Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-0 w-64 h-64 bg-white rounded-full blur-3xl"></div>
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-white rounded-full blur-3xl"></div>
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.6 }}
            className="text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
              className="inline-block mb-6"
            >
              <div className="bg-white/20 backdrop-blur-sm rounded-full p-4">
                <DocumentTextIcon className="w-12 h-12 text-white" />
              </div>
            </motion.div>

            <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white to-blue-100">
              Frequently Asked Questions
            </h1>

            <p className="text-xl md:text-2xl text-blue-100 max-w-3xl mx-auto mb-8">
              Logistics Challenges FAQ - Overcome with TrueLog's Expertise
            </p>

            {/* Search Bar */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="max-w-2xl mx-auto mt-8"
            >
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 w-6 h-6 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search FAQs... (e.g., customs, delivery, compliance)"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-4 focus:ring-blue-300 shadow-2xl text-lg"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                )}
              </div>
              {searchQuery && (
                <p className="text-blue-100 text-sm mt-3">
                  Found {filteredFAQs.length} result{filteredFAQs.length !== 1 ? 's' : ''}
                </p>
              )}
            </motion.div>
          </motion.div>
        </div>
      </motion.div>

      {/* Introduction Section */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="bg-white rounded-lg shadow-lg p-8 mb-12"
        >
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Global Trade Compliance: Your Essential Guide to IT Import/Export
          </h2>
          <p className="text-gray-700 mb-6">
            Navigating the complexities of international IT equipment trade? We've got you covered.
            Our comprehensive FAQ addresses the critical aspects of global trade compliance, including:
          </p>
          <ul className="space-y-2 text-gray-700">
            <li className="flex items-start">
              <span className="text-blue-600 mr-2">•</span>
              <span>Decoding HS (Harmonized System) codes and their significance</span>
            </li>
            <li className="flex items-start">
              <span className="text-blue-600 mr-2">•</span>
              <span>Understanding export licenses and certifications</span>
            </li>
            <li className="flex items-start">
              <span className="text-blue-600 mr-2">•</span>
              <span>Identifying and mitigating risks in cross-border IT transactions</span>
            </li>
            <li className="flex items-start">
              <span className="text-blue-600 mr-2">•</span>
              <span>Ensuring compliance with international trade regulations</span>
            </li>
          </ul>
          <p className="text-gray-700 mt-6">
            Let Truelog.com.sg be your trusted partner in mastering the intricacies of IT equipment
            import and export. Explore our FAQ to unlock the potential of seamless international trade
            in the technology sector.
          </p>
        </motion.div>

        {/* FAQ Accordion with Enhanced UI */}
        <AnimatePresence mode="wait">
          {filteredFAQs.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="text-center py-16"
            >
              <div className="bg-white rounded-2xl shadow-lg p-12">
                <MagnifyingGlassIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-gray-700 mb-2">No results found</h3>
                <p className="text-gray-500">Try searching with different keywords</p>
              </div>
            </motion.div>
          ) : (
            <div className="space-y-4">
              {filteredFAQs.map((faq, index) => {
                const Icon = faq.icon;
                const actualIndex = faqData.indexOf(faq);
                const isOpen = openIndex === actualIndex;

                return (
                  <motion.div
                    key={actualIndex}
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: index * 0.05 }}
                    className={`bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden border-2 ${
                      isOpen ? 'border-blue-500' : 'border-transparent'
                    }`}
                  >
                    <button
                      onClick={() => toggleFAQ(actualIndex)}
                      className="w-full px-6 py-5 text-left flex items-start gap-4 hover:bg-gradient-to-r hover:from-blue-50 hover:to-transparent transition-all duration-200"
                    >
                      {/* Icon */}
                      <div className={`flex-shrink-0 p-3 rounded-xl transition-colors ${
                        isOpen ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-600'
                      }`}>
                        <Icon className="w-6 h-6" />
                      </div>

                      {/* Question and Category */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs font-semibold px-3 py-1 rounded-full ${
                            isOpen ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-700'
                          }`}>
                            {faq.category}
                          </span>
                        </div>
                        <h3 className="text-lg font-bold text-gray-900 pr-8">
                          {faq.question}
                        </h3>
                      </div>

                      {/* Chevron */}
                      <div className="flex-shrink-0">
                        <motion.div
                          animate={{ rotate: isOpen ? 180 : 0 }}
                          transition={{ duration: 0.3 }}
                          className={`p-2 rounded-lg ${
                            isOpen ? 'bg-blue-600' : 'bg-gray-100'
                          }`}
                        >
                          <ChevronDownIcon
                            className={`w-5 h-5 ${
                              isOpen ? 'text-white' : 'text-gray-600'
                            }`}
                          />
                        </motion.div>
                      </div>
                    </button>

                    {/* Answer */}
                    <AnimatePresence>
                      {isOpen && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.3 }}
                          className="overflow-hidden"
                        >
                          <div className="px-6 pb-6 pl-20">
                            <div className="bg-gradient-to-r from-blue-50 to-transparent p-6 rounded-xl border-l-4 border-blue-500">
                              <p className="text-gray-700 leading-relaxed text-base">
                                {faq.answer}
                              </p>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>
          )}
        </AnimatePresence>

        {/* Certifications Section */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="bg-gradient-to-br from-white to-blue-50 rounded-2xl shadow-2xl p-8 md:p-12 mt-16 border border-blue-100"
        >
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2, type: "spring" }}
              className="inline-block mb-4"
            >
              <ShieldCheckIcon className="w-12 h-12 text-blue-600 mx-auto" />
            </motion.div>
            <h3 className="text-3xl font-bold text-gray-900 mb-4">
              Accreditations & Certifications
            </h3>
            <div className="max-w-3xl mx-auto">
              <p className="text-gray-700 text-lg italic leading-relaxed bg-blue-50 p-6 rounded-xl border-l-4 border-blue-500">
                "Our mission is to be a flexible, competitive and trustworthy logistics provider, offering
                added value in a swift manner to our clients. We take great pride in providing you with the
                best solution. Your word of mouth is what makes us grow and excel."
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 items-center justify-items-center mt-8">
            {['ALNA', 'BizSafe', 'FIATA', 'Freight Lounge', 'IATA', 'SLA'].map((cert, idx) => (
              <motion.div
                key={cert}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
                whileHover={{ scale: 1.1, y: -5 }}
                className="text-center"
              >
                <div className="bg-white p-6 rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 border-2 border-transparent hover:border-blue-500">
                  <div className="text-blue-600 font-bold text-lg">{cert}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* CTA Section */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mt-16 mb-8"
        >
          <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl shadow-2xl p-12 text-white relative overflow-hidden">
            {/* Background Pattern */}
            <div className="absolute inset-0 opacity-10">
              <div className="absolute top-0 right-0 w-64 h-64 bg-white rounded-full blur-3xl"></div>
              <div className="absolute bottom-0 left-0 w-96 h-96 bg-white rounded-full blur-3xl"></div>
            </div>

            <div className="relative">
              <motion.div
                initial={{ scale: 0 }}
                whileInView={{ scale: 1 }}
                viewport={{ once: true }}
                transition={{ type: "spring", stiffness: 200 }}
              >
                <DocumentTextIcon className="w-16 h-16 mx-auto mb-6 text-blue-200" />
              </motion.div>

              <h3 className="text-3xl md:text-4xl font-bold mb-4">
                Still Have Questions?
              </h3>
              <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
                Our team of logistics experts is here to help you with any questions about our services.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                <motion.a
                  href="/contact-us"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="inline-flex items-center gap-2 bg-white text-blue-600 px-8 py-4 rounded-xl font-bold hover:bg-blue-50 transition-all shadow-lg text-lg"
                >
                  Contact Us
                  <ChevronDownIcon className="w-5 h-5 rotate-[-90deg]" />
                </motion.a>

                <motion.a
                  href="tel:+6569093756"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="inline-flex items-center gap-2 bg-blue-700 text-white px-8 py-4 rounded-xl font-bold hover:bg-blue-800 transition-all shadow-lg text-lg border-2 border-white/20"
                >
                  Call: +65 6909 3756
                </motion.a>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default FAQ;
