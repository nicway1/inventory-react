import React, { useState, useEffect, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
  TruckIcon,
  GlobeAltIcon,
  BuildingStorefrontIcon,
  UserGroupIcon,
  CheckIcon
} from '@heroicons/react/24/outline';
import { GlowCard, MagneticButton } from './ui';

interface AnimatedCounterProps {
  target: number;
  suffix?: string;
  duration?: number;
}

const AnimatedCounter: React.FC<AnimatedCounterProps> = ({ target, suffix = '', duration = 2 }) => {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (!isInView) return;

    let startTime: number;
    let animationFrame: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(easeOut * target));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [isInView, target, duration]);

  return (
    <span ref={ref}>
      {count.toLocaleString()}{suffix}
    </span>
  );
};

const Stats: React.FC = () => {
  const stats = [
    {
      icon: TruckIcon,
      end: 50000,
      suffix: '+',
      label: 'Successful Deliveries',
      description: 'Packages delivered worldwide',
      gradient: 'from-blue-500 to-indigo-600',
    },
    {
      icon: GlobeAltIcon,
      end: 50,
      suffix: '+',
      label: 'Countries Served',
      description: 'Global logistics network',
      gradient: 'from-emerald-500 to-teal-600',
    },
    {
      icon: BuildingStorefrontIcon,
      end: 25,
      suffix: '+',
      label: 'Warehouse Facilities',
      description: 'Strategic locations',
      gradient: 'from-purple-500 to-pink-600',
    },
    {
      icon: UserGroupIcon,
      end: 1000,
      suffix: '+',
      label: 'Happy Clients',
      description: 'Trusted partnerships',
      gradient: 'from-amber-500 to-orange-600',
    }
  ];

  const features = [
    { title: 'Industry Expertise', description: '15+ years in logistics and supply chain management' },
    { title: 'Technology Driven', description: 'Advanced tracking and management systems' },
    { title: 'Global Network', description: 'Strategic partnerships across major trade routes' },
    { title: 'Customer Focus', description: 'Dedicated support and customized solutions' }
  ];

  const metrics = [
    { value: '99.9%', label: 'On-time Delivery', gradient: 'from-primary-500 to-primary-600' },
    { value: '24/7', label: 'Customer Support', gradient: 'from-emerald-500 to-green-600' },
    { value: 'ISO', label: 'Certified Quality', gradient: 'from-purple-500 to-indigo-600' },
    { value: '100%', label: 'Cargo Insurance', gradient: 'from-amber-500 to-orange-600' },
  ];

  return (
    <section className="section-padding bg-mesh relative overflow-hidden">
      {/* Background Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:40px_40px]" />

      {/* Floating Orbs */}
      <motion.div
        className="absolute top-20 left-10 w-64 h-64 bg-primary-500/10 rounded-full blur-3xl"
        animate={{ x: [0, 30, 0], y: [0, -20, 0] }}
        transition={{ duration: 8, repeat: Infinity }}
      />
      <motion.div
        className="absolute bottom-20 right-10 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl"
        animate={{ x: [0, -30, 0], y: [0, 20, 0] }}
        transition={{ duration: 10, repeat: Infinity, delay: 1 }}
      />

      <div className="container-custom relative">
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
            Our Impact
          </motion.span>
          <h2 className="text-4xl lg:text-5xl font-heading font-bold text-secondary-900 mb-4">
            Trusted by Businesses{' '}
            <span className="gradient-text">Worldwide</span>
          </h2>
          <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
            Our track record speaks for itself. Join thousands of satisfied clients who trust us with their logistics needs.
          </p>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
            >
              <GlowCard className="p-8 bg-white text-center h-full" glowColor="primary">
                <motion.div
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  transition={{ type: 'spring', stiffness: 300 }}
                  className={`w-16 h-16 bg-gradient-to-br ${stat.gradient} rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-lg`}
                >
                  <stat.icon className="h-8 w-8 text-white" />
                </motion.div>

                <div className="text-4xl lg:text-5xl font-bold text-secondary-900 mb-2">
                  <AnimatedCounter target={stat.end} suffix={stat.suffix} />
                </div>
                <div className="text-lg font-semibold text-secondary-800 mb-1">
                  {stat.label}
                </div>
                <div className="text-sm text-secondary-500">
                  {stat.description}
                </div>

                {/* Progress Bar */}
                <div className="mt-6 w-full bg-secondary-100 rounded-full h-1.5 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: '100%' }}
                    viewport={{ once: true }}
                    transition={{ duration: 2, delay: index * 0.2 }}
                    className={`h-full bg-gradient-to-r ${stat.gradient} rounded-full`}
                  />
                </div>
              </GlowCard>
            </motion.div>
          ))}
        </div>

        {/* Why Choose Us Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <GlowCard className="p-8 lg:p-12 bg-white" glowColor="gradient">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              {/* Left - Content */}
              <div>
                <motion.span
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  className="inline-block px-4 py-2 bg-purple-100 text-purple-700 rounded-full text-sm font-medium mb-4"
                >
                  Why Choose Us
                </motion.span>
                <h3 className="text-3xl lg:text-4xl font-heading font-bold text-secondary-900 mb-8">
                  The Truelog{' '}
                  <span className="gradient-text">Advantage</span>
                </h3>
                <div className="space-y-5">
                  {features.map((item, index) => (
                    <motion.div
                      key={item.title}
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.6, delay: index * 0.1 }}
                      className="flex items-start gap-4 group"
                    >
                      <motion.div
                        whileHover={{ scale: 1.1 }}
                        className="w-8 h-8 bg-gradient-to-br from-primary-500 to-purple-500 rounded-lg flex items-center justify-center flex-shrink-0 shadow-md"
                      >
                        <CheckIcon className="w-4 h-4 text-white" />
                      </motion.div>
                      <div>
                        <h4 className="font-semibold text-secondary-900 mb-1 group-hover:text-primary-600 transition-colors">
                          {item.title}
                        </h4>
                        <p className="text-secondary-600 text-sm">
                          {item.description}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.5 }}
                  className="mt-8"
                >
                  <MagneticButton variant="primary" size="lg">
                    Learn More About Us
                  </MagneticButton>
                </motion.div>
              </div>

              {/* Right - Metrics Grid */}
              <div className="relative">
                <div className="bg-gradient-to-br from-primary-50 via-purple-50 to-cyan-50 rounded-3xl p-8">
                  <div className="grid grid-cols-2 gap-4">
                    {metrics.map((metric, index) => (
                      <motion.div
                        key={metric.label}
                        initial={{ opacity: 0, scale: 0.9 }}
                        whileInView={{ opacity: 1, scale: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.3 + index * 0.1 }}
                        whileHover={{ y: -5, scale: 1.02 }}
                        className="bg-white rounded-2xl p-5 text-center shadow-lg hover:shadow-xl transition-all duration-300"
                      >
                        <div className={`text-2xl lg:text-3xl font-bold bg-gradient-to-r ${metric.gradient} bg-clip-text text-transparent mb-1`}>
                          {metric.value}
                        </div>
                        <div className="text-xs text-secondary-600">
                          {metric.label}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>

                {/* Floating Icons */}
                <motion.div
                  animate={{ y: [0, -10, 0] }}
                  transition={{ duration: 3, repeat: Infinity }}
                  className="absolute -top-4 -right-4 bg-white rounded-2xl p-4 shadow-xl"
                >
                  <TruckIcon className="h-6 w-6 text-primary-600" />
                </motion.div>

                <motion.div
                  animate={{ y: [0, 10, 0] }}
                  transition={{ duration: 4, repeat: Infinity, delay: 0.5 }}
                  className="absolute -bottom-4 -left-4 bg-white rounded-2xl p-4 shadow-xl"
                >
                  <GlobeAltIcon className="h-6 w-6 text-emerald-600" />
                </motion.div>
              </div>
            </div>
          </GlowCard>
        </motion.div>
      </div>
    </section>
  );
};

export default Stats;
