import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps';

// Region definitions with colors inspired by TecEx's teal-green gradient
export interface Region {
  id: string;
  name: string;
  color: string;
  hoverColor: string;
  description: string;
  countries: CountryInfo[];
  stats: {
    markets: number;
    partners: number;
  };
}

export interface CountryInfo {
  name: string;
  code: string; // ISO 2-letter code for flag
  hasOffice?: boolean;
  isPartner?: boolean;
}

// Country to region mapping
const COUNTRY_REGIONS: { [key: string]: string } = {
  // Africa
  'Algeria': 'africa', 'Angola': 'africa', 'Benin': 'africa', 'Botswana': 'africa',
  'Burkina Faso': 'africa', 'Burundi': 'africa', 'Cameroon': 'africa', 'Cape Verde': 'africa',
  'Central African Rep.': 'africa', 'Chad': 'africa', 'Comoros': 'africa', 'Congo': 'africa',
  "Côte d'Ivoire": 'africa', 'Dem. Rep. Congo': 'africa', 'Djibouti': 'africa', 'Egypt': 'africa',
  'Eq. Guinea': 'africa', 'Eritrea': 'africa', 'Ethiopia': 'africa', 'Gabon': 'africa',
  'Gambia': 'africa', 'Ghana': 'africa', 'Guinea': 'africa', 'Guinea-Bissau': 'africa',
  'Kenya': 'africa', 'Lesotho': 'africa', 'Liberia': 'africa', 'Libya': 'africa',
  'Madagascar': 'africa', 'Malawi': 'africa', 'Mali': 'africa', 'Mauritania': 'africa',
  'Mauritius': 'africa', 'Morocco': 'africa', 'Mozambique': 'africa', 'Namibia': 'africa',
  'Niger': 'africa', 'Nigeria': 'africa', 'Rwanda': 'africa', 'São Tomé and Principe': 'africa',
  'Senegal': 'africa', 'Seychelles': 'africa', 'Sierra Leone': 'africa', 'Somalia': 'africa',
  'South Africa': 'africa', 'S. Sudan': 'africa', 'Sudan': 'africa', 'Swaziland': 'africa',
  'Tanzania': 'africa', 'Togo': 'africa', 'Tunisia': 'africa', 'Uganda': 'africa',
  'W. Sahara': 'africa', 'Zambia': 'africa', 'Zimbabwe': 'africa',

  // Asia
  'Afghanistan': 'asia', 'Armenia': 'asia', 'Azerbaijan': 'asia', 'Bahrain': 'asia',
  'Bangladesh': 'asia', 'Bhutan': 'asia', 'Brunei': 'asia', 'Cambodia': 'asia',
  'China': 'asia', 'Cyprus': 'asia', 'Georgia': 'asia', 'Hong Kong': 'asia',
  'India': 'asia', 'Indonesia': 'asia', 'Iran': 'asia', 'Iraq': 'asia', 'Israel': 'asia',
  'Japan': 'asia', 'Jordan': 'asia', 'Kazakhstan': 'asia', 'Kuwait': 'asia',
  'Kyrgyzstan': 'asia', 'Laos': 'asia', 'Lebanon': 'asia', 'Malaysia': 'asia',
  'Maldives': 'asia', 'Mongolia': 'asia', 'Myanmar': 'asia', 'Nepal': 'asia',
  'North Korea': 'asia', 'Oman': 'asia', 'Pakistan': 'asia', 'Palestine': 'asia',
  'Philippines': 'asia', 'Qatar': 'asia', 'Saudi Arabia': 'asia', 'Singapore': 'asia',
  'South Korea': 'asia', 'Sri Lanka': 'asia', 'Syria': 'asia', 'Taiwan': 'asia',
  'Tajikistan': 'asia', 'Thailand': 'asia', 'Timor-Leste': 'asia', 'Turkey': 'asia',
  'Turkmenistan': 'asia', 'United Arab Emirates': 'asia', 'Uzbekistan': 'asia',
  'Vietnam': 'asia', 'Yemen': 'asia',

  // Europe
  'Albania': 'europe', 'Andorra': 'europe', 'Austria': 'europe', 'Belarus': 'europe',
  'Belgium': 'europe', 'Bosnia and Herz.': 'europe', 'Bulgaria': 'europe', 'Croatia': 'europe',
  'Czech Rep.': 'europe', 'Denmark': 'europe', 'Estonia': 'europe', 'Finland': 'europe',
  'France': 'europe', 'Germany': 'europe', 'Greece': 'europe', 'Hungary': 'europe',
  'Iceland': 'europe', 'Ireland': 'europe', 'Italy': 'europe', 'Kosovo': 'europe',
  'Latvia': 'europe', 'Liechtenstein': 'europe', 'Lithuania': 'europe', 'Luxembourg': 'europe',
  'Macedonia': 'europe', 'Malta': 'europe', 'Moldova': 'europe', 'Monaco': 'europe',
  'Montenegro': 'europe', 'Netherlands': 'europe', 'Norway': 'europe', 'Poland': 'europe',
  'Portugal': 'europe', 'Romania': 'europe', 'Russia': 'europe', 'San Marino': 'europe',
  'Serbia': 'europe', 'Slovakia': 'europe', 'Slovenia': 'europe', 'Spain': 'europe',
  'Sweden': 'europe', 'Switzerland': 'europe', 'Ukraine': 'europe', 'United Kingdom': 'europe',
  'Vatican': 'europe',

  // North America
  'Antigua and Barb.': 'northAmerica', 'Bahamas': 'northAmerica', 'Barbados': 'northAmerica',
  'Belize': 'northAmerica', 'Canada': 'northAmerica', 'Costa Rica': 'northAmerica',
  'Cuba': 'northAmerica', 'Dominica': 'northAmerica', 'Dominican Rep.': 'northAmerica',
  'El Salvador': 'northAmerica', 'Grenada': 'northAmerica', 'Guatemala': 'northAmerica',
  'Haiti': 'northAmerica', 'Honduras': 'northAmerica', 'Jamaica': 'northAmerica',
  'Mexico': 'northAmerica', 'Nicaragua': 'northAmerica', 'Panama': 'northAmerica',
  'Puerto Rico': 'northAmerica', 'St. Kitts and Nevis': 'northAmerica', 'Saint Lucia': 'northAmerica',
  'St. Vin. and Gren.': 'northAmerica', 'Trinidad and Tobago': 'northAmerica',
  'United States': 'northAmerica', 'United States of America': 'northAmerica',

  // South America
  'Argentina': 'southAmerica', 'Bolivia': 'southAmerica', 'Brazil': 'southAmerica',
  'Chile': 'southAmerica', 'Colombia': 'southAmerica', 'Ecuador': 'southAmerica',
  'Falkland Is.': 'southAmerica', 'French Guiana': 'southAmerica', 'Guyana': 'southAmerica',
  'Paraguay': 'southAmerica', 'Peru': 'southAmerica', 'Suriname': 'southAmerica',
  'Uruguay': 'southAmerica', 'Venezuela': 'southAmerica',

  // Oceania
  'Australia': 'oceania', 'Fiji': 'oceania', 'Kiribati': 'oceania',
  'Marshall Is.': 'oceania', 'Micronesia': 'oceania', 'Nauru': 'oceania',
  'New Zealand': 'oceania', 'Palau': 'oceania', 'Papua New Guinea': 'oceania',
  'Samoa': 'oceania', 'Solomon Is.': 'oceania', 'Tonga': 'oceania',
  'Tuvalu': 'oceania', 'Vanuatu': 'oceania',
};

