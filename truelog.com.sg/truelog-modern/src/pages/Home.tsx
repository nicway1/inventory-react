import React from 'react';
import Hero from '../components/Hero';
import About from '../components/About';
import Services from '../components/Services';
import Stats from '../components/Stats';
import Testimonials from '../components/Testimonials';
import GlobalMap from '../components/GlobalMap';

const Home: React.FC = () => {
  return (
    <div>
      <Hero />
      <About />
      <Services />
      <Stats />
      <Testimonials />
      <GlobalMap />
    </div>
  );
};

export default Home;