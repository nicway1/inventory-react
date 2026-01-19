import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { BuildingOfficeIcon, UserGroupIcon } from '@heroicons/react/24/outline';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';

interface Office {
  country: string;
  city: string;
  type: string;
  status: 'Operational' | 'Coming Soon';
  employees?: number;
  coordinates: {
    lng: number; // Longitude
    lat: number; // Latitude
  };
  address?: string;
  hours?: string;
}

const GlobalMap: React.FC = () => {
  const [hoveredOffice, setHoveredOffice] = useState<Office | null>(null);
  const [selectedOffice, setSelectedOffice] = useState<Office | null>(null);

  const offices: Office[] = [
    {
      country: 'Singapore',
      city: 'Singapore',
      type: 'HQ',
      status: 'Operational',
      employees: 10,
      coordinates: { lng: 103.8198, lat: 1.3521 }
    },
    {
      country: 'India',
      city: 'Bangalore',
      type: 'Office',
      status: 'Operational',
      employees: 4,
      coordinates: { lng: 77.5946, lat: 12.9716 }
    },
    {
      country: 'Vietnam',
      city: 'Ho Chi Minh',
      type: 'Office',
      status: 'Operational',
      employees: 10,
      coordinates: { lng: 106.6297, lat: 10.8231 }
    },
    {
      country: 'South Africa',
      city: 'Cape Town',
      type: 'Office',
      status: 'Operational',
      employees: 1,
      coordinates: { lng: 18.4241, lat: -33.9249 }
    },
    {
      country: 'Belgium',
      city: 'Brussels',
      type: 'Office',
      status: 'Operational',
      employees: 1,
      coordinates: { lng: 4.3517, lat: 50.8503 }
    },
    {
      country: 'Canada',
      city: 'Toronto',
      type: 'Partner Facility',
      status: 'Operational',
      employees: 4,
      coordinates: { lng: -79.3832, lat: 43.6532 }
    },
    {
      country: 'Israel',
      city: 'Tel Aviv',
      type: 'Partner Facility',
      status: 'Operational',
      employees: 2,
      coordinates: { lng: 34.7818, lat: 32.0853 }
    },
    {
      country: 'Philippines',
      city: 'Manila',
      type: 'Partner Facility',
      status: 'Operational',
      employees: 4,
      coordinates: { lng: 120.9842, lat: 14.5995 }
    },
    {
      country: 'Japan',
      city: 'Osaka',
      type: 'Partner Facility',
      status: 'Operational',
      employees: 3,
      coordinates: { lng: 135.5023, lat: 34.6937 }
    },
    {
      country: 'Australia',
      city: 'Sydney',
      type: 'Partner Facility',
      status: 'Operational',
      employees: 3,
      coordinates: { lng: 151.2093, lat: -33.8688 }
    },
    {
      country: 'Malaysia',
      city: 'Johore',
      type: 'Partner Facility',
      status: 'Coming Soon',
      employees: 21,
      coordinates: { lng: 103.7414, lat: 1.4655 }
    },
    {
      country: 'Thailand',
      city: 'Bangkok',
      type: 'Partner Facility',
      status: 'Coming Soon',
      employees: 2,
      coordinates: { lng: 100.5018, lat: 13.7563 }
    },
    {
      country: 'Hong Kong',
      city: 'Hong Kong',
      type: 'Partner Facility',
      status: 'Coming Soon',
      employees: 7,
      coordinates: { lng: 114.1694, lat: 22.3193 }
    }
  ];

  const operationalOffices = offices.filter(office => office.status === 'Operational');
  const comingSoonOffices = offices.filter(office => office.status === 'Coming Soon');

  return (
    <section className="py-20 bg-gray-100 relative overflow-hidden">
      {/* Subtle Background Pattern */}
      <div className="absolute inset-0 opacity-3">
        <div className="absolute inset-0 bg-gradient-to-br from-gray-200/30 to-gray-300/30"></div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
            Instant Access to Over 200 Markets
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Expedite your global growth with our worldwide network of offices and partner facilities.
          </p>
        </motion.div>

        {/* Interactive World Map */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1 }}
          className="bg-white rounded-2xl shadow-xl p-6 relative overflow-hidden"
        >
          {/* World Map */}
          <div className="relative w-full h-[500px] md:h-[700px] bg-gray-50 rounded-xl overflow-hidden">
            <ComposableMap
              projectionConfig={{
                scale: 180,
                center: [0, 0]
              }}
              className="w-full h-full"
              style={{
                width: '100%',
                height: '100%'
              }}
            >
              <Geographies geography="https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json">
                {({ geographies }: { geographies: any[] }) =>
                  geographies.map((geo: any) => (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      fill="#E5E7EB"
                      stroke="#9CA3AF"
                      strokeWidth={0.5}
                      style={{
                        default: {
                          fill: "#E5E7EB",
                          outline: "none"
                        },
                        hover: {
                          fill: "#D1D5DB",
                          outline: "none"
                        },
                        pressed: {
                          fill: "#D1D5DB",
                          outline: "none"
                        }
                      }}
                    />
                  ))
                }
              </Geographies>
              
              {/* Office Markers */}
              {offices.map((office, index) => (
                <Marker
                  key={index}
                  coordinates={[office.coordinates.lng, office.coordinates.lat]}
                  onClick={() => setSelectedOffice(office)}
                  onMouseEnter={() => setHoveredOffice(office)}
                  onMouseLeave={() => setHoveredOffice(null)}
                >
                  <motion.g
                    initial={{ scale: 0, opacity: 0 }}
                    whileInView={{ scale: 1, opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    whileHover={{ scale: 1.3 }}
                    className="cursor-pointer"
                  >
                    {office.type === 'HQ' ? (
                      <g>
                        <circle
                          r={15}
                          fill={office.status === 'Operational' ? '#dc2626' : '#f97316'}
                          stroke="#ffffff"
                          strokeWidth={4}
                          className="drop-shadow-lg"
                        />
                        <circle
                          r={6}
                          fill="#ffffff"
                        />
                        <circle
                          r={3}
                          fill={office.status === 'Operational' ? '#dc2626' : '#f97316'}
                        />
                        {office.status === 'Operational' && (
                          <circle
                            r={20}
                            fill="none"
                            stroke="#10b981"
                            strokeWidth={3}
                            className="animate-ping"
                            opacity={0.8}
                          />
                        )}
                      </g>
                    ) : (
                      <g>
                        <circle
                          r={8}
                          fill={office.status === 'Operational' ? '#2563eb' : '#f97316'}
                          stroke="#ffffff"
                          strokeWidth={2}
                          className="drop-shadow-lg"
                        />
                        {office.status === 'Operational' && (
                          <circle
                            r={12}
                            fill="none"
                            stroke="#10b981"
                            strokeWidth={2}
                            className="animate-ping"
                            opacity={0.4}
                          />
                        )}
                        {office.status === 'Coming Soon' && (
                          <circle
                            r={12}
                            fill="none"
                            stroke="#fb923c"
                            strokeWidth={2}
                            className="animate-ping"
                            opacity={0.4}
                          />
                        )}
                      </g>
                    )}
                  </motion.g>
                </Marker>
              ))}
            </ComposableMap>
            
            {/* Hover Tooltip */}
            {hoveredOffice && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="absolute z-30 bg-white rounded-xl shadow-lg p-4 border border-gray-200 pointer-events-none top-4 left-4"
              >
                <div className="text-sm font-semibold text-gray-900 mb-1">
                  {hoveredOffice.city}, {hoveredOffice.country}
                </div>
                <div className="text-xs text-gray-600 mb-2">
                  {hoveredOffice.type} • {hoveredOffice.status}
                </div>
                {hoveredOffice.employees ? (
                  <div className="flex items-center text-xs text-gray-500">
                    <UserGroupIcon className="h-3 w-3 mr-1" />
                    {hoveredOffice.employees} employees
                  </div>
                ) : hoveredOffice.hours && (
                  <div className="text-xs text-gray-500">
                    {hoveredOffice.hours}
                  </div>
                )}
              </motion.div>
            )}
          </div>

          {/* Legend */}
          <div className="mt-6 flex flex-wrap justify-center gap-6 p-4 bg-gray-50 rounded-xl">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-primary-600 rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              </div>
              <span className="text-sm font-medium text-gray-700">Operational ({operationalOffices.length})</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-orange-500 rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-orange-400 rounded-full animate-pulse"></div>
              </div>
              <span className="text-sm font-medium text-gray-700">Coming Soon ({comingSoonOffices.length})</span>
            </div>
            <div className="flex items-center space-x-2">
              <BuildingOfficeIcon className="h-4 w-4 text-primary-600" />
              <span className="text-sm font-medium text-gray-700">Headquarters</span>
            </div>
          </div>
        </motion.div>

        {/* Office Details Modal */}
        {selectedOffice && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedOffice(null)}
          >
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.5, opacity: 0 }}
              className="bg-white rounded-2xl shadow-2xl p-6 max-w-md w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-gray-900">
                  {selectedOffice.city}, {selectedOffice.country}
                </h3>
                <button
                  onClick={() => setSelectedOffice(null)}
                  className="text-gray-400 hover:text-gray-600 p-1"
                >
                  ✕
                </button>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Type:</span>
                  <span className="text-sm font-medium text-gray-900">{selectedOffice.type}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Status:</span>
                  <span className={`text-sm font-medium px-2 py-1 rounded-full ${
                    selectedOffice.status === 'Operational' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-orange-100 text-orange-800'
                  }`}>
                    {selectedOffice.status}
                  </span>
                </div>
                {selectedOffice.employees && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Employees:</span>
                    <span className="text-sm font-medium text-gray-900">{selectedOffice.employees}</span>
                  </div>
                )}
                {selectedOffice.address && (
                  <div>
                    <span className="text-sm text-gray-600">Address:</span>
                    <div className="text-sm text-gray-900 mt-1">{selectedOffice.address}</div>
                  </div>
                )}
                {selectedOffice.hours && (
                  <div>
                    <span className="text-sm text-gray-600">Hours:</span>
                    <div className="text-sm text-gray-900 mt-1">{selectedOffice.hours}</div>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </div>
    </section>
  );
};

export default GlobalMap;