// Region data with TecEx-inspired teal-green gradient colors
export const REGIONS: Region[] = [
  {
    id: 'africa',
    name: 'Africa',
    color: '#0d9488', // teal-600
    hoverColor: '#0f766e', // teal-700
    description: 'Strategic logistics solutions across the African continent with local expertise and customs knowledge.',
    countries: [
      { name: 'South Africa', code: 'ZA', hasOffice: true },
      { name: 'Nigeria', code: 'NG', isPartner: true },
      { name: 'Kenya', code: 'KE', isPartner: true },
      { name: 'Egypt', code: 'EG', isPartner: true },
      { name: 'Morocco', code: 'MA', isPartner: true },
      { name: 'Ghana', code: 'GH', isPartner: true },
      { name: 'Ethiopia', code: 'ET', isPartner: true },
      { name: 'Tanzania', code: 'TZ', isPartner: true },
    ],
    stats: { markets: 54, partners: 25 },
  },
  {
    id: 'asia',
    name: 'Asia',
    color: '#14b8a6', // teal-500
    hoverColor: '#0d9488', // teal-600
    description: 'Comprehensive coverage across Asia with headquarters in Singapore and offices throughout the region.',
    countries: [
      { name: 'Singapore', code: 'SG', hasOffice: true },
      { name: 'India', code: 'IN', hasOffice: true },
      { name: 'Vietnam', code: 'VN', hasOffice: true },
      { name: 'Japan', code: 'JP', isPartner: true },
      { name: 'Philippines', code: 'PH', isPartner: true },
      { name: 'Hong Kong', code: 'HK', isPartner: true },
      { name: 'Thailand', code: 'TH', isPartner: true },
      { name: 'Malaysia', code: 'MY', isPartner: true },
      { name: 'China', code: 'CN', isPartner: true },
      { name: 'Indonesia', code: 'ID', isPartner: true },
      { name: 'South Korea', code: 'KR', isPartner: true },
      { name: 'Israel', code: 'IL', isPartner: true },
    ],
    stats: { markets: 48, partners: 85 },
  },
  {
    id: 'europe',
    name: 'Europe',
    color: '#2dd4bf', // teal-400
    hoverColor: '#14b8a6', // teal-500
    description: 'Pan-European logistics network with strategic hubs and customs expertise for seamless cross-border operations.',
    countries: [
      { name: 'Belgium', code: 'BE', hasOffice: true },
      { name: 'Germany', code: 'DE', isPartner: true },
      { name: 'Netherlands', code: 'NL', isPartner: true },
      { name: 'United Kingdom', code: 'GB', isPartner: true },
      { name: 'France', code: 'FR', isPartner: true },
      { name: 'Italy', code: 'IT', isPartner: true },
      { name: 'Spain', code: 'ES', isPartner: true },
      { name: 'Poland', code: 'PL', isPartner: true },
      { name: 'Switzerland', code: 'CH', isPartner: true },
    ],
    stats: { markets: 44, partners: 60 },
  },
  {
    id: 'northAmerica',
    name: 'North America',
    color: '#5eead4', // teal-300
    hoverColor: '#2dd4bf', // teal-400
    description: 'Full coverage across North America with integrated cross-border solutions for US, Canada, and Mexico.',
    countries: [
      { name: 'Canada', code: 'CA', isPartner: true },
      { name: 'United States', code: 'US', isPartner: true },
      { name: 'Mexico', code: 'MX', isPartner: true },
      { name: 'Panama', code: 'PA', isPartner: true },
      { name: 'Costa Rica', code: 'CR', isPartner: true },
    ],
    stats: { markets: 23, partners: 35 },
  },
  {
    id: 'southAmerica',
    name: 'South America',
    color: '#99f6e4', // teal-200
    hoverColor: '#5eead4', // teal-300
    description: 'Growing presence across South American markets with local partners and expertise in complex customs procedures.',
    countries: [
      { name: 'Brazil', code: 'BR', isPartner: true },
      { name: 'Argentina', code: 'AR', isPartner: true },
      { name: 'Chile', code: 'CL', isPartner: true },
      { name: 'Colombia', code: 'CO', isPartner: true },
      { name: 'Peru', code: 'PE', isPartner: true },
    ],
    stats: { markets: 12, partners: 20 },
  },
  {
    id: 'oceania',
    name: 'Oceania',
    color: '#ccfbf1', // teal-100
    hoverColor: '#99f6e4', // teal-200
    description: 'Reliable logistics solutions for Australia, New Zealand, and Pacific Island nations.',
    countries: [
      { name: 'Australia', code: 'AU', isPartner: true },
      { name: 'New Zealand', code: 'NZ', isPartner: true },
      { name: 'Fiji', code: 'FJ', isPartner: true },
    ],
    stats: { markets: 14, partners: 15 },
  },
];

