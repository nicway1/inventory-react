import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import Header from './components/Header';
import Footer from './components/Footer';
import Home from './pages/Home';
import AboutUs from './pages/AboutUs';
import ContactUs from './pages/ContactUs';
import Services from './pages/Services';
import GlobalCoverage from './pages/GlobalCoverage';
import Resources from './pages/Resources';
import FAQ from './pages/FAQ';
import Blog from './pages/Blog';
import BlogPost from './pages/BlogPost';
import FreightForwarding from './pages/services/FreightForwarding';
import GlobalFulfillment from './pages/services/GlobalFulfillment';
import ICTLogistics from './pages/services/ICTLogistics';
import IORSolutions from './pages/services/IORSolutions';
import Compliance from './pages/services/Compliance';

function App() {
  return (
    <ThemeProvider>
      <Router basename={process.env.PUBLIC_URL}>
        <div className="App min-h-screen bg-white dark:bg-slate-900 text-secondary-900 dark:text-gray-100 transition-colors duration-300">
          <Header />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/about-us" element={<AboutUs />} />
            <Route path="/contact-us" element={<ContactUs />} />
            <Route path="/services" element={<Services />} />
            <Route path="/global-coverage" element={<GlobalCoverage />} />
            <Route path="/resources" element={<Resources />} />
            <Route path="/faq" element={<FAQ />} />
            <Route path="/blog" element={<Blog />} />
            <Route path="/blog/:slug" element={<BlogPost />} />
            <Route path="/services/freight-forwarding" element={<FreightForwarding />} />
            <Route path="/services/global-fulfillment" element={<GlobalFulfillment />} />
            <Route path="/services/ict-logistics" element={<ICTLogistics />} />
            <Route path="/services/ior-eor-solutions" element={<IORSolutions />} />
            <Route path="/services/compliance" element={<Compliance />} />
          </Routes>
          </main>
          <Footer />
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
