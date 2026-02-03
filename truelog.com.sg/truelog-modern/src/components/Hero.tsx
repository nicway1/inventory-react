import React, { useRef, useEffect, useState, useCallback } from 'react';
import { motion, useScroll, useTransform, useSpring, useMotionValue, AnimatePresence } from 'framer-motion';
import { ArrowRightIcon, TruckIcon, GlobeAltIcon, ShieldCheckIcon, ClockIcon, PlayIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { MagneticButton, AnimatedText, GlowCard } from './ui';
import { Link } from 'react-router-dom';

// Particle system for background
interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  opacity: number;
}

const ParticleBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Initialize particles
    const particleCount = 80;
    particlesRef.current = Array.from({ length: particleCount }, (_, i) => ({
      id: i,
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 0.5,
      speedX: (Math.random() - 0.5) * 0.5,
      speedY: (Math.random() - 0.5) * 0.5,
      opacity: Math.random() * 0.5 + 0.2,
    }));

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particlesRef.current.forEach((particle: Particle, i: number) => {
        // Update position
        particle.x += particle.speedX;
        particle.y += particle.speedY;

        // Wrap around edges
        if (particle.x < 0) particle.x = canvas.width;
        if (particle.x > canvas.width) particle.x = 0;
        if (particle.y < 0) particle.y = canvas.height;
        if (particle.y > canvas.height) particle.y = 0;

        // Draw particle with TrueLog blue
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(56, 92, 242, ${particle.opacity})`;
        ctx.fill();

        // Draw connections
        particlesRef.current.slice(i + 1).forEach((otherParticle: Particle) => {
          const dx = particle.x - otherParticle.x;
          const dy = particle.y - otherParticle.y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 150) {
            ctx.beginPath();
            ctx.moveTo(particle.x, particle.y);
            ctx.lineTo(otherParticle.x, otherParticle.y);
            ctx.strokeStyle = `rgba(14, 158, 213, ${0.1 * (1 - distance / 150)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        });
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none"
      style={{ opacity: 0.6 }}
    />
  );
};

// Animated gradient orbs with TrueLog colors
const GradientOrbs: React.FC = () => (
  <div className="absolute inset-0 overflow-hidden">
    <motion.div
      className="absolute top-1/4 -left-32 w-[500px] h-[500px] rounded-full blur-[100px]"
      style={{ background: 'linear-gradient(135deg, rgba(56, 92, 242, 0.3) 0%, rgba(14, 158, 213, 0.2) 100%)' }}
      animate={{
        x: [0, 100, 0],
        y: [0, 50, 0],
        scale: [1, 1.2, 1],
      }}
      transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut' }}
    />
    <motion.div
      className="absolute top-1/2 right-0 w-[400px] h-[400px] rounded-full blur-[80px]"
      style={{ background: 'linear-gradient(135deg, rgba(14, 158, 213, 0.25) 0%, rgba(56, 92, 242, 0.15) 100%)' }}
      animate={{
        x: [0, -80, 0],
        y: [0, 80, 0],
        scale: [1, 1.3, 1],
      }}
      transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
    />
    <motion.div
      className="absolute bottom-1/4 left-1/3 w-[350px] h-[350px] rounded-full blur-[90px]"
      style={{ background: 'linear-gradient(135deg, rgba(56, 92, 242, 0.2) 0%, rgba(14, 158, 213, 0.15) 100%)' }}
      animate={{
        x: [0, 60, 0],
        y: [0, -60, 0],
        scale: [1, 1.15, 1],
      }}
      transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut', delay: 4 }}
    />
  </div>
);

// Floating 3D cards
const FloatingCard: React.FC<{
  children: React.ReactNode;
  delay?: number;
  className?: string;
}> = ({ children, delay = 0, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, y: 50, rotateX: -15 }}
    animate={{ opacity: 1, y: 0, rotateX: 0 }}
    transition={{ duration: 1, delay, type: 'spring', stiffness: 100 }}
    className={className}
  >
    <motion.div
      animate={{ y: [0, -10, 0] }}
      transition={{ duration: 4 + delay, repeat: Infinity, ease: 'easeInOut' }}
    >
      {children}
    </motion.div>
  </motion.div>
);

