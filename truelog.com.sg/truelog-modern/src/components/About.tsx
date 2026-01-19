import React, { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
  CheckCircleIcon,
  UserGroupIcon,
  GlobeAsiaAustraliaIcon,
  TrophyIcon,
  SparklesIcon,
  ShieldCheckIcon,
  LightBulbIcon,
  EyeIcon
} from '@heroicons/react/24/outline';
import { GlowCard } from './ui';

interface CounterProps {
  target: number;
  suffix?: string;
  duration?: number;
}

const AnimatedCounter: React.FC<CounterProps> = ({ target, suffix = '', duration = 2 }) => {
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

      // Ease out cubic
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

const About: React.FC = () => {
  const achievements = [
    {
      icon: UserGroupIcon,
      number: 500,
      suffix: '+',
      label: 'Happy Clients',
      description: 'Trusted by businesses worldwide',
      gradient: 'from-blue-500 to-indigo-600',
    },
    {
      icon: GlobeAsiaAustraliaIcon,
      number: 50,
      suffix: '+',
      label: 'Countries Served',
      description: 'Global logistics network',
      gradient: 'from-cyan-500 to-blue-600',
    },
    {
      icon: TrophyIcon,
      number: 15,
      suffix: '+',
      label: 'Years Experience',
      description: 'Industry expertise and knowledge',
      gradient: 'from-amber-500 to-orange-600',
    },
    {
      icon: CheckCircleIcon,
      number: 99.9,
      suffix: '%',
      label: 'Success Rate',
      description: 'Reliable and efficient service',
      gradient: 'from-emerald-500 to-green-600',
    }
  ];

  const values = [
    {
      icon: ShieldCheckIcon,
      title: 'Reliability',
      description: 'We deliver on our promises with consistent, dependable service that you can count on.',
      gradient: 'from-blue-500 to-indigo-600',
    },
    {
      icon: LightBulbIcon,
      title: 'Innovation',
      description: 'Leveraging cutting-edge technology and modern solutions to optimize your supply chain.',
      gradient: 'from-purple-500 to-pink-600',
    },
    {
      icon: EyeIcon,
      title: 'Transparency',
      description: 'Clear communication and full visibility into your logistics operations at every step.',
      gradient: 'from-cyan-500 to-blue-600',
    },
    {
      icon: SparklesIcon,
      title: 'Excellence',
      description: 'Committed to exceeding expectations and delivering world-class logistics solutions.',
      gradient: 'from-amber-500 to-orange-600',
    }
  ];

  const features = [
    'IATA and FIATA certified operations',
    '24/7 customer support and tracking',
    'Advanced warehouse management systems',
    'Comprehensive insurance coverage',
    'Dedicated account management'
  ];

  return (
    <section id="about" className="section-padding bg-white overflow-hidden">
      <div className="container-custom">
        {/* Main About Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center mb-24">
          {/* Left Column - Text */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, type: 'spring' }}
          >
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="inline-block px-4 py-2 bg-primary-100 text-primary-700 rounded-full text-sm font-medium mb-6"
            >
              About Truelog
            </motion.span>

            <h2 className="text-4xl lg:text-5xl font-heading font-bold text-secondary-900 mb-6 leading-tight">
              Leading Logistics{' '}
              <span className="gradient-text block">Innovation in Singapore</span>
            </h2>

            <p className="text-lg text-secondary-600 mb-6 leading-relaxed">
              Truelog is Singapore's premier integrated logistics solutions provider,
              delivering comprehensive freight forwarding, warehousing, and specialized
              IT logistics services across the Asia-Pacific region and beyond.
            </p>

            <p className="text-lg text-secondary-600 mb-8 leading-relaxed">
              With over 15 years of industry expertise, we combine traditional logistics
              excellence with modern technology to provide seamless, efficient, and
              cost-effective supply chain solutions for businesses of all sizes.
            </p>

            {/* Key Features */}
            <div className="space-y-4">
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="flex items-center group"
                >
                  <motion.div
                    whileHover={{ scale: 1.2 }}
                    className="w-6 h-6 rounded-full bg-gradient-to-r from-primary-500 to-accent-cyan flex items-center justify-center mr-4 flex-shrink-0"
                  >
                    <CheckCircleIcon className="h-4 w-4 text-white" />
                  </motion.div>
                  <span className="text-secondary-700 group-hover:text-secondary-900 transition-colors">
                    {feature}
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Right Column - Visual */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, type: 'spring' }}
            className="relative"
          >
            <GlowCard className="p-8 bg-gradient-to-br from-secondary-50 to-primary-50" glowColor="gradient">
              <div className="bg-white rounded-2xl p-6 shadow-lg mb-6">
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    className="text-center p-6 bg-gradient-to-br from-primary-50 to-primary-100 rounded-xl"
                  >
                    <div className="text-3xl font-bold gradient-text">
                      <AnimatedCounter target={500} suffix="+" />
                    </div>
                    <div className="text-sm text-secondary-600 mt-1">Clients</div>
                  </motion.div>
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    className="text-center p-6 bg-gradient-to-br from-cyan-50 to-cyan-100 rounded-xl"
                  >
                    <div className="text-3xl font-bold text-cyan-600">
                      <AnimatedCounter target={50} suffix="+" />
                    </div>
                    <div className="text-sm text-secondary-600 mt-1">Countries</div>
                  </motion.div>
                </div>

                <div className="h-36 bg-gradient-to-r from-primary-500 via-purple-500 to-accent-cyan rounded-xl flex items-center justify-center relative overflow-hidden">
                  <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.1)_1px,transparent_1px)] bg-[size:20px_20px]" />
                  <span className="text-white font-semibold text-lg relative z-10">Singapore Logistics Hub</span>
                </div>
              </div>

              {/* Certification Badges */}
              <div className="flex justify-between items-center gap-4">
                {['IATA', 'ISO 9001', 'FIATA'].map((cert, index) => (
                  <motion.div
                    key={cert}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    whileHover={{ y: -5 }}
                    className="bg-white rounded-xl p-4 shadow-md flex-1 text-center"
                  >
                    <div className="text-xs text-secondary-500 mb-1">{cert.split(' ')[0]}</div>
                    <div className="text-sm font-bold gradient-text">{cert.includes(' ') ? cert.split(' ')[1] : 'Certified'}</div>
                  </motion.div>
                ))}
              </div>
            </GlowCard>

            {/* Floating Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.5 }}
              animate={{ y: [0, -10, 0] }}
              className="absolute -top-6 -right-6"
            >
              <div className="bg-gradient-to-br from-primary-500 to-purple-600 text-white rounded-2xl p-5 shadow-xl shadow-primary-500/30">
                <div className="text-2xl font-bold">15+</div>
                <div className="text-xs text-white/80">Years</div>
              </div>
            </motion.div>
          </motion.div>
        </div>

        {/* Stats Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-24"
        >
          {achievements.map((achievement, index) => (
            <motion.div
              key={achievement.label}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
            >
              <GlowCard className="p-8 bg-white text-center h-full" glowColor="primary">
                <motion.div
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  className={`w-16 h-16 bg-gradient-to-br ${achievement.gradient} rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-lg`}
                >
                  <achievement.icon className="h-8 w-8 text-white" />
                </motion.div>
                <div className="text-4xl font-bold text-secondary-900 mb-2">
                  <AnimatedCounter
                    target={achievement.number}
                    suffix={achievement.suffix}
                  />
                </div>
                <div className="text-lg font-semibold text-secondary-800 mb-2">
                  {achievement.label}
                </div>
                <div className="text-sm text-secondary-500">
                  {achievement.description}
                </div>
              </GlowCard>
            </motion.div>
          ))}
        </motion.div>

        {/* Values Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <motion.span
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="inline-block px-4 py-2 bg-purple-100 text-purple-700 rounded-full text-sm font-medium mb-4"
          >
            Our Values
          </motion.span>
          <h3 className="text-3xl lg:text-4xl font-heading font-bold text-secondary-900 mb-4">
            The Principles That{' '}
            <span className="gradient-text">Guide Us</span>
          </h3>
          <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
            Our core values define our commitment to excellence and shape every interaction with our clients.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {values.map((value, index) => (
            <motion.div
              key={value.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="text-center group"
            >
              <motion.div
                whileHover={{ scale: 1.1, y: -5 }}
                className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${value.gradient} flex items-center justify-center mx-auto mb-6 shadow-lg transition-shadow group-hover:shadow-xl`}
              >
                <value.icon className="h-10 w-10 text-white" />
              </motion.div>
              <h4 className="text-xl font-bold text-secondary-900 mb-3 group-hover:gradient-text transition-all">
                {value.title}
              </h4>
              <p className="text-secondary-600 leading-relaxed">
                {value.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default About;
