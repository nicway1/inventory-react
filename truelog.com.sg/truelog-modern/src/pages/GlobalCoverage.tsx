import React from 'react';
import { motion } from 'framer-motion';
import { GlobeAltIcon, MapPinIcon, TruckIcon, BuildingOfficeIcon, ClockIcon, PhoneIcon } from '@heroicons/react/24/outline';

const GlobalCoverage: React.FC = () => {
  const regions = [
    {
      name: 'Southeast Asia',
      countries: ['Singapore', 'Malaysia', 'Thailand', 'Vietnam', 'Indonesia', 'Philippines'],
      hubs: ['Singapore Hub', 'Kuala Lumpur', 'Bangkok', 'Ho Chi Minh City'],
      specialties: ['Electronics', 'Manufacturing', 'Automotive', 'Pharmaceuticals'],
      flag: '🌏'
    },
    {
      name: 'East Asia',
      countries: ['China', 'Hong Kong', 'Taiwan', 'South Korea', 'Japan'],
      hubs: ['Hong Kong Hub', 'Shanghai', 'Shenzhen', 'Seoul'],
      specialties: ['Technology', 'Electronics', 'Textiles', 'Machinery'],
      flag: '🏯'
    },
    {
      name: 'Europe',
      countries: ['Germany', 'Netherlands', 'United Kingdom', 'France', 'Belgium'],
      hubs: ['Amsterdam Hub', 'Hamburg', 'London', 'Rotterdam'],
      specialties: ['Automotive', 'Chemicals', 'Machinery', 'Pharmaceuticals'],
      flag: '🇪🇺'
    },
    {
      name: 'North America',
      countries: ['United States', 'Canada', 'Mexico'],
      hubs: ['Los Angeles Hub', 'New York', 'Chicago', 'Vancouver'],
      specialties: ['Technology', 'Aerospace', 'Automotive', 'Healthcare'],
      flag: '🇺🇸'
    }
  ];

  const services = [
    {
      icon: TruckIcon,
      title: 'Land Transportation',
      description: 'Comprehensive trucking and rail services across regional networks.',
      coverage: '15+ countries',
      features: ['Cross-border trucking', 'Rail freight', 'Last-mile delivery', 'Intermodal solutions']
    },
    {
      icon: GlobeAltIcon,
      title: 'Ocean Freight',
      description: 'Global sea freight services connecting major ports worldwide.',
      coverage: '200+ ports',
      features: ['FCL & LCL services', 'Port-to-port', 'Door-to-door', 'Project cargo']
    },
    {
      icon: BuildingOfficeIcon,
      title: 'Air Freight',
      description: 'Fast and reliable air cargo services to global destinations.',
      coverage: '500+ airports',
      features: ['Express delivery', 'Charter services', 'Temperature control', 'Dangerous goods']
    },
    {
      icon: MapPinIcon,
      title: 'Warehousing',
      description: 'Strategic warehouse locations for optimal supply chain efficiency.',
      coverage: '50+ facilities',
      features: ['Distribution centers', '3PL services', 'Cross-docking', 'Value-added services']
    }
  ];

  const keyPorts = [
    { name: 'Singapore', type: 'Sea Port', rank: '#2 Global', volume: '37.2M TEU' },
    { name: 'Shanghai', type: 'Sea Port', rank: '#1 Global', volume: '47.0M TEU' },
    { name: 'Rotterdam', type: 'Sea Port', rank: '#10 Global', volume: '14.8M TEU' },
    { name: 'Los Angeles', type: 'Sea Port', rank: '#9 Global', volume: '10.7M TEU' },
    { name: 'Changi Airport', type: 'Air Port', rank: '#7 Global', volume: '2.0M tonnes' },
    { name: 'Hong Kong Airport', type: 'Air Port', rank: '#8 Global', volume: '4.8M tonnes' }
  ];

  const stats = [
    { number: '50+', label: 'Countries Served', icon: GlobeAltIcon },
    { number: '200+', label: 'Partner Locations', icon: MapPinIcon },
    { number: '24/7', label: 'Global Support', icon: ClockIcon },
    { number: '99.5%', label: 'On-time Delivery', icon: TruckIcon }
  ];

  return (
    <div className="pt-16 bg-white dark:bg-slate-900">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-primary-600 via-blue-600 to-primary-700 dark:from-slate-900 dark:via-blue-900 dark:to-slate-800 py-20 relative overflow-hidden">
        {/* Background Elements */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-cyan-600/20"></div>
          
          {/* World map overlay */}
          <div className="absolute inset-0 opacity-10">
            <img
              src={`${process.env.PUBLIC_URL}/assets/images/world-map.png`}
              alt="World Map"
              className="w-full h-full object-cover"
            />
          </div>
          
          {/* Global network lines */}
          <div className="absolute inset-0 opacity-20">
            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <path d="M10 30 Q30 20 50 30 Q70 40 90 25" stroke="#06b6d4" strokeWidth="0.5" fill="none">
                <animate attributeName="stroke-dasharray" values="0,200;100,100;200,0;0,200" dur="10s" repeatCount="indefinite"/>
              </path>
              <path d="M5 70 Q25 60 45 70 Q65 80 85 65" stroke="#3b82f6" strokeWidth="0.5" fill="none">
                <animate attributeName="stroke-dasharray" values="200,0;100,100;0,200;200,0" dur="8s" repeatCount="indefinite"/>
              </path>
              <path d="M20 50 Q40 40 60 50 Q80 60 95 45" stroke="#00d4ff" strokeWidth="0.3" fill="none">
                <animate attributeName="stroke-dasharray" values="0,150;75,75;150,0;0,150" dur="12s" repeatCount="indefinite"/>
              </path>
            </svg>
          </div>
          
          {/* Connection nodes */}
          <div className="absolute top-1/4 left-1/4 w-3 h-3 bg-cyan-400 rounded-full animate-pulse"></div>
          <div className="absolute top-1/3 right-1/3 w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{animationDelay: '1s'}}></div>
          <div className="absolute bottom-1/3 left-1/3 w-2.5 h-2.5 bg-cyan-300 rounded-full animate-pulse" style={{animationDelay: '2s'}}></div>
          <div className="absolute bottom-1/4 right-1/4 w-2 h-2 bg-blue-300 rounded-full animate-pulse" style={{animationDelay: '3s'}}></div>
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-5xl font-heading font-bold text-white mb-6">
              Global Coverage
            </h1>
            <p className="text-xl text-gray-100 dark:text-gray-200 max-w-3xl mx-auto">
              Worldwide logistics network spanning major trade routes and destinations
            </p>
          </motion.div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="text-center"
              >
                <div className="w-16 h-16 bg-primary-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <stat.icon className="h-8 w-8 text-primary-600" />
                </div>
                <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2">{stat.number}</div>
                <div className="text-gray-600 dark:text-gray-300">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Regional Coverage */}
      <section className="py-20 bg-gray-50 dark:bg-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 dark:text-white mb-4">
              Regional Coverage
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
              Strategic presence across key global markets and trade corridors
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {regions.map((region, index) => (
              <motion.div
                key={region.name}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-white dark:bg-slate-900 rounded-2xl p-8 border border-gray-200 dark:border-slate-700/50 shadow-lg"
              >
                <div className="flex items-center mb-6">
                  <div className="text-4xl mr-4">{region.flag}</div>
                  <h3 className="text-2xl font-semibold text-gray-900 dark:text-white">{region.name}</h3>
                </div>

                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Countries</h4>
                    <div className="flex flex-wrap gap-2">
                      {region.countries.map((country, countryIndex) => (
                        <span
                          key={countryIndex}
                          className="px-3 py-1 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 text-sm rounded-full"
                        >
                          {country}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Key Hubs</h4>
                    <div className="flex flex-wrap gap-2">
                      {region.hubs.map((hub, hubIndex) => (
                        <span
                          key={hubIndex}
                          className="px-3 py-1 bg-primary-500/20 text-primary-700 text-sm rounded-full"
                        >
                          {hub}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Industry Specialties</h4>
                    <div className="flex flex-wrap gap-2">
                      {region.specialties.map((specialty, specialtyIndex) => (
                        <span
                          key={specialtyIndex}
                          className="px-3 py-1 bg-green-500/20 text-green-400 text-sm rounded-full"
                        >
                          {specialty}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Service Coverage */}
      <section className="py-20 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 dark:text-white mb-4">
              Service Coverage
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
              Comprehensive logistics services across all major transportation modes
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {services.map((service, index) => (
              <motion.div
                key={service.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-gray-50 dark:bg-slate-800 rounded-2xl p-8 shadow-lg"
              >
                <div className="flex items-start space-x-4">
                  <div className="w-12 h-12 bg-primary-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                    <service.icon className="h-6 w-6 text-primary-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xl font-semibold text-gray-900 dark:text-white">{service.title}</h3>
                      <span className="text-primary-600 font-semibold text-sm">{service.coverage}</span>
                    </div>
                    <p className="text-gray-600 dark:text-gray-300 mb-4">{service.description}</p>
                    <div className="grid grid-cols-2 gap-2">
                      {service.features.map((feature, featureIndex) => (
                        <div key={featureIndex} className="flex items-center text-sm">
                          <div className="w-1.5 h-1.5 rounded-full bg-primary-600 mr-2"></div>
                          <span className="text-gray-600 dark:text-gray-300">{feature}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Key Ports & Airports */}
      <section className="py-20 bg-gray-50 dark:bg-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 dark:text-white mb-4">
              Key Ports & Airports
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
              Strategic partnerships with major global transportation hubs
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {keyPorts.map((port, index) => (
              <motion.div
                key={port.name}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-white dark:bg-slate-900 rounded-xl p-6 shadow-lg text-center border border-gray-200 dark:border-slate-700/50"
              >
                <div className="w-12 h-12 bg-primary-500/20 rounded-lg flex items-center justify-center mx-auto mb-4">
                  {port.type === 'Sea Port' ? (
                    <span className="text-2xl">🚢</span>
                  ) : (
                    <span className="text-2xl">✈️</span>
                  )}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">{port.name}</h3>
                <div className="text-sm text-gray-600 dark:text-gray-300 mb-1">{port.type}</div>
                <div className="text-primary-600 font-semibold text-sm mb-1">{port.rank}</div>
                <div className="text-gray-500 dark:text-gray-400 text-sm">{port.volume}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section className="py-20 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 dark:text-white mb-4">
              Global Support Network
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
              24/7 support across all time zones with local expertise
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                region: 'Asia Pacific',
                timezone: 'GMT+8',
                phone: '+65 6123 4567',
                email: 'apac@truelog.com.sg',
                hours: '24/7 Operations'
              },
              {
                region: 'Europe',
                timezone: 'GMT+1',
                phone: '+31 20 123 4567',
                email: 'europe@truelog.com.sg',
                hours: '24/7 Operations'
              },
              {
                region: 'Americas',
                timezone: 'GMT-5',
                phone: '+1 555 123 4567',
                email: 'americas@truelog.com.sg',
                hours: '24/7 Operations'
              }
            ].map((contact, index) => (
              <motion.div
                key={contact.region}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-gray-50 dark:bg-slate-800 rounded-xl p-6 text-center shadow-lg border border-gray-200 dark:border-slate-700/50"
              >
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">{contact.region}</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex items-center justify-center space-x-2">
                    <ClockIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                    <span className="text-gray-600 dark:text-gray-300">{contact.timezone}</span>
                  </div>
                  <div className="flex items-center justify-center space-x-2">
                    <PhoneIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                    <span className="text-gray-600 dark:text-gray-300">{contact.phone}</span>
                  </div>
                  <div className="text-gray-600 dark:text-gray-300">{contact.email}</div>
                  <div className="text-primary-600 font-semibold">{contact.hours}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl font-heading font-bold text-white mb-4">
              Ready to Go Global?
            </h2>
            <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
              Leverage our worldwide network to expand your business reach and optimize your supply chain.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-slate-900 text-primary-600 px-8 py-4 rounded-xl font-semibold text-lg hover:bg-slate-800 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Explore Global Solutions
            </motion.button>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default GlobalCoverage;