// Office locations for markers
const OFFICE_LOCATIONS = [
  { name: 'Singapore', country: 'Singapore', type: 'HQ', coordinates: [103.8198, 1.3521] as [number, number] },
  { name: 'Bangalore', country: 'India', type: 'Office', coordinates: [77.5946, 12.9716] as [number, number] },
  { name: 'Ho Chi Minh', country: 'Vietnam', type: 'Office', coordinates: [106.6297, 10.8231] as [number, number] },
  { name: 'Cape Town', country: 'South Africa', type: 'Office', coordinates: [18.4241, -33.9249] as [number, number] },
  { name: 'Brussels', country: 'Belgium', type: 'Office', coordinates: [4.3517, 50.8503] as [number, number] },
  { name: 'Toronto', country: 'Canada', type: 'Partner', coordinates: [-79.3832, 43.6532] as [number, number] },
  { name: 'Tel Aviv', country: 'Israel', type: 'Partner', coordinates: [34.7818, 32.0853] as [number, number] },
  { name: 'Manila', country: 'Philippines', type: 'Partner', coordinates: [120.9842, 14.5995] as [number, number] },
  { name: 'Osaka', country: 'Japan', type: 'Partner', coordinates: [135.5023, 34.6937] as [number, number] },
  { name: 'Sydney', country: 'Australia', type: 'Partner', coordinates: [151.2093, -33.8688] as [number, number] },
];

