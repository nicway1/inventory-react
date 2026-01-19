import React from 'react';
import { motion } from 'framer-motion';

const Resources: React.FC = () => {
  return (
    <div className="pt-16">
      <section className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-5xl font-heading font-bold text-white mb-6">
              Resources
            </h1>
            <p className="text-xl text-gray-200 max-w-3xl mx-auto">
              Documentation, guides, and helpful resources for your logistics needs
            </p>
          </motion.div>
        </div>
      </section>

      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-4xl font-heading font-bold text-gray-900 mb-8">
              Coming Soon
            </h2>
            <p className="text-xl text-gray-600">
              This page is under construction. Please check back soon for helpful resources, documentation, and guides.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Resources;