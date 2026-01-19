import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CalendarIcon, EyeIcon, ArrowRightIcon } from '@heroicons/react/24/outline';

interface BlogPost {
  id: number;
  title: string;
  slug: string;
  excerpt: string;
  featured_image: string | null;
  author: string;
  published_at: string;
  view_count: number;
}

const Blog: React.FC = () => {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://www.truelog.site';

  useEffect(() => {
    fetchPosts();
  }, [page, searchTerm]);

  const fetchPosts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: '9',
        ...(searchTerm && { search: searchTerm })
      });

      const response = await fetch(`${API_BASE_URL}/api/blog/posts?${params}`);
      const data = await response.json();

      if (data.success) {
        setPosts(data.posts);
        setTotalPages(data.total_pages);
      } else {
        setError(data.error || 'Failed to fetch posts');
      }
    } catch (err) {
      setError('Unable to connect to blog service');
      console.error('Blog fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 via-white to-gray-50 dark:from-secondary-900 dark:via-secondary-800 dark:to-secondary-900">
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 dark:text-white mb-6"
          >
            Industry <span className="text-primary-600 dark:text-primary-400">Insights</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-xl text-gray-600 dark:text-secondary-300 max-w-3xl mx-auto mb-8"
          >
            Stay updated with the latest logistics industry news, expert insights, and supply chain trends from TrueLog.
          </motion.p>

          {/* Search Bar */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="max-w-xl mx-auto"
          >
            <div className="relative">
              <input
                type="text"
                placeholder="Search articles..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setPage(1);
                }}
                className="w-full px-6 py-4 rounded-2xl bg-gray-100 dark:bg-white/10 backdrop-blur-sm border border-gray-300 dark:border-white/20 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all duration-300"
              />
              <svg
                className="absolute right-5 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-white/50"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Blog Posts Grid */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="bg-gray-200 dark:bg-white/10 rounded-2xl h-48 mb-4"></div>
                  <div className="bg-gray-200 dark:bg-white/10 rounded h-6 w-3/4 mb-2"></div>
                  <div className="bg-gray-200 dark:bg-white/10 rounded h-4 w-1/2"></div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="text-center py-20">
              <p className="text-gray-600 dark:text-secondary-400 text-lg">{error}</p>
              <button
                onClick={fetchPosts}
                className="mt-4 px-6 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-500 transition-colors"
              >
                Try Again
              </button>
            </div>
          ) : posts.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-gray-600 dark:text-secondary-400 text-lg">No blog posts found.</p>
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="mt-4 px-6 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-500 transition-colors"
                >
                  Clear Search
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {posts.map((post, index) => (
                  <motion.article
                    key={post.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    className="group"
                  >
                    <Link to={`/blog/${post.slug}`} className="block">
                      <div className="bg-white dark:bg-white/5 backdrop-blur-sm rounded-2xl overflow-hidden border border-gray-200 dark:border-white/10 hover:border-primary-500/50 transition-all duration-300 hover:shadow-xl hover:shadow-primary-500/10 shadow-lg">
                        {/* Featured Image */}
                        <div className="relative h-48 overflow-hidden bg-gradient-to-br from-primary-600/20 to-accent-cyan/20">
                          {post.featured_image ? (
                            <img
                              src={post.featured_image}
                              alt={post.title}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <svg className="w-16 h-16 text-gray-300 dark:text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                              </svg>
                            </div>
                          )}
                        </div>

                        {/* Content */}
                        <div className="p-6">
                          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors line-clamp-2">
                            {post.title}
                          </h3>
                          <p className="text-gray-600 dark:text-secondary-400 text-sm mb-4 line-clamp-3">
                            {post.excerpt}
                          </p>

                          {/* Meta */}
                          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-secondary-500">
                            <div className="flex items-center gap-4">
                              <span className="flex items-center gap-1">
                                <CalendarIcon className="w-4 h-4" />
                                {post.published_at ? formatDate(post.published_at) : 'Draft'}
                              </span>
                              <span className="flex items-center gap-1">
                                <EyeIcon className="w-4 h-4" />
                                {post.view_count}
                              </span>
                            </div>
                            <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                          </div>
                        </div>
                      </div>
                    </Link>
                  </motion.article>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center items-center gap-2 mt-12">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-4 py-2 rounded-xl bg-gray-200 dark:bg-white/10 text-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300 dark:hover:bg-white/20 transition-colors"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 text-gray-600 dark:text-secondary-400">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-4 py-2 rounded-xl bg-gray-200 dark:bg-white/10 text-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300 dark:hover:bg-white/20 transition-colors"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </section>
    </div>
  );
};

export default Blog;
