import React from 'react';
import { motion } from 'framer-motion';
import { StarIcon } from '@heroicons/react/24/solid';

const Testimonials: React.FC = () => {
  const testimonials = [
    {
      name: 'Sarah Chen',
      position: 'Supply Chain Director',
      company: 'TechFlow Solutions',
      image: '👩‍💼',
      rating: 5,
      text: 'Truelog has transformed our logistics operations. Their IT logistics expertise and real-time tracking have improved our efficiency by 40%. Outstanding service!',
      industry: 'Technology'
    },
    {
      name: 'Michael Rodriguez',
      position: 'Operations Manager',
      company: 'Global Manufacturing Inc.',
      image: '👨‍💼',
      rating: 5,
      text: 'The freight forwarding services are exceptional. Fast, reliable, and cost-effective. Truelog has become our trusted logistics partner for international shipments.',
      industry: 'Manufacturing'
    },
    {
      name: 'Emily Watson',
      position: 'Procurement Head',
      company: 'MedTech Innovations',
      image: '👩‍⚕️',
      rating: 5,
      text: 'Their compliance expertise saved us months of regulatory headaches. The IOR/EOR services made our global expansion seamless. Highly recommended!',
      industry: 'Healthcare'
    },
    {
      name: 'David Kim',
      position: 'Logistics Coordinator',
      company: 'E-commerce Plus',
      image: '👨‍💻',
      rating: 5,
      text: 'The warehousing and fulfillment services are top-notch. Same-day processing and 99.9% accuracy rate. Our customers love the fast delivery times.',
      industry: 'E-commerce'
    },
    {
      name: 'Lisa Thompson',
      position: 'Import/Export Manager',
      company: 'Fashion Forward Ltd.',
      image: '👩‍🎨',
      rating: 5,
      text: 'Truelog\'s global coverage is impressive. They handle our shipments to 30+ countries with consistent quality. The customer support is available 24/7.',
      industry: 'Fashion'
    },
    {
      name: 'James Wilson',
      position: 'CEO',
      company: 'StartUp Dynamics',
      image: '👨‍🚀',
      rating: 5,
      text: 'As a growing startup, we needed flexible logistics solutions. Truelog scaled with us perfectly, providing cost-effective services without compromising quality.',
      industry: 'Startup'
    }
  ];

  return (
    <section className="py-20 bg-gradient-to-br from-gray-50 to-blue-50 relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute top-20 left-20 w-32 h-32 bg-primary-600 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-20 w-40 h-40 bg-secondary-600 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-60 h-60 bg-purple-600 rounded-full blur-3xl"></div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl lg:text-5xl font-heading font-bold text-gray-900 mb-4">
            What Our Clients Say
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Don't just take our word for it. Here's what industry leaders say about our logistics solutions.
          </p>
        </motion.div>

        {/* Testimonials Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {testimonials.map((testimonial, index) => (
            <motion.div
              key={testimonial.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: index * 0.1 }}
              whileHover={{ y: -5 }}
              className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-100 relative"
            >
              {/* Quote Icon */}
              <div className="absolute -top-4 -left-4 w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                <svg className="h-4 w-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z"/>
                </svg>
              </div>

              {/* Rating */}
              <div className="flex items-center mb-4">
                {[...Array(testimonial.rating)].map((_, i) => (
                  <StarIcon key={i} className="h-5 w-5 text-yellow-400" />
                ))}
              </div>

              {/* Testimonial Text */}
              <p className="text-gray-700 mb-6 leading-relaxed italic">
                "{testimonial.text}"
              </p>

              {/* Client Info */}
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-gradient-to-br from-primary-100 to-primary-200 rounded-full flex items-center justify-center text-2xl">
                  {testimonial.image}
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">{testimonial.name}</h4>
                  <p className="text-sm text-gray-600">{testimonial.position}</p>
                  <p className="text-sm text-primary-600 font-medium">{testimonial.company}</p>
                </div>
              </div>

              {/* Industry Tag */}
              <div className="absolute top-4 right-4">
                <span className="px-3 py-1 bg-primary-100 text-primary-700 text-xs font-medium rounded-full">
                  {testimonial.industry}
                </span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Trust Indicators */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="mt-16 bg-white rounded-3xl p-8 lg:p-12 shadow-lg"
        >
          <div className="text-center mb-8">
            <h3 className="text-2xl font-heading font-bold text-gray-900 mb-4">
              Trusted by Industry Leaders
            </h3>
            <p className="text-gray-600">
              Join hundreds of companies that trust Truelog with their logistics needs
            </p>
          </div>

          {/* Company Logos Placeholder */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-8 items-center opacity-60">
            {[
              'TechFlow', 'GlobalMfg', 'MedTech', 'E-comm+', 'Fashion', 'StartUp'
            ].map((company, index) => (
              <motion.div
                key={company}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                className="text-center"
              >
                <div className="w-16 h-16 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-2">
                  <span className="text-gray-400 font-bold text-xs">{company}</span>
                </div>
              </motion.div>
            ))}
          </div>

          {/* CTA */}
          <div className="text-center mt-12">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-primary-600 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:bg-primary-700 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Join Our Success Stories
            </motion.button>
          </div>
        </motion.div>

        {/* Floating Review Cards */}
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity }}
          className="absolute top-20 right-10 bg-white rounded-xl p-4 shadow-lg hidden lg:block"
        >
          <div className="flex items-center space-x-2 mb-2">
            {[...Array(5)].map((_, i) => (
              <StarIcon key={i} className="h-4 w-4 text-yellow-400" />
            ))}
          </div>
          <p className="text-sm text-gray-700 font-medium">4.9/5 Rating</p>
          <p className="text-xs text-gray-500">500+ Reviews</p>
        </motion.div>

        <motion.div
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 5, repeat: Infinity }}
          className="absolute bottom-20 left-10 bg-white rounded-xl p-4 shadow-lg hidden lg:block"
        >
          <div className="text-2xl font-bold text-green-600 mb-1">98%</div>
          <p className="text-sm text-gray-700 font-medium">Client Retention</p>
          <p className="text-xs text-gray-500">Industry Leading</p>
        </motion.div>
      </div>
    </section>
  );
};

export default Testimonials;