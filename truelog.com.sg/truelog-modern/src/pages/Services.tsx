import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const Services: React.FC = () => {
  const services = [
    {
      title: 'FREIGHT FORWARDING',
      description: 'Comprehensive sea and air freight services ensuring safe, efficient transportation.',
      image: `${process.env.PUBLIC_URL}/assets/images/Air-Frieght-Services.jpg`,
      link: '/services/freight-forwarding',
      features: ['Sea Freight Services', 'Air Freight Services', 'Cargo Insurance', 'Customs Clearance']
    },
    {
      title: 'GLOBAL FULFILLMENT',
      description: 'Efficient, end-to-end supply chain management ensuring timely and accurate worldwide delivery.',
      image: `${process.env.PUBLIC_URL}/assets/images/containerized-services.jpg`,
      link: '/services/global-fulfillment',
      features: ['Singapore Flagship Warehouse', '3PL Warehousing Solutions', 'Return Merchandise Authorization', 'Distribution Services']
    },
    {
      title: 'ICT LOGISTICS',
      description: 'Specialized logistics solutions for technology hardware, ensuring compliance and efficiency.',
      image: `${process.env.PUBLIC_URL}/assets/images/trucking-services.jpg`,
      link: '/services/ict-logistics',
      features: ['IT Asset Management (ITAM)', 'Tech Equipment Shipping', 'Secure Handling', 'White Glove Service']
    },
    {
      title: 'IOR/EOR',
      description: 'Complete Importer of Record services ensuring legal compliance and seamless customs clearance for global IT shipments.',
      image: `${process.env.PUBLIC_URL}/assets/images/Air-Frieght-Services.jpg`,
      link: '/services/ior-eor-solutions',
      features: ['Customs Classification & HS Codes', 'Document Preparation & Submission', 'Duties & Taxes Management', 'Licenses & Regulatory Compliance']
    },
    {
      title: 'COMPLIANCE',
      description: 'Specialized logistics solutions for technology hardware, ensuring compliance and efficiency.',
      image: `${process.env.PUBLIC_URL}/assets/images/containerized-services.jpg`,
      link: '/services/compliance',
      features: ['Import Licenses', 'Trade Compliance', 'Documentation', 'Regulatory Support']
    }
  ];

  return (
    <div className="pt-16 bg-white dark:bg-slate-900">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-primary-600 via-blue-600 to-primary-700 dark:from-slate-900 dark:via-blue-900 dark:to-slate-800 py-20 overflow-hidden">
        {/* Background with shipping boxes and network lines */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-cyan-600/20"></div>
          
          {/* Network lines background */}
          <div className="absolute inset-0 opacity-20">
            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <path d="M10 20 Q30 10 50 30 T90 25" stroke="#06b6d4" strokeWidth="0.5" fill="none">
                <animate attributeName="stroke-dasharray" values="0,100;50,50;100,0;0,100" dur="8s" repeatCount="indefinite"/>
              </path>
              <path d="M20 80 Q40 60 60 70 T85 75" stroke="#3b82f6" strokeWidth="0.5" fill="none">
                <animate attributeName="stroke-dasharray" values="100,0;50,50;0,100;100,0" dur="6s" repeatCount="indefinite"/>
              </path>
            </svg>
          </div>
          
          {/* Floating shipping boxes */}
          <div className="absolute top-20 left-20 opacity-10">
            <div className="w-16 h-12 bg-yellow-400 rounded transform rotate-12"></div>
          </div>
          <div className="absolute top-32 right-32 opacity-10">
            <div className="w-20 h-14 bg-yellow-400 rounded transform -rotate-6"></div>
          </div>
          <div className="absolute bottom-20 left-1/4 opacity-10">
            <div className="w-14 h-10 bg-yellow-400 rounded transform rotate-45"></div>
          </div>
          <div className="absolute bottom-32 right-20 opacity-10">
            <div className="w-18 h-12 bg-yellow-400 rounded transform -rotate-12"></div>
          </div>
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-5xl lg:text-6xl font-heading font-bold text-white mb-6">
              Freight forwarding
            </h1>
            <p className="text-xl text-gray-100 dark:text-gray-200 max-w-3xl mx-auto mb-8">
              Provides comprehensive air & sea freight services for a diverse range of cargo types
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-primary-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-primary-700 transition-colors duration-200"
            >
              CLICK HERE
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* Services Overview */}
      <section className="py-20 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <p className="text-primary-600 dark:text-cyan-400 text-sm font-medium mb-2">SINGAPORE LOGISTICS SERVICES</p>
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">Home » Services</p>
            <h2 className="text-4xl lg:text-5xl font-heading font-bold text-gray-900 dark:text-white mb-4">
              Continously Moving Forward
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-4xl mx-auto">
              Freight forwarder Singapore, TrueLog provides expert logistics services to enhance your shipping experience.
            </p>
          </motion.div>

          {/* Services Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
            {services.slice(0, 2).map((service, index) => (
              <motion.div
                key={service.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.2 }}
                className="group"
              >
                <div className="bg-gray-50 dark:bg-slate-800/50 backdrop-blur-sm rounded-2xl overflow-hidden border border-gray-200 dark:border-slate-700/50 hover:border-primary-500/50 transition-all duration-300 shadow-lg">
                  <div className="relative h-64 overflow-hidden">
                    <img
                      src={service.image}
                      alt={service.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
                  </div>

                  <div className="p-8">
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">{service.title}</h3>
                    <p className="text-gray-600 dark:text-gray-300 mb-6 leading-relaxed">{service.description}</p>

                    <Link
                      to={service.link}
                      className="inline-block bg-primary-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-primary-700 transition-colors duration-200"
                    >
                      LEARN MORE
                    </Link>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Bottom Row - 3 Services */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {services.slice(2).map((service, index) => (
              <motion.div
                key={service.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.2 }}
                className="group"
              >
                <div className="bg-gray-50 dark:bg-slate-800/50 backdrop-blur-sm rounded-2xl overflow-hidden border border-gray-200 dark:border-slate-700/50 hover:border-primary-500/50 transition-all duration-300 shadow-lg">
                  <div className="relative h-48 overflow-hidden">
                    <img
                      src={service.image}
                      alt={service.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
                  </div>

                  <div className="p-6">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">{service.title}</h3>
                    <p className="text-gray-600 dark:text-gray-300 mb-4 text-sm leading-relaxed">{service.description}</p>

                    <Link
                      to={service.link}
                      className="inline-block bg-primary-600 text-white px-4 py-2 rounded-lg font-semibold text-sm hover:bg-primary-700 transition-colors duration-200"
                    >
                      LEARN MORE
                    </Link>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default Services;