import React from 'react';
import { motion } from 'framer-motion';
import { DocumentCheckIcon, ShieldCheckIcon, ScaleIcon, ClipboardDocumentCheckIcon, ExclamationTriangleIcon, AcademicCapIcon } from '@heroicons/react/24/outline';

const Compliance: React.FC = () => {
  const services = [
    {
      title: 'Import Licenses',
      description: 'Comprehensive import licensing services ensuring compliance with local regulations.',
      features: ['License Applications', 'Renewal Management', 'Regulatory Updates', 'Compliance Monitoring']
    },
    {
      title: 'Trade Compliance',
      description: 'Expert guidance on international trade compliance and regulatory requirements.',
      features: ['Trade Agreement Analysis', 'Tariff Classification', 'Origin Determination', 'Preferential Treatment']
    },
    {
      title: 'Documentation',
      description: 'Complete documentation services for import/export compliance and audit readiness.',
      features: ['Document Preparation', 'Record Keeping', 'Audit Support', 'Digital Archives']
    },
    {
      title: 'Regulatory Support',
      description: 'Ongoing regulatory support and updates to ensure continuous compliance.',
      features: ['Regulatory Monitoring', 'Policy Updates', 'Training Programs', 'Compliance Audits']
    }
  ];

  const complianceAreas = [
    {
      icon: ScaleIcon,
      title: 'Customs Regulations',
      description: 'Navigate complex customs regulations across multiple jurisdictions.',
      details: ['Customs Valuation', 'Classification Systems', 'Rules of Origin', 'Duty Optimization']
    },
    {
      icon: ShieldCheckIcon,
      title: 'Security Compliance',
      description: 'Ensure compliance with international security and safety standards.',
      details: ['C-TPAT Certification', 'AEO Programs', 'Security Assessments', 'Supply Chain Security']
    },
    {
      icon: DocumentCheckIcon,
      title: 'Product Compliance',
      description: 'Verify product compliance with destination country requirements.',
      details: ['Product Certifications', 'Testing Requirements', 'Labeling Standards', 'Safety Regulations']
    },
    {
      icon: ExclamationTriangleIcon,
      title: 'Sanctions & Restrictions',
      description: 'Navigate trade sanctions and export control regulations.',
      details: ['Denied Party Screening', 'Export Controls', 'Sanctions Compliance', 'License Requirements']
    }
  ];

  const industries = [
    {
      name: 'Electronics & Technology',
      regulations: ['FCC Compliance', 'CE Marking', 'RoHS Directive', 'WEEE Compliance'],
      icon: '💻'
    },
    {
      name: 'Pharmaceuticals',
      regulations: ['FDA Approval', 'GMP Standards', 'Drug Registration', 'Import Permits'],
      icon: '💊'
    },
    {
      name: 'Automotive',
      regulations: ['DOT Standards', 'EPA Compliance', 'FMVSS Requirements', 'Type Approval'],
      icon: '🚗'
    },
    {
      name: 'Food & Beverage',
      regulations: ['FDA Registration', 'HACCP Compliance', 'Nutritional Labeling', 'Import Permits'],
      icon: '🍎'
    },
    {
      name: 'Chemicals',
      regulations: ['REACH Compliance', 'SDS Requirements', 'Hazmat Regulations', 'Chemical Registration'],
      icon: '⚗️'
    },
    {
      name: 'Textiles',
      regulations: ['Textile Labeling', 'Flammability Standards', 'Country of Origin', 'Quota Management'],
      icon: '👕'
    }
  ];

  return (
    <div className="pt-16">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 py-20 relative overflow-hidden">
        {/* Background Elements */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-cyan-600/20"></div>
          
          {/* Compliance icons */}
          <div className="absolute top-20 left-20 opacity-10">
            <ShieldCheckIcon className="w-24 h-24 text-white" />
          </div>
          <div className="absolute bottom-20 right-20 opacity-10">
            <ScaleIcon className="w-20 h-20 text-white" />
          </div>
          
          {/* Regulatory network lines */}
          <div className="absolute inset-0 opacity-20">
            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <path d="M20 30 Q40 20 60 40 T90 35" stroke="#06b6d4" strokeWidth="0.5" fill="none">
                <animate attributeName="stroke-dasharray" values="0,100;50,50;100,0;0,100" dur="8s" repeatCount="indefinite"/>
              </path>
              <path d="M10 70 Q30 50 50 60 T85 65" stroke="#3b82f6" strokeWidth="0.5" fill="none">
                <animate attributeName="stroke-dasharray" values="100,0;50,50;0,100;100,0" dur="6s" repeatCount="indefinite"/>
              </path>
            </svg>
          </div>
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-5xl font-heading font-bold text-white mb-6">
              Compliance Services
            </h1>
            <p className="text-xl text-gray-200 max-w-3xl mx-auto">
              Comprehensive regulatory compliance and documentation services for international trade
            </p>
          </motion.div>
        </div>
      </section>

      {/* Services Grid */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
              Comprehensive Compliance Solutions
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Navigate complex regulatory landscapes with confidence and expertise
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
                className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100 hover:shadow-xl transition-shadow duration-300"
              >
                <h3 className="text-2xl font-semibold text-gray-900 mb-4">{service.title}</h3>
                <p className="text-gray-600 mb-6">{service.description}</p>
                
                <div className="space-y-2">
                  {service.features.map((feature, featureIndex) => (
                    <div key={featureIndex} className="flex items-center text-sm">
                      <div className="w-2 h-2 rounded-full bg-primary-600 mr-3"></div>
                      <span className="text-gray-700">{feature}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Compliance Areas */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
              Key Compliance Areas
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Expert guidance across all major compliance domains
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {complianceAreas.map((area, index) => (
              <motion.div
                key={area.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-white rounded-2xl p-8 shadow-lg"
              >
                <div className="flex items-start space-x-4">
                  <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <area.icon className="h-6 w-6 text-primary-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">{area.title}</h3>
                    <p className="text-gray-600 mb-4">{area.description}</p>
                    <div className="grid grid-cols-2 gap-2">
                      {area.details.map((detail, detailIndex) => (
                        <div key={detailIndex} className="flex items-center text-sm">
                          <div className="w-1.5 h-1.5 rounded-full bg-primary-600 mr-2"></div>
                          <span className="text-gray-700">{detail}</span>
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

      {/* Industry Expertise */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
              Industry-Specific Expertise
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Specialized compliance knowledge across diverse industries
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {industries.map((industry, index) => (
              <motion.div
                key={industry.name}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-gray-50 rounded-xl p-6 text-center hover:shadow-lg transition-shadow duration-300"
              >
                <div className="text-4xl mb-3">{industry.icon}</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">{industry.name}</h3>
                <div className="space-y-1">
                  {industry.regulations.map((regulation, regIndex) => (
                    <div key={regIndex} className="text-sm text-gray-600">
                      {regulation}
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Compliance Process */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">
              Our Compliance Process
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Systematic approach to ensure comprehensive compliance management
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { step: '01', title: 'Assessment', description: 'Comprehensive compliance assessment and gap analysis', icon: ClipboardDocumentCheckIcon },
              { step: '02', title: 'Planning', description: 'Develop customized compliance strategy and roadmap', icon: DocumentCheckIcon },
              { step: '03', title: 'Implementation', description: 'Execute compliance measures and documentation', icon: ShieldCheckIcon },
              { step: '04', title: 'Monitoring', description: 'Ongoing monitoring and continuous improvement', icon: AcademicCapIcon }
            ].map((process, index) => (
              <motion.div
                key={process.step}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.2 }}
                className="text-center bg-white rounded-xl p-6 shadow-lg"
              >
                <div className="w-16 h-16 bg-primary-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                  {process.step}
                </div>
                <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                  <process.icon className="h-6 w-6 text-primary-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{process.title}</h3>
                <p className="text-gray-600 text-sm">{process.description}</p>
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
              Ensure Complete Compliance
            </h2>
            <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
              Let our compliance experts navigate the regulatory complexities for you.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-white text-primary-600 px-8 py-4 rounded-xl font-semibold text-lg hover:bg-gray-50 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Get Compliance Assessment
            </motion.button>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default Compliance;