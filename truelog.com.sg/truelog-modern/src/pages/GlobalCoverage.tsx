import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GlobeAltIcon,
  MapPinIcon,
  TruckIcon,
  BuildingOfficeIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import InteractiveWorldMap, { Region, REGIONS } from '../components/InteractiveWorldMap';
import { getCountryByCode } from '../data/countryData';

// Country flag component using flag-icons CDN or emoji fallback
const CountryFlag: React.FC<{ code: string; name: string; size?: 'sm' | 'md' | 'lg' }> = ({
  code,
  name,
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'w-5 h-4',
    md: 'w-6 h-5',
    lg: 'w-8 h-6',
  };

  return (
    <img
      src={`https://flagcdn.com/w40/${code.toLowerCase()}.png`}
      srcSet={`https://flagcdn.com/w80/${code.toLowerCase()}.png 2x`}
      alt={`${name} flag`}
      className={`${sizeClasses[size]} object-cover rounded-sm shadow-sm`}
      onError={(e) => {
        // Fallback to placeholder if flag not found
        (e.target as HTMLImageElement).style.display = 'none';
      }}
    />
  );
};

const GlobalCoverage: React.FC = () => {
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const navigate = useNavigate();

  const handleCountryClick = (countryCode: string) => {
    const country = getCountryByCode(countryCode);
    if (country) {
      navigate(`/countries/${country.slug}`);
    }
  };

  const globalStats = [
    { number: '200+', label: 'Markets', icon: GlobeAltIcon, color: 'from-blue-500 to-indigo-500' },
    { number: '240+', label: 'Partners', icon: MapPinIcon, color: 'from-sky-500 to-blue-500' },
    { number: '6', label: 'Continents', icon: TruckIcon, color: 'from-indigo-500 to-purple-500' },
    { number: '24/7', label: 'Support', icon: BuildingOfficeIcon, color: 'from-blue-400 to-sky-500' },
  ];

  const services = [
    {
      title: 'Air Freight',
      description: 'Express and standard air cargo services to any destination worldwide.',
      icon: '✈️',
    },
    {
      title: 'Ocean Freight',
      description: 'FCL and LCL sea freight solutions with competitive rates.',
      icon: '🚢',
    },
    {
      title: 'Road Transport',
      description: 'Cross-border trucking and last-mile delivery services.',
      icon: '🚚',
    },
    {
      title: 'Customs Brokerage',
      description: 'Expert customs clearance and compliance services.',
      icon: '📋',
    },
  ];

  return (
    <div className="pt-16 bg-white dark:bg-slate-900">
      {/* Hero Section with Interactive Map */}
      <section className="relative bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 py-12 md:py-20 overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 left-0 w-96 h-96 bg-blue-500 rounded-full filter blur-3xl -translate-x-1/2 -translate-y-1/2" />
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-indigo-500 rounded-full filter blur-3xl translate-x-1/2 translate-y-1/2" />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-8 md:mb-12"
          >
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-heading font-bold text-white mb-4">
              Global <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">Coverage</span>
            </h1>
            <p className="text-lg md:text-xl text-gray-300 max-w-3xl mx-auto">
              Instant access to over 200 markets worldwide. Click on any region to explore our coverage.
            </p>
          </motion.div>

          {/* Interactive Map */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.2 }}
          >
            <InteractiveWorldMap
              selectedRegion={selectedRegion}
              onRegionSelect={setSelectedRegion}
              onCountryClick={handleCountryClick}
              showOfficeMarkers={true}
              className="mb-8"
            />
          </motion.div>
        </div>
      </section>

      {/* Region Detail Panel - Shows when a region is selected */}
      <AnimatePresence>
        {selectedRegion && (
          <motion.section
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 overflow-hidden"
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12">
              <div className="flex flex-col lg:flex-row gap-8 items-start">
                {/* Region Info */}
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-3xl md:text-4xl font-bold text-white">
                      {selectedRegion.name}
                    </h2>
                    <button
                      onClick={() => setSelectedRegion(null)}
                      className="p-2 hover:bg-white/20 rounded-full transition-colors"
                    >
                      <XMarkIcon className="h-6 w-6 text-white" />
                    </button>
                  </div>
                  <p className="text-lg text-blue-100 mb-6">
                    {selectedRegion.description}
                  </p>

                  {/* Region Stats */}
                  <div className="flex gap-8 mb-6">
                    <div>
                      <div className="text-4xl font-bold text-white">{selectedRegion.stats.markets}</div>
                      <div className="text-blue-200 text-sm">Markets</div>
                    </div>
                    <div>
                      <div className="text-4xl font-bold text-white">{selectedRegion.stats.partners}</div>
                      <div className="text-blue-200 text-sm">Partners</div>
                    </div>
                  </div>

                  {/* CTA Button */}
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="inline-flex items-center px-6 py-3 bg-white text-blue-700 font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all"
                  >
                    Get a Quote for {selectedRegion.name}
                    <ArrowRightIcon className="ml-2 h-5 w-5" />
                  </motion.button>
                </div>

                {/* Countries List */}
                <div className="lg:w-1/2">
                  <h3 className="text-lg font-semibold text-white mb-4">Key Markets</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                    {selectedRegion.countries.map((country) => {
                      const countryData = getCountryByCode(country.code);
                      const countrySlug = countryData?.slug;

                      return countrySlug ? (
                        <Link
                          key={country.name}
                          to={`/countries/${countrySlug}`}
                        >
                          <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg px-3 py-2 hover:bg-white/20 transition-colors cursor-pointer"
                          >
                            <CountryFlag code={country.code} name={country.name} size="sm" />
                            <span className="text-white text-sm truncate">{country.name}</span>
                            {country.hasOffice && (
                              <span className="w-2 h-2 bg-red-500 rounded-full flex-shrink-0" title="TrueLog Office" />
                            )}
                          </motion.div>
                        </Link>
                      ) : (
                        <motion.div
                          key={country.name}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg px-3 py-2"
                        >
                          <CountryFlag code={country.code} name={country.name} size="sm" />
                          <span className="text-white text-sm truncate">{country.name}</span>
                          {country.hasOffice && (
                            <span className="w-2 h-2 bg-red-500 rounded-full flex-shrink-0" title="TrueLog Office" />
                          )}
                        </motion.div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Stats Section */}
      <section className="py-16 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8">
            {globalStats.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                className="relative group"
              >
                <div className="absolute inset-0 bg-gradient-to-r opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity duration-300"
                  style={{ backgroundImage: `linear-gradient(to right, var(--tw-gradient-stops))` }}
                />
                <div className="text-center p-6 rounded-2xl border border-gray-100 dark:border-slate-700 hover:border-blue-200 dark:hover:border-blue-700 transition-all duration-300 hover:shadow-lg">
                  <div className={`w-14 h-14 mx-auto mb-4 rounded-xl bg-gradient-to-r ${stat.color} flex items-center justify-center shadow-lg`}>
                    <stat.icon className="h-7 w-7 text-white" />
                  </div>
                  <div className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-1">
                    {stat.number}
                  </div>
                  <div className="text-gray-600 dark:text-gray-400 font-medium">
                    {stat.label}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Regional Coverage Grid */}
      <section className="py-16 md:py-24 bg-gray-50 dark:bg-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-12 md:mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-heading font-bold text-gray-900 dark:text-white mb-4">
              Coverage by Region
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
              Explore our strategic presence across all continents with local expertise and customs knowledge.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {REGIONS.map((region, index) => (
              <motion.div
                key={region.id}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                onClick={() => {
                  setSelectedRegion(region);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                className="bg-white dark:bg-slate-900 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden cursor-pointer group border border-gray-100 dark:border-slate-700"
              >
                {/* Region Header */}
                <div
                  className="p-6 text-white"
                  style={{ backgroundColor: region.color }}
                >
                  <h3 className="text-2xl font-bold mb-1">{region.name}</h3>
                  <div className="flex gap-6 text-sm opacity-90">
                    <span>{region.stats.markets} Markets</span>
                    <span>{region.stats.partners} Partners</span>
                  </div>
                </div>

                {/* Region Content */}
                <div className="p-6">
                  <p className="text-gray-600 dark:text-gray-300 text-sm mb-4 line-clamp-2">
                    {region.description}
                  </p>

                  {/* Countries Preview */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {region.countries.slice(0, 5).map((country) => {
                      const countryData = getCountryByCode(country.code);
                      const countrySlug = countryData?.slug;

                      return countrySlug ? (
                        <Link
                          key={country.name}
                          to={`/countries/${countrySlug}`}
                          onClick={(e) => e.stopPropagation()}
                          className="flex items-center space-x-1.5 bg-gray-100 dark:bg-slate-800 rounded-full px-3 py-1 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
                        >
                          <CountryFlag code={country.code} name={country.name} size="sm" />
                          <span className="text-xs text-gray-700 dark:text-gray-300">{country.name}</span>
                        </Link>
                      ) : (
                        <div
                          key={country.name}
                          className="flex items-center space-x-1.5 bg-gray-100 dark:bg-slate-800 rounded-full px-3 py-1"
                        >
                          <CountryFlag code={country.code} name={country.name} size="sm" />
                          <span className="text-xs text-gray-700 dark:text-gray-300">{country.name}</span>
                        </div>
                      );
                    })}
                    {region.countries.length > 5 && (
                      <span className="text-xs text-gray-500 dark:text-gray-400 self-center">
                        +{region.countries.length - 5} more
                      </span>
                    )}
                  </div>

                  {/* View Details Link */}
                  <div className="flex items-center text-blue-600 dark:text-blue-400 font-medium text-sm group-hover:translate-x-1 transition-transform">
                    Explore {region.name}
                    <ArrowRightIcon className="ml-1 h-4 w-4" />
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section className="py-16 md:py-24 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-12 md:mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-heading font-bold text-gray-900 dark:text-white mb-4">
              Global Services
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
              Comprehensive logistics services available across all our markets.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {services.map((service, index) => (
              <motion.div
                key={service.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                className="bg-gray-50 dark:bg-slate-800 rounded-2xl p-6 hover:shadow-lg transition-all duration-300 border border-gray-100 dark:border-slate-700"
              >
                <div className="text-4xl mb-4">{service.icon}</div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {service.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm">
                  {service.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Choose Us Section */}
      <section className="py-16 md:py-24 bg-gray-50 dark:bg-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <h2 className="text-3xl md:text-4xl font-heading font-bold text-gray-900 dark:text-white mb-6">
                Why Choose TrueLog for{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-indigo-500">
                  Global Logistics
                </span>
              </h2>
              <p className="text-lg text-gray-600 dark:text-gray-300 mb-8">
                With strategic locations across 6 continents, we offer unparalleled access to global markets
                with local expertise and streamlined customs clearance.
              </p>

              <ul className="space-y-4">
                {[
                  'Local expertise in over 200 markets',
                  'Customs brokerage and compliance support',
                  '24/7 shipment tracking and visibility',
                  'Dedicated account management',
                  'Competitive rates with no hidden fees',
                  'End-to-end supply chain solutions',
                ].map((feature, index) => (
                  <motion.li
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    className="flex items-start space-x-3"
                  >
                    <CheckCircleIcon className="h-6 w-6 text-blue-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                  </motion.li>
                ))}
              </ul>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="relative"
            >
              <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-3xl p-8 md:p-10 text-white">
                <h3 className="text-2xl font-bold mb-4">Ready to Go Global?</h3>
                <p className="text-blue-100 mb-6">
                  Get a customized logistics solution for your international shipping needs.
                  Our experts are ready to help you navigate global trade.
                </p>
                <div className="space-y-4">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full bg-white text-blue-700 font-semibold py-3 px-6 rounded-xl hover:shadow-lg transition-all"
                  >
                    Get a Free Quote
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full bg-blue-700/50 text-white font-semibold py-3 px-6 rounded-xl hover:bg-blue-700/70 transition-all"
                  >
                    Contact Sales Team
                  </motion.button>
                </div>

                {/* Decorative elements */}
                <div className="absolute -top-4 -right-4 w-24 h-24 bg-indigo-400/30 rounded-full blur-2xl" />
                <div className="absolute -bottom-6 -left-6 w-32 h-32 bg-blue-400/30 rounded-full blur-2xl" />
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 md:py-20 bg-gradient-to-r from-blue-600 to-indigo-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-3xl md:text-4xl font-heading font-bold text-white mb-4">
              Ship Anywhere in the World
            </h2>
            <p className="text-lg text-blue-100 mb-8 max-w-2xl mx-auto">
              From Singapore to every corner of the globe. Start shipping today with TrueLog's global network.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-white text-blue-700 px-8 py-4 rounded-xl font-semibold text-lg hover:shadow-xl transition-all"
              >
                Get Started
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-blue-700/50 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:bg-blue-700/70 transition-all border border-white/20"
              >
                Contact Us
              </motion.button>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default GlobalCoverage;
