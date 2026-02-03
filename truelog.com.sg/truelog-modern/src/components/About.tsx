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

// TrueLog Brand Colors
const TRUELOG_BLUE = '#385CF2';
const TRUELOG_CYAN = '#0E9ED5';

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
    },
    {
      icon: GlobeAsiaAustraliaIcon,
      number: 50,
      suffix: '+',
      label: 'Countries Served',
      description: 'Global logistics network',
    },
    {
      icon: TrophyIcon,
      number: 15,
      suffix: '+',
      label: 'Years Experience',
      description: 'Industry expertise and knowledge',
    },
    {
      icon: CheckCircleIcon,
      number: 99.9,
      suffix: '%',
      label: 'Success Rate',
      description: 'Reliable and efficient service',
    }
  ];

  const values = [
    {
      icon: ShieldCheckIcon,
      title: 'Reliability',
      description: 'We deliver on our promises with consistent, dependable service that you can count on.',
    },
    {
      icon: LightBulbIcon,
      title: 'Innovation',
      description: 'Leveraging cutting-edge technology and modern solutions to optimize your supply chain.',
    },
    {
      icon: EyeIcon,
      title: 'Transparency',
      description: 'Clear communication and full visibility into your logistics operations at every step.',
    },
    {
      icon: SparklesIcon,
      title: 'Excellence',
      description: 'Committed to exceeding expectations and delivering world-class logistics solutions.',
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
              className="inline-block px-4 py-2 rounded-full text-sm font-medium mb-6"
              style={{ 
                background: `linear-gradient(135deg, ${TRUELOG_BLUE}15 0%, ${TRUELOG_CYAN}15 100%)`,
                border: `1px solid ${TRUELOG_BLUE}30`,
                color: TRUELOG_BLUE
              }}
            >
              About Truelog
            </motion.span>

            {/* H2 - Inter Bold, 28-32px, #000000 */}
            <h2 className="text-[28px] lg:text-[32px] font-bold text-black mb-6 leading-tight">
              Leading Logistics{' '}
              <span style={{ 
                background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>
                Innovation in Singapore
              </span>
            </h2>

            {/* Body Text - Inter Regular, 14-16px */}
            <p className="text-[16px] text-black mb-6 leading-relaxed">
              Truelog is Singapore's premier integrated logistics solutions provider,
              delivering comprehensive freight forwarding, warehousing, and specialized
              IT logistics services across the Asia-Pacific region and beyond.
            </p>

            <p className="text-[16px] text-black mb-8 leading-relaxed">
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
                    className="w-6 h-6 rounded-full flex items-center justify-center mr-4 flex-shrink-0"
                    style={{ background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)` }}
                  >
                    <CheckCircleIcon className="h-4 w-4 text-white" />
                  </motion.div>
                  <span className="text-black group-hover:text-slate-900 transition-colors">
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
            <GlowCard className="p-8 bg-gradient-to-br from-slate-50 to-blue-50" glowColor="gradient">
              <div className="bg-white rounded-2xl p-6 shadow-lg mb-6">
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    className="text-center p-6 rounded-xl"
                    style={{ background: `linear-gradient(135deg, ${TRUELOG_BLUE}10 0%, ${TRUELOG_BLUE}20 100%)` }}
                  >
                    <div 
                      className="text-3xl font-bold"
                      style={{ 
                        background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text'
                      }}
                    >
                      <AnimatedCounter target={500} suffix="+" />
                    </div>
                    <div className="text-sm text-black mt-1">Clients</div>
                  </motion.div>
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    className="text-center p-6 rounded-xl"
                    style={{ background: `linear-gradient(135deg, ${TRUELOG_CYAN}10 0%, ${TRUELOG_CYAN}20 100%)` }}
                  >
                    <div className="text-3xl font-bold" style={{ color: TRUELOG_CYAN }}>
                      <AnimatedCounter target={50} suffix="+" />
                    </div>
                    <div className="text-sm text-black mt-1">Countries</div>
                  </motion.div>
                </div>

                <div 
                  className="h-36 rounded-xl flex items-center justify-center relative overflow-hidden"
                  style={{ background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)` }}
                >
                  <div className="absolute inset-0" style={{ background: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
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
                    <div className="text-xs text-slate-500 mb-1">{cert.split(' ')[0]}</div>
                    <div 
                      className="text-sm font-bold"
                      style={{ 
                        background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text'
                      }}
                    >
                      {cert.includes(' ') ? cert.split(' ')[1] : 'Certified'}
                    </div>
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
              <div 
                className="text-white rounded-2xl p-5 shadow-xl"
                style={{ 
                  background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
                  boxShadow: `0 10px 40px -10px ${TRUELOG_BLUE}50`
                }}
              >
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
                  className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-lg"
                  style={{ 
                    background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
                    boxShadow: `0 10px 30px -10px ${TRUELOG_BLUE}40`
                  }}
                >
                  <achievement.icon className="h-8 w-8 text-white" />
                </motion.div>
                <div className="text-4xl font-bold text-black mb-2">
                  <AnimatedCounter
                    target={achievement.number}
                    suffix={achievement.suffix}
                  />
                </div>
                <div className="text-lg font-semibold text-black mb-2">
                  {achievement.label}
                </div>
                <div className="text-sm text-slate-500">
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
            className="inline-block px-4 py-2 rounded-full text-sm font-medium mb-4"
            style={{ 
              background: `${TRUELOG_CYAN}15`,
              border: `1px solid ${TRUELOG_CYAN}30`,
              color: TRUELOG_CYAN
            }}
          >
            Our Values
          </motion.span>
          {/* H2 style */}
          <h3 className="text-[28px] lg:text-[32px] font-bold text-black mb-4">
            The Principles That{' '}
            <span style={{ 
              background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              Guide Us
            </span>
          </h3>
          <p className="text-[16px] text-black max-w-3xl mx-auto">
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
                className="w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg transition-shadow group-hover:shadow-xl"
                style={{ 
                  background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
                  boxShadow: `0 10px 30px -10px ${TRUELOG_BLUE}40`
                }}
              >
                <value.icon className="h-10 w-10 text-white" />
              </motion.div>
              {/* H3 style - Inter Medium, 20-24px, #0E9ED5 */}
              <h4 
                className="text-[20px] lg:text-[24px] font-medium mb-3 transition-all"
                style={{ color: TRUELOG_CYAN }}
              >
                {value.title}
              </h4>
              <p className="text-[14px] lg:text-[16px] text-black leading-relaxed">
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