const Hero: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const [showVideo, setShowVideo] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(0);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start'],
  });

  const y = useTransform(scrollYProgress, [0, 1], ['0%', '50%']);
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);
  const scale = useTransform(scrollYProgress, [0, 0.5], [1, 0.95]);

  const springConfig = { stiffness: 100, damping: 30, restDelta: 0.001 };
  const springX = useSpring(mouseX, springConfig);
  const springY = useSpring(mouseY, springConfig);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      const x = (e.clientX - rect.left - rect.width / 2) / 30;
      const y = (e.clientY - rect.top - rect.height / 2) / 30;
      mouseX.set(x);
      mouseY.set(y);
    }
  }, [mouseX, mouseY]);

  const features = [
    { icon: TruckIcon, title: 'Express Delivery', description: 'Same-day options', color: 'from-[#385CF2] to-[#0E9ED5]' },
    { icon: GlobeAltIcon, title: 'Global Network', description: '50+ countries', color: 'from-[#0E9ED5] to-[#385CF2]' },
    { icon: ShieldCheckIcon, title: 'Fully Insured', description: '100% protected', color: 'from-[#385CF2] to-[#0E9ED5]' },
    { icon: ClockIcon, title: '24/7 Support', description: 'Always available', color: 'from-[#0E9ED5] to-[#385CF2]' },
  ];

  const stats = [
    { value: '50K+', label: 'Shipments', suffix: 'Delivered' },
    { value: '99.9%', label: 'Success', suffix: 'Rate' },
    { value: '50+', label: 'Countries', suffix: 'Covered' },
  ];

  const headlines = [
    { main: 'Building the', highlight: 'Future of', sub: 'IT Logistics' },
    { main: 'Global', highlight: 'Freight', sub: 'Forwarding' },
    { main: 'Smart', highlight: 'Supply Chain', sub: 'Management' },
  ];

  // Auto-rotate headlines
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentSlide((prev: number) => (prev + 1) % headlines.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [headlines.length]);

  return (
    <section
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950"
    >
      {/* Video Background */}
      <div className="absolute inset-0 z-0">
        <video
          autoPlay
          muted
          loop
          playsInline
          className="w-full h-full object-cover opacity-20"
          poster={`${process.env.PUBLIC_URL}/assets/images/hero-bg.jpg`}
        >
          <source src="https://videostream44.b-cdn.net/truelog-loop.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-gradient-to-b from-slate-950/80 via-slate-900/60 to-slate-950/90" />
      </div>

      {/* Particle Background */}
      <ParticleBackground />

      {/* Gradient Orbs */}
      <GradientOrbs />

      {/* Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(56,92,242,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(56,92,242,0.03)_1px,transparent_1px)] bg-[size:64px_64px]" />

      {/* Radial gradient overlay */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(15,23,42,0.8)_100%)]" />

      <motion.div style={{ y, opacity, scale }} className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-32 pt-40">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left Column - Text Content */}
          <div className="text-left">
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full backdrop-blur-xl text-sm text-white/90 mb-8"
              style={{ 
                background: 'linear-gradient(135deg, rgba(56, 92, 242, 0.15) 0%, rgba(14, 158, 213, 0.15) 100%)',
                border: '1px solid rgba(56, 92, 242, 0.3)'
              }}
            >
              <motion.span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: '#0E9ED5' }}
                animate={{ scale: [1, 1.2, 1], opacity: [1, 0.7, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <span className="font-medium">Trusted by 500+ companies worldwide</span>
              <motion.span
                className="px-2 py-0.5 rounded-full text-xs"
                style={{ backgroundColor: 'rgba(14, 158, 213, 0.3)', color: '#0E9ED5' }}
                animate={{ opacity: [0.7, 1, 0.7] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                New
              </motion.span>
            </motion.div>

            {/* Animated Headlines - Following TrueLog Typography */}
            <div className="relative h-[200px] lg:h-[240px] mb-8">
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentSlide}
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -30 }}
                  transition={{ duration: 0.6 }}
                  className="absolute inset-0"
                >
                  {/* H1 - Inter Bold, 40-48px, #385CF2 */}
                  <h1 className="text-[40px] lg:text-[48px] font-bold leading-tight" style={{ color: '#385CF2' }}>
                    <AnimatedText text={headlines[currentSlide].main} className="block" delay={0.1} />
                    <span className="block" style={{ 
                      background: 'linear-gradient(135deg, #385CF2 0%, #0E9ED5 100%)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      backgroundClip: 'text'
                    }}>
                      <AnimatedText text={headlines[currentSlide].highlight} delay={0.3} />
                    </span>
                    <AnimatedText text={headlines[currentSlide].sub} className="block text-white" delay={0.5} />
                  </h1>
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Headline indicators */}
            <div className="flex gap-2 mb-8">
              {headlines.map((_, index) => (
                <motion.button
                  key={index}
                  onClick={() => setCurrentSlide(index)}
                  className="h-1.5 rounded-full transition-all duration-300"
                  style={{
                    width: index === currentSlide ? '32px' : '8px',
                    backgroundColor: index === currentSlide ? '#0E9ED5' : 'rgba(255,255,255,0.3)'
                  }}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                />
              ))}
            </div>

            {/* Description - Body Text: Inter Regular, 14-16px */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="text-[16px] text-slate-300 leading-relaxed max-w-xl mb-10"
            >
              Enhance your supply chain with our comprehensive logistics solutions.
              From freight forwarding to IT logistics, we deliver efficiency and reliability
              across Singapore and beyond.
            </motion.p>

            {/* CTA Buttons - Inter Bold, 14-16px, ALL CAPS, White on #0E9ED5 */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.5 }}
              className="flex flex-col sm:flex-row gap-4 mb-12"
            >
              <Link to="/contact-us">
                <motion.button
                  className="px-8 py-4 rounded-xl font-bold uppercase tracking-wider text-white text-[16px] transition-all duration-300"
                  style={{ backgroundColor: '#0E9ED5' }}
                  whileHover={{ 
                    scale: 1.02, 
                    boxShadow: '0 10px 40px -10px rgba(14, 158, 213, 0.5)',
                    backgroundColor: '#0b7aa6'
                  }}
                  whileTap={{ scale: 0.98 }}
                >
                  GET A QUOTE
                  <ArrowRightIcon className="w-5 h-5 ml-2 inline-block" />
                </motion.button>
              </Link>
              <motion.button
                onClick={() => setShowVideo(true)}
                className="group flex items-center gap-3 px-6 py-3 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 text-white hover:bg-white/10 transition-all duration-300"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform"
                  style={{ background: 'linear-gradient(135deg, #385CF2 0%, #0E9ED5 100%)' }}
                >
                  <PlayIcon className="w-4 h-4 text-white ml-0.5" />
                </div>
                <span className="font-medium">Watch Our Story</span>
              </motion.button>
            </motion.div>

            {/* Stats Row */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
              className="flex gap-8 lg:gap-12"
            >
              {stats.map((stat, index) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.7 + index * 0.1 }}
                  className="relative group"
                >
                  <motion.div
                    className="absolute -inset-2 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ background: 'linear-gradient(135deg, rgba(56, 92, 242, 0.2) 0%, rgba(14, 158, 213, 0.2) 100%)' }}
                  />
                  <div className="relative">
                    <div 
                      className="text-3xl lg:text-4xl font-bold"
                      style={{ 
                        background: 'linear-gradient(135deg, #ffffff 0%, #e2e8f0 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text'
                      }}
                    >
                      {stat.value}
                    </div>
                    <div className="text-sm text-slate-400">
                      {stat.label} <span style={{ color: '#0E9ED5' }}>{stat.suffix}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>

          {/* Right Column - Interactive Dashboard */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, x: 50 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            transition={{ duration: 1, delay: 0.3 }}
            className="relative perspective-2000 hidden lg:block"
          >
            <motion.div
              style={{
                rotateX: springY,
                rotateY: springX,
              }}
              className="preserve-3d"
            >
              <GlowCard className="p-1" glowColor="gradient" tilt={false}>
                <div 
                  className="bg-slate-900/90 backdrop-blur-xl rounded-2xl p-6 border border-white/10"
                  style={{ background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%)' }}
                >
                  {/* Dashboard Header */}
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <motion.div
                        className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{ background: 'linear-gradient(135deg, #385CF2 0%, #0E9ED5 100%)' }}
                        animate={{ rotate: [0, 5, -5, 0] }}
                        transition={{ duration: 4, repeat: Infinity }}
                      >
                        <TruckIcon className="w-6 h-6 text-white" />
                      </motion.div>
                      <div>
                        <div className="text-white font-semibold">Logistics Dashboard</div>
                        <div className="text-xs text-slate-400 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: '#0E9ED5' }} />
                          Real-time tracking
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-red-400 hover:bg-red-300 transition-colors cursor-pointer" />
                      <div className="w-3 h-3 rounded-full bg-yellow-400 hover:bg-yellow-300 transition-colors cursor-pointer" />
                      <div className="w-3 h-3 rounded-full bg-green-400 hover:bg-green-300 transition-colors cursor-pointer" />
                    </div>
                  </div>

                  {/* Feature Cards Grid */}
                  <div className="grid grid-cols-2 gap-3 mb-6">
                    {features.map((feature, index) => (
                      <motion.div
                        key={feature.title}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.8 + index * 0.1 }}
                        whileHover={{ scale: 1.03, y: -3 }}
                        className="relative bg-white/5 backdrop-blur rounded-xl p-4 border border-white/10 hover:border-[#0E9ED5]/50 transition-all duration-300 cursor-pointer group overflow-hidden"
                      >
                        <motion.div
                          className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
                          style={{ background: 'linear-gradient(135deg, rgba(56, 92, 242, 0.1) 0%, rgba(14, 158, 213, 0.1) 100%)' }}
                        />
                        <div 
                          className={`relative w-10 h-10 rounded-lg bg-gradient-to-br ${feature.color} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform shadow-lg`}
                        >
                          <feature.icon className="w-5 h-5 text-white" />
                        </div>
                        <div className="relative text-sm font-medium text-white">{feature.title}</div>
                        <div className="relative text-xs text-slate-400">{feature.description}</div>
                      </motion.div>
                    ))}
                  </div>

                  {/* Progress Bars */}
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-slate-300">Active Shipments</span>
                        <motion.span
                          style={{ color: '#385CF2' }}
                          className="font-medium"
                          animate={{ opacity: [1, 0.7, 1] }}
                          transition={{ duration: 2, repeat: Infinity }}
                        >
                          1,247
                        </motion.span>
                      </div>
                      <div className="h-2.5 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full relative"
                          style={{ background: 'linear-gradient(90deg, #385CF2 0%, #0E9ED5 100%)' }}
                          initial={{ width: 0 }}
                          animate={{ width: '78%' }}
                          transition={{ duration: 1.5, delay: 1, ease: 'easeOut' }}
                        >
                          <motion.div
                            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                            animate={{ x: ['-100%', '100%'] }}
                            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                          />
                        </motion.div>
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-slate-300">Delivery Success</span>
                        <span className="text-emerald-400 font-medium">99.9%</span>
                      </div>
                      <div className="h-2.5 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full relative"
                          initial={{ width: 0 }}
                          animate={{ width: '99.9%' }}
                          transition={{ duration: 1.5, delay: 1.2, ease: 'easeOut' }}
                        >
                          <motion.div
                            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                            animate={{ x: ['-100%', '100%'] }}
                            transition={{ duration: 2, repeat: Infinity, ease: 'linear', delay: 0.5 }}
                          />
                        </motion.div>
                      </div>
                    </div>
                  </div>
                </div>
              </GlowCard>

              {/* Floating Badge - Top Right */}
              <FloatingCard delay={1.2} className="absolute -top-6 -right-6 z-20">
                <div className="bg-white rounded-2xl p-4 shadow-2xl shadow-black/30">
                  <div 
                    className="text-2xl font-bold"
                    style={{ 
                      background: 'linear-gradient(135deg, #385CF2 0%, #0E9ED5 100%)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      backgroundClip: 'text'
                    }}
                  >
                    24/7
                  </div>
                  <div className="text-xs text-slate-600">Support</div>
                </div>
              </FloatingCard>

              {/* Floating Badge - Bottom Left */}
              <FloatingCard delay={1.4} className="absolute -bottom-6 -left-6 z-20">
                <div className="bg-white rounded-2xl p-4 shadow-2xl shadow-black/30">
                  <div className="text-2xl font-bold text-emerald-500">ISO</div>
                  <div className="text-xs text-slate-600">Certified</div>
                </div>
              </FloatingCard>

              {/* Floating Badge - Top Left */}
              <FloatingCard delay={1.6} className="absolute top-1/4 -left-12 z-20">
                <div 
                  className="rounded-xl p-3 shadow-xl"
                  style={{ 
                    background: 'linear-gradient(135deg, #385CF2 0%, #0E9ED5 100%)',
                    boxShadow: '0 10px 40px -10px rgba(56, 92, 242, 0.5)'
                  }}
                >
                  <GlobeAltIcon className="w-6 h-6 text-white" />
                </div>
              </FloatingCard>
            </motion.div>
          </motion.div>
        </div>
      </motion.div>

      {/* Scroll Indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1.5 }}
        className="absolute bottom-8 left-1/2 transform -translate-x-1/2 z-10"
      >
        <motion.div
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="flex flex-col items-center gap-2"
        >
          <span className="text-sm text-slate-400 font-medium">Scroll to explore</span>
          <div className="w-6 h-10 border-2 border-slate-500 rounded-full flex justify-center pt-2">
            <motion.div
              animate={{ y: [0, 12, 0], opacity: [1, 0.3, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-1.5 h-3 rounded-full"
              style={{ background: 'linear-gradient(180deg, #385CF2 0%, #0E9ED5 100%)' }}
            />
          </div>
        </motion.div>
      </motion.div>

      {/* Video Modal */}
      <AnimatePresence>
        {showVideo && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
            onClick={() => setShowVideo(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="relative w-full max-w-4xl mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => setShowVideo(false)}
                className="absolute -top-12 right-0 text-white transition-colors"
                style={{ color: 'white' }}
                onMouseEnter={(e) => e.currentTarget.style.color = '#0E9ED5'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'white'}
              >
                <XMarkIcon className="w-8 h-8" />
              </button>
              <div className="aspect-video bg-slate-900 rounded-2xl overflow-hidden shadow-2xl">
                <video
                  autoPlay
                  controls
                  className="w-full h-full object-cover"
                >
                  <source src="https://videostream44.b-cdn.net/truelog-loop.mp4" type="video/mp4" />
                </video>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
};

export default Hero;
