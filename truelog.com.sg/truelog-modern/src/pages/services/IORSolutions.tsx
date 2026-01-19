import React from 'react';
import { motion } from 'framer-motion';
import { DocumentTextIcon, GlobeAltIcon, ShieldCheckIcon, ClockIcon, BanknotesIcon, ScaleIcon, CogIcon } from '@heroicons/react/24/outline';

const IORSolutions: React.FC = () => {
  const responsibilities = [
    {
      title: 'Customs classification & HS codes',
      description: 'We ensure your goods are correctly classified according to the Harmonized System, which determines duty rates and import treatment.',
      icon: DocumentTextIcon
    },
    {
      title: 'Document preparation & submission',
      description: 'We prepare and file all required documents: commercial invoices, packing lists, bills of lading, power of attorney, import permits, and any country‑specific forms.',
      icon: DocumentTextIcon
    },
    {
      title: 'Duties, taxes & fees management',
      description: 'We calculate, declare, and pay import duties, VAT/GST, and other applicable charges on your behalf.',
      icon: BanknotesIcon
    },
    {
      title: 'Licences & regulatory compliance',
      description: 'For controlled goods (e.g. telecom devices, dual‑use equipment), we manage necessary import permits, certifications, and adherence to local regulations.',
      icon: ShieldCheckIcon
    },
    {
      title: 'Liability & risk management',
      description: 'As IOR, we shoulder legal responsibility during the import process. If customs flags noncompliance, Truelog handles resolution — we don\'t punt the risk back to you.',
      icon: ScaleIcon
    }
  ];

  const qualifications = [
    'Be a local, registered entity in the destination country.',
    'Hold the necessary licenses or authorisations to import goods there.',
    'Be willing to assume legal liability and manage compliance risks.'
  ];

  const roles = [
    {
      title: 'Consignee',
      description: 'The party designated to receive the goods. Once customs formalities complete, the consignee becomes legal owner.'
    },
    {
      title: 'Exporter / Exporter of Record (EOR)',
      description: 'The legal exporting party in the origin country. The EOR ensures export compliance; the IOR ensures import compliance.'
    },
    {
      title: 'Customs broker / freight forwarder',
      description: 'These act as agents in clearing goods through customs, but are not automatically IORs unless explicitly appointed and licensed to assume that role.'
    }
  ];

  const advantages = [
    {
      icon: ClockIcon,
      title: 'Speed and reliability',
      description: 'First‑time customs clearance becomes far less risky, helping your schedule stay on track.'
    },
    {
      icon: GlobeAltIcon,
      title: 'Local compliance expertise',
      description: 'We stay current with regulations, so you don\'t need in‑house staff versed in every country\'s laws.'
    },
    {
      icon: ShieldCheckIcon,
      title: 'Risk mitigation',
      description: 'We assume the legal burden — mistakes in classification or omissions can lead to fines, seizure, or customs delays.'
    },
    {
      icon: CogIcon,
      title: 'Simplified logistics',
      description: 'You avoid forming local entities or navigating foreign registration. You focus on your core business; we handle regulatory duties.'
    }
  ];

  const useCases = [
    'You\'re shipping IT hardware to countries where you have no legal entity.',
    'You\'re rolling out global datacentre infrastructure or telecom networks.',
    'You prefer to outsource regulatory complexity rather than manage it internally.',
    'You want to mitigate risk of customs delays or compliance missteps when expanding into new markets.'
  ];

  const faqs = [
    {
      question: 'Does the IOR own the goods?',
      answer: 'Only during the import clearance process. Once customs duties are settled, ownership typically transfers to the consignee.'
    },
    {
      question: 'Can a freight forwarder act as IOR?',
      answer: 'Only if they hold local registration and accept legal liability. Many forwarders decline that role — always check.'
    },
    {
      question: 'Under DDP (Delivered Duty Paid), who is IOR?',
      answer: 'Under a DDP arrangement, the seller or vendor often takes on IOR responsibilities, handling all import obligations before handed to the buyer.'
    },
    {
      question: 'Can I be my own IOR?',
      answer: 'Yes, if you have local registration, licensing, and compliance capability in the destination country. But for most vendors expanding globally, outsourcing is far more cost‑effective.'
    }
  ];

  const whyTruelog = [
    'You avoid the time, cost, and complexity of local entity setup.',
    'You reduce compliance risk with a partner who understands IT hardware regulations.',
    'You gain access to global scale — one trusted point of contact for many markets.'
  ];

  return (
    <div className="pt-16">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 py-20 relative overflow-hidden">
        {/* Background Elements */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-cyan-600/20"></div>

          {/* Document icons */}
          <div className="absolute top-20 left-20 opacity-10">
            <DocumentTextIcon className="w-24 h-24 text-white" />
          </div>
          <div className="absolute bottom-20 right-20 opacity-10">
            <ScaleIcon className="w-20 h-20 text-white" />
          </div>

          {/* Global network lines */}
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
              What Is an Importer of Record (IOR)?
            </h1>
            <p className="text-xl text-gray-200 max-w-4xl mx-auto">
              When IT equipment, servers or infrastructure cross borders, there's more involved than just booking a freight lane. Every country enforces customs law, duty regimes, import licensing, and regulatory compliance. The Importer of Record (IOR) is the legal entity responsible for ensuring all import formalities are fulfilled — and that goods enter the country legally and on time.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Introduction */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-12"
          >
            <p className="text-lg text-gray-700 max-w-4xl mx-auto">
              As your trusted partner, Truelog offers IOR services in global markets so you don't need local entities or to navigate unfamiliar regulations yourself.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Key Responsibilities */}
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
              Key Responsibilities of the IOR
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              When Truelog acts as your IOR, we take charge of:
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {responsibilities.map((responsibility, index) => (
              <motion.div
                key={responsibility.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100 hover:shadow-xl transition-shadow duration-300"
              >
                <div className="w-16 h-16 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-6">
                  <responsibility.icon className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4 text-center">{responsibility.title}</h3>
                <p className="text-gray-600 text-center">{responsibility.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Who Can Be IOR */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <h2 className="text-4xl font-heading font-bold text-gray-900 mb-6">
                Who Can Be an Importer of Record?
              </h2>
              <p className="text-lg text-gray-600 mb-6">
                Not every logistics provider or freight forwarder qualifies to act as IOR. To be legally recognised as an IOR, an entity must:
              </p>
              <div className="space-y-4">
                {qualifications.map((qualification, index) => (
                  <div key={index} className="flex items-start space-x-3">
                    <div className="w-6 h-6 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-white text-xs font-bold">✓</span>
                    </div>
                    <p className="text-gray-700">{qualification}</p>
                  </div>
                ))}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="bg-gray-50 rounded-2xl p-8"
            >
              <p className="text-gray-700 mb-6">
                In many cases, companies don't want (or can't) set up their own local branches in every market. That's where Truelog steps in — we already hold registrations and licences in the jurisdictions where we operate.
              </p>
              <p className="text-gray-700">
                If your consignee (the receiving party) already has local registration, they may act as IOR. But often, vendors or end customers prefer outsourcing that function to a trusted third party — freeing them from regulatory burden.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* How IOR Relates to Other Roles */}
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
              How IOR Relates to Other Roles
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              It's helpful to see IOR in context with other key supply‑chain actors:
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
            {roles.map((role, index) => (
              <motion.div
                key={role.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-white rounded-2xl p-8 shadow-lg text-center"
              >
                <h3 className="text-2xl font-semibold text-gray-900 mb-4">{role.title}</h3>
                <p className="text-gray-600">{role.description}</p>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="bg-primary-50 rounded-2xl p-8 text-center"
          >
            <p className="text-lg font-semibold text-primary-800">
              In short: IOR = legal responsibility for import compliance; broker/forwarder = operational agent.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Why Use Third-Party IOR */}
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
              Why Use a Third‑Party IOR?
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Working with a specialist IOR provider like Truelog delivers several advantages:
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {advantages.map((advantage, index) => (
              <motion.div
                key={advantage.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="text-center bg-gray-50 rounded-xl p-6"
              >
                <div className="w-16 h-16 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <advantage.icon className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{advantage.title}</h3>
                <p className="text-gray-600">{advantage.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Typical Use Cases */}
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
              Typical Use Cases
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Truelog's IOR service is ideal when:
            </p>
          </motion.div>

          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {useCases.map((useCase, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.8, delay: index * 0.1 }}
                  className="flex items-start space-x-3 bg-white rounded-xl p-6 shadow-lg"
                >
                  <div className="w-6 h-6 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-white text-xs font-bold">✓</span>
                  </div>
                  <p className="text-gray-700">{useCase}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* FAQs */}
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
              Frequently Asked Questions (FAQs)
            </h2>
          </motion.div>

          <div className="max-w-4xl mx-auto space-y-6">
            {faqs.map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                className="bg-gray-50 rounded-2xl p-8"
              >
                <h3 className="text-xl font-semibold text-gray-900 mb-4">{faq.question}</h3>
                <p className="text-gray-700">{faq.answer}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Truelog */}
      <section className="py-20 bg-primary-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-heading font-bold text-white mb-6">
              Why Truelog as Your IOR?
            </h2>
            <p className="text-xl text-primary-100 max-w-4xl mx-auto mb-8">
              At Truelog, we specialise in IT, telecom and datacentre logistics. We already hold import licences in key global markets, and deal daily with technology goods requiring special permits, certifications, or dual‑use controls.
            </p>
          </motion.div>

          <div className="max-w-4xl mx-auto">
            <div className="bg-white/10 rounded-2xl p-8 mb-8">
              <p className="text-primary-100 text-lg mb-6 text-center">
                By appointing Truelog as your IOR:
              </p>
              <div className="space-y-4">
                {whyTruelog.map((reason, index) => (
                  <div key={index} className="flex items-start space-x-3">
                    <div className="w-6 h-6 bg-white rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-primary-600 text-xs font-bold">✓</span>
                    </div>
                    <p className="text-primary-100">{reason}</p>
                  </div>
                ))}
              </div>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center"
            >
              <p className="text-xl text-primary-100 mb-8">
                Let us carry the regulatory burden so you can focus on growth, deployment, and service.
              </p>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-white text-primary-600 px-8 py-4 rounded-xl font-semibold text-lg hover:bg-gray-50 transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                Get IOR Quote
              </motion.button>
            </motion.div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default IORSolutions;