interface InteractiveWorldMapProps {
  onRegionSelect?: (region: Region | null) => void;
  selectedRegion?: Region | null;
  showOfficeMarkers?: boolean;
  className?: string;
}

const InteractiveWorldMap: React.FC<InteractiveWorldMapProps> = ({
  onRegionSelect,
  selectedRegion,
  showOfficeMarkers = true,
  className = '',
}) => {
  const [hoveredCountry, setHoveredCountry] = useState<string | null>(null);
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  const getRegionForCountry = (countryName: string): Region | undefined => {
    const regionId = COUNTRY_REGIONS[countryName];
    return REGIONS.find(r => r.id === regionId);
  };

  const getCountryColor = (countryName: string): string => {
    const region = getRegionForCountry(countryName);
    if (!region) return '#E5E7EB'; // gray-200 for unmapped countries

    if (selectedRegion && selectedRegion.id === region.id) {
      return region.hoverColor;
    }

    if (hoveredRegion === region.id || hoveredCountry === countryName) {
      return region.hoverColor;
    }

    return region.color;
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    setTooltipPosition({ x: event.clientX, y: event.clientY });
  };

  const handleCountryClick = (countryName: string) => {
    const region = getRegionForCountry(countryName);
    if (region && onRegionSelect) {
      if (selectedRegion?.id === region.id) {
        onRegionSelect(null);
      } else {
        onRegionSelect(region);
      }
    }
  };

  const hoveredRegionData = useMemo(() => {
    if (hoveredCountry) {
      return getRegionForCountry(hoveredCountry);
    }
    return null;
  }, [hoveredCountry]);

  return (
    <div className={`relative ${className}`} onMouseMove={handleMouseMove}>
      {/* World Map */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl overflow-hidden shadow-2xl">
        <ComposableMap
          projectionConfig={{
            scale: 160,
            center: [0, 20],
          }}
          className="w-full"
          style={{
            width: '100%',
            height: 'auto',
            aspectRatio: '2/1',
          }}
        >
          <ZoomableGroup zoom={1}>
            <Geographies geography="https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json">
              {({ geographies }: { geographies: any[] }) =>
                geographies.map((geo: any) => {
                  const countryName = geo.properties.name;
                  const region = getRegionForCountry(countryName);

                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      fill={getCountryColor(countryName)}
                      stroke="#1e293b"
                      strokeWidth={0.5}
                      onMouseEnter={() => {
                        setHoveredCountry(countryName);
                        if (region) setHoveredRegion(region.id);
                      }}
                      onMouseLeave={() => {
                        setHoveredCountry(null);
                        setHoveredRegion(null);
                      }}
                      onClick={() => handleCountryClick(countryName)}
                      style={{
                        default: {
                          outline: 'none',
                          cursor: region ? 'pointer' : 'default',
                          transition: 'fill 0.2s ease',
                        },
                        hover: {
                          outline: 'none',
                          cursor: region ? 'pointer' : 'default',
                        },
                        pressed: {
                          outline: 'none',
                        },
                      }}
                    />
                  );
                })
              }
            </Geographies>

            {/* Office Markers */}
            {showOfficeMarkers && OFFICE_LOCATIONS.map((office, index) => (
              <Marker key={office.name} coordinates={office.coordinates}>
                <motion.g
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.5, delay: index * 0.05 }}
                >
                  {office.type === 'HQ' ? (
                    <>
                      <circle r={8} fill="#dc2626" stroke="#fff" strokeWidth={2} />
                      <circle r={4} fill="#fff" />
                      <motion.circle
                        r={12}
                        fill="none"
                        stroke="#dc2626"
                        strokeWidth={2}
                        initial={{ scale: 1, opacity: 0.8 }}
                        animate={{ scale: 1.5, opacity: 0 }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                    </>
                  ) : office.type === 'Office' ? (
                    <>
                      <circle r={5} fill="#2563eb" stroke="#fff" strokeWidth={1.5} />
                      <motion.circle
                        r={8}
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth={1}
                        initial={{ scale: 1, opacity: 0.6 }}
                        animate={{ scale: 1.3, opacity: 0 }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                    </>
                  ) : (
                    <circle r={4} fill="#059669" stroke="#fff" strokeWidth={1} />
                  )}
                </motion.g>
              </Marker>
            ))}
          </ZoomableGroup>
        </ComposableMap>
      </div>

      {/* Hover Tooltip */}
      <AnimatePresence>
        {hoveredCountry && hoveredRegionData && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="fixed z-50 bg-white rounded-lg shadow-xl p-3 pointer-events-none"
            style={{
              left: tooltipPosition.x + 15,
              top: tooltipPosition.y + 15,
            }}
          >
            <div className="text-sm font-semibold text-gray-900">{hoveredCountry}</div>
            <div className="text-xs text-gray-500">{hoveredRegionData.name} Region</div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-4 max-w-xs">
        <div className="text-xs font-semibold text-gray-700 mb-3 uppercase tracking-wider">Legend</div>
        <div className="grid grid-cols-2 gap-2">
          {REGIONS.map((region) => (
            <button
              key={region.id}
              onClick={() => onRegionSelect?.(selectedRegion?.id === region.id ? null : region)}
              className={`flex items-center space-x-2 p-1.5 rounded-lg transition-all ${
                selectedRegion?.id === region.id
                  ? 'bg-gray-100 ring-2 ring-teal-500'
                  : 'hover:bg-gray-50'
              }`}
            >
              <div
                className="w-3 h-3 rounded-sm flex-shrink-0"
                style={{ backgroundColor: region.color }}
              />
              <span className="text-xs text-gray-700 truncate">{region.name}</span>
            </button>
          ))}
        </div>
        <div className="mt-3 pt-3 border-t border-gray-200 space-y-1.5">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-600" />
            <span className="text-xs text-gray-600">Headquarters</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-blue-600" />
            <span className="text-xs text-gray-600">Regional Office</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-emerald-600" />
            <span className="text-xs text-gray-600">Partner Facility</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InteractiveWorldMap;
export { COUNTRY_REGIONS, OFFICE_LOCATIONS };
