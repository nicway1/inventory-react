import React, { useRef, useState } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  TruckIcon,
  BuildingStorefrontIcon,
  ComputerDesktopIcon,
  GlobeAltIcon,
  ClipboardDocumentCheckIcon,
  ShieldCheckIcon,
  ArrowRightIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';

// TrueLog Brand Colors
const TRUELOG_BLUE = '#385CF2';
const TRUELOG_CYAN = '#0E9ED5';

// 3D Tilt Card Component
interface TiltCardProps {
  children: React.ReactNode;
  className?: string;
}

const TiltCard: React.FC<TiltCardProps> = ({ children, className = '' }) => {
  const ref = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const mouseXSpring = useSpring(x, { stiffness: 300, damping: 30 });
  const mouseYSpring = useSpring(y, { stiffness: 300, damping: 30 });

  const rotateX = useTransform(mouseYSpring, [-0.5, 0.5], ['10deg', '-10deg']);
  const rotateY = useTransform(mouseXSpring, [-0.5, 0.5], ['-10deg', '10deg']);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const xPct = mouseX / width - 0.5;
    const yPct = mouseY / height - 0.5;
    x.set(xPct);
    y.set(yPct);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={handleMouseLeave}
      style={{
        rotateX,
        rotateY,
        transformStyle: 'preserve-3d',
      }}
      className={`relative ${className}`}
    >
      <motion.div
        style={{
          transform: 'translateZ(75px)',
          transformStyle: 'preserve-3d',
        }}
        className="h-full"
      >
        {children}
      </motion.div>
      {/* Glow effect with TrueLog colors */}
      <motion.div
        className="absolute inset-0 rounded-3xl blur-xl -z-10"
        style={{ background: `linear-gradient(135deg, ${TRUELOG_BLUE}20 0%, ${TRUELOG_CYAN}20 100%)` }}
        animate={{ opacity: isHovered ? 1 : 0 }}
        transition={{ duration: 0.3 }}
      />
    </motion.div>
  );
};

// Animated Background Pattern
const BackgroundPattern: React.FC = () => (
  <div className="absolute inset-0 overflow-hidden">
    <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-blue-50/30" />
    <svg className="absolute inset-0 w-full h-full opacity-[0.03]" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
          <path d="M 60 0 L 0 0 0 60" fill="none" stroke="currentColor" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
    </svg>
    <motion.div
      className="absolute top-1/4 -left-32 w-96 h-96 rounded-full blur-3xl"
      style={{ background: `${TRUELOG_BLUE}15` }}
      animate={{ x: [0, 50, 0], y: [0, 30, 0] }}
      transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
    />
    <motion.div
      className="absolute bottom-1/4 -right-32 w-80 h-80 rounded-full blur-3xl"
      style={{ background: `${TRUELOG_CYAN}15` }}
      animate={{ x: [0, -30, 0], y: [0, 50, 0] }}
      transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
    />
  </div>
);

