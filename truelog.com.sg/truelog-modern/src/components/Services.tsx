import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  TruckIcon,
  BuildingStorefrontIcon,
  ComputerDesktopIcon,
  GlobeAltIcon,
  ClipboardDocumentCheckIcon,
  ShieldCheckIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';
import { GlowCard, MagneticButton } from './ui';

const Services: React.FC = () => {
  const services = [
    {
      icon: TruckIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/Air-Frieght-Services.jpg`,
      title: 'Freight Forwarding',
      description: 'Comprehensive air and sea freight services with global reach and competitive rates.',
      features: ['Air Freight', 'Sea Freight', 'Customs Clearance', 'Cargo Insurance'],
      href: '/services/freight-forwarding',
      gradient: 'from-blue-500 to-indigo-600',
    },
    {
      icon: BuildingStorefrontIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/containerized-services.jpg`,
      title: 'Global Fulfillment',
      description: 'End-to-end warehousing and distribution solutions for seamless supply chain management.',
      features: ['3PL Warehousing', 'Distribution', 'Inventory Management', 'Order Fulfillment'],
      href: '/services/global-fulfillment',
      gradient: 'from-purple-500 to-pink-600',
    },
    {
      icon: ComputerDesktopIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/trucking-services.jpg`,
      title: 'IT Logistics',
      description: 'Specialized logistics solutions for technology equipment and sensitive electronics.',
      features: ['IT Asset Management', 'Tech Equipment Shipping', 'Secure Handling', 'White Glove Service'],
      href: '/services/ict-logistics',
      gradient: 'from-cyan-500 to-blue-600',
    },
    {
      icon: ClipboardDocumentCheckIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/Air-Frieght-Services.jpg`,
      title: 'IOR/EOR Solutions',
      description: 'Importer and Exporter of Record services for seamless international trade.',
      features: ['Import Compliance', 'Export Documentation', 'Trade Regulations', 'Risk Management'],
      href: '/services/ior-eor-solutions',
      gradient: 'from-amber-500 to-orange-600',
    },
    {
      icon: GlobeAltIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/containerized-services.jpg`,
      title: 'Global Coverage',
      description: 'Worldwide logistics network with local expertise in key markets.',
      features: ['International Network', 'Local Partners', 'Regional Expertise', 'Global Standards'],
      href: '/global-coverage',
      gradient: 'from-emerald-500 to-teal-600',
    },
    {
      icon: ShieldCheckIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/trucking-services.jpg`,
      title: 'Compliance',
      description: 'Regulatory compliance and documentation services for international trade.',
      features: ['Import Licenses', 'Trade Compliance', 'Documentation', 'Regulatory Support'],
      href: '/services/compliance',
      gradient: 'from-rose-500 to-red-600',
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: 'spring' as const,
        stiffness: 100,
        damping: 20,
      },
    },
  };

  return (
    <section id="services" className="section-padding bg-secondary-50">
      <div className="container-custom">
        {/* Section Header */}
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
            className="inline-block px-4 py-2 bg-primary-100 text-primary-700 rounded-full text-sm font-medium mb-4"
          >
            Our Services
          </motion.span>
          <h2 className="text-4xl lg:text-5xl font-heading font-bold text-secondary-900 mb-6">
            Comprehensive{' '}
            <span className="gradient-text">Logistics Solutions</span>
          </h2>
          <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
            From freight forwarding to specialized IT logistics, we provide end-to-end
            solutions designed to optimize your supply chain and drive business growth.
          </p>
        </motion.div>

        {/* Services Grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
        >
          {services.map((service, index) => (
            <motion.div key={service.title} variants={cardVariants}>
              <GlowCard
                className="h-full bg-white"
                glowColor="primary"
                tilt={true}
                glow={true}
              >
                {/* Image Container */}
                <div className="relative h-48 overflow-hidden rounded-t-2xl">
                  <motion.img
                    src={service.image}
                    alt={service.title}
                    className="w-full h-full object-cover"
                    whileHover={{ scale: 1.1 }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />

                  {/* Icon Badge */}
                  <motion.div
                    className={`absolute top-4 right-4 w-12 h-12 rounded-xl bg-gradient-to-br ${service.gradient} flex items-center justify-center shadow-lg`}
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                  >
                    <service.icon className="h-6 w-6 text-white" />
                  </motion.div>

                  {/* Title on Image */}
                  <div className="absolute bottom-4 left-4 right-4">
                    <h3 className="text-xl font-bold text-white">{service.title}</h3>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  <p className="text-secondary-600 mb-6 leading-relaxed">
                    {service.description}
                  </p>

                  {/* Features List */}
                  <div className="space-y-2 mb-6">
                    {service.features.map((feature, featureIndex) => (
                      <motion.div
                        key={featureIndex}
                        className="flex items-center text-sm group"
                        initial={{ opacity: 0, x: -10 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 * featureIndex }}
                      >
                        <div className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${service.gradient} mr-3 group-hover:scale-150 transition-transform`} />
                        <span className="text-secondary-700 group-hover:text-secondary-900 transition-colors">
                          {feature}
                        </span>
                      </motion.div>
                    ))}
                  </div>

                  {/* Learn More Link */}
                  <Link
                    to={service.href}
                    className="group inline-flex items-center text-sm font-semibold text-primary-600 hover:text-primary-700 transition-colors"
                  >
                    Learn More
                    <motion.span
                      className="ml-2"
                      whileHover={{ x: 5 }}
                      transition={{ type: 'spring', stiffness: 400 }}
                    >
                      <ArrowRightIcon className="h-4 w-4" />
                    </motion.span>
                  </Link>
                </div>
              </GlowCard>
            </motion.div>
          ))}
        </motion.div>

        {/* CTA Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="mt-20"
        >
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-primary-600 via-primary-700 to-purple-700 p-12 lg:p-16">
            {/* Background Pattern */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:32px_32px]" />

            {/* Floating Orbs */}
            <motion.div
              className="absolute -top-20 -right-20 w-64 h-64 bg-white/10 rounded-full blur-3xl"
              animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
              transition={{ duration: 5, repeat: Infinity }}
            />
            <motion.div
              className="absolute -bottom-20 -left-20 w-64 h-64 bg-purple-400/20 rounded-full blur-3xl"
              animate={{ scale: [1.2, 1, 1.2], opacity: [0.5, 0.3, 0.5] }}
              transition={{ duration: 5, repeat: Infinity, delay: 1 }}
            />

            <div className="relative z-10 text-center">
              <h3 className="text-3xl lg:text-4xl font-heading font-bold text-white mb-4">
                Ready to Optimize Your Supply Chain?
              </h3>
              <p className="text-primary-100 text-lg mb-8 max-w-2xl mx-auto">
                Get started with our comprehensive logistics solutions and experience
                the difference of working with industry leaders.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <MagneticButton variant="secondary" size="lg">
                  Get Free Consultation
                  <ArrowRightIcon className="w-5 h-5 ml-2" />
                </MagneticButton>
                <MagneticButton variant="ghost" size="lg" className="text-white border-white/30 hover:bg-white/10">
                  View All Services
                </MagneticButton>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Services;
