import React, { useEffect, useRef, useState } from 'react';

interface LiquidEtherProps {
  className?: string;
  colors?: string[];
  speed?: number;
  blur?: number;
}

const LiquidEther: React.FC<LiquidEtherProps> = ({
  className = '',
  colors = ['#3b82f6', '#6366f1', '#8b5cf6', '#ec4899', '#f97316', '#10b981', '#06b6d4'],
  speed = 0.0003,
  blur = 120
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;
    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let targetMouseX = mouseX;
    let targetMouseY = mouseY;
    let mouseVelocityX = 0;
    let mouseVelocityY = 0;

    // Set canvas size
    const setCanvasSize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    setCanvasSize();
    window.addEventListener('resize', setCanvasSize);

    // Enhanced mouse tracking with velocity
    const handleMouseMove = (e: MouseEvent) => {
      const newMouseX = e.clientX;
      const newMouseY = e.clientY;

      mouseVelocityX = (newMouseX - targetMouseX) * 0.5;
      mouseVelocityY = (newMouseY - targetMouseY) * 0.5;

      targetMouseX = newMouseX;
      targetMouseY = newMouseY;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Convert hex colors to RGB
    const hexToRgb = (hex: string) => {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
      } : { r: 59, g: 130, b: 246 };
    };

    const rgbColors = colors.map(hexToRgb);

    // Particle system for extra effects
    class Particle {
      x: number;
      y: number;
      vx: number;
      vy: number;
      life: number;
      maxLife: number;
      size: number;
      color: { r: number; g: number; b: number };

      constructor(x: number, y: number) {
        this.x = x;
        this.y = y;
        this.vx = (Math.random() - 0.5) * 2;
        this.vy = (Math.random() - 0.5) * 2;
        this.life = 1;
        this.maxLife = Math.random() * 60 + 40;
        this.size = Math.random() * 3 + 1;
        this.color = rgbColors[Math.floor(Math.random() * rgbColors.length)];
      }

      update() {
        this.x += this.vx;
        this.y += this.vy;
        this.life -= 1 / this.maxLife;
        this.vx *= 0.98;
        this.vy *= 0.98;
      }

      draw(ctx: CanvasRenderingContext2D) {
        if (this.life <= 0) return;

        ctx.save();
        ctx.globalAlpha = this.life * 0.6;
        const gradient = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.size * 3);
        gradient.addColorStop(0, `rgba(${this.color.r}, ${this.color.g}, ${this.color.b}, ${this.life})`);
        gradient.addColorStop(1, 'transparent');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size * 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    }

    const particles: Particle[] = [];

    // Enhanced Blob with more features
    class Blob {
      x: number;
      y: number;
      radius: number;
      baseRadius: number;
      color: { r: number; g: number; b: number };
      speedX: number;
      speedY: number;
      angle: number;
      baseX: number;
      baseY: number;
      pulsePhase: number;
      rotationSpeed: number;

      constructor() {
        this.x = Math.random() * (canvas?.width || window.innerWidth);
        this.y = Math.random() * (canvas?.height || window.innerHeight);
        this.baseX = this.x;
        this.baseY = this.y;
        this.baseRadius = Math.random() * 200 + 150;
        this.radius = this.baseRadius;
        this.color = rgbColors[Math.floor(Math.random() * rgbColors.length)];
        this.speedX = (Math.random() - 0.5) * 0.8;
        this.speedY = (Math.random() - 0.5) * 0.8;
        this.angle = Math.random() * Math.PI * 2;
        this.pulsePhase = Math.random() * Math.PI * 2;
        this.rotationSpeed = (Math.random() - 0.5) * 0.02;
      }

      update(time: number, mouseX: number, mouseY: number, mouseVelX: number, mouseVelY: number) {
        if (!canvas) return;

        // Pulsing effect
        this.radius = this.baseRadius + Math.sin(time * 0.05 + this.pulsePhase) * 30;

        // Rotation
        this.angle += this.rotationSpeed;

        // Smooth autonomous motion
        this.baseX += Math.sin(this.angle + time * 0.001) * this.speedX;
        this.baseY += Math.cos(this.angle + time * 0.001) * this.speedY;

        // Wrap around edges
        if (this.baseX < -this.radius) this.baseX = canvas.width + this.radius;
        if (this.baseX > canvas.width + this.radius) this.baseX = -this.radius;
        if (this.baseY < -this.radius) this.baseY = canvas.height + this.radius;
        if (this.baseY > canvas.height + this.radius) this.baseY = -this.radius;

        // Enhanced mouse interaction
        const dx = mouseX - this.baseX;
        const dy = mouseY - this.baseY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const maxDistance = 400;

        if (distance < maxDistance) {
          const force = (maxDistance - distance) / maxDistance;
          const pullStrength = 0.4 + Math.abs(mouseVelX + mouseVelY) * 0.01;

          this.x = this.baseX + dx * force * pullStrength;
          this.y = this.baseY + dy * force * pullStrength;

          // Add particle trail when mouse is moving fast
          if (Math.abs(mouseVelX) + Math.abs(mouseVelY) > 5 && Math.random() > 0.7) {
            particles.push(new Particle(this.x, this.y));
          }
        } else {
          this.x += (this.baseX - this.x) * 0.08;
          this.y += (this.baseY - this.y) * 0.08;
        }
      }

      draw(ctx: CanvasRenderingContext2D) {
        // Multi-layer gradient for depth
        const gradient = ctx.createRadialGradient(
          this.x,
          this.y,
          0,
          this.x,
          this.y,
          this.radius
        );

        // Enhanced gradient with multiple stops
        gradient.addColorStop(0, `rgba(${this.color.r}, ${this.color.g}, ${this.color.b}, 0.8)`);
        gradient.addColorStop(0.4, `rgba(${this.color.r}, ${this.color.g}, ${this.color.b}, 0.6)`);
        gradient.addColorStop(0.7, `rgba(${this.color.r}, ${this.color.g}, ${this.color.b}, 0.3)`);
        gradient.addColorStop(1, 'transparent');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Create more blobs for richer effect
    const blobs: Blob[] = [];
    const blobCount = 7;

    for (let i = 0; i < blobCount; i++) {
      blobs.push(new Blob());
    }

    // Animation loop with advanced effects
    const animate = () => {
      time += 1;

      // Smooth mouse interpolation
      mouseX += (targetMouseX - mouseX) * 0.1;
      mouseY += (targetMouseY - mouseY) * 0.1;

      // Clear with slight trail effect for smoothness
      ctx.fillStyle = 'rgba(15, 23, 42, 0.3)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Apply advanced blur and blending
      ctx.filter = `blur(80px) brightness(1.1) contrast(1.2)`;
      ctx.globalCompositeOperation = 'screen';

      // Update and draw blobs
      blobs.forEach((blob) => {
        blob.update(time, mouseX, mouseY, mouseVelocityX, mouseVelocityY);
        blob.draw(ctx);
      });

      // Reset filter for particles
      ctx.filter = 'blur(2px)';
      ctx.globalCompositeOperation = 'lighter';

      // Update and draw particles
      for (let i = particles.length - 1; i >= 0; i--) {
        particles[i].update();
        particles[i].draw(ctx);

        if (particles[i].life <= 0) {
          particles.splice(i, 1);
        }
      }

      // Add ambient particles occasionally
      if (Math.random() > 0.95 && particles.length < 50) {
        particles.push(new Particle(
          Math.random() * canvas.width,
          Math.random() * canvas.height
        ));
      }

      // Decay velocity
      mouseVelocityX *= 0.9;
      mouseVelocityY *= 0.9;

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    // Cleanup
    return () => {
      window.removeEventListener('resize', setCanvasSize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className={`fixed inset-0 -z-10 ${className}`}>
      {/* Animated gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900">
        {/* Radial gradient overlay for vignette effect */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,transparent_0%,rgba(15,23,42,0.8)_100%)]"></div>
      </div>

      {/* Canvas for liquid effect */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0"
        style={{
          mixBlendMode: 'screen',
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      />

      {/* Noise texture overlay for graininess */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' /%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' /%3E%3C/svg%3E")`,
        }}
      ></div>

      {/* Floating orbs for extra ambience */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-float"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-float-delayed"></div>
        <div className="absolute top-1/2 right-1/3 w-64 h-64 bg-pink-500/10 rounded-full blur-3xl animate-float-slow"></div>
      </div>
    </div>
  );
};

export default LiquidEther;