const Services: React.FC = () => {
  const services = [
    {
      icon: TruckIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/Air-Frieght-Services.jpg`,
      title: 'Freight Forwarding',
      description: 'Comprehensive air and sea freight services with global reach and competitive rates.',
      features: ['Air Freight', 'Sea Freight', 'Customs Clearance', 'Cargo Insurance'],
      href: '/services/freight-forwarding',
      gradient: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
    },
    {
      icon: BuildingStorefrontIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/containerized-services.jpg`,
      title: 'Global Fulfillment',
      description: 'End-to-end warehousing and distribution solutions for seamless supply chain management.',
      features: ['3PL Warehousing', 'Distribution', 'Inventory Management', 'Order Fulfillment'],
      href: '/services/global-fulfillment',
      gradient: `linear-gradient(135deg, ${TRUELOG_CYAN} 0%, ${TRUELOG_BLUE} 100%)`,
    },
    {
      icon: ComputerDesktopIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/trucking-services.jpg`,
      title: 'ICT Logistics',
      description: 'Specialized logistics solutions for technology equipment and sensitive electronics.',
      features: ['IT Asset Management', 'Tech Equipment Shipping', 'Secure Handling', 'White Glove Service'],
      href: '/services/ict-logistics',
      gradient: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
    },
    {
      icon: ClipboardDocumentCheckIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/Air-Frieght-Services.jpg`,
      title: 'IOR/EOR Solutions',
      description: 'Importer and Exporter of Record services for seamless international trade.',
      features: ['Import Compliance', 'Export Documentation', 'Trade Regulations', 'Risk Management'],
      href: '/services/ior-eor-solutions',
      gradient: `linear-gradient(135deg, ${TRUELOG_CYAN} 0%, ${TRUELOG_BLUE} 100%)`,
    },
    {
      icon: GlobeAltIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/containerized-services.jpg`,
      title: 'Global Coverage',
      description: 'Worldwide logistics network with local expertise in key markets.',
      features: ['International Network', 'Local Partners', 'Regional Expertise', 'Global Standards'],
      href: '/global-coverage',
      gradient: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
    },
    {
      icon: ShieldCheckIcon,
      image: `${process.env.PUBLIC_URL}/assets/images/trucking-services.jpg`,
      title: 'Compliance',
      description: 'Regulatory compliance and documentation services for international trade.',
      features: ['Import Licenses', 'Trade Compliance', 'Documentation', 'Regulatory Support'],
      href: '/services/compliance',
      gradient: `linear-gradient(135deg, ${TRUELOG_CYAN} 0%, ${TRUELOG_BLUE} 100%)`,
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
      },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 50, rotateX: -10 },
    visible: {
      opacity: 1,
      y: 0,
      rotateX: 0,
      transition: {
        type: 'spring' as const,
        stiffness: 100,
        damping: 20,
      },
    },
  };

  return (
    <section id="services" className="relative py-24 lg:py-32 overflow-hidden">
      <BackgroundPattern />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header - Following TrueLog Typography */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-20"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-5 py-2.5 backdrop-blur-sm rounded-full text-sm font-medium mb-6"
            style={{
              background: `linear-gradient(135deg, ${TRUELOG_BLUE}15 0%, ${TRUELOG_CYAN}15 100%)`,
              border: `1px solid ${TRUELOG_BLUE}30`,
              color: TRUELOG_BLUE
            }}
          >
            <SparklesIcon className="w-4 h-4" />
            Our Services
          </motion.div>
          {/* H2 - Inter Bold, 28-32px, #000000 */}
          <h2 className="text-[28px] lg:text-[32px] font-bold text-black mb-6">
            Our{' '}
            <span style={{
              background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              Solutions
            </span>
          </h2>
          {/* Body Text - Inter Regular, 14-16px */}
          <p className="text-[16px] text-black max-w-3xl mx-auto leading-relaxed">
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
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 perspective-1000"
        >
          {services.map((service, index) => (
            <motion.div key={service.title} variants={cardVariants}>
              <TiltCard className="h-full">
                <div className="h-full bg-white rounded-3xl shadow-xl shadow-slate-200/50 overflow-hidden border border-slate-100 hover:border-[#0E9ED5]/30 transition-colors duration-300 group">
                  {/* Image Container */}
                  <div className="relative h-52 overflow-hidden">
                    <motion.img
                      src={service.image}
                      alt={service.title}
                      className="w-full h-full object-cover"
                      whileHover={{ scale: 1.1 }}
                      transition={{ duration: 0.6, ease: 'easeOut' }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-slate-900/40 to-transparent" />

                    {/* Animated gradient overlay on hover */}
                    <motion.div
                      className="absolute inset-0 opacity-0 group-hover:opacity-30 transition-opacity duration-500"
                      style={{ background: service.gradient }}
                    />

                    {/* Icon Badge */}
                    <motion.div
                      className="absolute top-4 right-4 w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg"
                      style={{ background: service.gradient }}
                      whileHover={{ scale: 1.1, rotate: 5 }}
                      transition={{ type: 'spring', stiffness: 300 }}
                    >
                      <service.icon className="h-7 w-7 text-white" />
                    </motion.div>

                    {/* Title on Image - H3 style */}
                    <div className="absolute bottom-4 left-4 right-4">
                      <h3 className="text-[20px] lg:text-[24px] font-medium text-white drop-shadow-lg">{service.title}</h3>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-6">
                    {/* Body text */}
                    <p className="text-[14px] lg:text-[16px] text-black mb-6 leading-relaxed">
                      {service.description}
                    </p>

                    {/* Features List */}
                    <div className="space-y-3 mb-6">
                      {service.features.map((feature, featureIndex) => (
                        <motion.div
                          key={featureIndex}
                          className="flex items-center text-sm group/feature"
                          initial={{ opacity: 0, x: -10 }}
                          whileInView={{ opacity: 1, x: 0 }}
                          viewport={{ once: true }}
                          transition={{ delay: 0.1 * featureIndex }}
                        >
                          <motion.div
                            className="w-2 h-2 rounded-full mr-3 group-hover/feature:scale-150 transition-transform"
                            style={{ background: service.gradient }}
                            whileHover={{ scale: 1.5 }}
                          />
                          <span className="text-black group-hover/feature:text-slate-900 transition-colors font-medium">
                            {feature}
                          </span>
                        </motion.div>
                      ))}
                    </div>

                    {/* Learn More Link */}
                    <Link
                      to={service.href}
                      className="group/link inline-flex items-center text-sm font-semibold transition-opacity"
                      style={{ color: TRUELOG_CYAN }}
                    >
                      Learn More
                      <motion.span
                        className="ml-2"
                        initial={{ x: 0 }}
                        whileHover={{ x: 5 }}
                        transition={{ type: 'spring', stiffness: 400 }}
                      >
                        <ArrowRightIcon className="h-4 w-4" style={{ color: TRUELOG_CYAN }} />
                      </motion.span>
                    </Link>
                  </div>
                </div>
              </TiltCard>
            </motion.div>
          ))}
        </motion.div>

        {/* CTA Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="mt-24"
        >
          <div className="relative overflow-hidden rounded-[2rem] p-12 lg:p-16" style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)' }}>
            {/* Animated Background */}
            <div className="absolute inset-0">
              <div className="absolute inset-0" style={{ background: `linear-gradient(rgba(56, 92, 242, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(56, 92, 242, 0.1) 1px, transparent 1px)`, backgroundSize: '40px 40px' }} />
              <motion.div
                className="absolute -top-32 -right-32 w-96 h-96 rounded-full blur-[100px]"
                style={{ background: `${TRUELOG_BLUE}30` }}
                animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
                transition={{ duration: 8, repeat: Infinity }}
              />
              <motion.div
                className="absolute -bottom-32 -left-32 w-80 h-80 rounded-full blur-[80px]"
                style={{ background: `${TRUELOG_CYAN}25` }}
                animate={{ scale: [1.2, 1, 1.2], opacity: [0.5, 0.3, 0.5] }}
                transition={{ duration: 8, repeat: Infinity, delay: 2 }}
              />
              <motion.div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full blur-[60px]"
                style={{ background: `${TRUELOG_BLUE}20` }}
                animate={{ scale: [1, 1.3, 1], opacity: [0.4, 0.2, 0.4] }}
                transition={{ duration: 6, repeat: Infinity, delay: 1 }}
              />
            </div>

            <div className="relative z-10 text-center">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full text-sm text-white/80 mb-6"
              >
                <span className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: TRUELOG_CYAN }} />
                Free consultation available
              </motion.div>
              {/* H2 style for CTA */}
              <h3 className="text-[28px] lg:text-[32px] font-bold text-white mb-6">
                Ready to Optimize Your{' '}
                <span style={{
                  background: `linear-gradient(135deg, ${TRUELOG_BLUE} 0%, ${TRUELOG_CYAN} 100%)`,
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text'
                }}>
                  Supply Chain?
                </span>
              </h3>
              <p className="text-slate-300 text-[16px] mb-10 max-w-2xl mx-auto leading-relaxed">
                Get started with our comprehensive logistics solutions and experience
                the difference of working with industry leaders.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link to="/contact-us">
                  {/* CTA Button - Inter Bold, 14-16px, ALL CAPS, White on #0E9ED5 */}
                  <motion.button
                    className="px-8 py-4 rounded-xl font-bold uppercase tracking-wider text-white text-[16px] transition-all duration-300"
                    style={{ backgroundColor: TRUELOG_CYAN }}
                    whileHover={{
                      scale: 1.02,
                      boxShadow: `0 10px 40px -10px ${TRUELOG_CYAN}80`,
                      backgroundColor: '#0b7aa6'
                    }}
                    whileTap={{ scale: 0.98 }}
                  >
                    GET FREE CONSULTATION
                    <ArrowRightIcon className="w-5 h-5 ml-2 inline-block" />
                  </motion.button>
                </Link>
                <Link to="/services">
                  <motion.button
                    className="px-8 py-4 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 text-white font-semibold hover:bg-white/20 transition-all duration-300"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    View All Services
                  </motion.button>
                </Link>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Services;
