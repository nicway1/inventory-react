import React from 'react';
import { motion } from 'framer-motion';
import { ComputerDesktopIcon, ShieldCheckIcon, TruckIcon, WrenchScrewdriverIcon, GlobeAltIcon, ClockIcon } from '@heroicons/react/24/outline';

const ICTLogistics: React.FC = () => {
  const services = [
    {
      title: 'IT Asset Management (ITAM)',
      description: 'Complete lifecycle management of IT assets from procurement to disposal.',
      features: ['Asset Tracking & Tagging', 'Inventory Management', 'Lifecycle Monitoring', 'Disposal & Recycling']
    },
    {
      title: 'Tech Equipment Shipping',
      description: 'Specialized handling and transportation of sensitive technology equipment.',
      features: ['Anti-static Packaging', 'Temperature Control', 'Shock Protection', 'Chain of Custody']
    },
    {
      title: 'Secure Handling',
      description: 'Enhanced security protocols for high-value technology shipments.',
      features: ['Secure Facilities', 'Background-checked Staff', 'GPS Tracking', 'Insurance Coverage']
    },
    {
      title: 'White Glove Service',
      description: 'Premium delivery and installation services for critical IT equipment.',
      features: ['Professional Installation', 'Configuration Support', 'Testing & Validation', 'User Training']
    }
  ];

  const specializations = [
    {
      icon: ComputerDesktopIcon,
      title: 'Servers & Data Centers',
      description: 'Specialized handling of enterprise servers, storage systems, and data center equipment.',
      examples: ['Rack Servers', 'Storage Arrays', 'Network Switches', 'UPS Systems']
    },
    {
      icon: ShieldCheckIcon,
      title: 'Security Equipment',
      description: 'Secure logistics for surveillance systems, access control, and security hardware.',
      examples: ['CCTV Systems', 'Access Control', 'Biometric Devices', 'Security Appliances']
    },
    {
      icon: WrenchScrewdriverIcon,
      title: 'Industrial IoT',
      description: 'Logistics solutions for industrial automation and IoT device deployments.',
      examples: ['Sensors & Gateways', 'Industrial PCs', 'Automation Controllers', 'Edge Computing']
    },
    {
      icon: GlobeAltIcon,
      title: 'Telecom Infrastructure',
      description: 'Specialized handling of telecommunications and network infrastructure equipment.',
      examples: ['Base Stations', 'Fiber Equipment', 'Routers & Switches', 'Satellite Equipment']
    }
  ];

  return (
    <div className="pt-16">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 py-20 relative overflow-hidden">
        {/* Tech Background Elements */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-cyan-600/20"></div>
          
          {/* Circuit patterns */}
          <div className="absolute inset-0 opacity-10">
            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <defs>
                <pattern id="circuit" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
                  <path d="M10 0v5h5v5h-5v5h-5v-5H0v-5h5V0z" fill="currentColor" opacity="0.3"/>
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#circuit)"/>
            </svg>
          </div>
          
          {/* Tech icons */}
          <div className="absolute top-20 left-20 opacity-10">
            <ComputerDesktopIcon className="w-24 h-24 text-white" />
          </div>
          <div className="absolute bottom-20 right-20 opacity-10">
            <ShieldCheckIcon className="w-20 h-20 text-white" />
          </div>
          
          {/* Data flow lines */}
          <div className="absolute inset-0 opacity-20">
            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <path d="M0 20 Q25 10 50 20 T100 15" stroke="#00d4ff" strokeWidth="0.5" fill="none">
                <animate attributeName="stroke-dasharray" values="0,100;50,50;100,0;0,100" dur="4s" repeatCount="indefinite"/>
              </path>
              <path d="M0 80 Q25 70 50 80 T100 75" stroke="#0099ff" strokeWidth="0.5" fill="none">
                <animate attributeName="stroke-dasharray" values="100,0;50,50;0,100;100,0" dur="6s" repeatCount="indefinite"/>
              </path>
            </svg>
          </div>
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-5xl font-heading font-bold text-white mb-6">
              ICT Logistics
            </h1>
            <p className="text-xl text-gray-200 max-w-3xl mx-auto">
              Specialized logistics solutions for technology equipment and sensitive electronics
            </p>
          </motion.div>
        </div>
      </section>

      {/* Services Grid */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
              Specialized ICT Services
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Expert handling of technology equipment with industry-leading security and care
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {services.map((service, index) => (
              <motion.div
                key={service.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100 hover:shadow-xl transition-shadow duration-300"
              >
                <h3 className="text-2xl font-semibold text-gray-900 mb-4">{service.title}</h3>
                <p className="text-gray-600 mb-6">{service.description}</p>
                
                <div className="space-y-2">
                  {service.features.map((feature, featureIndex) => (
                    <div key={featureIndex} className="flex items-center text-sm">
                      <div className="w-2 h-2 rounded-full bg-primary-600 mr-3"></div>
                      <span className="text-gray-700">{feature}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Specializations */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
              Technology Specializations
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Expertise across all major technology categories and equipment types
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {specializations.map((spec, index) => (
              <motion.div
                key={spec.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-white rounded-2xl p-8 shadow-lg"
              >
                <div className="flex items-start space-x-4">
                  <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <spec.icon className="h-6 w-6 text-primary-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">{spec.title}</h3>
                    <p className="text-gray-600 mb-4">{spec.description}</p>
                    <div className="flex flex-wrap gap-2">
                      {spec.examples.map((example, exampleIndex) => (
                        <span
                          key={exampleIndex}
                          className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-full"
                        >
                          {example}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Security & Compliance */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
              Security & Compliance Standards
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Meeting the highest industry standards for technology logistics
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: ShieldCheckIcon,
                title: 'ISO 27001 Certified',
                description: 'Information security management system certification ensuring data protection.',
                features: ['Data Encryption', 'Access Controls', 'Audit Trails', 'Incident Response']
              },
              {
                icon: ClockIcon,
                title: 'Chain of Custody',
                description: 'Complete tracking and documentation of equipment throughout the logistics process.',
                features: ['Digital Signatures', 'Photo Documentation', 'Time Stamps', 'Handover Records']
              },
              {
                icon: TruckIcon,
                title: 'Secure Transport',
                description: 'Specialized vehicles and protocols for high-value technology shipments.',
                features: ['GPS Monitoring', 'Tamper-evident Seals', 'Climate Control', 'Real-time Alerts']
              }
            ].map((standard, index) => (
              <motion.div
                key={standard.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="text-center bg-gray-50 rounded-xl p-8"
              >
                <div className="w-16 h-16 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <standard.icon className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">{standard.title}</h3>
                <p className="text-gray-600 mb-4">{standard.description}</p>
                <div className="space-y-1">
                  {standard.features.map((feature, featureIndex) => (
                    <div key={featureIndex} className="flex items-center justify-center text-sm">
                      <div className="w-1.5 h-1.5 rounded-full bg-primary-600 mr-2"></div>
                      <span className="text-gray-700">{feature}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl font-heading font-bold text-white mb-4">
              Secure Your Technology Logistics
            </h2>
            <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
              Trust your valuable IT equipment to our specialized logistics experts.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-white text-primary-600 px-8 py-4 rounded-xl font-semibold text-lg hover:bg-gray-50 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Get ICT Logistics Quote
            </motion.button>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default ICTLogistics;