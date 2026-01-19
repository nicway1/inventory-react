import React from 'react';
import { motion } from 'framer-motion';
import { BuildingStorefrontIcon, TruckIcon, GlobeAltIcon, ChartBarIcon } from '@heroicons/react/24/outline';

const GlobalFulfillment: React.FC = () => {
  const services = [
    {
      title: 'Singapore Flagship Warehouse',
      description: 'State-of-the-art 50,000 sq ft facility with advanced inventory management systems.',
      features: ['Climate Controlled Storage', 'Real-time Inventory Tracking', 'Automated Picking Systems', 'Quality Control Processes']
    },
    {
      title: '3PL Warehousing Solutions',
      description: 'Comprehensive third-party logistics services tailored to your business needs.',
      features: ['Flexible Storage Options', 'Pick & Pack Services', 'Kitting & Assembly', 'Cross-docking Solutions']
    },
    {
      title: 'Return Merchandise Authorization',
      description: 'Streamlined RMA processes to handle returns efficiently and cost-effectively.',
      features: ['Automated RMA Processing', 'Quality Inspection', 'Refurbishment Services', 'Disposal Management']
    },
    {
      title: 'Distribution Services',
      description: 'Last-mile delivery and distribution network across Southeast Asia.',
      features: ['Same-day Delivery', 'Multi-channel Distribution', 'Route Optimization', 'Proof of Delivery']
    }
  ];

  const capabilities = [
    {
      icon: BuildingStorefrontIcon,
      title: 'Advanced Warehousing',
      description: 'Modern facilities with WMS integration and automated systems for maximum efficiency.',
      stats: '50,000+ sq ft'
    },
    {
      icon: TruckIcon,
      title: 'Last-Mile Delivery',
      description: 'Comprehensive delivery network covering Singapore and regional destinations.',
      stats: '99.2% delivery rate'
    },
    {
      icon: GlobeAltIcon,
      title: 'Regional Network',
      description: 'Strategic partnerships across APAC for seamless cross-border fulfillment.',
      stats: '15+ countries'
    },
    {
      icon: ChartBarIcon,
      title: 'Analytics & Reporting',
      description: 'Real-time dashboards and detailed analytics for inventory and performance tracking.',
      stats: 'Real-time data'
    }
  ];

  return (
    <div className="pt-16">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 py-20 relative overflow-hidden">
        {/* Background Elements */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-cyan-600/20"></div>
          
          {/* Warehouse icons */}
          <div className="absolute top-20 left-20 opacity-10">
            <BuildingStorefrontIcon className="w-24 h-24 text-white" />
          </div>
          <div className="absolute bottom-20 right-20 opacity-10">
            <TruckIcon className="w-20 h-20 text-white" />
          </div>
          
          {/* Network lines */}
          <div className="absolute inset-0 opacity-20">
            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <path d="M20 30 Q40 20 60 40 T90 35" stroke="#06b6d4" strokeWidth="0.5" fill="none">
                <animate attributeName="stroke-dasharray" values="0,100;50,50;100,0;0,100" dur="8s" repeatCount="indefinite"/>
              </path>
              <path d="M10 70 Q30 50 50 60 T85 65" stroke="#3b82f6" strokeWidth="0.5" fill="none">
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
              Global Fulfillment
            </h1>
            <p className="text-xl text-gray-200 max-w-3xl mx-auto">
              End-to-end warehousing and distribution solutions for seamless supply chain management
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
              Comprehensive Fulfillment Solutions
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              From storage to delivery, we handle every aspect of your fulfillment needs
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

      {/* Capabilities Section */}
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
              Our Fulfillment Capabilities
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Advanced infrastructure and technology for superior fulfillment performance
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {capabilities.map((capability, index) => (
              <motion.div
                key={capability.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="text-center bg-white rounded-xl p-6 shadow-lg"
              >
                <div className="w-16 h-16 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <capability.icon className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{capability.title}</h3>
                <p className="text-gray-600 mb-3">{capability.description}</p>
                <div className="text-primary-600 font-semibold text-lg">{capability.stats}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Process Flow */}
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
              Fulfillment Process
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Streamlined workflow from order receipt to delivery
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { step: '01', title: 'Order Receipt', description: 'Automated order processing and validation' },
              { step: '02', title: 'Inventory Pick', description: 'Efficient picking with barcode scanning' },
              { step: '03', title: 'Quality Check', description: 'Thorough inspection and packaging' },
              { step: '04', title: 'Dispatch', description: 'Fast shipping with tracking updates' }
            ].map((process, index) => (
              <motion.div
                key={process.step}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.2 }}
                className="text-center relative"
              >
                <div className="w-16 h-16 bg-primary-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                  {process.step}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{process.title}</h3>
                <p className="text-gray-600">{process.description}</p>
                
                {index < 3 && (
                  <div className="hidden md:block absolute top-8 left-full w-full">
                    <div className="w-full h-0.5 bg-gray-300 relative">
                      <div className="absolute right-0 top-0 w-2 h-2 bg-primary-600 rounded-full transform translate-x-1 -translate-y-0.75"></div>
                    </div>
                  </div>
                )}
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
              Ready to Optimize Your Fulfillment?
            </h2>
            <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
              Let us handle your warehousing and distribution while you focus on growing your business.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-white text-primary-600 px-8 py-4 rounded-xl font-semibold text-lg hover:bg-gray-50 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Get Fulfillment Quote
            </motion.button>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default GlobalFulfillment;