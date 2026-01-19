import React from 'react';
import { motion } from 'framer-motion';
import { TruckIcon, GlobeAltIcon, ShieldCheckIcon, ClockIcon } from '@heroicons/react/24/outline';

const FreightForwarding: React.FC = () => {
  const services = [
    {
      title: 'Sea Freight Services',
      description: 'Cost-effective ocean freight solutions for large shipments worldwide.',
      features: ['FCL & LCL Options', 'Door-to-Door Service', 'Competitive Rates', 'Global Network']
    },
    {
      title: 'Air Freight Services',
      description: 'Fast and reliable air cargo services for time-sensitive shipments.',
      features: ['Express Delivery', 'Temperature Control', 'Dangerous Goods', 'Charter Services']
    },
    {
      title: 'Cargo Insurance',
      description: 'Comprehensive coverage to protect your valuable shipments.',
      features: ['All Risk Coverage', 'Competitive Rates', 'Quick Claims', 'Global Coverage']
    },
    {
      title: 'Customs Clearance',
      description: 'Expert customs brokerage services for smooth border crossings.',
      features: ['Import/Export Permits', 'Duty Optimization', 'Compliance Support', 'Fast Processing']
    }
  ];

  return (
    <div className="pt-16">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-5xl font-heading font-bold text-white mb-6">
              Freight Forwarding
            </h1>
            <p className="text-xl text-gray-200 max-w-3xl mx-auto">
              Comprehensive air and sea freight services with global reach and competitive rates
            </p>
          </motion.div>
        </div>
      </section>

      {/* Services Grid */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {services.map((service, index) => (
              <motion.div
                key={service.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100"
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

      {/* Why Choose Us */}
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
              Why Choose Our Freight Forwarding?
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Experience the difference with our comprehensive freight solutions
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              {
                icon: GlobeAltIcon,
                title: 'Global Network',
                description: 'Worldwide coverage with trusted partners in every major port and airport.'
              },
              {
                icon: ShieldCheckIcon,
                title: 'Secure Handling',
                description: 'Advanced security protocols to ensure your cargo arrives safely.'
              },
              {
                icon: ClockIcon,
                title: 'On-Time Delivery',
                description: '99.5% on-time delivery rate with real-time tracking capabilities.'
              },
              {
                icon: TruckIcon,
                title: 'Door-to-Door',
                description: 'Complete logistics solutions from pickup to final delivery.'
              }
            ].map((benefit, index) => (
              <motion.div
                key={benefit.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="text-center"
              >
                <div className="w-16 h-16 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <benefit.icon className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{benefit.title}</h3>
                <p className="text-gray-600">{benefit.description}</p>
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
              Ready to Ship with Confidence?
            </h2>
            <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
              Get a customized freight forwarding quote tailored to your specific needs.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-white text-primary-600 px-8 py-4 rounded-xl font-semibold text-lg hover:bg-gray-50 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Get Free Quote
            </motion.button>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default FreightForwarding;